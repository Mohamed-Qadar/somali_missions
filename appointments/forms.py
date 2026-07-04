from django import forms
from django.utils.translation import gettext_lazy as _

from .models import AppointmentSlot


class BookAppointmentForm(forms.Form):
    full_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control rounded-lg border border-border px-3 py-2 w-full'}),
        label=_('Full Name'),
    )
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={'class': 'form-control rounded-lg border border-border px-3 py-2 w-full'}),
        label=_('Email (for confirmation)'),
    )
    phone = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control rounded-lg border border-border px-3 py-2 w-full'}),
        label=_('Phone'),
    )

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get('email') and not cleaned_data.get('phone'):
            raise forms.ValidationError(_('Please provide at least an email or a phone number so we can reach you.'))
        return cleaned_data


class AppointmentSlotForm(forms.ModelForm):
    class Meta:
        model = AppointmentSlot
        fields = ['service', 'date', 'start_time', 'end_time', 'capacity', 'is_active']
        widgets = {
            'service': forms.Select(attrs={'class': 'form-control rounded-lg border border-border px-3 py-2 w-full'}),
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control rounded-lg border border-border px-3 py-2 w-full'}),
            'start_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control rounded-lg border border-border px-3 py-2 w-full'}),
            'end_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control rounded-lg border border-border px-3 py-2 w-full'}),
            'capacity': forms.NumberInput(attrs={'class': 'form-control rounded-lg border border-border px-3 py-2 w-full', 'min': 1}),
        }

    def __init__(self, *args, mission=None, **kwargs):
        super().__init__(*args, **kwargs)
        if mission is not None:
            self.fields['service'].queryset = mission.services.filter(is_active=True)


class AppointmentActionForm(forms.Form):
    ACTIONS = [
        ('approve', _('Approve')),
        ('reject', _('Reject')),
        ('reschedule', _('Reschedule')),
        ('cancel', _('Cancel')),
        ('complete', _('Mark Completed')),
        ('no_show', _('Mark No-Show')),
    ]
    action = forms.ChoiceField(choices=ACTIONS)
    new_slot = forms.ModelChoiceField(queryset=AppointmentSlot.objects.all(), required=False)
    note = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 2}))
