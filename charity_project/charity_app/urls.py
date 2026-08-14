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

    # Static / informational pages
    path('about/', views.about_view, name='about'),
    path('contact/', views.contact_view, name='contact'),
    path('faq/', views.faq_view, name='faq'),
    path('privacy-policy/', views.privacy_policy_view, name='privacy_policy'),
    path('terms-of-service/', views.terms_view, name='terms'),

    # Donation flow: Step 1 (details form) -> Step 2 (payment gateway) -> Success
    path('donate/', views.donate, name='donate_generic'),
    path('donate/<int:campaign_id>/', views.donate, name='donate'),
    path('payment/', views.payment_gateway, name='payment_gateway'),
    path('payment-success/',views.payment_success,name='payment_success'),
    path('success/<int:donation_id>/', views.success_view, name='success'),

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
    path('myadmin/reports/', views.admin_reports, name='admin_reports'),
    path('myadmin/account-settings/', views.admin_account_settings, name='admin_account_settings'),

    path('myadmin/campaigns/', views.admin_campaign_list, name='admin_campaign_list'),
    path('myadmin/campaigns/add/', views.admin_campaign_add, name='admin_campaign_add'),
    path('myadmin/campaigns/<int:campaign_id>/edit/', views.admin_campaign_edit, name='admin_campaign_edit'),
    path('myadmin/campaigns/<int:campaign_id>/delete/', views.admin_campaign_delete, name='admin_campaign_delete'),

    path('myadmin/donations/', views.admin_donation_list, name='admin_donation_list'),
    path('myadmin/donors/', views.admin_donor_list, name='admin_donor_list'),

    path('myadmin/settings/', views.admin_site_settings, name='admin_site_settings'),

    path('myadmin/testimonials/', views.admin_testimonial_list, name='admin_testimonial_list'),
    path('myadmin/testimonials/<int:testimonial_id>/edit/', views.admin_testimonial_edit, name='admin_testimonial_edit'),
    path('myadmin/testimonials/<int:testimonial_id>/delete/', views.admin_testimonial_delete, name='admin_testimonial_delete'),

    path('myadmin/faqs/', views.admin_faq_list, name='admin_faq_list'),
    path('myadmin/faqs/add/', views.admin_faq_add, name='admin_faq_add'),
    path('myadmin/faqs/<int:faq_id>/edit/', views.admin_faq_edit, name='admin_faq_edit'),
    path('myadmin/faqs/<int:faq_id>/delete/', views.admin_faq_delete, name='admin_faq_delete'),

    path('myadmin/messages/', views.admin_contact_list, name='admin_contact_list'),
    path('myadmin/messages/<int:message_id>/', views.admin_contact_view, name='admin_contact_view'),
    path('myadmin/messages/<int:message_id>/delete/', views.admin_contact_delete, name='admin_contact_delete'),

    # Help requests (submitted from the homepage "Get Help" form)
    path('myadmin/requests/', views.admin_request_list, name='request'),
    path('myadmin/requests/<int:request_id>/', views.admin_request_detail, name='admin_request_detail'),
    path('myadmin/requests/<int:request_id>/delete/', views.admin_request_delete, name='admin_request_delete'),

    # Notifications
    path('myadmin/notifications/', views.admin_notifications_list, name='admin_notifications_list'),
    path('myadmin/notifications/<int:notification_id>/read/', views.admin_notification_mark_read, name='admin_notification_mark_read'),
    path('myadmin/notifications/mark-all-read/', views.admin_notifications_mark_all_read, name='admin_notifications_mark_all_read'),
]
