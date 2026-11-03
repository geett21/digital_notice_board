from django import forms
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordResetForm,
    UserCreationForm,
)
from django.core.validators import RegexValidator
from django.db import transaction
from django.db.models import Q

from .models import (
    College,
    ContactMessage,
    Notice,
    StudentBranch,
    StudentProfile,
    StudentSemester,
)


DEFAULT_COLLEGE_NAME = (
    'LKCTC (Lyallpur Khalsa College Technical Campus, Cantt. Road, Jalandhar)'
)


class AdminLoginForm(forms.Form):
    username = forms.CharField(
        label='Username',
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'autocomplete': 'username',
            'autofocus': True,
            'placeholder': 'Enter your username',
        }),
    )
    password = forms.CharField(
        label='Password',
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-lg',
            'autocomplete': 'current-password',
            'placeholder': 'Enter your password',
        }),
    )

    def __init__(self, request=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.request = request
        self.user = None

    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get('username')
        password = cleaned_data.get('password')
        if username and password:
            self.user = authenticate(
                self.request,
                username=username,
                password=password,
            )
            if self.user is None:
                raise forms.ValidationError(
                    'The username or password is incorrect.'
                )
            if not self.user.is_active:
                raise forms.ValidationError('This account is inactive.')
            if not self.user.is_staff:
                raise forms.ValidationError(
                    'This account does not have administrator access.'
                )
        return cleaned_data


class StudentRegistrationForm(UserCreationForm):
    full_name = forms.CharField(
        label='Full name',
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'autocomplete': 'name',
            'placeholder': 'Enter your full name',
        }),
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'autocomplete': 'email',
            'placeholder': 'Enter your Gmail address',
        }),
    )
    college = forms.ModelChoiceField(
        queryset=College.objects.none(),
        empty_label='Select your college',
        help_text='Choose the college whose code you will use to log in.',
        widget=forms.Select(attrs={
            'class': 'form-select',
            'autocomplete': 'organization',
        }),
    )
    mobile_number = forms.CharField(
        max_length=24,
        validators=[RegexValidator(
            regex=r'^\+?[0-9][0-9\s()\-]{6,22}$',
            message='Enter a valid mobile number.',
        )],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'type': 'tel',
            'autocomplete': 'tel',
            'placeholder': 'Your mobile number',
        }),
    )
    branch = forms.ChoiceField(
        choices=[
            ('', 'Select your branch'),
            *StudentBranch.choices,
        ],
        widget=forms.Select(attrs={
            'class': 'form-select',
        }),
    )
    semester = forms.TypedChoiceField(
        choices=[
            ('', 'Select your semester'),
            *StudentSemester.choices,
        ],
        coerce=int,
        empty_value=None,
        widget=forms.Select(attrs={
            'class': 'form-select',
        }),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'Registration number'
        self.fields['email'].label = 'Gmail address'
        colleges = College.objects.filter(
            Q(code__isnull=False) & ~Q(code=''),
        ).order_by('name')
        self.fields['college'].queryset = colleges
        if not colleges.exists():
            self.fields['college'].help_text = (
                'Registration is unavailable until a college administrator '
                'adds a college and login code.'
            )
        if not self.is_bound and 'college' not in self.initial:
            default_college = self.fields['college'].queryset.filter(
                name=DEFAULT_COLLEGE_NAME,
            ).first()
            if default_college:
                self.initial['college'] = default_college.pk
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'autocomplete': 'username',
            'placeholder': 'Enter your registration number',
        })
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'autocomplete': 'new-password',
            'placeholder': 'Create a password',
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'autocomplete': 'new-password',
            'placeholder': 'Enter the password again',
        })

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ('full_name', 'username', 'email', 'college')

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if get_user_model().objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                'An account with this email address already exists.'
            )
        return email

    def clean_full_name(self):
        return ' '.join(self.cleaned_data['full_name'].split())

    @transaction.atomic
    def save(self, commit=True):
        user = super().save(commit=False)
        name_parts = self.cleaned_data['full_name'].split(maxsplit=1)
        user.first_name = name_parts[0]
        user.last_name = name_parts[1] if len(name_parts) > 1 else ''
        if commit:
            user.save()
            college = self.cleaned_data['college']
            StudentProfile.objects.create(
                user=user,
                college_name=college.name,
                college=college,
                mobile_number=self.cleaned_data['mobile_number'],
                branch=self.cleaned_data['branch'],
                semester=self.cleaned_data['semester'],
            )
        return user


class StudentPasswordResetForm(PasswordResetForm):
    email = forms.EmailField(
        label='Student account email',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'autocomplete': 'email',
            'placeholder': 'Enter your registered email',
        }),
    )

    def get_users(self, email):
        user_model = get_user_model()
        active_users = user_model._default_manager.filter(
            email__iexact=email,
            is_active=True,
            is_staff=False,
            student_profile__isnull=False,
        )
        return (
            user for user in active_users
            if user.has_usable_password()
        )


class StudentLoginForm(AuthenticationForm):
    college_code = forms.CharField(
        label='College Code',
        max_length=32,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'autocomplete': 'organization',
            'placeholder': 'Enter your college code',
        }),
    )
    remember_me = forms.BooleanField(required=False)

    error_messages = {
        **AuthenticationForm.error_messages,
        'invalid_login': (
            'The college code, student ID/email, or password is incorrect.'
        ),
    }

    def __init__(self, request=None, *args, **kwargs):
        super().__init__(request, *args, **kwargs)
        self.college = None
        self.order_fields(['college_code', 'username', 'password', 'remember_me'])
        self.fields['username'].label = 'Roll Number / Student ID'
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'autocomplete': 'username',
            'placeholder': 'Enter your roll number or student ID',
        })
        self.fields['password'].widget.attrs.update({
            'class': 'form-control',
            'autocomplete': 'current-password',
            'placeholder': 'Enter your password',
        })
        self.fields['remember_me'].widget.attrs.update({
            'class': 'form-check-input',
        })

    def clean(self):
        code = self.data.get('college_code', '').strip().upper()
        self.college = College.objects.filter(code=code).first() if code else None
        identifier = self.cleaned_data.get('username', '').strip()
        if '@' in identifier:
            user = get_user_model().objects.filter(
                email__iexact=identifier,
            ).first()
            if user is not None:
                self.cleaned_data['username'] = user.get_username()
        return super().clean()

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if user.is_staff:
            raise forms.ValidationError(
                self.error_messages['invalid_login'],
                code='invalid_login',
            )
        if not hasattr(user, 'student_profile'):
            raise forms.ValidationError(
                self.error_messages['invalid_login'],
                code='invalid_login',
            )
        if (
            self.college is None
            or user.student_profile.college_id != self.college.pk
        ):
            raise forms.ValidationError(
                self.error_messages['invalid_login'],
                code='invalid_login',
            )


class NoticeForm(forms.ModelForm):
    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('is_published') and not cleaned_data.get('college'):
            self.add_error(
                'college',
                'Select a college before publishing this notice.',
            )
        return cleaned_data

    class Meta:
        model = Notice
        fields = [
            'title',
            'description',
            'category',
            'college',
            'target_branch',
            'pdf_file',
            'expiry_date',
            'is_important',
            'is_published',
        ]

        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter notice title',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Enter notice details',
                'rows': 5,
            }),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'college': forms.Select(attrs={'class': 'form-select'}),
            'target_branch': forms.Select(attrs={'class': 'form-select'}),
            'expiry_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control',
            }),
            'pdf_file': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,application/pdf',
            }),
            'is_important': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
            'is_published': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
        }


class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ['name', 'email', 'subject', 'message']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'autocomplete': 'name',
                'placeholder': 'Your name',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'autocomplete': 'email',
                'placeholder': 'you@example.com',
            }),
            'subject': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'How can we help?',
            }),
            'message': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Write your message',
            }),
        }