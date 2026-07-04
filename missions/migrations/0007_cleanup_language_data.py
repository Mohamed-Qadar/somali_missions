from django.db import migrations


REPLACEMENTS = {
    'B\u00fcy\u00fckel\u00e7ilik': 'Embassy',
    'B\u00fcy\u00fckel\u00e7ili\u011fi': 'Embassy',
    '\u004b\u006f\u006e\u0073\u006f\u006c\u006f\u0073\u006c\u0075\u006b': 'Consulate',
    '\u0046\u0061\u0068\u0072\u0069\u0020\u004b\u006f\u006e\u0073\u006f\u006c\u006f\u0073\u006c\u0075\u006b': 'Honorary Consulate',
    '\u0044\u0061\u0069\u006d\u0069\u0020\u0054\u0065\u006d\u0073\u0069\u006c\u0063\u0069\u006c\u0069\u006b': 'Permanent Mission',
    '\u0130svi\u00e7re': 'Switzerland',
    'T\u00fcrkiye': 'Turkey',
    '\u0043\u0065\u006e\u0065\u0076\u0072\u0065': 'Geneva',
    '\u0130stanbul': 'Istanbul',
    '\u0043\u0069\u0062\u0075\u0074\u0069': 'Djibouti',
    'M\u0131s\u0131r': 'Egypt',
    '\u004b\u0061\u0068\u0069\u0072\u0065': 'Cairo',
    'Bel\u00c3\u00a7ika': 'Belgium',
    'Bel\u00e7ika': 'Belgium',
    'Br\u00fcksel': 'Brussels',
    '\u00c7in': 'China',
    '\u0050\u0065\u006b\u0069\u006e': 'Beijing',
    'Mon\u2013Fri 9:00 AM \u2013 4:00 PM': 'Mon-Fri 9:00 AM - 4:00 PM',
    'Mon\u00e2\u20ac\u201cFri 9:00 AM \u00e2\u20ac\u201c 4:00 PM': 'Mon-Fri 9:00 AM - 4:00 PM',
}


def cleanup_mission_language_data(apps, schema_editor):
    Mission = apps.get_model('missions', 'Mission')
    fields = ('name', 'country', 'city', 'address', 'working_hours')

    for mission in Mission.objects.all():
        changed = False
        for field in fields:
            value = getattr(mission, field, '') or ''
            cleaned = value
            for old, new in REPLACEMENTS.items():
                cleaned = cleaned.replace(old, new)
            if cleaned != value:
                setattr(mission, field, cleaned)
                changed = True
        if changed:
            mission.save(update_fields=fields)


class Migration(migrations.Migration):

    dependencies = [
        ('missions', '0006_communitygroup_studentassociation_and_more'),
    ]

    operations = [
        migrations.RunPython(cleanup_mission_language_data, migrations.RunPython.noop),
    ]
