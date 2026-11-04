
import uuid

from django import forms
from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.forms import (
    AuthenticationForm,
    SetPasswordForm,
    UserCreationForm,
)
from django.contrib.auth.password_validation import (
    MinimumLengthValidator,
    get_default_password_validators,
    password_validators_help_text_html,
)
from django.core.validators import RegexValidator
from django.db import transaction
from django.db.models import Q

from .models import (
    College,
    ContactMessage,
    Notice,
    StudentBranch,
    StudentSemester,
    StudentProfile,
)


DEFAULT_COLLEGE_NAME = (
    'LKCTC (Lyallpur Khalsa College Technical Campus, Cantt. Road, Jalandhar)'
)


def password_help_text_without_minimum_length():
    validators = [
        validator
        for validator in get_default_password_validators()
        if not isinstance(validator, MinimumLengthValidator)
    ]
    return password_validators_help_text_html(validators)


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
                raise forms.ValidationError(
                    'This account is inactive.'
                )

            if not self.user.is_staff:
                raise forms.ValidationError(
                    'This account does not have administrator access.'
                )

        return cleaned_data


class AdminRegistrationForm(UserCreationForm):
    signup_code = forms.CharField(
        label='Admin signup code',
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-lg',
            'autocomplete': 'off',
            'placeholder': 'Enter the admin signup code',
        }),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'class': 'form-control form-control-lg',
            'autocomplete': 'username',
            'placeholder': 'Choose a username',
        })
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control form-control-lg',
            'autocomplete': 'new-password',
            'placeholder': 'Create a password',
        })
        self.fields['password1'].help_text = (
            password_help_text_without_minimum_length()
        )
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control form-control-lg',
            'autocomplete': 'new-password',
            'placeholder': 'Enter the password again',
        })

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ('username',)

    def clean_signup_code(self):
        signup_code = self.cleaned_data['signup_code']
        if signup_code != settings.ADMIN_SIGNUP_CODE:
            raise forms.ValidationError('The admin signup code is incorrect.')
        return signup_code

    def save(self, commit=True):
        user = super().save(commit=False)
        user.is_staff = True
        if commit:
            user.save()
        return user


class StudentRegistrationForm(UserCreationForm):
    username = forms.CharField(
        required=False,
        widget=forms.HiddenInput,
    )

    college_code = forms.CharField(
        label='College code',
        max_length=32,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'autocomplete': 'off',
            'placeholder': 'Enter your college code',
        }),
    )

    semester = forms.ChoiceField(
        choices=[
            ('', 'Select your semester'),
            *StudentSemester.choices,
        ],
        widget=forms.Select(attrs={
            'class': 'form-select',
        }),
    )

    mobile_number = forms.CharField(
        max_length=24,
        validators=[
            RegexValidator(
                regex=r'^\+?[0-9][0-9\s()\-]{6,22}$',
                message='Enter a valid mobile number.',
            )
        ],
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.college = None
        self.fields['email'].widget.attrs.update({
            'class': 'form-control',
            'autocomplete': 'email',
            'type': 'email',
            'placeholder': 'Your Gmail address',
        })
        self.order_fields([
            'username',
            'email',
            'college_code',
            'branch',
            'semester',
            'mobile_number',
            'password1',
            'password2',
        ])

        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'autocomplete': 'new-password',
            'placeholder': 'Create a password',
        })
        self.fields['password1'].help_text = (
            password_help_text_without_minimum_length()
        )

        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'autocomplete': 'new-password',
            'placeholder': 'Enter the password again',
        })

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ('username', 'email')

    def clean_username(self):
        username = uuid.uuid4().hex
        while get_user_model().objects.filter(username=username).exists():
            username = uuid.uuid4().hex
        return username

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if not email.endswith('@gmail.com'):
            raise forms.ValidationError('Enter a valid Gmail address.')
        return email

    def clean_college_code(self):
        code = self.cleaned_data['college_code'].strip()
        self.college = College.objects.filter(code__iexact=code).first()
        if self.college is None:
            raise forms.ValidationError(
                'Enter a valid college code provided by your college.'
            )
        return code

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        if email and self.college and get_user_model().objects.filter(
            email__iexact=email,
            student_profile__college=self.college,
        ).exists():
            self.add_error(
                'email',
                'An account with this Gmail address already exists for this college.',
            )
        return cleaned_data

    @transaction.atomic
    def save(self, commit=True):
        user = super().save(commit=commit)

        if commit:
            StudentProfile.objects.create(
                user=user,
                college_name=self.college.name,
                college=self.college,
                mobile_number=self.cleaned_data['mobile_number'],
                branch=self.cleaned_data['branch'],
                semester=self.cleaned_data['semester'],
            )

        return user


class StudentSetPasswordForm(SetPasswordForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['new_password1'].help_text = (
            password_help_text_without_minimum_length()
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
            'The college code, Gmail address, or password is incorrect.'
        ),
    }

    def __init__(self, request=None, *args, **kwargs):
        super().__init__(request, *args, **kwargs)

        self.college = None

        self.order_fields([
            'college_code',
            'username',
            'password',
            'remember_me',
        ])

        self.fields['username'].label = 'Gmail address'

        self.fields['username'].widget.attrs.update({
            'class': 'form-control form-control-lg',
            'autocomplete': 'email',
            'type': 'email',
            'placeholder': 'Enter your Gmail address',
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
        cleaned_data = self.cleaned_data
        code = cleaned_data.get('college_code', '').strip()
        email = cleaned_data.get('username', '').strip()
        password = cleaned_data.get('password')
        self.college = (
            College.objects.filter(code__iexact=code).first()
            if code else None
        )

        if email and password and self.college:
            candidates = get_user_model().objects.filter(
                Q(email__iexact=email) | Q(username__iexact=email),
                is_active=True,
                is_staff=False,
                student_profile__college=self.college,
            ).distinct()
            self.user_cache = next(
                (
                    candidate
                    for candidate in candidates
                    if candidate.check_password(password)
                ),
                None,
            )

        if self.user_cache is None:
            raise forms.ValidationError(
                self.error_messages['invalid_login'],
                code='invalid_login',
            )

        self.user = self.user_cache
        self.confirm_login_allowed(self.user_cache)
        return cleaned_data

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


class StudentPasswordResetForm(forms.Form):

    username = forms.CharField(
        label='Registration number',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your registration number',
        }),
    )

    college_code = forms.CharField(
        label='College Code',
        max_length=32,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your college code',
        }),
    )

    def clean(self):
        cleaned_data = super().clean()

        username = cleaned_data.get('username')
        college_code = cleaned_data.get('college_code', '').strip().upper()

        if username and college_code:
            user = get_user_model().objects.filter(
                username=username,
                is_active=True,
                is_staff=False,
            ).first()

            college = College.objects.filter(
                code=college_code,
            ).first()

            if (
                user is None
                or college is None
                or not hasattr(user, 'student_profile')
                or user.student_profile.college_id != college.pk
            ):
                raise forms.ValidationError(
                    'Invalid registration number or college code.'
                )

            cleaned_data['user'] = user

        return cleaned_data


class NoticeForm(forms.ModelForm):

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

            'category': forms.Select(attrs={
                'class': 'form-select',
            }),

            'college': forms.Select(attrs={
                'class': 'form-select',
            }),

            'target_branch': forms.Select(attrs={
                'class': 'form-select',
            }),

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

        fields = [
            'name',
            'email',
            'subject',
            'message',
        ]

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
