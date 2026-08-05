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
