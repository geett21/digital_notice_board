from django.contrib import admin

from .models import ContactMessage, Notice


@admin.register(Notice)
class NoticeAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'category',
        'created_at',
        'expiry_date',
        'is_important',
        'is_published',
    )
    list_filter = ('category', 'is_important', 'is_published')
    search_fields = ('title', 'description')
    ordering = ('-created_at',)


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('subject', 'name', 'email', 'submitted_at', 'is_read')
    list_filter = ('is_read', 'submitted_at')
    search_fields = ('name', 'email', 'subject', 'message')
    readonly_fields = ('name', 'email', 'subject', 'message', 'submitted_at')
