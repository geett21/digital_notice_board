from datetime import timedelta
import re

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .forms import NoticeForm
from .models import (
    College,
    ContactMessage,
    Notice,
    StudentBranch,
    StudentProfile,
)


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
        self.college = College.objects.create(
            name='Example College',
            code='EXAMPLE',
        )
        StudentProfile.objects.create(
            user=self.student,
            college_name=self.college.name,
            college=self.college,
            mobile_number='+1 555-123-4567',
            branch=StudentBranch.CSE,
        )

    def tearDown(self):
        self.media_settings.disable()

    def create_notice(self, **overrides):
        values = {
            'title': 'Campus update',
            'description': 'A message for students.',
            'category': Notice.Category.GENERAL,
            'college': self.college,
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
        self.client.force_login(self.student)

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

        self.client.force_login(self.student)
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        for category in expected:
            with self.subTest(category=category):
                self.assertContains(response, category)

    def test_student_branches_are_limited_to_supported_options(self):
        response = self.client.get(reverse('student_register'))
        self.assertContains(response, 'value="CSE"')
        self.assertContains(response, 'value="IT"')
        self.assertContains(response, 'value="BCA"')
        self.assertContains(response, 'value="ECE"')

        invalid_response = self.client.post(reverse('student_register'), {
            'username': 'unsupported-branch-student',
            'email': 'unsupported@example.com',
            'password1': 'Strong-Pass-723!',
            'password2': 'Strong-Pass-723!',
            'full_name': 'Unsupported Student',
            'college': self.college.pk,
            'mobile_number': '+1 555-765-4321',
            'branch': 'ADMIN',
            'semester': '1',
        })
        self.assertEqual(invalid_response.status_code, 200)
        self.assertFalse(
            get_user_model().objects.filter(
                username='unsupported-branch-student',
            ).exists(),
        )

    def test_notice_list_search_and_category_filters(self):
        self.create_notice(
            title='Midterm schedule',
            description='Bring your student card.',
            category=Notice.Category.EXAMINATION,
        )
        self.create_notice(
            title='Annual sports meet',
            category=Notice.Category.SPORTS,
            is_important=True,
        )
        self.client.force_login(self.student)

        search_response = self.client.get(
            reverse('notice_list'),
            {'q': 'student card'},
        )
        category_response = self.client.get(
            reverse('notice_list'),
            {'category': Notice.Category.SPORTS},
        )
        important_response = self.client.get(
            reverse('notice_list'),
            {'important': '1'},
        )

        self.assertContains(search_response, 'Midterm schedule')
        self.assertNotContains(search_response, 'Annual sports meet')
        self.assertContains(category_response, 'Annual sports meet')
        self.assertNotContains(category_response, 'Midterm schedule')
        self.assertContains(important_response, 'Annual sports meet')
        self.assertNotContains(important_response, 'Midterm schedule')
        self.assertContains(category_response, 'notice-category-scroll')

    def test_channel_directory_uses_visible_notices_for_categories(self):
        self.create_notice(
            title='Semester examination update',
            category=Notice.Category.EXAMINATION,
        )
        self.create_notice(
            title='Annual campus sports',
            category=Notice.Category.SPORTS,
        )
        self.client.force_login(self.student)

        response = self.client.get(reverse('channel_directory'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Notice categories')
        self.assertContains(response, 'Semester examination update')
        self.assertContains(response, 'Annual campus sports')
        self.assertContains(response, '1 notice')

        academic_response = self.client.get(
            reverse('channel_directory'),
            {'group': 'academic'},
        )
        self.assertContains(academic_response, 'Semester examination update')
        self.assertNotContains(academic_response, 'Annual campus sports')

        search_response = self.client.get(
            reverse('channel_directory'),
            {'q': 'sports'},
        )
        self.assertContains(search_response, 'Annual campus sports')
        self.assertNotContains(search_response, 'Semester examination update')

    def test_channel_directory_requires_notice_board_access(self):
        response = self.client.get(reverse('channel_directory'))
        self.assertRedirects(
            response,
            f'{reverse("student_login")}?next={reverse("channel_directory")}',
        )

    def test_students_only_see_their_branch_and_all_branch_notices(self):
        cse_notice = self.create_notice(
            title='CSE lab schedule',
            target_branch=StudentBranch.CSE,
        )
        self.create_notice(
            title='IT lab schedule',
            target_branch=StudentBranch.IT,
        )
        all_branches_notice = self.create_notice(
            title='College holiday',
            target_branch='ALL',
        )
        self.client.force_login(self.student)

        list_response = self.client.get(reverse('notice_list'))
        home_response = self.client.get(reverse('home'))
        self.assertContains(list_response, cse_notice.title)
        self.assertContains(list_response, all_branches_notice.title)
        self.assertNotContains(list_response, 'IT lab schedule')
        self.assertContains(home_response, cse_notice.title)
        self.assertNotContains(home_response, 'IT lab schedule')

        it_user = get_user_model().objects.create_user(
            username='it-student',
            password='test-it-password-91',
        )
        StudentProfile.objects.create(
            user=it_user,
            college_name=self.college.name,
            college=self.college,
            mobile_number='+1 555-987-6543',
            branch=StudentBranch.IT,
        )
        self.client.force_login(it_user)
        it_list_response = self.client.get(reverse('notice_list'))
        self.assertContains(it_list_response, 'IT lab schedule')
        self.assertContains(it_list_response, all_branches_notice.title)
        self.assertNotContains(it_list_response, cse_notice.title)
        self.assertEqual(
            self.client.get(
                reverse('notice_detail', args=[cse_notice.pk]),
            ).status_code,
            404,
        )
        self.assertEqual(
            self.client.get(
                reverse('download_notice_pdf', args=[cse_notice.pk]),
            ).status_code,
            404,
        )

        self.client.force_login(self.admin)
        admin_list_response = self.client.get(reverse('notice_list'))
        self.assertContains(admin_list_response, cse_notice.title)
        self.assertContains(admin_list_response, 'IT lab schedule')

    def test_notice_detail_and_pdf_download(self):
        notice = self.create_notice(pdf_file=self.pdf_upload())
        self.client.force_login(self.student)

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
        self.client.force_login(self.student)

        for notice in (draft, expired):
            response = self.client.get(
                reverse('notice_detail', args=[notice.pk]),
            )
            self.assertEqual(response.status_code, 404)

    def test_anonymous_users_must_register_or_log_in_to_view_notices(self):
        notice = self.create_notice(title='Members-only notice')

        home_response = self.client.get(reverse('home'))
        self.assertEqual(home_response.status_code, 200)
        self.assertContains(home_response, 'Create student account')
        self.assertContains(home_response, 'Student / User Portal')
        self.assertContains(home_response, f'href="{reverse("admin_login")}"')
        self.assertNotContains(home_response, 'FOR COLLEGE STAFF')
        self.assertNotContains(home_response, notice.title)

        list_response = self.client.get(reverse('notice_list'))
        self.assertRedirects(
            list_response,
            f'{reverse("student_login")}?next={reverse("notice_list")}',
        )
        detail_response = self.client.get(
            reverse('notice_detail', args=[notice.pk]),
        )
        self.assertRedirects(
            detail_response,
            f'{reverse("student_login")}?next={reverse("notice_detail", args=[notice.pk])}',
        )

    def test_student_registration_saves_college_mobile_and_branch(self):
        response = self.client.post(reverse('student_register'), {
            'username': 'new-student',
            'email': 'new.student@gmail.com',
            'full_name': 'New Student',
            'password1': 'Strong-Pass-723!',
            'password2': 'Strong-Pass-723!',
            'college': self.college.pk,
            'mobile_number': '+1 555-765-4321',
            'branch': StudentBranch.IT,
            'semester': '3',
        })

        user = get_user_model().objects.get(username='new-student')
        profile = user.student_profile
        self.assertRedirects(response, reverse('notice_list'))
        self.assertEqual(profile.college_name, self.college.name)
        self.assertEqual(profile.college, self.college)
        self.assertEqual(profile.mobile_number, '+1 555-765-4321')
        self.assertEqual(profile.branch, StudentBranch.IT)
        self.assertEqual(profile.semester, 3)
        self.assertEqual(user.get_full_name(), 'New Student')
        self.assertEqual(user.email, 'new.student@gmail.com')
        self.assertFalse(user.is_staff)
        self.assertIn('_auth_user_id', self.client.session)
        notice = self.create_notice(
            title='Student-only announcement',
            college=profile.college,
        )
        self.assertContains(
            self.client.get(reverse('notice_list')),
            notice.title,
        )

    def test_registration_rejects_colleges_without_a_login_code(self):
        self.college.code = None
        self.college.save(update_fields=['code'])
        registration_page = self.client.get(reverse('student_register'))
        self.assertContains(
            registration_page,
            'Registration is unavailable until a college administrator',
        )

        response = self.client.post(reverse('student_register'), {
            'username': 'unconfigured-college-student',
            'email': 'unconfigured@example.com',
            'full_name': 'Unconfigured Student',
            'password1': 'Strong-Pass-723!',
            'password2': 'Strong-Pass-723!',
            'college': self.college.pk,
            'mobile_number': '+1 555-765-4321',
            'branch': StudentBranch.CSE,
            'semester': '1',
        })

        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            get_user_model().objects.filter(
                username='unconfigured-college-student',
            ).exists(),
        )
        self.assertIn('college', response.context['form'].errors)

    def test_registration_offers_configured_college_and_student_details(self):
        response = self.client.get(reverse('student_register'))
        self.assertContains(response, 'Example College (EXAMPLE)')
        self.assertContains(response, 'Full name')
        self.assertContains(response, 'Registration number')
        self.assertContains(response, 'Gmail address')
        self.assertContains(response, 'Select your semester')
        self.assertContains(response, 'Semester 8')

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    )
    def test_student_password_reset_sends_a_valid_single_use_link(self):
        self.student.email = 'student@gmail.com'
        self.student.save(update_fields=['email'])
        self.admin.email = 'admin@example.com'
        self.admin.save(update_fields=['email'])

        response = self.client.post(reverse('password_reset'), {
            'email': self.student.email,
        })

        self.assertRedirects(response, reverse('password_reset_done'))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('student@gmail.com', mail.outbox[0].to)
        reset_path = re.search(
            r'/student/reset/[^/\s]+/[^/\s]+/',
            mail.outbox[0].body,
        ).group()
        confirmation = self.client.get(reset_path, follow=True)
        self.assertEqual(confirmation.status_code, 200)
        reset_response = self.client.post(
            confirmation.request['PATH_INFO'],
            {
                'new_password1': 'New-Strong-Pass-723!',
                'new_password2': 'New-Strong-Pass-723!',
            },
        )

        self.assertRedirects(
            reset_response,
            reverse('password_reset_complete'),
        )
        self.student.refresh_from_db()
        self.admin.refresh_from_db()
        self.assertTrue(self.student.check_password('New-Strong-Pass-723!'))
        self.assertFalse(self.admin.check_password('New-Strong-Pass-723!'))

    def test_password_reset_response_does_not_disclose_unknown_emails(self):
        response = self.client.post(reverse('password_reset'), {
            'email': 'not-registered@example.com',
        })

        self.assertRedirects(response, reverse('password_reset_done'))
        self.assertEqual(len(mail.outbox), 0)


    def test_student_registration_requires_valid_mobile_and_matching_passwords(self):
        response = self.client.post(reverse('student_register'), {
            'username': 'invalid-student',
            'email': 'invalid.student@gmail.com',
            'full_name': 'Invalid Student',
            'password1': 'Strong-Pass-723!',
            'password2': 'Different-Pass-723!',
            'college': self.college.pk,
            'mobile_number': 'not-a-phone-number',
            'branch': StudentBranch.IT,
            'semester': '2',
        })

        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            get_user_model().objects.filter(username='invalid-student').exists(),
        )
        self.assertContains(response, 'Enter a valid mobile number.')

    def test_student_login_page_shows_requested_controls(self):
        response = self.client.get(reverse('student_login'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Digital Notice Board')
        self.assertContains(response, 'Student Login Portal')
        self.assertContains(response, 'notices/images/favicon.svg')
        self.assertContains(response, 'College Code')
        self.assertContains(response, 'Roll Number / Student ID')
        self.assertContains(response, 'Gmail')
        self.assertContains(response, 'Remember me')
        self.assertContains(response, 'Forgot password?')
        self.assertContains(response, 'Register here')
        self.assertContains(response, 'id="togglePassword"')

    def test_authenticated_homepage_and_navigation_are_role_specific(self):
        self.client.force_login(self.student)
        student_home = self.client.get(reverse('home'))

        self.assertContains(student_home, 'Student Notice Board')
        self.assertContains(student_home, 'Notice board')
        self.assertNotContains(student_home, 'Admin Login')
        self.assertNotContains(student_home, 'FOR COLLEGE STAFF')

        self.client.force_login(self.admin)
        admin_home = self.client.get(reverse('home'))
        self.assertRedirects(admin_home, reverse('admin_dashboard'))
        admin_home = self.client.get(reverse('admin_dashboard'))

        self.assertContains(admin_home, 'Dashboard')
        self.assertNotContains(admin_home, 'Student Notice Board')
        self.assertNotContains(admin_home, '>Notice board</a>')
        self.assertNotContains(admin_home, 'Admin Login')
        self.assertContains(admin_home, 'Create user account')
        self.assertNotContains(admin_home, '>User login</a>')

    def test_admin_can_create_student_without_losing_admin_login(self):
        self.client.force_login(self.admin)

        registration_page = self.client.get(reverse('student_register'))
        self.assertEqual(registration_page.status_code, 200)
        self.assertContains(registration_page, 'Create your account')

        response = self.client.post(reverse('student_register'), {
            'username': 'admin-created-student',
            'email': 'admin.created@gmail.com',
            'full_name': 'Admin Created',
            'password1': 'Strong-Pass-723!',
            'password2': 'Strong-Pass-723!',
            'college': self.college.pk,
            'mobile_number': '+1 555-765-4321',
            'branch': StudentBranch.CSE,
            'semester': '1',
        })

        self.assertRedirects(response, reverse('admin_dashboard'))
        student = get_user_model().objects.get(
            username='admin-created-student',
        )
        self.assertEqual(
            self.client.session['_auth_user_id'],
            str(self.admin.pk),
        )
        self.assertTrue(student.has_usable_password())
        self.assertTrue(student.student_profile)
        self.assertEqual(
            self.client.get(reverse('student_login')).url,
            reverse('admin_dashboard'),
        )

        self.client.post(reverse('admin_logout'))
        login_response = self.client.post(reverse('admin_login'), {
            'username': self.admin.username,
            'password': 'test-admin-password-91',
        })
        self.assertRedirects(login_response, reverse('admin_dashboard'))
        self.assertEqual(
            self.client.session['_auth_user_id'],
            str(self.admin.pk),
        )

    def test_authenticated_roles_cannot_switch_through_other_login_page(self):
        self.client.force_login(self.student)
        self.assertEqual(
            self.client.get(reverse('admin_login')).url,
            reverse('notice_list'),
        )
        self.assertEqual(
            self.client.get(reverse('add_notice')).status_code,
            302,
        )

        self.client.force_login(self.admin)
        self.assertEqual(
            self.client.get(reverse('student_login')).url,
            reverse('admin_dashboard'),
        )

    def test_student_login_validates_college_and_student_logout_requires_post(self):
        admin_response = self.client.post(reverse('student_login'), {
            'college_code': self.college.code,
            'username': self.admin.username,
            'password': 'test-admin-password-91',
        })
        self.assertEqual(admin_response.status_code, 200)
        self.assertContains(admin_response, 'college code, student ID/email, or password is incorrect')
        self.assertNotIn('_auth_user_id', self.client.session)

        wrong_college_response = self.client.post(reverse('student_login'), {
            'college_code': 'OTHER-COLLEGE',
            'username': self.student.username,
            'password': 'test-student-password-91',
        })
        self.assertEqual(wrong_college_response.status_code, 200)
        self.assertContains(wrong_college_response, 'college code, student ID/email, or password is incorrect')
        self.assertNotIn('_auth_user_id', self.client.session)

        other_college = College.objects.create(
            name='Other College',
            code='OTHER',
        )
        matching_credentials_wrong_college = self.client.post(
            reverse('student_login'),
            {
                'college_code': other_college.code,
                'username': self.student.username,
                'password': 'test-student-password-91',
            },
        )
        self.assertContains(
            matching_credentials_wrong_college,
            'college code, student ID/email, or password is incorrect',
        )
        self.assertNotIn('_auth_user_id', self.client.session)

        wrong_password_response = self.client.post(reverse('student_login'), {
            'college_code': self.college.code,
            'username': self.student.username,
            'password': 'incorrect-password',
        })
        self.assertContains(
            wrong_password_response,
            'college code, student ID/email, or password is incorrect',
        )
        self.assertNotIn('_auth_user_id', self.client.session)

        login_response = self.client.post(reverse('student_login'), {
            'college_code': 'example',
            'username': self.student.username,
            'password': 'test-student-password-91',
            'remember_me': 'on',
        })
        self.assertRedirects(login_response, reverse('notice_list'))
        self.assertFalse(self.client.session.get_expire_at_browser_close())
        self.assertEqual(
            self.client.get(reverse('student_logout')).status_code,
            405,
        )
        self.assertEqual(
            self.client.post(reverse('student_logout')).status_code,
            302,
        )

    def test_student_login_without_remember_me_uses_browser_session(self):
        response = self.client.post(reverse('student_login'), {
            'college_code': self.college.code,
            'username': self.student.username,
            'password': 'test-student-password-91',
        })

        self.assertRedirects(response, reverse('notice_list'))
        self.assertTrue(self.client.session.get_expire_at_browser_close())

    def test_student_can_log_in_using_registered_email(self):
        self.student.email = 'student@gmail.com'
        self.student.save(update_fields=['email'])

        response = self.client.post(reverse('student_login'), {
            'college_code': self.college.code,
            'username': 'STUDENT@GMAIL.COM',
            'password': 'test-student-password-91',
        })

        self.assertRedirects(response, reverse('notice_list'))
        self.assertEqual(
            self.client.session['_auth_user_id'],
            str(self.student.pk),
        )

    def test_registration_rejects_duplicate_student_email(self):
        self.student.email = 'already.registered@gmail.com'
        self.student.save(update_fields=['email'])

        response = self.client.post(reverse('student_register'), {
            'username': 'duplicate-email-student',
            'email': 'ALREADY.REGISTERED@gmail.com',
            'full_name': 'Duplicate Email',
            'password1': 'Strong-Pass-723!',
            'password2': 'Strong-Pass-723!',
            'college': self.college.pk,
            'mobile_number': '+1 555-765-4321',
            'branch': StudentBranch.CSE,
            'semester': '1',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'An account with this email address already exists.')
        self.assertFalse(
            get_user_model().objects.filter(
                username='duplicate-email-student',
            ).exists(),
        )

    def test_students_cannot_access_another_colleges_notices(self):
        other_college = College.objects.create(
            name='Other College',
            code='OTHER',
        )
        notice = self.create_notice(
            title='Other college notice',
            college=other_college,
            pdf_file=self.pdf_upload(),
        )
        self.client.force_login(self.student)

        self.assertNotContains(
            self.client.get(reverse('notice_list')),
            notice.title,
        )
        self.assertEqual(
            self.client.get(reverse('notice_detail', args=[notice.pk])).status_code,
            404,
        )
        self.assertEqual(
            self.client.get(
                reverse('download_notice_pdf', args=[notice.pk]),
            ).status_code,
            404,
        )

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
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('admin_login'), response.url)
        self.assertRedirects(
            self.client.get(response.url),
            reverse('notice_list'),
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
        self.assertContains(add_form, 'LIVE PREVIEW')
        self.assertContains(add_form, 'Target branch')
        self.assertContains(add_form, 'broadcastPreviewTitle')
        self.assertEqual(edit_form.status_code, 200)
        self.assertContains(edit_form, 'Current notice')

    def test_admin_dashboard_shows_student_count_and_filters_notices(self):
        self.create_notice(
            title='CSE examination',
            category=Notice.Category.EXAMINATION,
            target_branch=StudentBranch.CSE,
        )
        self.create_notice(
            title='IT sports event',
            category=Notice.Category.SPORTS,
            target_branch=StudentBranch.IT,
        )
        self.client.force_login(self.admin)

        response = self.client.get(
            reverse('admin_dashboard'),
            {
                'category': Notice.Category.SPORTS,
                'branch': StudentBranch.IT,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['student_count'], 1)
        self.assertContains(response, 'IT sports event')
        self.assertNotContains(response, 'CSE examination')

    def test_student_home_shows_profile_and_academic_details(self):
        self.student.first_name = 'Campus'
        self.student.last_name = 'Student'
        self.student.save(update_fields=['first_name', 'last_name'])
        self.student.student_profile.semester = 4
        self.student.student_profile.save(update_fields=['semester'])
        self.client.force_login(self.student)

        response = self.client.get(reverse('home'))

        self.assertContains(response, 'Welcome, Campus Student')
        self.assertContains(response, self.college.name)
        self.assertContains(response, 'CSE')
        self.assertContains(response, 'Semester 4')

    def test_published_notice_requires_a_college(self):
        form_data = {
            'title': 'College notice',
            'description': 'Notice details.',
            'category': Notice.Category.GENERAL,
            'target_branch': 'ALL',
            'is_published': 'on',
        }

        published_form = NoticeForm(data=form_data)
        self.assertFalse(published_form.is_valid())
        self.assertIn('college', published_form.errors)

        draft_form = NoticeForm(data={
            **form_data,
            'is_published': '',
        })
        self.assertTrue(draft_form.is_valid(), draft_form.errors)

    def test_admin_can_add_and_edit_notice(self):
        self.client.force_login(self.admin)
        uploaded_pdf = self.pdf_upload()
        add_response = self.client.post(reverse('add_notice'), {
            'title': 'Exam timetable',
            'description': 'Read the attached timetable.',
            'category': Notice.Category.EXAMINATION,
            'college': self.college.pk,
            'target_branch': StudentBranch.CSE,
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
        self.assertEqual(
            self.client.session['_auth_user_id'],
            str(self.admin.pk),
        )
        self.assertContains(
            self.client.get(reverse('admin_dashboard')),
            'Exam timetable',
        )

        edit_response = self.client.post(
            reverse('edit_notice', args=[notice.pk]),
            {
                'title': 'Updated exam timetable',
                'description': 'The schedule has changed.',
                'category': Notice.Category.EXAMINATION,
                'college': self.college.pk,
                'target_branch': 'ALL',
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
            'college': self.college.pk,
            'target_branch': 'ALL',
            'is_published': 'on',
        }, files={'pdf_file': self.pdf_upload()})
        self.assertTrue(valid_form.is_valid(), valid_form.errors)

        invalid_form = NoticeForm(data={
            'title': 'Not a PDF',
            'description': 'Invalid document.',
            'category': Notice.Category.GENERAL,
            'college': self.college.pk,
            'target_branch': 'ALL',
        }, files={
            'pdf_file': self.pdf_upload(content=b'not a PDF document'),
        })
        self.assertFalse(invalid_form.is_valid())
        self.assertIn('pdf_file', invalid_form.errors)

        oversized_form = NoticeForm(data={
            'title': 'Large PDF',
            'description': 'Too large.',
            'category': Notice.Category.GENERAL,
            'college': self.college.pk,
            'target_branch': 'ALL',
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
        self.assertContains(about_response, 'Lyallpur Khalsa College Technical Campus')
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
