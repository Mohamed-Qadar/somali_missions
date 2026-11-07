from django import forms
from django.utils.translation import gettext_lazy as _

from .models import ConsularApplication

_INPUT = 'form-control rounded-lg border border-border px-3 py-2 w-full'


class ConsularApplicationForm(forms.ModelForm):
    """Applicant-facing details. Mission and service are chosen in the step
    before this form (so the service's document checklist can be shown), then
    passed in by the view - they are deliberately not editable fields here."""

    class Meta:
        model = ConsularApplication
        fields = [
            'full_name', 'email', 'phone', 'date_of_birth',
            'passport_number', 'national_id', 'notes',
        ]
        widgets = {
            'full_name': forms.TextInput(attrs={'class': _INPUT}),
            'email': forms.EmailInput(attrs={'class': _INPUT}),
            'phone': forms.TextInput(attrs={'class': _INPUT}),
            'date_of_birth': forms.DateInput(attrs={'type': 'date', 'class': _INPUT}),
            'passport_number': forms.TextInput(attrs={'class': _INPUT}),
            'national_id': forms.TextInput(attrs={'class': _INPUT}),
            'notes': forms.Textarea(attrs={'class': _INPUT, 'rows': 4}),
        }

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get('email') and not cleaned.get('phone'):
            raise forms.ValidationError(
                _('Please provide at least an email or a phone number so the mission can reach you.')
            )
        return cleaned


class StaffApplicationActionForm(forms.Form):
    """Mission-staff review actions on a single application."""

    ACTIONS = [
        ('under_review', _('Move to Under Review')),
        ('request_documents', _('Request Additional Documents')),
        ('approve', _('Mark Approved / Ready')),
        ('require_appointment', _('Require Appointment')),
        ('complete', _('Mark Completed')),
        ('reject', _('Reject')),
    ]
    action = forms.ChoiceField(choices=ACTIONS, widget=forms.Select(attrs={'class': _INPUT}))
    citizen_message = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': _INPUT, 'rows': 3}),
        label=_('Message to the citizen (visible to them)'),
    )
    staff_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': _INPUT, 'rows': 3}),
        label=_('Internal notes (staff only)'),
    )
