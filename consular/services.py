"""Presentation-only grouping of MissionService.ServiceType values into the
four citizen-facing cards on the Consular Services landing page.

This is a display convenience, not a second source of truth: services
themselves live in missions.MissionService (per-mission, admin-configurable).
A service type not listed here still works everywhere - it just falls under
the catch-all "Other Consular Services" card via ``category_for``."""
from django.utils.translation import gettext_lazy as _

from missions.models import MissionService

_ST = MissionService.ServiceType

SERVICE_CATEGORIES = [
    {
        'key': 'passport',
        'label': _('Passport Services'),
        'blurb': _('Renewal, new passport, lost passport, emergency travel document'),
        'icon': 'menu_book',
        'types': [
            _ST.PASSPORT_RENEWAL, _ST.NEW_PASSPORT,
            _ST.LOST_PASSPORT, _ST.EMERGENCY_TRAVEL_DOC,
        ],
    },
    {
        'key': 'civil',
        'label': _('Civil Registration'),
        'blurb': _('Birth, marriage and death certificates and registration'),
        'icon': 'family_restroom',
        'types': [
            _ST.BIRTH_REGISTRATION, _ST.MARRIAGE_REGISTRATION,
            _ST.DEATH_REGISTRATION, _ST.CIVIL_REGISTRATION,
        ],
    },
    {
        'key': 'documents',
        'label': _('Document Services'),
        'blurb': _('Attestation, legalization, authentication, power of attorney'),
        'icon': 'verified',
        'types': [
            _ST.DOCUMENT_AUTHENTICATION, _ST.DOCUMENT_CERTIFICATION,
            _ST.POWER_OF_ATTORNEY, _ST.CONSULAR_LETTER,
        ],
    },
    {
        'key': 'other',
        'label': _('Other Consular Services'),
        'blurb': _('Citizenship requests and any other consular assistance'),
        'icon': 'contact_support',
        'types': [_ST.CITIZENSHIP, _ST.VISA, _ST.EMERGENCY_ASSISTANCE, _ST.OTHER],
    },
]

_CATEGORY_BY_KEY = {c['key']: c for c in SERVICE_CATEGORIES}


def types_for_category(key):
    """Return the list of service_type values in a category, or None if the
    key is unknown (meaning 'do not filter')."""
    category = _CATEGORY_BY_KEY.get(key)
    return [str(t) for t in category['types']] if category else None


def category_for(service_type):
    """Reverse lookup: which category key a service_type belongs to. Falls back
    to 'other' so nothing is ever orphaned."""
    for category in SERVICE_CATEGORIES:
        if service_type in [str(t) for t in category['types']]:
            return category['key']
    return 'other'
