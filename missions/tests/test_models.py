from django.test import TestCase

from missions.models import Complaint, EscalationLog, Mission
from missions.utils.sentiment import compute_sentiment


class ComplaintModelTests(TestCase):
    def setUp(self):
        self.mission = Mission.objects.create(name='Test Embassy', country='Test', city='Test')

    def test_tracking_code_generated_on_save(self):
        c1 = Complaint.objects.create(
            mission=self.mission, subject='A', message='Test message here', rating=4,
        )
        c2 = Complaint.objects.create(
            mission=self.mission, subject='B', message='Another test message', rating=2,
        )
        self.assertEqual(len(c1.tracking_code), 8)
        self.assertEqual(len(c2.tracking_code), 8)
        self.assertNotEqual(c1.tracking_code, c2.tracking_code)

    def test_anonymous_clears_pii(self):
        complaint = Complaint(
            mission=self.mission,
            subject='Anon',
            message='Anonymous complaint text',
            rating=3,
            full_name='John',
            email='john@example.com',
            phone='+1234567890',
            is_anonymous=True,
        )
        complaint.save()
        self.assertEqual(complaint.full_name, '')
        self.assertEqual(complaint.email, '')
        self.assertEqual(complaint.phone, '')

    def test_hardship_factors_make_complaint_critical(self):
        complaint = Complaint.objects.create(
            mission=self.mission,
            subject='Stranded after long travel',
            message='I am at the consulate and have no accommodation.',
            rating=2,
            currently_at_mission=True,
            travelled_from_another_city=True,
            no_accommodation=True,
        )
        complaint.refresh_priority_from_rules()

        self.assertEqual(complaint.priority, Complaint.Priority.CRITICAL)
        self.assertIn('no accommodation', complaint.critical_reason)

    def test_manual_escalation_log_records_target_role(self):
        complaint = Complaint.objects.create(
            mission=self.mission,
            subject='Emergency',
            message='Urgent assistance required.',
            rating=1,
            category=Complaint.Category.EMERGENCY,
        )
        log = EscalationLog.objects.create(
            complaint=complaint,
            target_role='MINISTRY_REVIEWER',
            message='Manual escalation requested.',
        )

        self.assertEqual(log.complaint, complaint)
        self.assertEqual(log.target_role, 'MINISTRY_REVIEWER')


class SentimentTests(TestCase):
    def test_sentiment_from_rating(self):
        self.assertEqual(compute_sentiment(5, 'Good service'), Complaint.Sentiment.POSITIVE)
        self.assertEqual(compute_sentiment(3, 'OK'), Complaint.Sentiment.NEUTRAL)
        self.assertEqual(compute_sentiment(1, 'Bad'), Complaint.Sentiment.NEGATIVE)
        self.assertEqual(compute_sentiment(5, ''), Complaint.Sentiment.UNKNOWN)
