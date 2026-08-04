"""
URL configuration for charity_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# NOTE: We are NOT using Django's default admin site (django.contrib.admin) here.
# This project ships its own custom-built admin panel instead, which lives
# entirely inside charity_app.urls under the "/myadmin/" prefix
# (see admin_login, admin_dashboard, admin_campaign_list, etc. in views.py).

urlpatterns = [
    # All charity_app URLs (home, campaigns, donate, dashboard, custom admin panel, etc.)
    path('', include('charity_app.urls')),
]

# This lets Django serve uploaded campaign images during development (DEBUG=True)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
