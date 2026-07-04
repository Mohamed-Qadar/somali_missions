from django.shortcuts import render

from .models import AssistantConversationLog, AssistantTopic
from .providers import get_answer_provider

ACTION_URL_NAMES = {
    'book_appointment': 'book_appointment',
    'submit_complaint': 'submit_complaint_wizard',
    'view_requirements': 'before_you_travel',
    'track_complaint': 'track',
}


def ask_assistant_view(request):
    answer = None
    question = ''

    if request.method == 'POST':
        question = request.POST.get('question', '').strip()
        if question:
            provider = get_answer_provider()
            answer = provider.answer(question)
            matched_topic = (
                AssistantTopic.objects.filter(topic_key=answer.topic_key).first()
                if answer.topic_key else None
            )
            AssistantConversationLog.objects.create(
                session_key=request.session.session_key or '',
                user=request.user if request.user.is_authenticated else None,
                query_text=question,
                matched_topic=matched_topic,
                confidence=answer.confidence,
            )

    action_url_name = ACTION_URL_NAMES.get(answer.suggested_action) if answer else None

    return render(request, 'assistant/ask.html', {
        'question': question,
        'answer': answer,
        'action_url_name': action_url_name,
    })
