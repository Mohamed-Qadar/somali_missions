from django.core.management.base import BaseCommand
from django.db import transaction

from missions.management.commands.seed_missions import MISSIONS
from missions.models import (
    Complaint, EmbassyInvitation, Mission, MissionPerformanceScore, UserProfile,
)

# Old seed-script names (from an earlier iteration) that map 1:1 onto a
# country/city with no current duplicate -> renamed to match the current
# canonical MISSIONS list so re-running seed_missions updates them in place
# instead of creating a fresh duplicate row.
RENAMES = [
    ('Somali Embassy Djibouti City, Djibouti', 'Embassy of Somalia in Djibouti'),
    ('Somali Embassy Kampala, Uganda', 'Embassy of Somalia in Uganda'),
    ('Somali Embassy Brussels, Belgium', 'Embassy of Somalia in Belgium'),
    ('Somali Embassy Beijing, China', 'Embassy of Somalia in China'),
    ('Permanent Mission of Somalia to the UN, Geneva', 'Permanent Mission of Somalia to the UN in Geneva'),
    ('Somali Embassy New Delhi, India', 'Embassy of Somalia in India'),
    ('Somali Embassy Kuala Lumpur, Malaysia', 'Embassy of Somalia in Malaysia'),
    ('Somali Embassy Muscat, Oman', 'Embassy of Somalia in Oman'),
    ('Somali Embassy Islamabad, Pakistan', 'Embassy of Somalia in Pakistan'),
    ('Somali Embassy Moscow, Russia', 'Embassy of Somalia in Russia'),
    ('Somali Embassy Kuwait City, Kuwait', 'Embassy of Somalia in Kuwait'),
    ('Consulate General of Somalia Jeddah, Saudi Arabia', 'Consulate General of Somalia in Jeddah'),
    ('Somali Embassy Rome, Italy', 'Embassy of Somalia in Italy'),
    ('Somali Embassy Khartoum, Sudan', 'Embassy of Somalia in Sudan'),
]

# A handful of missions use a different spelling/abbreviation of the same
# country than the canonical seed list. Mapped to a common key purely so the
# dedup grouping below recognises them as the same place as the canonical row.
COUNTRY_ALIASES = {
    'turkiye': 'turkey',
    'uae': 'united arab emirates',
    'usa': 'united states',
}


class Command(BaseCommand):
    help = (
        'One-off cleanup of duplicate/junk Mission records and leftover '
        'Turkish test data accumulated during development. Safe to re-run.'
    )

    def handle(self, *args, **options):
        with transaction.atomic():
            self._fix_known_bugs()
            self._rename_to_canonical()
            self._dedupe_missions()
            self._clean_junk_complaints()
            self._clean_profile_text()
        self.stdout.write(self.style.SUCCESS('Mission/data cleanup complete.'))

    def _fix_known_bugs(self):
        geneva = Mission.objects.filter(name__icontains='Permanent Mission of Somalia to the UN').first()
        if geneva and geneva.country.strip().lower() == 'geneva':
            geneva.country, geneva.city = geneva.city, geneva.country
            geneva.save(update_fields=['country', 'city'])
            self.stdout.write(f'Fixed reversed country/city for: {geneva.name}')

        fixed = Mission.objects.filter(city='New Delh').update(city='New Delhi')
        if fixed:
            self.stdout.write('Fixed "New Delh" -> "New Delhi" typo.')

        fixed = Mission.objects.filter(name__icontains='Kuwait City', city='City').update(city='Kuwait City')
        if fixed:
            self.stdout.write('Fixed truncated Kuwait City name.')

        for m in Mission.objects.all():
            cleaned = m.city.strip().rstrip(',').strip()
            if cleaned != m.city:
                m.city = cleaned
                m.save(update_fields=['city'])

    def _rename_to_canonical(self):
        for old_name, new_name in RENAMES:
            updated = Mission.objects.filter(name=old_name).update(name=new_name)
            if updated:
                self.stdout.write(f'Renamed "{old_name}" -> "{new_name}"')

    def _dedupe_missions(self):
        canonical_names = {m['name'].lower() for m in MISSIONS}
        groups = {}
        def normalize(value):
            return ''.join(ch for ch in value.strip().lower() if ch.isalnum())

        for m in Mission.objects.all():
            raw_country = m.country.strip().lower()
            resolved_country = COUNTRY_ALIASES.get(raw_country, raw_country)
            country_key = normalize(resolved_country)
            city_key = normalize(m.city)
            groups.setdefault((country_key, city_key), []).append(m)

        for missions_in_group in groups.values():
            if len(missions_in_group) <= 1:
                continue

            def sort_key(mission):
                is_canonical = mission.name.lower() in canonical_names
                return (not is_canonical, -mission.complaints.count(), mission.pk)

            missions_in_group.sort(key=sort_key)
            canonical, duplicates = missions_in_group[0], missions_in_group[1:]
            for dup in duplicates:
                self._merge_mission(dup, canonical)

    def _merge_mission(self, dup, canonical):
        Complaint.objects.filter(mission=dup).update(mission=canonical)
        EmbassyInvitation.objects.filter(mission=dup).update(mission=canonical)
        MissionPerformanceScore.objects.filter(mission=dup).update(mission=canonical)
        UserProfile.objects.filter(mission=dup).update(mission=canonical)
        for staff in dup.staff_users.all():
            canonical.staff_users.add(staff)
        self.stdout.write(f'Merging duplicate "{dup.name}" (id={dup.pk}) into "{canonical.name}" (id={canonical.pk})')
        dup.delete()

    def _clean_junk_complaints(self):
        junk = Complaint.objects.filter(subject__iexact='şikeyet', message__icontains='kötü')
        count = junk.count()
        if count:
            junk.delete()
            self.stdout.write(f'Deleted {count} junk test complaint(s) with placeholder Turkish text.')

    def _clean_profile_text(self):
        updated = 0
        for profile in UserProfile.objects.filter(country_of_residence__icontains='rkiye'):
            profile.country_of_residence = 'Turkey'
            profile.save(update_fields=['country_of_residence'])
            updated += 1
        for profile in UserProfile.objects.filter(full_name__icontains='İ'):
            profile.full_name = profile.full_name.replace('İ', 'I')
            profile.save(update_fields=['full_name'])
        if updated:
            self.stdout.write(f'Normalized country_of_residence for {updated} profile(s).')
