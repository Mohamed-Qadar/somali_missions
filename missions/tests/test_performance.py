from django.core.cache import cache
from django.db import connection
from django.test import Client, TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from missions.models import Complaint, EmbassyResponse, Mission


class QueryCountRegressionTests(TestCase):
    """Lock in the N+1 fixes so they can't silently regress."""

    def test_mission_detail_responses_are_prefetched(self):
        mission = Mission.objects.create(name='M', country='C', city='Ct')
        for i in range(6):
            complaint = Complaint.objects.create(mission=mission, subject=f's{i}', message='x', rating=3)
            EmbassyResponse.objects.create(complaint=complaint, responder_name='off', message='r', is_public=True)

        with CaptureQueriesContext(connection) as ctx:
            response = Client().get(reverse('mission_detail', args=[mission.pk]))
        self.assertEqual(response.status_code, 200)
        # has_public_response/public_responses read the prefetched cache, so the
        # responses table is hit once total - not once per complaint.
        response_queries = [q for q in ctx.captured_queries if 'embassyresponse' in q['sql'].lower()]
        self.assertLessEqual(len(response_queries), 1, response_queries)

    def test_transparency_satisfaction_is_one_aggregate(self):
        for i in range(8):
            m = Mission.objects.create(name=f'M{i}', country='C', city=f'Ct{i}')
            Complaint.objects.create(mission=m, subject='s', message='x', rating=4, satisfaction_rating=4)
        cache.clear()  # transparency caches its context; force a fresh DB pass

        with CaptureQueriesContext(connection) as ctx:
            response = Client().get(reverse('transparency'))
        self.assertEqual(response.status_code, 200)
        # Satisfaction averages come from ONE grouped aggregate, not one AVG()
        # query per mission (which would be 8 here before the fix).
        agg_queries = [
            q for q in ctx.captured_queries
            if 'avg(' in q['sql'].lower() and 'satisfaction_rating' in q['sql'].lower()
        ]
        self.assertEqual(len(agg_queries), 1, agg_queries)
