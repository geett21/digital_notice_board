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
                raise forms.ValidationError('This account is inactive.')
            if not self.user.is_staff:
                raise forms.ValidationError(
                    'This account does not have administrator access.'
                )
        return cleaned_data


class StudentRegistrationForm(UserCreationForm):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'autocomplete': 'email',
            'placeholder': 'Enter your Gmail address',
        }),
    )
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'Registration number'
        self.fields['email'].label = 'Gmail address'
        if not self.is_bound:
            self.initial.setdefault('college_name', DEFAULT_COLLEGE_NAME)
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
        fields = ('username', 'email')

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if get_user_model().objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                'An account with this email address already exists.'
            )
        return email

    @transaction.atomic
    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            StudentProfile.objects.create(
                user=user,
                college_name=self.cleaned_data['college_name'],
                college=College.objects.get_or_create(
                    name=self.cleaned_data['college_name'],
                )[0],
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