from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import user_passes_test
from django.db.models import Count, OuterRef, Q, Subquery
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import (
    AdminLoginForm,
    ContactForm,
    NoticeForm,
    StudentPasswordResetForm,
    StudentLoginForm,
    StudentRegistrationForm,
)
from .models import ContactMessage, Notice, StudentProfile


def published_notices(user=None):
    today = timezone.localdate()
    notices = Notice.objects.filter(is_published=True).filter(
        Q(expiry_date__isnull=True) | Q(expiry_date__gte=today)
    )
    if user is not None and not user.is_staff:
        college_id = user.student_profile.college_id
        if college_id is None:
            return notices.none()
        notices = notices.filter(college_id=college_id)
        notices = notices.filter(
            Q(target_branch='ALL')
            | Q(target_branch=user.student_profile.branch)
        )
    return notices


def home(request):
    if request.user.is_staff:
        return redirect('admin_dashboard')

    can_view_notices = can_view_notice_board(request.user)
    student_profile = (
        getattr(request.user, 'student_profile', None)
        if can_view_notices and not request.user.is_staff
        else None
    )
    notices = (
        published_notices(request.user)
        if can_view_notices
        else Notice.objects.none()
    )
    return render(request, 'notices/home.html', {
        'categories': Notice.Category.choices,
        'latest_notices': notices[:6],
        'important_notices': notices.filter(is_important=True)[:3],
        'notice_count': notices.count(),
        'can_view_notices': can_view_notices,
        'student_profile': student_profile,
    })


def is_registered_student(user):
    return (
        user.is_authenticated
        and not user.is_staff
        and hasattr(user, 'student_profile')
    )


def can_view_notice_board(user):
    return user.is_staff or is_registered_student(user)


notice_board_required = user_passes_test(
    can_view_notice_board,
    login_url='student_login',
)


def student_register(request):
    if request.user.is_authenticated:
        if is_registered_student(request.user):
            return redirect('notice_list')
        if not request.user.is_staff:
            messages.error(
                request,
                'This account has no student profile. Contact the college administrator.',
            )
            return redirect('home')

    form = StudentRegistrationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        if request.user.is_staff:
            messages.success(request, 'Student account created successfully.')
            return redirect('admin_dashboard')
        login(request, user)
        messages.success(
            request,
            'Student account created. Welcome to the notice board!',
        )
        return redirect('notice_list')
    return render(
        request,
        'notices/student_register.html',
        {'form': form},
    )


def student_login(request):
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect('admin_dashboard')
        if not request.user.is_staff and is_registered_student(request.user):
            return redirect('notice_list')

    form = StudentLoginForm(
        request,
        data=request.POST or None,
    )
    if request.method == 'POST' and form.is_valid():
        login(request, form.get_user())
        request.session.set_expiry(
            None if form.cleaned_data['remember_me'] else 0
        )
        next_url = request.POST.get('next', '')
        if next_url and url_has_allowed_host_and_scheme(
            next_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            return redirect(next_url)
        return redirect('notice_list')
    return render(request, 'notices/student_login.html', {'form': form})


@require_POST
@user_passes_test(is_registered_student, login_url='student_login')
def student_logout(request):
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('student_login')


@notice_board_required
def notice_list(request):
    all_notices = published_notices(request.user)
    category_counts = dict(
        all_notices.values('category')
        .annotate(total=Count('pk'))
        .values_list('category', 'total')
    )
    category_filters = [
        {
            'value': value,
            'label': label,
            'count': category_counts.get(value, 0),
        }
        for value, label in Notice.Category.choices
    ]
    notices = all_notices
    search_query = request.GET.get('q', '').strip()
    selected_category = request.GET.get('category', '').strip()
    important_only = request.GET.get('important') == '1'

    if search_query:
        notices = notices.filter(
            Q(title__icontains=search_query)
            | Q(description__icontains=search_query)
        )
    if selected_category in Notice.Category.values:
        notices = notices.filter(category=selected_category)
    if important_only:
        notices = notices.filter(is_important=True)

    return render(request, 'notices/notice_list.html', {
        'notices': notices,
        'category_filters': category_filters,
        'total_notice_count': all_notices.count(),
        'search_query': search_query,
        'selected_category': selected_category,
        'important_only': important_only,
    })


@notice_board_required
def channel_directory(request):
    notices = published_notices(request.user)
    latest_notice = notices.filter(
        category=OuterRef('category'),
    ).order_by('-created_at', '-pk')
    summaries = {
        summary['category']: summary
        for summary in notices.values('category').annotate(
            total=Count('pk'),
            latest_pk=Subquery(latest_notice.values('pk')[:1]),
            latest_title=Subquery(latest_notice.values('title')[:1]),
            latest_description=Subquery(
                latest_notice.values('description')[:1],
            ),
            latest_created=Subquery(latest_notice.values('created_at')[:1]),
        )
    }

    academic_categories = {
        Notice.Category.EXAMINATION,
        Notice.Category.RESULTS,
        Notice.Category.ADMISSIONS,
        Notice.Category.PLACEMENT,
        Notice.Category.SCHOLARSHIPS,
        Notice.Category.TIME_TABLE,
    }
    student_categories = {
        Notice.Category.EVENTS,
        Notice.Category.HOLIDAYS,
        Notice.Category.SPORTS,
        Notice.Category.GENERAL,
    }
    category_icons = {
        Notice.Category.EXAMINATION: 'bi-journal-check',
        Notice.Category.RESULTS: 'bi-award',
        Notice.Category.EVENTS: 'bi-calendar-event',
        Notice.Category.HOLIDAYS: 'bi-sun',
        Notice.Category.ADMISSIONS: 'bi-mortarboard',
        Notice.Category.SPORTS: 'bi-trophy',
        Notice.Category.PLACEMENT: 'bi-briefcase',
        Notice.Category.GENERAL: 'bi-megaphone',
        Notice.Category.SCHOLARSHIPS: 'bi-cash-coin',
        Notice.Category.TIME_TABLE: 'bi-calendar3',
    }

    query = request.GET.get('q', '').strip()
    selected_group = request.GET.get('group', 'active').strip()
    if selected_group not in {'active', 'academic', 'student', 'all'}:
        selected_group = 'active'

    categories = []
    for value, label in Notice.Category.choices:
        summary = summaries.get(value, {})
        group = (
            'academic' if value in academic_categories else 'student'
        )
        if selected_group == 'active' and not summary:
            continue
        if selected_group in {'academic', 'student'} and group != selected_group:
            continue
        if query and not any(
            query.casefold() in str(text or '').casefold()
            for text in (
                label,
                summary.get('latest_title'),
                summary.get('latest_description'),
            )
        ):
            continue
        categories.append({
            'value': value,
            'label': label,
            'group': group,
            'icon': category_icons[value],
            'total': summary.get('total', 0),
            'latest_pk': summary.get('latest_pk'),
            'latest_title': summary.get('latest_title'),
            'latest_description': summary.get('latest_description'),
            'latest_created': summary.get('latest_created'),
        })

    categories.sort(key=lambda category: (-category['total'], category['label']))
    return render(request, 'notices/channel_directory.html', {
        'categories': categories,
        'popular_categories': [
            category for category in categories if category['total']
        ][:4],
        'query': query,
        'selected_group': selected_group,
        'active_channel_count': sum(
            bool(summary) for summary in summaries.values()
        ),
    })


@notice_board_required
def notice_detail(request, pk):
    notice = get_object_or_404(published_notices(request.user), pk=pk)
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


@notice_board_required
def download_notice_pdf(request, pk):
    notice = get_object_or_404(published_notices(request.user), pk=pk)
    if not notice.pdf_file:
        raise Http404('This notice has no PDF attachment.')
    return FileResponse(
        notice.pdf_file.open('rb'),
        as_attachment=True,
        filename=notice.pdf_file.name.rsplit('/', 1)[-1],
        content_type='application/pdf',
    )


def admin_login(request):
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect('admin_dashboard')
        if is_registered_student(request.user):
            return redirect('notice_list')

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
    branch_options = Notice._meta.get_field('target_branch').choices
    category_options = Notice.Category.choices
    selected_branch = request.GET.get('branch', '').strip()
    selected_category = request.GET.get('category', '').strip()
    recent_notices = notices.select_related('college')
    if selected_branch in dict(branch_options):
        recent_notices = recent_notices.filter(
            target_branch=selected_branch,
        )
    else:
        selected_branch = ''
    if selected_category in Notice.Category.values:
        recent_notices = recent_notices.filter(
            category=selected_category,
        )
    else:
        selected_category = ''
    return render(request, 'notices/admin_dashboard.html', {
        'total_notices': notices.count(),
        'published_count': notices.filter(is_published=True).count(),
        'expired_count': notices.filter(expiry_date__lt=today).count(),
        'important_count': notices.filter(is_important=True).count(),
        'student_count': StudentProfile.objects.count(),
        'recent_notices': recent_notices[:10],
        'branch_options': branch_options,
        'category_options': category_options,
        'selected_branch': selected_branch,
        'selected_category': selected_category,
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
