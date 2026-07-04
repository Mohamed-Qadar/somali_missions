"""
Pluggable answer-provider architecture for the Smart Citizen Assistant.

No AI model is implemented here - this defines the contract a future
AI-backed provider must satisfy, plus one working implementation
(RuleBasedAnswerProvider) that matches a question against
AssistantTopic keywords. Swapping in a real AI backend later only
requires implementing AnswerProvider and pointing
settings.ASSISTANT_PROVIDER at it - no caller-facing code changes.
"""
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from django.conf import settings

from .models import AssistantTopic


@dataclass
class AssistantAnswer:
    topic_key: Optional[str]
    title: str
    answer_text: str
    suggested_action: str
    confidence: float


class AnswerProvider(ABC):
    @abstractmethod
    def answer(self, question: str) -> AssistantAnswer:
        """Return the best-matching answer for a free-text citizen question."""
        raise NotImplementedError


class RuleBasedAnswerProvider(AnswerProvider):
    """Matches a question against AssistantTopic keyword lists. No ML involved."""

    FALLBACK_ANSWER = AssistantAnswer(
        topic_key=None,
        title='No match',
        answer_text=(
            "I couldn't find a specific answer to that. Please try rephrasing, "
            "browse the Before You Travel page for document requirements, or "
            "contact the mission directly."
        ),
        suggested_action=AssistantTopic.SuggestedAction.VIEW_REQUIREMENTS,
        confidence=0.0,
    )

    def answer(self, question: str) -> AssistantAnswer:
        # Whole-word matching, not substring matching: "lost passport" must not
        # lose to the bare word "passport" just because it's a shorter keyword
        # that happens to appear anywhere in the sentence. A keyword phrase only
        # counts if every one of its words appears in the question, and longer
        # (more specific) phrase matches are scored higher.
        question_words = set(re.findall(r"[a-z']+", question.lower()))
        best_topic = None
        best_score = 0

        for topic in AssistantTopic.objects.filter(is_active=True):
            score = 0
            for kw in topic.keyword_list():
                kw_words = kw.split()
                if kw_words and all(w in question_words for w in kw_words):
                    score += len(kw_words)
            if score > best_score:
                best_score = score
                best_topic = topic

        if not best_topic or best_score == 0:
            return self.FALLBACK_ANSWER

        confidence = min(1.0, best_score / 3)
        return AssistantAnswer(
            topic_key=best_topic.topic_key,
            title=best_topic.title,
            answer_text=best_topic.answer,
            suggested_action=best_topic.suggested_action,
            confidence=confidence,
        )


def get_answer_provider() -> AnswerProvider:
    provider_name = getattr(settings, 'ASSISTANT_PROVIDER', 'rule_based')
    if provider_name == 'rule_based':
        return RuleBasedAnswerProvider()
    raise NotImplementedError(
        f"Assistant provider '{provider_name}' is not implemented. "
        "Set settings.ASSISTANT_PROVIDER = 'rule_based' or implement a new "
        "AnswerProvider subclass and register it here."
    )
