from django.core.validators import FileExtensionValidator
from django.db import models
from django.conf import settings

from .validators import validate_pdf_file


class StudentBranch(models.TextChoices):
    CSE = 'CSE', 'CSE'
    IT = 'IT', 'IT'
    BCA = 'BCA', 'BCA'
    ECE = 'ECE', 'ECE'


NOTICE_BRANCH_CHOICES = [
    ('ALL', 'All branches'),
    *StudentBranch.choices,
]


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
    college = models.ForeignKey(
        'College',
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name='notices',
    )
    target_branch = models.CharField(
        max_length=10,
        choices=NOTICE_BRANCH_CHOICES,
        default='ALL',
    )
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


class College(models.Model):
    name = models.CharField(max_length=180, unique=True)
    code = models.CharField(
        max_length=32,
        unique=True,
        blank=True,
        null=True,
    )

    class Meta:
        ordering = ['name']

    def save(self, *args, **kwargs):
        if self.code is not None:
            self.code = self.code.strip().upper() or None
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.name} ({self.code or "Code not set"})'


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


class StudentProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='student_profile',
    )
    college_name = models.CharField(max_length=180)
    college = models.ForeignKey(
        College,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name='students',
    )
    mobile_number = models.CharField(max_length=24)
    branch = models.CharField(
        max_length=10,
        choices=StudentBranch.choices,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.user.get_username()} - {self.college_name}'
