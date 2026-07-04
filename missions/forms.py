from django import forms
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _

from .models import Complaint, EmbassyResponse, ContactMessage, UserProfile


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

