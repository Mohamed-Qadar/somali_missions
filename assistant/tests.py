from django.test import Client, TestCase
from django.urls import reverse

from .models import AssistantConversationLog, AssistantTopic
from .providers import RuleBasedAnswerProvider, get_answer_provider


class RuleBasedAnswerProviderTests(TestCase):
    def setUp(self):
        AssistantTopic.objects.create(
            topic_key=AssistantTopic.TopicKey.PASSPORT_RENEWAL,
            title='Passport Renewal',
            keywords='passport, renew, renewal',
            answer='Renewal answer.',
            suggested_action=AssistantTopic.SuggestedAction.BOOK_APPOINTMENT,
        )
        AssistantTopic.objects.create(
            topic_key=AssistantTopic.TopicKey.LOST_PASSPORT,
            title='Lost Passport',
            keywords='lost passport, stolen passport',
            answer='Lost passport answer.',
            suggested_action=AssistantTopic.SuggestedAction.BOOK_APPOINTMENT,
        )

    def test_more_specific_phrase_wins_over_generic_keyword(self):
        # Regression test: "I lost my passport" must match Lost Passport, not
        # the generic Passport Renewal topic just because "passport" alone
        # is one of its keywords too.
        provider = RuleBasedAnswerProvider()
        answer = provider.answer('I lost my passport in London, what should I do?')
        self.assertEqual(answer.topic_key, AssistantTopic.TopicKey.LOST_PASSPORT)

    def test_generic_keyword_still_matches_when_nothing_more_specific(self):
        provider = RuleBasedAnswerProvider()
        answer = provider.answer('How do I renew my passport?')
        self.assertEqual(answer.topic_key, AssistantTopic.TopicKey.PASSPORT_RENEWAL)

    def test_no_match_returns_fallback(self):
        provider = RuleBasedAnswerProvider()
        answer = provider.answer('asdkjaslkdjaslkdj random gibberish text')
        self.assertIsNone(answer.topic_key)
        self.assertEqual(answer.confidence, 0.0)

    def test_get_answer_provider_returns_rule_based_by_default(self):
        provider = get_answer_provider()
        self.assertIsInstance(provider, RuleBasedAnswerProvider)


class AskAssistantViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        AssistantTopic.objects.create(
            topic_key=AssistantTopic.TopicKey.OFFICE_HOURS,
            title='Office Hours',
            keywords='office hours, opening hours',
            answer='Mon-Fri 9-4.',
            suggested_action=AssistantTopic.SuggestedAction.VIEW_REQUIREMENTS,
        )

    def test_ask_page_loads(self):
        response = self.client.get(reverse('ask_assistant'))
        self.assertEqual(response.status_code, 200)

    def test_asking_a_question_logs_it_and_shows_answer(self):
        response = self.client.post(reverse('ask_assistant'), {'question': 'What are your office hours?'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Mon-Fri 9-4.')
        self.assertEqual(AssistantConversationLog.objects.count(), 1)
        log = AssistantConversationLog.objects.first()
        self.assertEqual(log.matched_topic.topic_key, AssistantTopic.TopicKey.OFFICE_HOURS)
