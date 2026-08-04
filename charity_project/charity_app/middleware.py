"""
middleware.py
--------------
WHY THIS FILE EXISTS
--------------------
By default, Django stores EVERY logged-in user (donor or staff) using the SAME
browser cookie ("sessionid"). That means if a donor is logged in and a staff
member then logs into the admin panel in the SAME browser, Django overwrites
that one shared cookie -- so the donor gets logged out (and vice versa).

THE FIX
-------
DualSessionMiddleware gives the admin panel (any URL starting with "/myadmin/")
its OWN separate cookie, called "admin_sessionid", completely independent from
the normal donor cookie ("sessionid"). This means:

- A donor can be logged in on the public site (using the "sessionid" cookie)
- A staff member can ALSO be logged in on the admin panel in the SAME browser
  (using the "admin_sessionid" cookie)
- Logging out of one does NOT affect the other

This is a drop-in replacement for Django's built-in SessionMiddleware -- it
works exactly the same way, it just picks a different cookie name depending
on whether the request is for "/myadmin/..." or for the rest of the site.
"""

import time

from django.conf import settings
from django.contrib.sessions.backends.base import UpdateError
from django.contrib.sessions.exceptions import SessionInterrupted
from django.contrib.sessions.middleware import SessionMiddleware
from django.utils.cache import patch_vary_headers
from django.utils.http import http_date


class DualSessionMiddleware(SessionMiddleware):

    # The donor-facing site keeps using Django's normal cookie name (usually "sessionid").
    DONOR_COOKIE_NAME = settings.SESSION_COOKIE_NAME

    # The custom admin panel gets its own, completely separate cookie.
    ADMIN_COOKIE_NAME = 'admin_sessionid'

    # Every URL that starts with this prefix is treated as "the admin panel"
    ADMIN_URL_PREFIX = '/myadmin/'

    def _cookie_name_for(self, request):
        """Decide which cookie this request should use, based on its URL."""
        if request.path.startswith(self.ADMIN_URL_PREFIX):
            return self.ADMIN_COOKIE_NAME
        return self.DONOR_COOKIE_NAME

    def process_request(self, request):
        # Remember which cookie name this request is using, so process_response
        # (below) knows where to save the session back to.
        cookie_name = self._cookie_name_for(request)
        request._dual_session_cookie_name = cookie_name

        session_key = request.COOKIES.get(cookie_name)
        request.session = self.SessionStore(session_key)

    def process_response(self, request, response):
        """
        This is a copy of Django's default SessionMiddleware.process_response,
        with every use of settings.SESSION_COOKIE_NAME replaced by the cookie
        name chosen in process_request() above (donor vs admin).
        """
        try:
            accessed = request.session.accessed
            modified = request.session.modified
            empty = request.session.is_empty()
        except AttributeError:
            return response

        cookie_name = getattr(request, '_dual_session_cookie_name', self.DONOR_COOKIE_NAME)

        # First check if we need to delete this cookie.
        # The session should be deleted only if the session is entirely empty.
        if cookie_name in request.COOKIES and empty:
            response.delete_cookie(
                cookie_name,
                path=settings.SESSION_COOKIE_PATH,
                domain=settings.SESSION_COOKIE_DOMAIN,
                samesite=settings.SESSION_COOKIE_SAMESITE,
            )
            need_vary_cookie = True
        else:
            # If the session was accessed, it must be varied on, regardless of
            # whether it was modified or will be saved.
            need_vary_cookie = accessed
            if (modified or settings.SESSION_SAVE_EVERY_REQUEST) and not empty:
                if request.session.get_expire_at_browser_close():
                    max_age = None
                    expires = None
                else:
                    max_age = request.session.get_expiry_age()
                    expires_time = time.time() + max_age
                    expires = http_date(expires_time)
                # Save the session data and refresh the client cookie.
                # Skip session save for 5xx responses.
                if response.status_code < 500:
                    try:
                        request.session.save()
                    except UpdateError:
                        raise SessionInterrupted(
                            "The request's session was deleted before the "
                            "request completed. The user may have logged "
                            "out in a concurrent request, for example."
                        )
                    response.set_cookie(
                        cookie_name,
                        request.session.session_key,
                        max_age=max_age,
                        expires=expires,
                        domain=settings.SESSION_COOKIE_DOMAIN,
                        path=settings.SESSION_COOKIE_PATH,
                        secure=settings.SESSION_COOKIE_SECURE or None,
                        httponly=settings.SESSION_COOKIE_HTTPONLY or None,
                        samesite=settings.SESSION_COOKIE_SAMESITE,
                    )
                    # With a session cookie set, it must be varied on.
                    need_vary_cookie = True

        if need_vary_cookie:
            patch_vary_headers(response, ("Cookie",))

        return response
