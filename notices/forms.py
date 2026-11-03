
from django import forms
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.core.validators import RegexValidator
from django.db import transaction

from .models import (
    College,
    ContactMessage,
    Notice,
    StudentBranch,
    StudentProfile,
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
                raise forms.ValidationError(
                    'This account is inactive.'
                )

            if not self.user.is_staff:
                raise forms.ValidationError(
                    'This account does not have administrator access.'
                )

        return cleaned_data


class StudentRegistrationForm(UserCreationForm):

    college_name = forms.CharField(
        max_length=180,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'autocomplete': 'organization',
            'list': 'college-name-suggestions',
            'placeholder': 'Your college name',
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

        self.fields['username'].label = 'Registration number'

        if not self.is_bound:
            self.initial.setdefault(
                'college_name',
                DEFAULT_COLLEGE_NAME,
            )

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
        fields = ('username',)

    @transaction.atomic
    def save(self, commit=True):
        user = super().save(commit=commit)

        if commit:
            college, created = College.objects.get_or_create(
                name=self.cleaned_data['college_name'],
            )

            StudentProfile.objects.create(
                user=user,
                college_name=self.cleaned_data['college_name'],
                college=college,
                mobile_number=self.cleaned_data['mobile_number'],
                branch=self.cleaned_data['branch'],
            )

        return user


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
            'The college code, student ID, or password is incorrect.'
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

        self.college = (
            College.objects.filter(code=code).first()
            if code else None
        )

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
