"""
context_processors.py
----------------------
A "context processor" is a small function that Django runs for EVERY page
request and adds its return value into every template's context automatically.

We use this so the navbar and footer (which appear on every single page) can
show the NGO name and contact info from SiteSettings, without us having to
manually pass it from every single view function.
"""

from django.db.utils import OperationalError, ProgrammingError

from .models import SiteSettings, UserProfile


def site_settings(request):
    """Makes {{ site_settings }} available in every template automatically."""
    return {'site_settings': SiteSettings.load()}


def user_profile(request):
    """
    Makes {{ nav_user_profile }} available in every template automatically,
    so the navbar can show the logged-in donor's profile picture without
    every single view having to fetch it manually.
    """
    if request.user.is_authenticated:
        try:
            profile, _ = UserProfile.objects.get_or_create(user=request.user)
            return {'nav_user_profile': profile}
        except (OperationalError, ProgrammingError):
                # This happens if a database migration hasn't been applied yet
                # (e.g. "python manage.py migrate" wasn't run after a model change).
                # We fail quietly here instead of crashing every page on the site --
                # the navbar/sidebar will just show the default icon until the
                # missing migration is applied.
            return {'nav_user_profile': None}
    return {'nav_user_profile': None}


def admin_alerts(request):
    """
    Makes unread-message / new-help-request badge counts AND latest notifications
    available on every admin page (sidebar + topbar bell), not just the dashboard.
    Only runs the queries for logged-in staff, to avoid extra DB work
    on the public site.
    """
    if request.path.startswith('/myadmin/') and request.user.is_authenticated and request.user.is_staff:
        try:
            from .models import ContactMessage, HelpRequest, Notification

            # Auto-mark notifications as read when the admin visits the corresponding page/detail
            if request.path.startswith('/myadmin/requests/'):
                Notification.objects.filter(notification_type='help_request', is_read=False).update(is_read=True)
            elif request.path.startswith('/myadmin/messages/'):
                Notification.objects.filter(notification_type='contact_message', is_read=False).update(is_read=True)
            elif request.path.startswith('/myadmin/donations/'):
                Notification.objects.filter(notification_type='donation', is_read=False).update(is_read=True)
            elif request.path.startswith('/myadmin/testimonials/') or request.path.startswith('/myadmin/site-settings/'):
                Notification.objects.filter(notification_type='story_submission', is_read=False).update(is_read=True)

            unread = ContactMessage.objects.filter(is_read=False).count()
            new_requests = HelpRequest.objects.filter(status='new').count()
            latest_notifications = Notification.objects.order_by('is_read', '-created_at')[:5]
            unread_notifications_count = Notification.objects.filter(is_read=False).count()
            return {
                'unread_messages_badge': unread,
                'new_help_requests_badge': new_requests,
                'total_alerts_badge': unread + new_requests,
                'latest_notifications': latest_notifications,
                'unread_notifications_count': unread_notifications_count,
            }
        except (OperationalError, ProgrammingError):
            pass
    return {}


def donation_appeals(request):
    """Makes active donation appeals available in every template automatically."""
    from .models import DonationAppeal
    from django.db.models import Q
    try:
        appeals = DonationAppeal.objects.filter(
            Q(campaign__isnull=True) | Q(campaign__status='active'),
            is_published=True
        ).select_related('campaign').prefetch_related('supply_items').order_by('display_order', '-created_at')
        return {'donation_appeals': appeals}
    except (OperationalError, ProgrammingError):
        return {'donation_appeals': []}
