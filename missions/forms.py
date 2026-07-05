import os

from django import forms
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _

from .models import (
    AbuseReport, Complaint, CommunityServiceCategory, EmbassyResponse,
    ContactMessage, Mission, MissionEvent, UserProfile,
)

_INPUT_CLS = 'form-control w-full rounded-lg border border-border px-3 py-3'
_ALLOWED_IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.webp'}


def _validate_uploaded_image(upload, max_mb):
    """Size + extension gate for organization logos/banners. ImageField
    already verifies the content is a real image via Pillow."""
    if upload.size > max_mb * 1024 * 1024:
        raise forms.ValidationError(
            _('File too large - maximum %(size)s MB.') % {'size': max_mb})
    ext = os.path.splitext(upload.name)[1].lower()
    if ext not in _ALLOWED_IMAGE_EXTENSIONS:
        raise forms.ValidationError(_('Only PNG, JPG, or WEBP images are allowed.'))
    return upload


class ComplaintForm(forms.ModelForm):
    submit_anonymously = forms.BooleanField(
        required=False,
        label=_('Submit anonymously'),
        widget=forms.CheckboxInput(attrs={'class': 'h-4 w-4 rounded border-gray-300 text-primary'}),
    )
    website = forms.CharField(required=False, widget=forms.HiddenInput())
    captcha_answer = forms.IntegerField(
        label=_('Security check'),
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': _('Answer')}),
    )

    class Meta:
        model = Complaint
        fields = ['full_name', 'email', 'phone', 'subject', 'message', 'rating', 'category']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Optional')}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': _('Optional')}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Optional')}),
            'subject': forms.TextInput(attrs={'class': 'form-control'}),
            'message': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'rating': forms.NumberInput(attrs={'type': 'hidden', 'id': 'rating_field', 'min': '1', 'max': '5'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'full_name': _('Full Name (Optional)'),
            'email': _('Email (Optional)'),
            'category': _('Category'),
        }

    def __init__(self, *args, **kwargs):
        self.captcha_expected = kwargs.pop('captcha_expected', None)
        super().__init__(*args, **kwargs)
        if self.captcha_expected is not None:
            self.fields['captcha_answer'].help_text = _('What is %(num1)s + %(num2)s?') % {
                'num1': self.captcha_expected[0],
                'num2': self.captcha_expected[1],
            }

    def clean_website(self):
        if self.cleaned_data.get('website'):
            raise forms.ValidationError(_('Invalid submission.'))
        return ''

    def clean_captcha_answer(self):
        answer = self.cleaned_data.get('captcha_answer')
        if self.captcha_expected is None:
            return answer
        expected = self.captcha_expected[0] + self.captcha_expected[1]
        if answer != expected:
            raise forms.ValidationError(_('Incorrect answer. Please try again.'))
        return answer

    def save(self, commit=True):
        complaint = super().save(commit=False)
        complaint.is_anonymous = self.cleaned_data.get('submit_anonymously', False)
        if commit:
            complaint.save()
        return complaint


class EmergencyReportForm(forms.Form):
    """Server-side validation for the emergency submission page.

    The template renders the fields by hand (custom emergency styling), so
    widgets here only need sensible types - see submit_emergency.html.
    """

    mission = forms.ModelChoiceField(
        queryset=Mission.objects.all(),
        error_messages={
            'required': _('Please choose the embassy or consulate nearest to you.'),
            'invalid_choice': _('Please choose a valid embassy or consulate.'),
        },
    )
    emergency_type = forms.ChoiceField(
        choices=Complaint.EmergencyType.choices,
        error_messages={
            'required': _('Please tell us the nature of the crisis.'),
            'invalid_choice': _('Please choose a valid crisis type.'),
        },
    )
    message = forms.CharField(
        min_length=10,
        error_messages={
            'required': _('Please describe what happened so officers can act.'),
            'min_length': _('Please give a few more details (at least 10 characters).'),
        },
    )
    full_name = forms.CharField(
        max_length=150,
        error_messages={'required': _('Please give a name officers can ask for.')},
    )
    phone = forms.CharField(
        max_length=50,
        error_messages={'required': _('A callback phone number is required for emergencies.')},
    )
    email = forms.EmailField(
        required=False,
        error_messages={'invalid': _('Please enter a valid email address, or leave it empty.')},
    )
    currently_at_mission = forms.BooleanField(required=False)
    travelled_from_another_city = forms.BooleanField(required=False)
    no_accommodation = forms.BooleanField(required=False)
    has_return_ticket = forms.BooleanField(required=False)
    waiting_more_than_two_hours = forms.BooleanField(required=False)

    def derived_category(self):
        """Map the crisis type to a complaint category (never trusted from POST)."""
        if self.cleaned_data.get('emergency_type') == Complaint.EmergencyType.LOST_PASSPORT:
            return Complaint.Category.LOST_DOCS
        return Complaint.Category.EMERGENCY


class ReportForm(forms.Form):
    report_type = forms.ChoiceField(
        choices=[
            ('complaint_log', _('Full Complaint Log (Per Consulate)')),
            ('monthly_summary', _('Monthly Performance Summary')),
            ('analytics', _('Overall Platform Analytics')),
        ],
        widget=forms.RadioSelect(attrs={'class': 'grid gap-2'}),
        initial='complaint_log',
    )
    consulate = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input w-full rounded-lg border border-border px-3 py-3 focus:border-primary focus:ring-primary',
            'placeholder': _('All Consulates'),
        }),
    )
    date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-input w-full rounded-lg border border-border px-3 py-3 focus:border-primary focus:ring-primary',
        }),
    )
    include_average = forms.BooleanField(required=False, initial=True)
    include_complaints = forms.BooleanField(required=False, initial=True)
    include_sentiment = forms.BooleanField(required=False, initial=True)

    def clean_consulate(self):
        value = self.cleaned_data.get('consulate')
        return value or 'All Consulates'


class TrackComplaintForm(forms.Form):
    tracking_code = forms.CharField(
        max_length=8,
        label=_('Tracking code'),
        widget=forms.TextInput(attrs={
            'class': 'form-control w-full rounded-lg border border-border px-3 py-3 uppercase',
            'placeholder': 'AB12CD34',
        }),
    )


class ComplaintStatusForm(forms.ModelForm):
    # Only offer the current status names in the dropdown - Complaint.Status
    # also carries legacy values (NEW/PRO/RES/CLO) kept for old rows and
    # existing filters elsewhere, which would otherwise show as confusing
    # duplicate options here (e.g. "Resolved" appearing twice).
    CURRENT_STATUSES = [
        Complaint.Status.SUBMITTED,
        Complaint.Status.ASSIGNED,
        Complaint.Status.UNDER_REVIEW,
        Complaint.Status.INVESTIGATION,
        Complaint.Status.AWAITING_RESPONSE,
        Complaint.Status.RESOLVED,
        Complaint.Status.CLOSED,
    ]

    class Meta:
        model = Complaint
        fields = ['status']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-control rounded-lg border border-border px-3 py-2'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        current_choices = [(value, label) for value, label in Complaint.Status.choices if value in self.CURRENT_STATUSES]
        instance_status = self.instance.status if self.instance else None
        if instance_status and instance_status not in self.CURRENT_STATUSES:
            current_choices.insert(0, (instance_status, dict(Complaint.Status.choices).get(instance_status, instance_status)))
        self.fields['status'].choices = current_choices


class EmbassyResponseForm(forms.ModelForm):
    class Meta:
        model = EmbassyResponse
        fields = ['responder_name', 'message', 'is_public']
        widgets = {
            'responder_name': forms.TextInput(attrs={'class': 'form-control rounded-lg border border-border px-3 py-2'}),
            'message': forms.Textarea(attrs={'class': 'form-control rounded-lg border border-border px-3 py-2', 'rows': 4}),
            'is_public': forms.CheckboxInput(attrs={'class': 'h-4 w-4 rounded'}),
        }
        labels = {
            'is_public': _('Show summary response on public tracking page'),
        }


class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ['name', 'email', 'subject', 'message']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control w-full rounded-lg border border-border px-3 py-3'}),
            'email': forms.EmailInput(attrs={'class': 'form-control w-full rounded-lg border border-border px-3 py-3'}),
            'subject': forms.TextInput(attrs={'class': 'form-control w-full rounded-lg border border-border px-3 py-3'}),
            'message': forms.Textarea(attrs={'class': 'form-control w-full rounded-lg border border-border px-3 py-3', 'rows': 5}),
        }

class LoginForm(forms.Form):
    username = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control w-full rounded-lg border border-border px-3 py-3'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control w-full rounded-lg border border-border px-3 py-3'}))
    remember_me = forms.BooleanField(required=False, label=_('Remember me'))

class CitizenRegistrationForm(forms.ModelForm):
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control w-full rounded-lg border border-border px-3 py-3'}),
        help_text=_('Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.')
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control w-full rounded-lg border border-border px-3 py-3'}),
        label=_('Password')
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control w-full rounded-lg border border-border px-3 py-3'}),
        label=_('Confirm Password')
    )
    full_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control w-full rounded-lg border border-border px-3 py-3'}),
        label=_('Full Name')
    )
    national_id = forms.CharField(
        required=False,
        max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control w-full rounded-lg border border-border px-3 py-3', 'placeholder': _('Optional')}),
        label=_('National ID (Optional)')
    )
    phone_number = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control w-full rounded-lg border border-border px-3 py-3'}),
        label=_('Phone Number')
    )
    country_of_residence = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control w-full rounded-lg border border-border px-3 py-3'}),
        label=_('Country of Residence')
    )

    class Meta:
        model = User
        fields = ['username', 'email']
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control w-full rounded-lg border border-border px-3 py-3'}),
        }

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError(_('A user with that username already exists.'))
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(_('A user with that email already exists.'))
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError(_('Passwords do not match.'))
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
            profile, created = UserProfile.objects.get_or_create(user=user)
            profile.role = UserProfile.Role.CITIZEN
            profile.full_name = self.cleaned_data['full_name']
            profile.national_id = self.cleaned_data['national_id']
            profile.phone_number = self.cleaned_data['phone_number']
            profile.country_of_residence = self.cleaned_data['country_of_residence']
            profile.email_verified = False
            profile.save()
        return user


class CommunityOrganizationRegistrationForm(forms.Form):
    """Self-registration for community groups / student associations: one
    representative account plus the organization record (Pending review)."""

    ORG_TYPES = (
        ('community', _('Somali Community Group')),
        ('student', _('Student Association')),
    )

    org_type = forms.ChoiceField(choices=ORG_TYPES, initial='community',
                                 widget=forms.RadioSelect)
    org_name = forms.CharField(max_length=180, label=_('Organization name'),
                               widget=forms.TextInput(attrs={'class': _INPUT_CLS}))
    university_name = forms.CharField(
        max_length=180, required=False, label=_('University name'),
        widget=forms.TextInput(attrs={'class': _INPUT_CLS}),
        help_text=_('Required for student associations.'))
    country = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': _INPUT_CLS}))
    city = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': _INPUT_CLS}))
    description = forms.CharField(
        label=_('What does your organization do?'),
        widget=forms.Textarea(attrs={'class': _INPUT_CLS, 'rows': 4}))
    contact_email = forms.EmailField(label=_('Organization contact email'),
                                     widget=forms.EmailInput(attrs={'class': _INPUT_CLS}))

    rep_full_name = forms.CharField(max_length=150, label=_('Representative full name'),
                                    widget=forms.TextInput(attrs={'class': _INPUT_CLS}))
    rep_title = forms.CharField(max_length=120, required=False, label=_('Representative role/title'),
                                widget=forms.TextInput(attrs={'class': _INPUT_CLS}))
    username = forms.CharField(
        max_length=150, widget=forms.TextInput(attrs={'class': _INPUT_CLS}),
        help_text=_('Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.'))
    email = forms.EmailField(label=_('Account email'),
                             widget=forms.EmailInput(attrs={'class': _INPUT_CLS}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': _INPUT_CLS}), label=_('Password'))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': _INPUT_CLS}),
                                       label=_('Confirm Password'))

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError(_('A user with that username already exists.'))
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(_('A user with that email already exists.'))
        return email

    def clean(self):
        cleaned = super().clean()
        password = cleaned.get('password')
        confirm = cleaned.get('confirm_password')
        if password and confirm and password != confirm:
            raise forms.ValidationError(_('Passwords do not match.'))
        if password and len(password) < 6:
            self.add_error('password', _('Password must be at least 6 characters.'))
        if cleaned.get('org_type') == 'student' and not cleaned.get('university_name', '').strip():
            self.add_error('university_name', _('Please give the university name for a student association.'))
        return cleaned


class CommunityProfileForm(forms.Form):
    """Self-service profile editing in the community portal. A plain Form
    (not ModelForm) because it drives both CommunityGroup and
    StudentAssociation, which share these fields."""

    description = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 4}))
    contact_email = forms.EmailField(
        required=False,
        error_messages={'invalid': _('Please enter a valid email address, or leave it empty.')})
    phone_whatsapp = forms.CharField(max_length=60, required=False)
    facebook_url = forms.URLField(required=False)
    instagram_url = forms.URLField(required=False)
    x_url = forms.URLField(required=False)
    website_url = forms.URLField(required=False)
    office_location = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 2}))
    languages_spoken = forms.CharField(max_length=200, required=False)
    service_categories = forms.MultipleChoiceField(
        choices=CommunityServiceCategory.choices, required=False,
        widget=forms.CheckboxSelectMultiple)
    emergency_support_available = forms.BooleanField(required=False)
    logo = forms.ImageField(required=False)
    banner = forms.ImageField(required=False)

    def clean_logo(self):
        logo = self.cleaned_data.get('logo')
        if logo and hasattr(logo, 'size'):
            _validate_uploaded_image(logo, max_mb=2)
        return logo

    def clean_banner(self):
        banner = self.cleaned_data.get('banner')
        if banner and hasattr(banner, 'size'):
            _validate_uploaded_image(banner, max_mb=4)
        return banner

    def apply_to(self, target, user):
        for field in ['description', 'contact_email', 'phone_whatsapp', 'facebook_url',
                      'instagram_url', 'x_url', 'website_url', 'office_location',
                      'languages_spoken']:
            setattr(target, field, self.cleaned_data.get(field, '') or '')
        target.service_categories = list(self.cleaned_data.get('service_categories') or [])
        target.emergency_support_available = self.cleaned_data.get('emergency_support_available', False)
        if self.cleaned_data.get('logo'):
            target.logo = self.cleaned_data['logo']
        if self.cleaned_data.get('banner'):
            target.banner = self.cleaned_data['banner']
        target.updated_by = user
        target.save()
        return target


class MissionEventForm(forms.ModelForm):
    class Meta:
        model = MissionEvent
        fields = ['title', 'event_type', 'description', 'country', 'city', 'location',
                  'starts_at', 'ends_at', 'organizer', 'registration_link', 'capacity']
        widgets = {
            'title': forms.TextInput(attrs={'class': _INPUT_CLS}),
            'event_type': forms.Select(attrs={'class': _INPUT_CLS}),
            'description': forms.Textarea(attrs={'class': _INPUT_CLS, 'rows': 3}),
            'country': forms.TextInput(attrs={'class': _INPUT_CLS, 'placeholder': _('Defaults to the mission country')}),
            'city': forms.TextInput(attrs={'class': _INPUT_CLS, 'placeholder': _('Defaults to the mission city')}),
            'location': forms.TextInput(attrs={'class': _INPUT_CLS, 'placeholder': _('Venue / address')}),
            'starts_at': forms.DateTimeInput(attrs={'class': _INPUT_CLS, 'type': 'datetime-local'}),
            'ends_at': forms.DateTimeInput(attrs={'class': _INPUT_CLS, 'type': 'datetime-local'}),
            'organizer': forms.TextInput(attrs={'class': _INPUT_CLS, 'placeholder': _('Defaults to the mission name')}),
            'registration_link': forms.URLInput(attrs={'class': _INPUT_CLS}),
            'capacity': forms.NumberInput(attrs={'class': _INPUT_CLS, 'min': 1}),
        }

    def clean(self):
        cleaned = super().clean()
        starts_at, ends_at = cleaned.get('starts_at'), cleaned.get('ends_at')
        if starts_at and ends_at and ends_at <= starts_at:
            self.add_error('ends_at', _('The end time must be after the start time.'))
        return cleaned


class AbuseReportForm(forms.ModelForm):
    class Meta:
        model = AbuseReport
        fields = ['reason', 'details', 'reporter_name', 'reporter_email']
        widgets = {
            'reason': forms.Select(attrs={'class': _INPUT_CLS}),
            'details': forms.Textarea(attrs={'class': _INPUT_CLS, 'rows': 4}),
            'reporter_name': forms.TextInput(attrs={'class': _INPUT_CLS, 'placeholder': _('Optional')}),
            'reporter_email': forms.EmailInput(attrs={'class': _INPUT_CLS, 'placeholder': _('Optional')}),
        }

    def clean_details(self):
        details = self.cleaned_data.get('details', '').strip()
        if len(details) < 10:
            raise forms.ValidationError(_('Please describe the problem (at least 10 characters).'))
        return details

