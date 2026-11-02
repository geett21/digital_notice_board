from django import forms
from django.contrib.auth import authenticate

from .models import ContactMessage, Notice


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


class NoticeForm(forms.ModelForm):
    class Meta:
        model = Notice
        fields = [
            'title',
            'description',
            'category',
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