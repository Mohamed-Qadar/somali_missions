from django.core.management.base import BaseCommand

from assistant.models import AssistantTopic

TopicKey = AssistantTopic.TopicKey
Action = AssistantTopic.SuggestedAction

TOPICS = [
    {
        'topic_key': TopicKey.PASSPORT_RENEWAL,
        'title': 'Passport Renewal',
        'keywords': 'passport, renew, renewal, expired passport, new passport',
        'answer': (
            'To renew your Somali passport, book an appointment at your nearest mission and bring your '
            'current or expired passport, two passport photos, and proof of residence. Processing usually '
            'takes 7-14 working days.'
        ),
        'suggested_action': Action.BOOK_APPOINTMENT,
    },
    {
        'topic_key': TopicKey.LOST_PASSPORT,
        'title': 'Lost Passport',
        'keywords': 'lost passport, stolen passport, missing passport',
        'answer': (
            'If your passport is lost or stolen, report it to local police first and get a police report. '
            'Then contact the nearest Somali mission with the police report and any other identity document - '
            'lost passport cases are handled as same-day triage.'
        ),
        'suggested_action': Action.BOOK_APPOINTMENT,
    },
    {
        'topic_key': TopicKey.VISA,
        'title': 'Visa Issues',
        'keywords': 'visa, entry visa, tourist visa, visa application',
        'answer': (
            'Visa services are handled directly by the mission for the country you wish to visit. Check the '
            'mission directory for contact details and required documents for your specific visa type.'
        ),
        'suggested_action': Action.VIEW_REQUIREMENTS,
    },
    {
        'topic_key': TopicKey.BIRTH_CERTIFICATE,
        'title': 'Birth Certificate',
        'keywords': 'birth certificate, newborn, birth registration',
        'answer': (
            'Birth certificates for children born abroad can be registered and authenticated through civil '
            'registration services at your nearest mission. Bring the original foreign birth certificate and '
            'both parents\' identity documents.'
        ),
        'suggested_action': Action.VIEW_REQUIREMENTS,
    },
    {
        'topic_key': TopicKey.MARRIAGE,
        'title': 'Marriage Documentation',
        'keywords': 'marriage, marriage certificate, wedding, spouse',
        'answer': (
            'Marriage certificates issued abroad can be authenticated at your nearest mission for use in '
            'Somalia. Bring the original certificate, a translation if it is not in Somali/English, and both '
            'spouses\' identity documents.'
        ),
        'suggested_action': Action.VIEW_REQUIREMENTS,
    },
    {
        'topic_key': TopicKey.EMERGENCY_TRAVEL,
        'title': 'Emergency Travel Document',
        'keywords': 'emergency travel, stranded, emergency document, urgent travel',
        'answer': (
            'If you are stranded and need to travel urgently without a valid passport, use the Emergency '
            'Support page to report your situation. This bypasses the normal queue and alerts a duty officer.'
        ),
        'suggested_action': Action.NONE,
    },
    {
        'topic_key': TopicKey.DOCUMENT_AUTHENTICATION,
        'title': 'Document Authentication',
        'keywords': 'authenticate, authentication, notarize, certify document, apostille',
        'answer': (
            'Document authentication (for use in Somalia or abroad) requires the original document, a copy of '
            'your Somali ID or passport, and a translation if the document is not in Somali or English. '
            'Processing is usually 1-3 working days.'
        ),
        'suggested_action': Action.BOOK_APPOINTMENT,
    },
    {
        'topic_key': TopicKey.CITIZENSHIP,
        'title': 'Citizenship Questions',
        'keywords': 'citizenship, nationality, dual citizenship, naturalization',
        'answer': (
            'Citizenship and nationality matters are handled case-by-case by the mission. Please book an '
            'appointment to discuss your specific situation with a consular officer.'
        ),
        'suggested_action': Action.BOOK_APPOINTMENT,
    },
    {
        'topic_key': TopicKey.REQUIRED_DOCUMENTS,
        'title': 'Required Documents',
        'keywords': 'what documents, required documents, what do i need, checklist',
        'answer': (
            'Document requirements vary by service and mission. Visit the Before You Travel page and select '
            'your mission and service to see the exact checklist.'
        ),
        'suggested_action': Action.VIEW_REQUIREMENTS,
    },
    {
        'topic_key': TopicKey.OFFICE_HOURS,
        'title': 'Office Hours',
        'keywords': 'office hours, opening hours, when open, working hours',
        'answer': (
            'Most missions are open Monday-Friday, 9:00 AM - 4:00 PM local time. Check the specific mission\'s '
            'page in the directory for exact hours, as they can vary.'
        ),
        'suggested_action': Action.VIEW_REQUIREMENTS,
    },
    {
        'topic_key': TopicKey.APPOINTMENT_GUIDANCE,
        'title': 'Appointment Guidance',
        'keywords': 'book appointment, schedule, reschedule, appointment slot',
        'answer': (
            'You can book an appointment online by choosing your mission, the service you need, and an '
            'available time slot. You will receive a QR-coded confirmation and an email.'
        ),
        'suggested_action': Action.BOOK_APPOINTMENT,
    },
    {
        'topic_key': TopicKey.COMPLAINT_GUIDANCE,
        'title': 'Complaint Guidance',
        'keywords': 'complaint, complain, report issue, bad service, staff behavior',
        'answer': (
            'You can submit a complaint about mission services - anonymously if you prefer - and receive a '
            'tracking code to follow its status. Use the Submit Complaint page to get started.'
        ),
        'suggested_action': Action.SUBMIT_COMPLAINT,
    },
]


class Command(BaseCommand):
    help = 'Seed the Smart Citizen Assistant topic/answer knowledge base.'

    def handle(self, *args, **options):
        for data in TOPICS:
            AssistantTopic.objects.update_or_create(
                topic_key=data['topic_key'],
                defaults={
                    'title': data['title'],
                    'keywords': data['keywords'],
                    'answer': data['answer'],
                    'suggested_action': data['suggested_action'],
                    'is_active': True,
                },
            )
        self.stdout.write(self.style.SUCCESS(f'Seeded {len(TOPICS)} assistant topics.'))
