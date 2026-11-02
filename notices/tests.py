from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .forms import NoticeForm
from .models import ContactMessage, Notice


class NoticeBoardTests(TestCase):
    def setUp(self):
        self.media_settings = override_settings(
            STORAGES={
                'default': {
                    'BACKEND': 'django.core.files.storage.InMemoryStorage',
                },
                'staticfiles': {
                    'BACKEND': (
                        'django.contrib.staticfiles.storage.StaticFilesStorage'
                    ),
                },
            },
        )
        self.media_settings.enable()
        user_model = get_user_model()
        self.admin = user_model.objects.create_user(
            username='board-admin',
            password='test-admin-password-91',
            is_staff=True,
        )
        self.student = user_model.objects.create_user(
            username='student',
            password='test-student-password-91',
        )

    def tearDown(self):
        self.media_settings.disable()

    def create_notice(self, **overrides):
        values = {
            'title': 'Campus update',
            'description': 'A message for students.',
            'category': Notice.Category.GENERAL,
            'is_published': True,
        }
        values.update(overrides)
        return Notice.objects.create(**values)

    def pdf_upload(self, name='notice.pdf', content=b'%PDF-1.4\ncollege notice'):
        return SimpleUploadedFile(name, content, content_type='application/pdf')

    def test_homepage_loads_and_only_counts_current_public_notices(self):
        self.create_notice(title='Visible update')
        self.create_notice(title='Hidden draft', is_published=False)
        self.create_notice(
            title='Expired update',
            expiry_date=timezone.localdate() - timedelta(days=1),
        )

        response = self.client.get(reverse('home'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Visible update')
        self.assertNotContains(response, 'Hidden draft')
        self.assertNotContains(response, 'Expired update')
        self.assertEqual(response.context['notice_count'], 1)

    def test_all_requested_categories_are_available(self):
        expected = {
            'Examination',
            'Results',
            'Events',
            'Holidays',
            'Admissions',
            'Sports',
            'Placement',
            'General',
            'Scholarships',
            'Time Table',
        }
        self.assertEqual(set(Notice.Category.values), expected)

        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        for category in expected:
            with self.subTest(category=category):
                self.assertContains(response, category)

    def test_notice_list_search_and_category_filters(self):
        self.create_notice(
            title='Midterm schedule',
            description='Bring your student card.',
            category=Notice.Category.EXAMINATION,
        )
        self.create_notice(
            title='Annual sports meet',
            category=Notice.Category.SPORTS,
        )

        search_response = self.client.get(
            reverse('notice_list'),
            {'q': 'student card'},
        )
        category_response = self.client.get(
            reverse('notice_list'),
            {'category': Notice.Category.SPORTS},
        )

        self.assertContains(search_response, 'Midterm schedule')
        self.assertNotContains(search_response, 'Annual sports meet')
        self.assertContains(category_response, 'Annual sports meet')
        self.assertNotContains(category_response, 'Midterm schedule')

    def test_notice_detail_and_pdf_download(self):
        notice = self.create_notice(pdf_file=self.pdf_upload())

        detail_response = self.client.get(
            reverse('notice_detail', args=[notice.pk]),
        )
        download_response = self.client.get(
            reverse('download_notice_pdf', args=[notice.pk]),
        )

        self.assertContains(detail_response, notice.title)
        self.assertEqual(download_response.status_code, 200)
        self.assertEqual(
            download_response['Content-Type'],
            'application/pdf',
        )
        self.assertIn('attachment', download_response['Content-Disposition'])
        downloaded_pdf = b''.join(download_response.streaming_content)
        download_response.close()
        self.assertEqual(downloaded_pdf, b'%PDF-1.4\ncollege notice')

    def test_unpublished_and_expired_notices_are_not_public(self):
        draft = self.create_notice(is_published=False)
        expired = self.create_notice(
            expiry_date=timezone.localdate() - timedelta(days=1),
        )

        for notice in (draft, expired):
            response = self.client.get(
                reverse('notice_detail', args=[notice.pk]),
            )
            self.assertEqual(response.status_code, 404)

    def test_admin_login_authenticates_staff_and_rejects_student(self):
        response = self.client.post(reverse('admin_login'), {
            'username': self.admin.username,
            'password': 'test-admin-password-91',
        })
        self.assertRedirects(response, reverse('admin_dashboard'))

        self.client.logout()
        response = self.client.post(reverse('admin_login'), {
            'username': self.student.username,
            'password': 'test-student-password-91',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'does not have administrator access')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_admin_pages_require_staff_and_logout_requires_post(self):
        dashboard_url = reverse('admin_dashboard')
        response = self.client.get(dashboard_url)
        self.assertRedirects(
            response,
            f'{reverse("admin_login")}?next={dashboard_url}',
        )

        self.client.force_login(self.student)
        response = self.client.get(dashboard_url)
        self.assertRedirects(
            response,
            f'{reverse("admin_login")}?next={dashboard_url}',
        )
        self.client.force_login(self.admin)
        self.assertEqual(
            self.client.get(reverse('admin_logout')).status_code,
            405,
        )
        self.assertEqual(
            self.client.post(reverse('admin_logout')).status_code,
            302,
        )

    def test_dashboard_counts_notices_and_management_forms_render(self):
        active = self.create_notice(title='Current notice')
        self.create_notice(
            title='Unpublished notice',
            is_published=False,
        )
        self.create_notice(
            title='Expired notice',
            expiry_date=timezone.localdate() - timedelta(days=1),
        )
        self.client.force_login(self.admin)

        dashboard = self.client.get(reverse('admin_dashboard'))
        add_form = self.client.get(reverse('add_notice'))
        edit_form = self.client.get(
            reverse('edit_notice', args=[active.pk]),
        )

        self.assertEqual(dashboard.status_code, 200)
        self.assertEqual(dashboard.context['total_notices'], 3)
        self.assertEqual(dashboard.context['published_count'], 2)
        self.assertEqual(dashboard.context['expired_count'], 1)
        self.assertEqual(add_form.status_code, 200)
        self.assertContains(add_form, 'Save notice')
        self.assertEqual(edit_form.status_code, 200)
        self.assertContains(edit_form, 'Current notice')

    def test_admin_can_add_and_edit_notice(self):
        self.client.force_login(self.admin)
        uploaded_pdf = self.pdf_upload()
        add_response = self.client.post(reverse('add_notice'), {
            'title': 'Exam timetable',
            'description': 'Read the attached timetable.',
            'category': Notice.Category.EXAMINATION,
            'is_important': 'on',
            'is_published': 'on',
            'pdf_file': uploaded_pdf,
        })
        uploaded_pdf.close()

        self.assertRedirects(add_response, reverse('admin_dashboard'))
        notice = Notice.objects.get(title='Exam timetable')
        self.assertTrue(notice.is_published)
        self.assertTrue(notice.is_important)
        self.assertTrue(notice.pdf_file.name.endswith('.pdf'))

        edit_response = self.client.post(
            reverse('edit_notice', args=[notice.pk]),
            {
                'title': 'Updated exam timetable',
                'description': 'The schedule has changed.',
                'category': Notice.Category.EXAMINATION,
                'expiry_date': '',
                'is_published': 'on',
            },
        )
        notice.refresh_from_db()
        self.assertRedirects(edit_response, reverse('admin_dashboard'))
        self.assertEqual(notice.title, 'Updated exam timetable')
        self.assertFalse(notice.is_important)

    def test_admin_delete_requires_confirmation_post(self):
        self.client.force_login(self.admin)
        notice = self.create_notice()

        confirmation = self.client.get(
            reverse('delete_notice', args=[notice.pk]),
        )
        self.assertEqual(confirmation.status_code, 200)
        self.assertTrue(Notice.objects.filter(pk=notice.pk).exists())

        response = self.client.post(
            reverse('delete_notice', args=[notice.pk]),
        )
        self.assertRedirects(response, reverse('admin_dashboard'))
        self.assertFalse(Notice.objects.filter(pk=notice.pk).exists())

    def test_pdf_upload_validation(self):
        valid_form = NoticeForm(data={
            'title': 'PDF notice',
            'description': 'Valid PDF content.',
            'category': Notice.Category.GENERAL,
            'is_published': 'on',
        }, files={'pdf_file': self.pdf_upload()})
        self.assertTrue(valid_form.is_valid(), valid_form.errors)

        invalid_form = NoticeForm(data={
            'title': 'Not a PDF',
            'description': 'Invalid document.',
            'category': Notice.Category.GENERAL,
        }, files={
            'pdf_file': self.pdf_upload(content=b'not a PDF document'),
        })
        self.assertFalse(invalid_form.is_valid())
        self.assertIn('pdf_file', invalid_form.errors)

        oversized_form = NoticeForm(data={
            'title': 'Large PDF',
            'description': 'Too large.',
            'category': Notice.Category.GENERAL,
        }, files={
            'pdf_file': self.pdf_upload(
                content=b'%PDF-' + b'x' * (10 * 1024 * 1024),
            ),
        })
        self.assertFalse(oversized_form.is_valid())
        self.assertIn('pdf_file', oversized_form.errors)

    def test_about_page_and_contact_message_submission(self):
        about_response = self.client.get(reverse('about'))
        contact_response = self.client.get(reverse('contact'))
        self.assertContains(about_response, 'About the College Digital Notice Board')
        self.assertEqual(contact_response.status_code, 200)

        response = self.client.post(reverse('contact'), {
            'name': 'Student Visitor',
            'email': 'student@example.com',
            'subject': 'Notice board question',
            'message': 'Where can I find the latest timetable?',
        })

        self.assertRedirects(response, reverse('contact'))
        inquiry = ContactMessage.objects.get()
        self.assertEqual(inquiry.name, 'Student Visitor')
        self.assertFalse(inquiry.is_read)
