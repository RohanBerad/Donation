"""
admin.py
--------
This project does NOT use Django's built-in admin site
(django.contrib.admin is intentionally left out of INSTALLED_APPS in settings.py).

Instead, Campaign management, Donation viewing, and Donor viewing are handled
by our own CUSTOM admin panel, which you can find at:

    /myadmin/login/       -> Admin login page
    /myadmin/              -> Admin dashboard
    /myadmin/campaigns/    -> Add / Edit / Delete campaigns
    /myadmin/donations/    -> View all donations
    /myadmin/donors/       -> View all donors

All of that logic lives in charity_app/views.py (see the "CUSTOM ADMIN PANEL" section)
and charity_app/urls.py. This file is kept empty on purpose.
"""
