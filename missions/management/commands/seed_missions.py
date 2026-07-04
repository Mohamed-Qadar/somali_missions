import random
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group
from django.utils import timezone
from datetime import timedelta

from missions.models import (
    Mission, Complaint, MissionService, RequiredDocument,
    EmergencySupportContact, EscalationRule, UserProfile, CommunityStatus,
    CommunityGroup, StudentAssociation, CommunityAnnouncement, CommunityEvent,
    EmergencySupportOffer,
)
from missions.utils.permissions import MINISTRY_ADMIN_GROUP, MISSION_STAFF_GROUP


MISSIONS = [
    {'name': 'Embassy of Somalia in Turkey', 'country': 'Turkey', 'city': 'Ankara', 'mission_type': 'EM', 'lat': '39.9208', 'lng': '32.8540', 'address': 'Kavaklidere, Ankara', 'phone': '+90 312 000 0000', 'email': 'ankara@mfa.gov.so'},
    {'name': 'Embassy of Somalia in Kenya', 'country': 'Kenya', 'city': 'Nairobi', 'mission_type': 'EM', 'lat': '-1.2921', 'lng': '36.8219', 'address': 'Nairobi, Kenya', 'phone': '+254 20 000 0000', 'email': 'nairobi@mfa.gov.so'},
    {'name': 'Embassy of Somalia in Ethiopia', 'country': 'Ethiopia', 'city': 'Addis Ababa', 'mission_type': 'EM', 'lat': '9.0320', 'lng': '38.7469', 'address': 'Addis Ababa, Ethiopia', 'phone': '+251 11 000 0000', 'email': 'addis@mfa.gov.so'},
    {'name': 'Embassy of Somalia in United Kingdom', 'country': 'United Kingdom', 'city': 'London', 'mission_type': 'EM', 'lat': '51.5074', 'lng': '-0.1278', 'address': 'London, UK', 'phone': '+44 20 0000 0000', 'email': 'london@mfa.gov.so'},
    {'name': 'Embassy of Somalia in United States', 'country': 'United States', 'city': 'Washington, D.C.', 'mission_type': 'EM', 'lat': '38.9072', 'lng': '-77.0369', 'address': 'Washington, D.C.', 'phone': '+1 202 000 0000', 'email': 'dc@mfa.gov.so'},
    {'name': 'Embassy of Somalia in United Arab Emirates', 'country': 'United Arab Emirates', 'city': 'Abu Dhabi', 'mission_type': 'EM', 'lat': '24.4539', 'lng': '54.3773', 'address': 'Abu Dhabi, UAE', 'phone': '+971 2 000 0000', 'email': 'abudhabi@mfa.gov.so'},
    {'name': 'Embassy of Somalia in Saudi Arabia', 'country': 'Saudi Arabia', 'city': 'Riyadh', 'mission_type': 'EM', 'lat': '24.7136', 'lng': '46.6753', 'address': 'Riyadh, Saudi Arabia', 'phone': '+966 11 000 0000', 'email': 'riyadh@mfa.gov.so'},
    {'name': 'Embassy of Somalia in Egypt', 'country': 'Egypt', 'city': 'Cairo', 'mission_type': 'EM', 'lat': '30.0444', 'lng': '31.2357', 'address': 'Cairo, Egypt', 'phone': '+20 2 0000 0000', 'email': 'cairo@mfa.gov.so'},
    {'name': 'Consulate General of Somalia in Istanbul', 'country': 'Turkey', 'city': 'Istanbul', 'mission_type': 'CO', 'lat': '41.0082', 'lng': '28.9784', 'address': 'Istanbul, Turkey', 'phone': '+90 212 000 0000', 'email': 'istanbul@mfa.gov.so'},
    {'name': 'Consulate General of Somalia in Minneapolis', 'country': 'United States', 'city': 'Minneapolis', 'mission_type': 'CO', 'lat': '44.9778', 'lng': '-93.2650', 'address': 'Minneapolis, MN', 'phone': '+1 612 000 0000', 'email': 'minneapolis@mfa.gov.so'},
    {'name': 'Consulate General of Somalia in Dubai', 'country': 'United Arab Emirates', 'city': 'Dubai', 'mission_type': 'CO', 'lat': '25.2048', 'lng': '55.2708', 'address': 'Dubai, UAE', 'phone': '+971 4 000 0000', 'email': 'dubai@mfa.gov.so'},
    {'name': 'Embassy of Somalia in Germany', 'country': 'Germany', 'city': 'Berlin', 'mission_type': 'EM', 'lat': '52.5200', 'lng': '13.4050', 'address': 'Berlin, Germany', 'phone': '+49 30 0000 0000', 'email': 'berlin@mfa.gov.so'},
    {'name': 'Embassy of Somalia in Sweden', 'country': 'Sweden', 'city': 'Stockholm', 'mission_type': 'EM', 'lat': '59.3293', 'lng': '18.0686', 'address': 'Stockholm, Sweden', 'phone': '+46 8 0000 0000', 'email': 'stockholm@mfa.gov.so'},
    {'name': 'Embassy of Somalia in Qatar', 'country': 'Qatar', 'city': 'Doha', 'mission_type': 'EM', 'lat': '25.2854', 'lng': '51.5310', 'address': 'Doha, Qatar', 'phone': '+974 0000 0000', 'email': 'doha@mfa.gov.so'},
    {'name': 'Embassy of Somalia in South Africa', 'country': 'South Africa', 'city': 'Pretoria', 'mission_type': 'EM', 'lat': '-25.7479', 'lng': '28.2293', 'address': 'Pretoria, South Africa', 'phone': '+27 12 000 0000', 'email': 'pretoria@mfa.gov.so'},
    {'name': 'Consulate General of Somalia in Toronto', 'country': 'Canada', 'city': 'Toronto', 'mission_type': 'CO', 'lat': '43.6532', 'lng': '-79.3832', 'address': 'Toronto, Canada', 'phone': '+1 416 000 0000', 'email': 'toronto@mfa.gov.so'},
]


class Command(BaseCommand):
    help = 'Seed Somali missions and sample complaints'

    def handle(self, *args, **options):
        ministry_group, _ = Group.objects.get_or_create(name=MINISTRY_ADMIN_GROUP)
        staff_group, _ = Group.objects.get_or_create(name=MISSION_STAFF_GROUP)

        created_missions = []
        for data in MISSIONS:
            mission, created = Mission.objects.update_or_create(
                name=data['name'],
                defaults={
                    'country': data['country'],
                    'city': data['city'],
                    'mission_type': data['mission_type'],
                    'address': data['address'],
                    'phone': data['phone'],
                    'email': data['email'],
                    'working_hours': 'Mon-Fri 9:00 AM - 4:00 PM',
                    'latitude': Decimal(data['lat']),
                    'longitude': Decimal(data['lng']),
                },
            )
            created_missions.append(mission)
            if created:
                self.stdout.write(f'Created mission: {mission.name}')

            service_defaults = [
                (
                    'Passport renewal',
                    MissionService.ServiceType.PASSPORT_RENEWAL,
                    '7-14 working days',
                    ['Current or expired Somali passport', 'Two passport photos', 'Proof of residence', 'Completed application form'],
                ),
                (
                    'Document authentication',
                    MissionService.ServiceType.DOCUMENT_AUTHENTICATION,
                    '1-3 working days',
                    ['Original document', 'Copy of Somali ID or passport', 'Translation if document is not in Somali/English'],
                ),
                (
                    'Lost passport emergency support',
                    MissionService.ServiceType.LOST_PASSPORT,
                    'Same day triage',
                    ['Police report', 'Any available identity document', 'Travel itinerary if urgent'],
                ),
            ]
            for service_name, service_type, processing_time, docs in service_defaults:
                service, _ = MissionService.objects.update_or_create(
                    mission=mission,
                    service_type=service_type,
                    name=service_name,
                    defaults={
                        'expected_processing_time': processing_time,
                        'appointment_required': service_type != MissionService.ServiceType.LOST_PASSPORT,
                        'best_arrival_time': 'Before 10:00 AM on working days',
                        'description': 'Pre-check guidance for citizens before travelling to the mission.',
                        'is_active': True,
                    },
                )
                for idx, doc_name in enumerate(docs, start=1):
                    RequiredDocument.objects.update_or_create(
                        service=service,
                        name=doc_name,
                        defaults={'sort_order': idx, 'is_required': True},
                    )

            EmergencySupportContact.objects.update_or_create(
                mission=mission,
                contact_type=EmergencySupportContact.ContactType.EMERGENCY,
                name=f'{mission.city} duty support line',
                defaults={
                    'phone': mission.phone,
                    'email': mission.email,
                    'notes': 'Use for citizens stranded after travel, urgent lost passport cases, or safety concerns.',
                    'is_public': True,
                },
            )
            EmergencySupportContact.objects.update_or_create(
                mission=mission,
                contact_type=EmergencySupportContact.ContactType.ASSOCIATION,
                name=f'Somali community association - {mission.city}',
                defaults={
                    'notes': 'Community support referral for translation help, local guidance, and temporary assistance.',
                    'is_public': True,
                },
            )

        if Complaint.objects.count() < 5:
            categories = list(Complaint.Category.values)
            for mission in created_missions[:8]:
                for _ in range(random.randint(1, 3)):
                    rating = random.randint(1, 5)
                    Complaint.objects.create(
                        mission=mission,
                        subject=random.choice(['Visa delay', 'Appointment issue', 'Staff behavior', 'Document processing']),
                        message='Sample feedback for demonstration purposes.',
                        rating=rating,
                        category=random.choice(categories),
                        is_anonymous=random.choice([True, False]),
                        full_name='' if random.choice([True, False]) else 'Sample User',
                        created_at=timezone.now() - timedelta(days=random.randint(0, 60)),
                    )

        featured_cities = [
            ('Turkey', 'Ankara', 'Ankara University Somali Students Association', 'Ankara University'),
            ('Turkey', 'Istanbul', 'Istanbul Somali Students Union', 'Istanbul University'),
            ('United Kingdom', 'London', 'London Somali Students Network', 'University of London'),
            ('United States', 'Minneapolis', 'Minnesota Somali Student Association', 'University of Minnesota'),
            ('Germany', 'Berlin', 'Berlin Somali Student Circle', 'Humboldt University of Berlin'),
        ]
        for country, city, assoc_name, university in featured_cities:
            assoc, _ = StudentAssociation.objects.update_or_create(
                name=assoc_name,
                defaults={
                    'country': country,
                    'city': city,
                    'university_name': university,
                    'description': 'Verified Somali student network offering orientation, translation guidance, embassy visit preparation, and peer support.',
                    'contact_email': f'{city.lower().replace(" ", "")}.students@example.org',
                    'phone_whatsapp': '+000 000 0000',
                    'office_location': f'{university} student centre',
                    'emergency_support_available': True,
                    'emergency_support_verified': True,
                    'status': CommunityStatus.VERIFIED,
                },
            )
            CommunityAnnouncement.objects.update_or_create(
                student_association=assoc,
                title='Before you travel to the Somali mission',
                defaults={
                    'announcement_type': CommunityAnnouncement.AnnouncementType.EMBASSY_VISIT,
                    'body': 'Bring printed copies of all documents, arrive early, and contact the association if you need translation or local transport guidance.',
                    'is_public': True,
                    'is_moderated': True,
                },
            )
            EmergencySupportOffer.objects.update_or_create(
                student_association=assoc,
                title='Emergency translation and local guidance',
                defaults={
                    'offer_type': EmergencySupportOffer.OfferType.TRANSLATION,
                    'description': 'Volunteer support for urgent consular visits, local language help, and transport directions.',
                    'contact_phone': assoc.phone_whatsapp,
                    'contact_email': assoc.contact_email,
                    'is_active': True,
                    'is_verified': True,
                },
            )

        community_cities = [
            ('Turkey', 'Ankara', 'Somali Community Association Ankara'),
            ('Turkey', 'Istanbul', 'Somali Community Centre Istanbul'),
            ('United Kingdom', 'London', 'Somali Community Support London'),
            ('United States', 'Minneapolis', 'Somali Community Volunteers Minneapolis'),
            ('Canada', 'Toronto', 'Toronto Somali Community Network'),
        ]
        for country, city, group_name in community_cities:
            group, _ = CommunityGroup.objects.update_or_create(
                name=group_name,
                defaults={
                    'country': country,
                    'city': city,
                    'description': 'Verified Somali community group supporting citizens with information, emergency referrals, accommodation guidance, and local orientation.',
                    'contact_email': f'{city.lower().replace(" ", "")}.community@example.org',
                    'phone_whatsapp': '+000 111 2222',
                    'office_location': f'{city} community office',
                    'emergency_support_available': True,
                    'emergency_support_verified': True,
                    'status': CommunityStatus.VERIFIED,
                },
            )
            CommunityEvent.objects.update_or_create(
                community_group=group,
                title='Monthly community orientation meeting',
                defaults={
                    'event_type': CommunityEvent.EventType.ORIENTATION,
                    'description': 'Orientation for newly arrived Somali citizens and students, including transport and consular visit guidance.',
                    'location': group.office_location,
                    'starts_at': timezone.now() + timedelta(days=14),
                    'is_public': True,
                },
            )
            EmergencySupportOffer.objects.update_or_create(
                community_group=group,
                title='Emergency accommodation referral',
                defaults={
                    'offer_type': EmergencySupportOffer.OfferType.ACCOMMODATION,
                    'description': 'Verified referral list for affordable guesthouses and short-term emergency accommodation options.',
                    'contact_phone': group.phone_whatsapp,
                    'contact_email': group.contact_email,
                    'is_active': True,
                    'is_verified': True,
                },
            )

        staff_user, user_created = User.objects.get_or_create(username='staff_london')
        if user_created:
            staff_user.set_password('staffpass123')
            staff_user.save()
        staff_user.groups.add(staff_group)
        london = Mission.objects.filter(city='London').first()
        if london:
            london.staff_users.add(staff_user)

        admin_user, admin_created = User.objects.get_or_create(username='ministry_admin')
        if admin_created:
            admin_user.set_password('adminpass123')
            admin_user.is_staff = True
            admin_user.save()
        admin_user.groups.add(ministry_group)

        for name, hours, role in [
            ('Critical case manager alert', 2, UserProfile.Role.EMBASSY_MANAGER),
            ('Critical case ministry review', 6, UserProfile.Role.MINISTRY_REVIEWER),
            ('Critical case ministry administration', 24, UserProfile.Role.MINISTRY_ADMIN),
        ]:
            EscalationRule.objects.update_or_create(
                name=name,
                defaults={'after_hours': hours, 'target_role': role, 'is_active': True},
            )

        self.stdout.write(self.style.SUCCESS(f'Seeded {len(created_missions)} missions.'))
