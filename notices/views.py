from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import user_passes_test
from django.db.models import Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import AdminLoginForm, ContactForm, NoticeForm
from .models import ContactMessage, Notice


def published_notices():
    today = timezone.localdate()
    return Notice.objects.filter(is_published=True).filter(
        Q(expiry_date__isnull=True) | Q(expiry_date__gte=today)
    )


def home(request):
    notices = published_notices()
    return render(request, 'notices/home.html', {
        'categories': Notice.Category.choices,
        'latest_notices': notices[:6],
        'important_notices': notices.filter(is_important=True)[:3],
        'notice_count': notices.count(),
    })


def notice_list(request):
    notices = published_notices()
    search_query = request.GET.get('q', '').strip()
    selected_category = request.GET.get('category', '').strip()

    if search_query:
        notices = notices.filter(
            Q(title__icontains=search_query)
            | Q(description__icontains=search_query)
        )
    if selected_category in Notice.Category.values:
        notices = notices.filter(category=selected_category)

    return render(request, 'notices/notice_list.html', {
        'notices': notices,
        'categories': Notice.Category.choices,
        'search_query': search_query,
        'selected_category': selected_category,
    })


def notice_detail(request, pk):
    notice = get_object_or_404(published_notices(), pk=pk)
    return render(request, 'notices/notice_detail.html', {'notice': notice})


def about(request):
    return render(request, 'notices/about.html')


def contact(request):
    form = ContactForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(
            request,
            'Your message has been received. The college office can follow up using the email you provided.',
        )
        return redirect('contact')
    return render(request, 'notices/contact.html', {'form': form})


def download_notice_pdf(request, pk):
    notice = get_object_or_404(published_notices(), pk=pk)
    if not notice.pdf_file:
        raise Http404('This notice has no PDF attachment.')
    return FileResponse(
        notice.pdf_file.open('rb'),
        as_attachment=True,
        filename=notice.pdf_file.name.rsplit('/', 1)[-1],
        content_type='application/pdf',
    )


def admin_login(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('admin_dashboard')

    form = AdminLoginForm(
        request,
        request.POST or None,
    )
    if request.method == 'POST' and form.is_valid():
        login(request, form.user)
        next_url = request.POST.get('next', '')
        if next_url and url_has_allowed_host_and_scheme(
            next_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            return redirect(next_url)
        return redirect('admin_dashboard')

    return render(request, 'notices/admin_login.html', {'form': form})


staff_required = user_passes_test(
    lambda user: user.is_authenticated and user.is_staff,
    login_url='admin_login',
)


@staff_required
def admin_dashboard(request):
    today = timezone.localdate()
    notices = Notice.objects.all()
    return render(request, 'notices/admin_dashboard.html', {
        'total_notices': notices.count(),
        'published_count': notices.filter(is_published=True).count(),
        'expired_count': notices.filter(expiry_date__lt=today).count(),
        'important_count': notices.filter(is_important=True).count(),
        'recent_notices': notices[:10],
        'today': today,
        'unread_messages_count': ContactMessage.objects.filter(
            is_read=False,
        ).count(),
        'recent_messages': ContactMessage.objects.all()[:5],
    })


@staff_required
def add_notice(request):
    form = NoticeForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Notice added successfully.')
        return redirect('admin_dashboard')

    return render(request, 'notices/add_notice.html', {
        'form': form,
        'page_title': 'Add a notice',
    })


@staff_required
def edit_notice(request, pk):
    notice = get_object_or_404(Notice, pk=pk)
    form = NoticeForm(
        request.POST or None,
        request.FILES or None,
        instance=notice,
    )
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Notice updated successfully.')
        return redirect('admin_dashboard')

    return render(request, 'notices/add_notice.html', {
        'form': form,
        'page_title': 'Edit notice',
        'notice': notice,
    })


@staff_required
def delete_notice(request, pk):
    notice = get_object_or_404(Notice, pk=pk)
    if request.method == 'POST':
        notice.delete()
        messages.success(request, 'Notice deleted successfully.')
        return redirect('admin_dashboard')
    return render(request, 'notices/delete_notice.html', {'notice': notice})


@require_POST
@staff_required
def admin_logout(request):
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('admin_login')
