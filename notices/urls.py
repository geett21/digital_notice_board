from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import views
from .forms import StudentPasswordResetForm

urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),

    path('student/register/', views.student_register, name='student_register'),
    path('student/login/', views.student_login, name='student_login'),
    path('student/logout/', views.student_logout, name='student_logout'),
    path(
        'student/password-reset/',
        auth_views.PasswordResetView.as_view(
            form_class=StudentPasswordResetForm,
            template_name='notices/password_reset_form.html',
            email_template_name='notices/password_reset_email.txt',
            subject_template_name='notices/password_reset_subject.txt',
            success_url=reverse_lazy('password_reset_done'),
        ),
        name='password_reset',
    ),
    path(
        'student/password-reset/done/',
        auth_views.PasswordResetDoneView.as_view(
            template_name='notices/password_reset_done.html',
        ),
        name='password_reset_done',
    ),
    path(
        'student/reset/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='notices/password_reset_confirm.html',
            success_url=reverse_lazy('password_reset_complete'),
        ),
        name='password_reset_confirm',
    ),
    path(
        'student/reset/complete/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='notices/password_reset_complete.html',
        ),
        name='password_reset_complete',
    ),

    path('channels/', views.channel_directory, name='channel_directory'),
    path('notices/', views.notice_list, name='notice_list'),
    path('notices/<int:pk>/', views.notice_detail, name='notice_detail'),
    path(
        'notices/<int:pk>/download/',
        views.download_notice_pdf,
        name='download_notice_pdf',
    ),
    path(
    'student/password-reset/',
    views.student_password_reset,
    name='student_password_reset',
),

    path('admin-login/', views.admin_login, name='admin_login'),
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),

    path('add-notice/', views.add_notice, name='add_notice'),
    path('edit-notice/<int:pk>/', views.edit_notice, name='edit_notice'),
    path('delete-notice/<int:pk>/', views.delete_notice, name='delete_notice'),

    path('logout/', views.admin_logout, name='admin_logout'),
]