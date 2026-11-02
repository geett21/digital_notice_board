from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),

    path('notices/', views.notice_list, name='notice_list'),
    path('notices/<int:pk>/', views.notice_detail, name='notice_detail'),
    path(
        'notices/<int:pk>/download/',
        views.download_notice_pdf,
        name='download_notice_pdf',
    ),

    path('admin-login/', views.admin_login, name='admin_login'),
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),

    path('add-notice/', views.add_notice, name='add_notice'),
    path('edit-notice/<int:pk>/', views.edit_notice, name='edit_notice'),
    path('delete-notice/<int:pk>/', views.delete_notice, name='delete_notice'),

    path('logout/', views.admin_logout, name='admin_logout'),
]