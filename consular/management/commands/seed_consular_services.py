"""Provision the standard consular service catalogue on every mission.

Idempotent (update_or_create), mission-independent - it loops over whatever
missions exist, so it works for all embassies/consulates and never hard-codes a
country. Run after `seed_missions`:

    python manage.py seed_consular_services

Ministry admins can still add/edit/enable/disable services per mission from the
Django admin afterwards; this only seeds sensible defaults."""
from django.core.management.base import BaseCommand

from missions.models import Mission, MissionService, RequiredDocument

_ST = MissionService.ServiceType

# (name, service_type, appointment_required, processing_time, [required documents])
CATALOG = [
    ('Passport Renewal', _ST.PASSPORT_RENEWAL, True, '7-14 working days',
     ['Current or expired Somali passport', 'Two passport photos', 'Proof of residence', 'Completed application form']),
    ('New Passport Application', _ST.NEW_PASSPORT, True, '15-30 working days',
     ['Birth certificate or proof of Somali nationality', 'Two passport photos', 'Proof of residence', 'Completed application form']),
    ('Lost / Stolen Passport', _ST.LOST_PASSPORT, False, 'Same-day triage',
     ['Police report', 'Any available identity document', 'Two passport photos']),
    ('Emergency Travel Document', _ST.EMERGENCY_TRAVEL_DOC, True, '1-3 working days',
     ['Proof of identity', 'Travel itinerary or ticket', 'Two passport photos']),
    ('Birth Registration / Certificate', _ST.BIRTH_REGISTRATION, False, '5-10 working days',
     ['Hospital birth notification', "Parents' passports or IDs", 'Marriage certificate of parents (if available)']),
    ('Marriage Registration / Certificate', _ST.MARRIAGE_REGISTRATION, True, '5-10 working days',
     ['Passports or IDs of both spouses', 'Existing marriage contract', 'Two witnesses identification']),
    ('Death Registration / Certificate', _ST.DEATH_REGISTRATION, False, '3-7 working days',
     ['Medical certificate of death', 'Passport or ID of the deceased', 'Identity of the person reporting']),
    ('Document Attestation / Legalization', _ST.DOCUMENT_AUTHENTICATION, False, '1-3 working days',
     ['Original document', 'Copy of Somali ID or passport', 'Certified translation if not in Somali/English']),
    ('Authentication / Certification of Documents', _ST.DOCUMENT_CERTIFICATION, False, '1-3 working days',
     ['Original document to certify', 'Copy of Somali ID or passport']),
    ('Power of Attorney', _ST.POWER_OF_ATTORNEY, True, '2-5 working days',
     ['Draft power of attorney text', 'Passport or ID of the grantor', 'Details of the appointed representative']),
    ('Consular Letter / Certificate', _ST.CONSULAR_LETTER, False, '1-3 working days',
     ['Passport or ID', 'Supporting documents relevant to the request']),
    ('Citizenship-related Request', _ST.CITIZENSHIP, True, '30+ working days',
     ['Proof of Somali origin', 'Passport or ID', 'Supporting civil documents']),
    ('General Consular Service / Other Request', _ST.OTHER, False, 'Varies',
     ['Passport or ID', 'Any documents relevant to your request']),
]


class Command(BaseCommand):
    help = 'Seed the standard consular service catalogue on every mission.'

    def handle(self, *args, **options):
        missions = Mission.objects.all()
        if not missions.exists():
            self.stdout.write(self.style.WARNING('No missions found. Run seed_missions first.'))
            return

        services_created = 0
        for mission in missions:
            for name, service_type, appt_required, processing_time, docs in CATALOG:
                service, created = MissionService.objects.update_or_create(
                    mission=mission,
                    service_type=service_type,
                    name=name,
                    defaults={
                        'expected_processing_time': processing_time,
                        'appointment_required': appt_required,
                        'description': 'Apply online, then attend the mission if an appointment is required.',
                        'is_active': True,
                    },
                )
                if created:
                    services_created += 1
                for idx, doc_name in enumerate(docs, start=1):
                    RequiredDocument.objects.update_or_create(
                        service=service, name=doc_name,
                        defaults={'sort_order': idx, 'is_required': True},
                    )

        self.stdout.write(self.style.SUCCESS(
            f'Consular catalogue ensured on {missions.count()} mission(s); '
            f'{services_created} new service rows created.'
        ))
