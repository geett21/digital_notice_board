from django.core.validators import FileExtensionValidator
from django.db import models

from .validators import validate_pdf_file


class Notice(models.Model):
    class Category(models.TextChoices):
        EXAMINATION = 'Examination', 'Examination'
        RESULTS = 'Results', 'Results'
        EVENTS = 'Events', 'Events'
        HOLIDAYS = 'Holidays', 'Holidays'
        ADMISSIONS = 'Admissions', 'Admissions'
        SPORTS = 'Sports', 'Sports'
        PLACEMENT = 'Placement', 'Placement'
        GENERAL = 'General', 'General'
        SCHOLARSHIPS = 'Scholarships', 'Scholarships'
        TIME_TABLE = 'Time Table', 'Time Table'

    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.CharField(max_length=50, choices=Category.choices)
    pdf_file = models.FileField(
        upload_to='notices/',
        blank=True,
        null=True,
        validators=[FileExtensionValidator(['pdf']), validate_pdf_file],
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expiry_date = models.DateField(blank=True, null=True)
    is_important = models.BooleanField(default=False)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at', '-pk']

    def __str__(self):
        return self.title


class ContactMessage(models.Model):
    name = models.CharField(max_length=120)
    email = models.EmailField()
    subject = models.CharField(max_length=180)
    message = models.TextField(max_length=5000)
    submitted_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['-submitted_at', '-pk']

    def __str__(self):
        return self.subject
