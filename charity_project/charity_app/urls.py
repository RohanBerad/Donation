"""
urls.py (charity_app)
----------------------
This file maps URLs (web addresses) to the view functions in views.py.
"""

from django.urls import path
from . import views

urlpatterns = [
    # ---------------- Public / Donor-facing pages ----------------
    path('', views.home, name='home'),
    path('campaigns/', views.campaign_list, name='campaign_list'),
    path('campaigns/<int:campaign_id>/', views.campaign_detail, name='campaign_detail'),

    # Donation flow: Step 1 (details form) -> Step 2 (payment gateway) -> Success
    path('donate/', views.donate, name='donate_generic'),
    path('donate/<int:campaign_id>/', views.donate, name='donate'),
    path('payment/', views.payment_gateway, name='payment_gateway'),
    path('success/<int:donation_id>/', views.success, name='success'),

    # Receipts
    path('receipt/<int:donation_id>/', views.receipt_view, name='receipt_view'),
    path('receipt/<int:donation_id>/download/', views.download_receipt, name='download_receipt'),

    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Forgot Password (OTP-based 3-step flow)
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('forgot-password/verify-otp/', views.verify_otp, name='verify_otp'),
    path('forgot-password/reset-password/', views.reset_password, name='reset_password'),

    # Donor Dashboard (sidebar with several sub-pages)
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/donations/', views.dashboard_donations, name='dashboard_donations'),
    path('dashboard/receipts/', views.dashboard_receipts, name='dashboard_receipts'),
    path('dashboard/profile/', views.dashboard_profile, name='dashboard_profile'),
    path('dashboard/change-password/', views.dashboard_change_password, name='dashboard_change_password'),

    # ---------------- Custom Admin Panel (our own, NOT Django's default /admin/) ----------------
    path('myadmin/login/', views.admin_login_view, name='admin_login'),
    path('myadmin/logout/', views.admin_logout_view, name='admin_logout'),
    path('myadmin/', views.admin_dashboard, name='admin_dashboard'),

    path('myadmin/campaigns/', views.admin_campaign_list, name='admin_campaign_list'),
    path('myadmin/campaigns/add/', views.admin_campaign_add, name='admin_campaign_add'),
    path('myadmin/campaigns/<int:campaign_id>/edit/', views.admin_campaign_edit, name='admin_campaign_edit'),
    path('myadmin/campaigns/<int:campaign_id>/delete/', views.admin_campaign_delete, name='admin_campaign_delete'),

    path('myadmin/donations/', views.admin_donation_list, name='admin_donation_list'),
    path('myadmin/donors/', views.admin_donor_list, name='admin_donor_list'),

    path('myadmin/settings/', views.admin_site_settings, name='admin_site_settings'),

    path('myadmin/testimonials/', views.admin_testimonial_list, name='admin_testimonial_list'),
    path('myadmin/testimonials/add/', views.admin_testimonial_add, name='admin_testimonial_add'),
    path('myadmin/testimonials/<int:testimonial_id>/edit/', views.admin_testimonial_edit, name='admin_testimonial_edit'),
    path('myadmin/testimonials/<int:testimonial_id>/delete/', views.admin_testimonial_delete, name='admin_testimonial_delete'),
]
