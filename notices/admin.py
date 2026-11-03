from django.contrib import admin

from .models import College, ContactMessage, Notice, StudentProfile


@admin.register(College)
class CollegeAdmin(admin.ModelAdmin):
    list_display = ('name', 'code')
    search_fields = ('name', 'code')


@admin.register(Notice)
class NoticeAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'category',
        'college',
        'target_branch',
        'created_at',
        'expiry_date',
        'is_important',
        'is_published',
    )
    list_filter = ('college', 'category', 'is_important', 'is_published')
    search_fields = ('title', 'description', 'college__name')
    ordering = ('-created_at',)


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('subject', 'name', 'email', 'submitted_at', 'is_read')
    list_filter = ('is_read', 'submitted_at')
    search_fields = ('name', 'email', 'subject', 'message')
    readonly_fields = ('name', 'email', 'subject', 'message', 'submitted_at')


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'college_name',
        'college',
        'branch',
        'mobile_number',
        'created_at',
    )
    list_filter = ('college', 'branch')
    search_fields = ('user__username', 'college_name', 'branch', 'mobile_number')
    readonly_fields = ('created_at',)
