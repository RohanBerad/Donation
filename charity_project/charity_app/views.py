"""
views.py
--------
This file contains all the "logic" of our website.
Each function here is called a "view" and it decides what HTML page to show
and what data to send to that page.

We use simple Function-Based Views (FBVs) everywhere, as requested,
so the code stays easy to read for beginners.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm, SetPasswordForm
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.core.mail import send_mail
from django.db.models import Sum, Avg
from django.core.paginator import Paginator
from decimal import Decimal
import random

import razorpay
from django.conf import settings
from django.contrib.auth.models import User
from .models import Campaign, Donation, SiteSettings, Testimonial, UserProfile, PasswordResetOTP, FAQ, ContactMessage, HelpRequest, Notification, Update, DonationAppeal, AppealSupplyItem, VolunteerMessage
from .forms import (
    DonationForm, RegisterForm, CampaignForm, AdminLoginForm,
    SiteSettingsForm, TestimonialForm, TestimonialSubmissionForm, ProfileForm, EmailLoginForm,
    FAQForm, ContactForm, HelpRequestForm, UpdateForm, DonationAppealForm, AppealSupplyItemFormSet,
    VolunteerMessageForm,
)


# ==========================================================
# CUSTOM ADMIN ACCESS CHECK
# ==========================================================
# We do NOT use Django's default /admin/ site. Instead, every "admin_*"
# view below is protected by this simple check: the logged-in user must
# have is_staff=True (this flag is automatically set to True for any
# account created with "python manage.py createsuperuser").
#
# If the check fails, the user is sent to our own custom admin login page
# (login_url='admin_login') instead of Django's default admin login.
admin_required = user_passes_test(lambda u: u.is_authenticated and u.is_staff, login_url='admin_login')


# A small fixed lookup so the "Our Impact" section on the home page can show
# a matching icon + short blurb for each campaign category. The category
# CHOICES themselves live on the Campaign model; this just decorates them.
CATEGORY_ICONS = {
    'education': {'icon': 'bi-mortarboard-fill', 'blurb': 'Providing quality education to underprivileged children.'},
    'medical': {'icon': 'bi-heart-pulse-fill', 'blurb': 'Supporting patients and providing medical care.'},
    'animal': {'icon': 'bi-egg-fried', 'blurb': 'Rescuing and providing shelter to animals.'},
    'disaster': {'icon': 'bi-house-heart-fill', 'blurb': 'Helping communities in times of natural disasters.'},
}


# ==========================================================
# 1. HOME PAGE
# ==========================================================
def home(request):
    """
    Shows the landing page with hero section, mission, impact stats,
    featured campaigns and testimonials.

    IMPORTANT: All the text on this page (hero title, mission text, impact
    numbers, footer contact info) comes from the SiteSettings model, which
    NGO staff can edit from our custom admin panel at /myadmin/settings/.
    There is no hardcoded marketing copy in this view or its template.

    This view also handles the "We're Here To Support You" (Get Help) form
    submission -- it lives inline on this page, so POSTs here too. On
    success we save a HelpRequest (including any attached document) and
    redirect back to the #get-help section with a confirmation message.
    """
    site_settings = SiteSettings.load()

    story_form = TestimonialSubmissionForm()
    help_request_form = HelpRequestForm()

    if request.method == 'POST' and 'submit_story' in request.POST:
        story_form = TestimonialSubmissionForm(request.POST, request.FILES)
        if story_form.is_valid():
            testimonial = story_form.save(commit=False)
            testimonial.is_active = False
            testimonial.is_approved = False
            testimonial.save()
            Notification.objects.create(
                notification_type='story_submission',
                title='New Story Submission',
                message=f"{testimonial.donor_name} shared a story: {testimonial.story_title or testimonial.donor_role}",
                url='/myadmin/testimonials/',
            )
            messages.success(
                request,
                "Thank you for sharing your message. Our team will review it and decide whether to publish it on the website."
            )
            return redirect('home')
        else:
            messages.error(request, "Please fill in a valid story before submitting.")
    elif request.method == 'POST' and 'submit_help_request' in request.POST:
        help_request_form = HelpRequestForm(request.POST, request.FILES)

        if help_request_form.is_valid():
            help_request = help_request_form.save()
            Notification.objects.create(
                notification_type='help_request',
                title='New Help Request',
                message=f"{help_request.full_name} needs help with {help_request.diagnosis_condition}",
                url='/myadmin/requests/',
            )
            messages.success(
                request,
                "Your request has been submitted. Our team will review it and reach out to you soon."
            )
            return redirect(f"{reverse('home')}#get-help")
        else:
            messages.error(request, "Please fix the errors below and submit the form again.")

    # Show only 3 active campaigns as "Featured Campaigns" on the home page
    featured_campaigns = Campaign.objects.filter(status='active').order_by('-created_at')[:3]

    # Build the "Our Impact" cards dynamically from the Campaign category choices
    impact_cards = []
    for value, label in Campaign.CATEGORY_CHOICES:
        info = CATEGORY_ICONS.get(value, {'icon': 'bi-heart-fill', 'blurb': ''})
        impact_cards.append({'label': label, 'icon': info['icon'], 'blurb': info['blurb']})

    # Testimonials that staff have approved AND marked active, in their chosen display order
    testimonials = Testimonial.objects.filter(is_active=True, is_approved=True)

    stories_shared_count = testimonials.count()
    average_rating = testimonials.aggregate(avg=Avg('rating'))['avg'] or 0

    # "Updates From [NGO Name]" cards -- managed from the admin panel, oldest first
    updates = Update.objects.filter(is_active=True).order_by('publish_date')[:12]

    context = {
        'settings': site_settings,
        'featured_campaigns': featured_campaigns,
        'impact_cards': impact_cards,
        'testimonials': testimonials,
        'help_request_form': help_request_form,
        'story_form': story_form,
        'stories_shared_count': stories_shared_count,
        'average_rating': average_rating,
        'updates': updates,
    }
    return render(request, 'website/index.html', context)


# ==========================================================
# 2. CAMPAIGN LIST PAGE
# ==========================================================
def campaign_list(request):
    """
    Shows all campaigns. Supports simple filtering by category using
    a URL query parameter, e.g. /campaigns/?category=medical
    """
    campaigns = Campaign.objects.all().order_by('-created_at')

    selected_category = request.GET.get('category')
    if selected_category:
        campaigns = campaigns.filter(category=selected_category)

    context = {
        'campaigns': campaigns,
        'categories': Campaign.CATEGORY_CHOICES,
        'selected_category': selected_category,
    }
    return render(request, 'website/campaign_list.html', context)


# ==========================================================
# 3. CAMPAIGN DETAIL PAGE
# ==========================================================
def campaign_detail(request, campaign_id):
    """
    Shows full details of one campaign: image, description, progress bar,
    donor count, days left, and a "Donate Now" button.
    """
    campaign = get_object_or_404(Campaign, id=campaign_id)
    context = {'campaign': campaign}
    return render(request, 'website/campaign_detail.html', context)


# ==========================================================
# 3B. ABOUT / CONTACT / FAQ / PRIVACY / TERMS PAGES
# ==========================================================
def about_view(request):
    """
    Public "About Us" page. All of the text/image here comes from the
    same SiteSettings singleton used on the Home Page, so staff can edit
    it from /myadmin/settings/ without touching any code.
    """
    site_settings = SiteSettings.load()
    testimonials = Testimonial.objects.filter(is_active=True, is_approved=True)

    story_form = TestimonialSubmissionForm()
    if request.method == 'POST' and 'submit_story' in request.POST:
        story_form = TestimonialSubmissionForm(request.POST, request.FILES)
        if story_form.is_valid():
            testimonial = story_form.save(commit=False)
            testimonial.is_active = False
            testimonial.is_approved = False
            testimonial.save()
            Notification.objects.create(
                notification_type='story_submission',
                title='New Story Submission',
                message=f"{testimonial.donor_name} shared a story: {testimonial.story_title or testimonial.donor_role}",
                url='/myadmin/testimonials/',
            )
            messages.success(request, "Thank you for sharing. The story is waiting for admin approval.")
            return redirect('about')
        else:
            messages.error(request, "Please fix the story form and try again.")

    context = {
        'site_settings': site_settings,
        'testimonials': testimonials,
        'story_form': story_form,
    }
    return render(request, 'website/about.html', context)


def get_support_view(request):
    """
    Public "Get Support" page. Explains how to request help, what documents
    to prepare, and the review process. The actual HelpRequest form remains
    on the home page (#get-help), but this page gives detailed guidance so
    beneficiaries know exactly what to expect and what to upload.
    """
    site_settings = SiteSettings.load()
    context = {
        'site_settings': site_settings,
    }
    return render(request, 'website/get_support.html', context)


def contact_view(request):
    """
    Public "Contact Us" page. Saves every submission as a ContactMessage
    row so staff can read it later from /myadmin/messages/.
    """
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            contact = form.save()
            Notification.objects.create(
                notification_type='contact_message',
                title='New Contact Message',
                message=f"{contact.name} sent: {contact.subject}",
                url='/myadmin/messages/',
            )
            messages.success(request, "Thanks for reaching out! We'll get back to you soon.")
            return redirect('contact')
    else:
        # If a logged-in user visits the Contact page, pre-fill their
        # name and email so they don't have to type it again.
        initial = {}
        if request.user.is_authenticated:
            initial['name'] = request.user.get_full_name() or request.user.username
            initial['email'] = request.user.email
        form = ContactForm(initial=initial)

    return render(request, 'website/contact.html', {'form': form})


def faq_view(request):
    """Shows every active FAQ, ordered the way staff arranged them in the admin panel."""
    faqs = FAQ.objects.filter(is_active=True)
    return render(request, 'website/faq.html', {'faqs': faqs})


def privacy_policy_view(request):
    """Static Privacy Policy page."""
    return render(request, 'website/privacy_policy.html')


def terms_view(request):
    """Static Terms of Service page."""
    return render(request, 'website/terms.html')


# ==========================================================
# 4. DONATE PAGE (Donation Form) -- Step 1 of the payment flow
# ==========================================================
def donate(request, campaign_id=None, appeal_id=None):
    """
    Donation Form (supports campaigns, appeals/stories, or general donations)
    """
    preselected_campaign = None
    preselected_appeal = None

    if campaign_id:
        preselected_campaign = get_object_or_404(Campaign, id=campaign_id)
    elif appeal_id:
        preselected_appeal = get_object_or_404(DonationAppeal, id=appeal_id)
        if preselected_appeal.campaign:
            preselected_campaign = preselected_appeal.campaign

    if request.method == 'POST':
        form = DonationForm(request.POST)
        if form.is_valid():
            campaign_obj = form.cleaned_data.get('campaign') or preselected_campaign
            request.session['pending_donation'] = {
                'campaign_id': campaign_obj.id if campaign_obj else None,
                'appeal_id': preselected_appeal.id if preselected_appeal else None,
                'donor_name': form.cleaned_data['donor_name'],
                'email': form.cleaned_data['email'],
                'amount': str(form.cleaned_data['amount']),
                'payment_method': form.cleaned_data['payment_method'],
            }
            return redirect('payment_gateway')
        else:
            print("FORM ERRORS", form.errors)
    else:
        initial = {}
        if preselected_campaign:
            initial['campaign'] = preselected_campaign
        if request.user.is_authenticated:
            initial['donor_name'] = request.user.username
            initial['email'] = request.user.email
        form = DonationForm(initial=initial)

    campaigns_json = {}
    for c in Campaign.objects.filter(status='active'):
        campaigns_json[str(c.id)] = {
            'name': c.campaign_name,
            'image': c.campaign_image.url if c.campaign_image else '',
            'raised': str(c.raised_amount),
            'goal': str(c.goal_amount),
            'percent': str(c.progress_percentage()),
        }

    context = {
        'form': form,
        'campaign': preselected_campaign,
        'appeal': preselected_appeal,
        'campaigns_json': campaigns_json,
    }

    return render(
        request,
        'website/donate.html',
        context
    )
# ==========================================================
# 5. PAYMENT GATEWAY PAGE -- Step 2 of the payment flow
# ==========================================================
def payment_gateway(request):
    pending = request.session.get('pending_donation')

    if not pending:
        return redirect('campaign_list')

    client = razorpay.Client(
        auth=(
            settings.RAZORPAY_KEY_ID,
            settings.RAZORPAY_KEY_SECRET
        )
    )

    campaign = None
    if pending.get('campaign_id'):
        campaign = get_object_or_404(Campaign, id=pending['campaign_id'])

    appeal = None
    if pending.get('appeal_id'):
        appeal = get_object_or_404(DonationAppeal, id=pending['appeal_id'])

    amount = int(float(pending['amount']) * 100)

    payment = client.order.create({
        "amount": amount,
        "currency": "INR",
        "payment_capture": "1"
    })

    subject_title = "General Donation"
    if campaign:
        subject_title = campaign.campaign_name
    elif appeal:
        subject_title = appeal.title

    context = {
        "pending": pending,
        "payment": payment,
        "key": settings.RAZORPAY_KEY_ID,
        "campaign": campaign,
        "appeal": appeal,
        "subject_title": subject_title,
    }

    return render(
        request,
        "website/payment_gateway.html",
        context
    )

# ==========================================================
# 6. PAYMENT SUCCESS PAGE
# ==========================================================


def payment_success(request):

    payment_id = request.GET.get('payment_id')

    if not payment_id:
        return redirect('campaign_list')

    pending = request.session.get('pending_donation')

    if not pending:
        return redirect('campaign_list')

    campaign = None
    if pending.get('campaign_id'):
        campaign = get_object_or_404(Campaign, id=pending['campaign_id'])

    appeal = None
    if pending.get('appeal_id'):
        appeal = get_object_or_404(DonationAppeal, id=pending['appeal_id'])

    donation = Donation(
        campaign=campaign,
        appeal=appeal,
        donor_name=pending['donor_name'],
        email=pending['email'],
        amount=Decimal(pending['amount']),
        payment_method=pending['payment_method'],
    )

    if request.user.is_authenticated:
        donation.user = request.user

    donation.razorpay_payment_id = payment_id
    donation.save()

    subject = donation.subject_name
    Notification.objects.create(
        notification_type='donation',
        title='New Donation Received',
        message=f"{donation.donor_name} donated Rs. {donation.amount} to {subject}",
        url='/myadmin/donations/',
    )

    del request.session['pending_donation']
    return redirect(
            'success',
            donation_id=donation.id
        )


def success_view(request, donation_id):
    """Shows the payment success page with donation details."""
    donation = get_object_or_404(Donation, id=donation_id)
    return render(request, 'website/success.html', {'donation': donation})


# ==========================================================
# 7. RECEIPT (view + download)
# ==========================================================
def receipt_view(request, donation_id):
    """
    Shows a nicely formatted, printable receipt page for one donation.
    The donor can use their browser's Print / Save-as-PDF option (a button
    on the page triggers window.print()), so no extra PDF library is needed.
    """
    donation = get_object_or_404(Donation, id=donation_id)
    return render(request, 'website/receipt.html', {'donation': donation})


def download_receipt(request, donation_id):
    """
    Generates a simple downloadable text receipt for a donation.
    (Kept as plain text for simplicity -- no extra PDF library required.)
    """
    donation = get_object_or_404(Donation, id=donation_id)

    receipt_text = f"""
================================================
      HELPING HANDS DONATION PLATFORM
             OFFICIAL RECEIPT
================================================

Donor Name     : {donation.donor_name}
Email          : {donation.email}
Supporting     : {donation.subject_name}
Amount Donated : Rs. {donation.amount}
Payment Method : {donation.get_payment_method_display()}
Transaction ID : {donation.transaction_id}
Donation Date  : {donation.donation_date.strftime('%d-%b-%Y %I:%M %p')}

------------------------------------------------
Thank you for your generous contribution!
This receipt is auto-generated for demo purposes.
================================================
"""

    response = HttpResponse(receipt_text, content_type='text/plain')
    response['Content-Disposition'] = f'attachment; filename="receipt_{donation.transaction_id}.txt"'
    return response


# ==========================================================
# 8. USER REGISTRATION
# ==========================================================
def register_view(request):
    """
    Shows the registration form and creates a new User account on submit.
    We also create a matching (empty) UserProfile so the donor can fill
    in their phone/address later from their dashboard.
    """
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            UserProfile.objects.create(user=user, is_volunteer=form.cleaned_data.get('is_volunteer', False))
            login(request, user)  # log the user in immediately after registering
            messages.success(request, 'Account created successfully! Welcome.')
            return redirect('dashboard')
    else:
        form = RegisterForm()

    return render(request, 'website/register.html', {'form': form})


# ==========================================================
# 9. USER LOGIN
# ==========================================================
def login_view(request):
    """
    Shows the login form and logs the user in on submit.

    NOTE: We log donors in by EMAIL, not username. Django's authentication
    system only knows how to check a username + password pair, so behind
    the scenes we first look up which account owns the entered email, then
    authenticate using that account's real username -- the donor never
    needs to know or type their username.
    """
    if request.method == 'POST':
        form = EmailLoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email'].strip().lower()
            password = form.cleaned_data['password']

            matching_user = User.objects.filter(email__iexact=email).first()

            user = None
            if matching_user is not None:
                user = authenticate(request, username=matching_user.username, password=password)

            if user is not None:
                request.session.set_expiry(settings.SESSION_COOKIE_AGE)
                request.session.modified = True
                login(request, user)
                return redirect('dashboard')
            else:
                messages.error(request, 'Invalid email or password. Please try again.')
    else:
        form = EmailLoginForm()

    return render(request, 'website/login.html', {'form': form})


# ==========================================================
# 10. USER LOGOUT
# ==========================================================
def logout_view(request):
    """
    Logs the current user out and sends them back to the home page.
    """
    logout(request)
    response = redirect('home')
    response.delete_cookie('sessionid', path=settings.SESSION_COOKIE_PATH)
    return response


# ==========================================================
# 10a. FORGOT PASSWORD (OTP-based, 3-step flow)
# ==========================================================
def forgot_password(request):
    """
    Step 1 of the forgot-password flow.
    The user enters their email address. If that email is registered,
    we generate a 6-digit OTP, save it to the DB, and send it via email
    (in development, Django prints it to the console).
    """
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()

        if not email:
            messages.error(request, 'Please enter your email address.')
            return render(request, 'website/forgot_password.html')

        # Check if a user with this email actually exists
        user_exists = User.objects.filter(email__iexact=email).exists()

        # For security, don't reveal whether the email exists or not
        # but only proceed with OTP generation if it does
        if user_exists:
            otp_code = str(random.randint(100000, 999999))

            # Invalidate any previous unused OTPs for this email
            PasswordResetOTP.objects.filter(email=email, is_used=False).update(is_used=True)

            # Create new OTP record
            PasswordResetOTP.objects.create(email=email, otp_code=otp_code)

            # Store email in session so the next steps know whose OTP to verify
            request.session['reset_email'] = email
            request.session.modified = True

            # Send the OTP via email (console backend in dev)
            try:
                send_mail(
                    subject='Your Password Reset OTP - Helping Hands',
                    message=f'Your OTP for password reset is: {otp_code}\n\nThis code will expire in 10 minutes.\n\nIf you did not request this, please ignore this email.',
                    from_email=None,
                    recipient_list=[email],
                    fail_silently=False,
                )
            except Exception as e:
                messages.error(request, f"Email could not be sent: {e}")
                return redirect("forgot_password")  

            messages.success(request, 'If an account with that email exists, an OTP has been sent.')
            return redirect('verify_otp')
        else:
            # Still show success to prevent email enumeration
            messages.success(request, 'If an account with that email exists, an OTP has been sent.')
            return redirect('forgot_password')

    return render(request, 'website/forgot_password.html')


def verify_otp(request):
    """
    Step 2 of the forgot-password flow.
    The user enters the 6-digit OTP they received by email.
    We look up the most recent unused OTP for the session's email.
    """
    email = request.session.get('reset_email')

    if not email:
        messages.error(request, 'Session expired. Please start the password reset process again.')
        return redirect('forgot_password')

    if request.method == 'POST':
        otp_input = request.POST.get('otp_code', '').strip()

        if not otp_input:
            messages.error(request, 'Please enter the OTP code.')
            return render(request, 'website/verify_otp.html', {'email': email})

        # Find the most recent unused OTP for this email
        otp_record = PasswordResetOTP.objects.filter(
            email=email, is_used=False
        ).order_by('-created_at').first()

        if not otp_record:
            messages.error(request, 'No active OTP found. Please request a new one.')
            return redirect('forgot_password')

        if otp_record.is_expired():
            messages.error(request, 'Your OTP has expired. Please request a new one.')
            otp_record.is_used = True
            otp_record.save()
            return redirect('forgot_password')

        if otp_record.otp_code != otp_input:
            messages.error(request, 'Invalid OTP code. Please try again.')
            return render(request, 'website/verify_otp.html', {'email': email})

        # OTP is valid -- mark it as used and proceed
# OTP is valid -- mark it as used and proceed
        otp_record.is_used = True
        otp_record.save()

        request.session["otp_verified"] = True

        messages.success(request, 'OTP verified successfully! Please set your new password.')
        return redirect('reset_password')

    return render(request, 'website/verify_otp.html', {'email': email})


def reset_password(request):
    """
    Step 3 of the forgot-password flow.
    The user enters their new password twice.
    """
    email = request.session.get('reset_email')
    if not request.session.get("otp_verified"):
        messages.error(request, "Please verify your OTP first.")
        return redirect("verify_otp")

    if not email:
        messages.error(request, 'Session expired. Please start the password reset process again.')
        return redirect('forgot_password')

    # IMPORTANT: this uses the exact same lookup as login_view() above
    # (User.objects.filter(email__iexact=email).first()) so that the account
    # whose password gets reset here is ALWAYS the same account the donor
    # will actually log into afterwards -- even for any old accounts that
    # happen to share an email from before duplicate emails were blocked.
    user = User.objects.filter(email__iexact=email).first()

    if not user:
        messages.error(request, 'User not found. Please try again.')
        return redirect('forgot_password')

    if request.method == 'POST':
        form = SetPasswordForm(user, request.POST)
        if form.is_valid():
            form.save()

            request.session.pop("reset_email", None)
            request.session.pop("otp_verified", None)
            messages.success(request, 'Your password has been reset successfully! You can now log in.')
            return redirect('login')
    else:
        form = SetPasswordForm(user)

    # Add Bootstrap classes
    for field in form.fields.values():
        field.widget.attrs.update({'class': 'form-control'})

    return render(request, 'website/reset_password.html', {'form': form})


# ==========================================================
# 11. DONOR DASHBOARD (split across a few pages, with a shared sidebar)
# ==========================================================
@login_required
def dashboard(request):
    """Overview page: profile summary card, quick stats, and recent donations."""
    donations = Donation.objects.filter(user=request.user).select_related('campaign', 'appeal').order_by('-donation_date')
    total_donated = donations.aggregate(total=Sum('amount'))['total'] or 0
    distinct_campaigns = donations.filter(campaign__isnull=False).values('campaign').distinct().count()
    distinct_appeals = donations.filter(appeal__isnull=False).values('appeal').distinct().count()
    has_general = donations.filter(campaign__isnull=True, appeal__isnull=True).exists()
    campaigns_supported = distinct_campaigns + distinct_appeals + (1 if has_general else 0)

    context = {
        'donations': donations[:5],
        'total_donated': total_donated,
        'total_donations_count': donations.count(),
        'campaigns_supported': campaigns_supported,
    }
    return render(request, 'website/dashboard_overview.html', context)


@login_required
def dashboard_donations(request):
    """Shows the donor's FULL donation history."""
    donations = Donation.objects.filter(user=request.user).select_related('campaign', 'appeal').order_by('-donation_date')
    return render(request, 'website/dashboard_donations.html', {'donations': donations})


@login_required
def dashboard_receipts(request):
    """Shows every donation with a Download Receipt button next to it."""
    donations = Donation.objects.filter(user=request.user).select_related('campaign', 'appeal').order_by('-donation_date')
    return render(request, 'website/dashboard_receipts.html', {'donations': donations})


@login_required
def dashboard_volunteer_messages(request):
    """Shows messages sent to the logged-in volunteer by the admin team."""
    volunteer_messages = VolunteerMessage.objects.filter(
        recipients=request.user
    ).select_related('sent_by').order_by('-sent_at')
    return render(request, 'website/dashboard_volunteer_messages.html', {
        'volunteer_messages': volunteer_messages,
    })


@login_required
def dashboard_profile(request):
    """Lets the donor view/update their profile: username, email, picture, phone, address."""
    profile, created = UserProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        # request.FILES is required here so the uploaded profile picture is captured.
        # current_user is passed so the form can validate the new username correctly.
        form = ProfileForm(request.POST, request.FILES, instance=profile, current_user=request.user)
        if form.is_valid():
            form.save()

            # username/email are NOT part of the UserProfile model, so they are
            # saved separately onto the actual User account here.
            request.user.username = form.cleaned_data['username']
            request.user.email = form.cleaned_data['email']
            request.user.save()

            # Saving a new username changes what Django uses to identify the
            # logged-in session, so we refresh the session hash here to make
            # sure the donor stays logged in instead of being signed out.
            update_session_auth_hash(request, request.user)

            messages.success(request, 'Profile updated successfully!')
            return redirect('dashboard_profile')
    else:
        form = ProfileForm(instance=profile, current_user=request.user)

    return render(request, 'website/dashboard_profile.html', {'form': form})



def dashboard_change_password(request):
    """Lets the donor change their account password."""
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # keeps the donor logged in after changing password
            messages.success(request, 'Password changed successfully!')
            return redirect('dashboard_profile')
    else:
        form = PasswordChangeForm(request.user)

    # Django's built-in PasswordChangeForm doesn't add Bootstrap classes by default,
    # so we add them here manually to keep the form looking consistent with the rest of the site.
    for field in form.fields.values():
        field.widget.attrs.update({'class': 'form-control'})

    return render(request, 'website/dashboard_change_password.html', {'form': form})


# ==========================================================================================
# CUSTOM ADMIN PANEL (our own -- NOT Django's default /admin/)
# ==========================================================================================
# All the views below live under the "/myadmin/" URL prefix (see urls.py) and use their own
# separate templates in templates/charity_app/admin/. Only staff accounts (is_staff=True)
# can access them, enforced by the @admin_required decorator defined above.
# ==========================================================================================


def admin_login_view(request):
    """
    A separate login page for NGO staff, completely independent from Django's
    built-in /admin/ login and from the donor-facing /login/ page.
    """
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('admin_dashboard')

    if request.method == 'POST':
        form = AdminLoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)

            if user is not None and user.is_staff:
                request.session.set_expiry(settings.SESSION_COOKIE_AGE)
                request.session.modified = True
                login(request, user)
                return redirect('admin_dashboard')
            else:
                messages.error(request, 'Invalid credentials, or this account does not have admin access.')
    else:
        form = AdminLoginForm()

    return render(request, 'admin/admin_login.html', {'form': form})


def admin_logout_view(request):
    """Logs the staff member out and returns them to the custom admin login page."""
    logout(request)
    response = redirect('admin_login')
    response.delete_cookie('admin_sessionid', path=settings.SESSION_COOKIE_PATH)
    return response


@admin_required
def admin_dashboard(request):
    """
    The main landing page of our custom admin panel.
    Shows quick stats, a 7-day donations chart, recent donations,
    campaign funding progress, and quick-action shortcuts.
    """
    from datetime import timedelta
    from django.utils import timezone

    today = timezone.localdate()
    period = request.GET.get('period', '7d')

    if period == '30d':
        days_back = 30
        chart_labels = []
        chart_values = []
        for i in range(29, -1, -1):
            day = today - timedelta(days=i)
            day_total = Donation.objects.filter(donation_date__date=day).aggregate(total=Sum('amount'))['total'] or 0
            chart_labels.append(day.strftime('%d %b'))
            chart_values.append(float(day_total))
        period_total = sum(chart_values)
        period_label = 'Last 30 Days'
    elif period == 'month':
        from calendar import monthrange
        first_of_month = today.replace(day=1)
        last_day = monthrange(today.year, today.month)[1]
        chart_labels = []
        chart_values = []
        for day_num in range(1, last_day + 1):
            day = first_of_month.replace(day=day_num)
            if day > today:
                break
            day_total = Donation.objects.filter(donation_date__date=day).aggregate(total=Sum('amount'))['total'] or 0
            chart_labels.append(day.strftime('%d %b'))
            chart_values.append(float(day_total))
        period_total = sum(chart_values)
        period_label = 'This Month'
    elif period == 'year':
        chart_labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        chart_values = []
        for month in range(1, 13):
            month_total = Donation.objects.filter(
                donation_date__year=today.year,
                donation_date__month=month
            ).aggregate(total=Sum('amount'))['total'] or 0
            chart_values.append(float(month_total))
        period_total = sum(chart_values)
        period_label = 'This Year'
    else:
        chart_labels = []
        chart_values = []
        for i in range(6, -1, -1):
            day = today - timedelta(days=i)
            day_total = Donation.objects.filter(donation_date__date=day).aggregate(total=Sum('amount'))['total'] or 0
            chart_labels.append(day.strftime('%d %b'))
            chart_values.append(float(day_total))
        period_total = sum(chart_values)
        period_label = 'Last 7 Days'

    context = {
        'total_campaigns': Campaign.objects.count(),
        'active_campaigns': Campaign.objects.filter(status='active').count(),
        'total_donations': Donation.objects.count(),
        'total_raised': Donation.objects.aggregate(total=Sum('amount'))['total'] or 0,
        'total_donors': Donation.objects.values('email').distinct().count(),
        'recent_donations': Donation.objects.select_related('campaign', 'appeal').order_by('-donation_date')[:5],
        'unread_messages': ContactMessage.objects.filter(is_read=False).count(),
        'new_help_requests': HelpRequest.objects.filter(status='new').count(),
        'total_testimonials': Testimonial.objects.count(),
        'active_testimonials': Testimonial.objects.filter(is_active=True).count(),
        'approved_testimonials': Testimonial.objects.filter(is_approved=True).count(),
        'pending_testimonials': Testimonial.objects.filter(is_approved=False).count(),
        'campaign_status_list': Campaign.objects.all().order_by('-created_at')[:4],
        'chart_labels': chart_labels,
        'chart_values': chart_values,
        'week_total': period_total,
        'donation_period': period,
        'donation_period_label': period_label,
    }
    return render(request, 'admin/admin_dashboard.html', context)


@admin_required
def admin_reports(request):
    """
    A simple Reports & Analytics page: top campaigns by amount raised,
    donations broken down by payment method, and a monthly totals table
    for the current year. All computed live from real data.
    """
    from django.db.models import Count
    from django.utils import timezone

    top_campaigns = Campaign.objects.order_by('-raised_amount')[:5]

    payment_breakdown = (
        Donation.objects.values('payment_method')
        .annotate(total=Sum('amount'), count=Count('id'))
        .order_by('-total')
    )

    current_year = timezone.now().year
    monthly_totals = []
    for month in range(1, 13):
        total = Donation.objects.filter(
            donation_date__year=current_year, donation_date__month=month
        ).aggregate(total=Sum('amount'))['total'] or 0
        monthly_totals.append({'month': month, 'total': total})

    context = {
        'top_campaigns': top_campaigns,
        'payment_breakdown': payment_breakdown,
        'monthly_totals': monthly_totals,
        'monthly_totals_values': [float(m['total']) for m in monthly_totals],
        'current_year': current_year,
        'total_raised': Donation.objects.aggregate(total=Sum('amount'))['total'] or 0,
        'total_donations': Donation.objects.count(),
    }
    return render(request, 'admin/admin_reports.html', context)


@admin_required
def admin_account_settings(request):
    """Lets the logged-in staff member update their own admin account password."""
    if request.method == 'POST':
        password_form = PasswordChangeForm(request.user, request.POST)
        if password_form.is_valid():
            user = password_form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Your admin password was updated successfully.')
            return redirect('admin_account_settings')
    else:
        password_form = PasswordChangeForm(request.user)

    for field in password_form.fields.values():
        field.widget.attrs.update({'class': 'form-control'})

    return render(request, 'admin/admin_account_settings.html', {'password_form': password_form})


@admin_required
def admin_profile(request):
    """Lets the logged-in admin view and update their own profile information."""
    profile, created = UserProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=profile, current_user=request.user)
        if form.is_valid():
            form.save()
            request.user.username = form.cleaned_data['username']
            request.user.email = form.cleaned_data['email']
            request.user.save()
            update_session_auth_hash(request, request.user)
            messages.success(request, 'Profile updated successfully!')
            return redirect('admin_profile')
    else:
        form = ProfileForm(instance=profile, current_user=request.user)

    return render(request, 'admin/admin_profile.html', {'form': form})


@admin_required
def admin_campaign_list(request):
    """Shows every campaign with quick Edit / Delete actions."""
    campaign_list = Campaign.objects.all().order_by('-created_at')
    paginator = Paginator(campaign_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'admin/admin_campaign_list.html', {'page_obj': page_obj})


@admin_required
def admin_campaign_add(request):
    """Lets a staff member create a brand new campaign."""
    if request.method == 'POST':
        form = CampaignForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Campaign created successfully!')
            return redirect('admin_campaign_list')
    else:
        form = CampaignForm()

    return render(request, 'admin/admin_campaign_form.html', {
        'form': form, 'page_title': 'Add New Campaign'
    })


@admin_required
def admin_campaign_edit(request, campaign_id):
    """Lets a staff member edit an existing campaign, including updating the raised amount."""
    campaign = get_object_or_404(Campaign, id=campaign_id)

    if request.method == 'POST':
        form = CampaignForm(request.POST, request.FILES, instance=campaign)
        if form.is_valid():
            form.save()
            messages.success(request, 'Campaign updated successfully!')
            return redirect('admin_campaign_list')
    else:
        form = CampaignForm(instance=campaign)

    return render(request, 'admin/admin_campaign_form.html', {
        'form': form, 'page_title': f'Edit Campaign - {campaign.campaign_name}', 'campaign': campaign
    })


@admin_required
def admin_campaign_delete(request, campaign_id):
    """Deletes a campaign after the staff member confirms on a simple confirmation page."""
    campaign = get_object_or_404(Campaign, id=campaign_id)

    if request.method == 'POST':
        campaign_name = campaign.campaign_name
        campaign.delete()
        messages.success(request, f'Campaign "{campaign_name}" was deleted.')
        return redirect('admin_campaign_list')

    return render(request, 'admin/admin_campaign_delete.html', {'campaign': campaign})


@admin_required
def admin_donation_list(request):
    """Shows every donation made on the platform, with the newest first."""
    donation_list = Donation.objects.select_related('campaign', 'appeal').order_by('-donation_date')
    paginator = Paginator(donation_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'admin/admin_donation_list.html', {'page_obj': page_obj})


@admin_required
def admin_donor_list(request):
    """
    Shows a unique list of donors (grouped by email) along with how many
    donations they've made and how much they've given in total.
    """
    donor_list = []
    seen_emails = set()
    for donation in Donation.objects.all():
        if donation.email in seen_emails:
            continue
        seen_emails.add(donation.email)
        donor_donations = Donation.objects.filter(email=donation.email)
        donor_list.append({
            'donor_name': donation.donor_name,
            'email': donation.email,
            'total_given': donor_donations.aggregate(total=Sum('amount'))['total'] or 0,
            'donation_count': donor_donations.count(),
        })

    donor_list.sort(key=lambda d: d['total_given'], reverse=True)

    paginator = Paginator(donor_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'admin/admin_donor_list.html', {'page_obj': page_obj})


# ==========================================================
# ADMIN: VOLUNTEERS
# ==========================================================
@admin_required
def admin_volunteer_list(request):
    """
    Shows every registered user who checked "I'd like to volunteer" at
    sign-up, with a checkbox to select some/all of them and send a message.
    """
    volunteers = UserProfile.objects.filter(is_volunteer=True).select_related('user').order_by('-profile_created_on')

    paginator = Paginator(volunteers, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    recent_messages = VolunteerMessage.objects.all()[:5]

    context = {
        'page_obj': page_obj,
        'total_volunteers': volunteers.count(),
        'recent_messages': recent_messages,
    }
    return render(request, 'admin/admin_volunteer_list.html', context)


@admin_required
def admin_volunteer_message(request):
    """
    Sends an email to either every volunteer, or a hand-picked subset,
    and logs it as a VolunteerMessage so staff can see what was sent.
    Reached from the "Send Message" button/checkboxes on the Volunteers page.
    """
    volunteer_qs = UserProfile.objects.filter(is_volunteer=True).select_related('user')

    if request.method == 'POST':
        form = VolunteerMessageForm(request.POST)
        selected_ids = request.POST.getlist('volunteer_ids')
        send_to_all = request.POST.get('send_to_all') == 'on'

        if send_to_all:
            recipients = volunteer_qs
        else:
            recipients = volunteer_qs.filter(user_id__in=selected_ids)

        if not recipients.exists():
            messages.error(request, 'Please select at least one volunteer, or choose "Send to all".')
        elif form.is_valid():
            subject = form.cleaned_data['subject']
            body = form.cleaned_data['body']
            recipient_emails = [v.user.email for v in recipients if v.user.email]

            try:
                send_mail(
                    subject=subject,
                    message=body,
                    from_email=None,
                    recipient_list=recipient_emails,
                    fail_silently=True,
                )
            except Exception:
                pass

            volunteer_message = VolunteerMessage.objects.create(
                subject=subject, body=body, sent_to_all=send_to_all,
                sent_by=request.user,
            )
            volunteer_message.recipients.set([v.user for v in recipients])

            messages.success(request, f'Message sent to {recipients.count()} volunteer(s).')
            return redirect('admin_volunteer_list')

    else:
        form = VolunteerMessageForm()
        selected_ids = request.GET.getlist('volunteer_ids')

    context = {
        'form': form,
        'volunteers': volunteer_qs,
        'preselected_ids': [int(i) for i in selected_ids] if selected_ids else [],
    }
    return render(request, 'admin/admin_volunteer_message.html', context)


@admin_required
def admin_site_settings(request):
    """
    Lets NGO staff edit ALL of the Home Page's text and images:
    hero title/subtitle, impact stats, mission section, and footer contact
    info. This is what makes the public website's content fully dynamic.
    """
    site_settings = SiteSettings.load()
    updates = Update.objects.all().order_by('-publish_date')
    donation_appeals = DonationAppeal.objects.all().select_related('campaign')

    if request.method == 'POST':
        form = SiteSettingsForm(request.POST, request.FILES, instance=site_settings)
        active_panel = request.POST.get('active_panel', 'home-page')
        if form.is_valid():
            form.save()
            messages.success(request, 'Website content updated successfully! Check the home page.')
            return redirect(reverse('admin_site_settings') + '?panel=' + active_panel)
    else:
        form = SiteSettingsForm(instance=site_settings)

    return render(request, 'admin/admin_site_settings.html', {'form': form, 'updates': updates, 'donation_appeals': donation_appeals})


@admin_required
def admin_testimonial_list(request):
    """Shows every testimonial with quick Edit / Delete actions."""
    testimonial_list = Testimonial.objects.all()
    paginator = Paginator(testimonial_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'admin/admin_testimonial_list.html', {'page_obj': page_obj})


@admin_required
def admin_testimonial_edit(request, testimonial_id):
    """Lets a staff member edit an existing testimonial."""
    testimonial = get_object_or_404(Testimonial, id=testimonial_id)

    if request.method == 'POST':
        form = TestimonialForm(request.POST, request.FILES, instance=testimonial)
        if form.is_valid():
            form.save()
            messages.success(request, 'Testimonial updated successfully!')
            return redirect('admin_testimonial_list')
    else:
        form = TestimonialForm(instance=testimonial)

    return render(request, 'admin/admin_testimonial_form.html', {
        'form': form, 'page_title': 'Edit Testimonial'
    })


@admin_required
def admin_testimonial_delete(request, testimonial_id):
    """Deletes a testimonial after confirmation."""
    testimonial = get_object_or_404(Testimonial, id=testimonial_id)

    if request.method == 'POST':
        testimonial.delete()
        messages.success(request, 'Testimonial deleted.')
        return redirect('admin_testimonial_list')

    return render(request, 'admin/admin_testimonial_delete.html', {'testimonial': testimonial})


# ==========================================================
# ADMIN: FAQ MANAGEMENT
# ==========================================================
@admin_required
def admin_faq_list(request):
    """Shows every FAQ with quick Edit / Delete actions."""
    faq_list = FAQ.objects.all()
    paginator = Paginator(faq_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'admin/admin_faq_list.html', {'page_obj': page_obj})


@admin_required
def admin_faq_add(request):
    """Lets a staff member add a new FAQ entry to show on the public FAQ page."""
    if request.method == 'POST':
        form = FAQForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'FAQ added successfully!')
            return redirect('admin_faq_list')
    else:
        form = FAQForm()

    return render(request, 'admin/admin_faq_form.html', {
        'form': form, 'page_title': 'Add New FAQ'
    })


@admin_required
def admin_faq_edit(request, faq_id):
    """Lets a staff member edit an existing FAQ entry."""
    faq = get_object_or_404(FAQ, id=faq_id)

    if request.method == 'POST':
        form = FAQForm(request.POST, instance=faq)
        if form.is_valid():
            form.save()
            messages.success(request, 'FAQ updated successfully!')
            return redirect('admin_faq_list')
    else:
        form = FAQForm(instance=faq)

    return render(request, 'admin/admin_faq_form.html', {
        'form': form, 'page_title': 'Edit FAQ'
    })


@admin_required
def admin_faq_delete(request, faq_id):
    """Deletes a FAQ entry after confirmation."""
    faq = get_object_or_404(FAQ, id=faq_id)

    if request.method == 'POST':
        faq.delete()
        messages.success(request, 'FAQ deleted.')
        return redirect('admin_faq_list')

    return render(request, 'admin/admin_faq_delete.html', {'faq': faq})


# ==========================================================
# ADMIN: HOME PAGE "UPDATES" CARDS
# ==========================================================
@admin_required
def admin_update_list(request):
    """Shows every 'Updates From [NGO]' card with quick Edit / Delete actions."""
    update_list = Update.objects.all()
    paginator = Paginator(update_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'admin/admin_update_list.html', {'page_obj': page_obj})


@admin_required
def admin_update_add(request):
    """Lets a staff member add a new update card to show on the home page."""
    if request.method == 'POST':
        form = UpdateForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Update added successfully!')
            return redirect(reverse('admin_site_settings') + '?panel=home-page')
    else:
        form = UpdateForm()

    return render(request, 'admin/admin_update_form.html', {
        'form': form, 'page_title': 'Add New Update'
    })


@admin_required
def admin_update_edit(request, update_id):
    """Lets a staff member edit an existing update card."""
    update = get_object_or_404(Update, id=update_id)

    if request.method == 'POST':
        form = UpdateForm(request.POST, request.FILES, instance=update)
        if form.is_valid():
            form.save()
            messages.success(request, 'Update saved successfully!')
            return redirect(reverse('admin_site_settings') + '?panel=home-page')
    else:
        form = UpdateForm(instance=update)

    return render(request, 'admin/admin_update_form.html', {
        'form': form, 'page_title': 'Edit Update'
    })


@admin_required
def admin_update_delete(request, update_id):
    """Deletes an update card after confirmation."""
    update = get_object_or_404(Update, id=update_id)

    if request.method == 'POST':
        update.delete()
        messages.success(request, 'Update deleted.')
        return redirect(reverse('admin_site_settings') + '?panel=home-page')

    return render(request, 'admin/admin_update_delete.html', {'update': update})


# ==========================================================
# ADMIN: DONATION APPEALS (rich "story" shown in the Donate flow)
# ==========================================================
@admin_required
def admin_appeal_add(request):
    """
    Lets a staff member write a new donation appeal -- the "Add New Story"
    form: title, rich content, image, linked campaign, and a dynamic table
    of essential supplies received.
    """
    if request.method == 'POST':
        form = DonationAppealForm(request.POST, request.FILES)
        formset = AppealSupplyItemFormSet(request.POST, prefix='items')

        if form.is_valid() and formset.is_valid():
            appeal = form.save()
            formset.instance = appeal
            formset.save()
            messages.success(request, 'Donation appeal saved successfully!')
            return redirect(reverse('admin_site_settings') + '?panel=home-page')
    else:
        form = DonationAppealForm()
        formset = AppealSupplyItemFormSet(prefix='items')

    return render(request, 'admin/admin_appeal_form.html', {
        'form': form, 'formset': formset, 'page_title': 'Add New Story'
    })


@admin_required
def admin_appeal_edit(request, appeal_id):
    """Lets a staff member edit an existing donation appeal and its supply list."""
    appeal = get_object_or_404(DonationAppeal, id=appeal_id)

    if request.method == 'POST':
        form = DonationAppealForm(request.POST, request.FILES, instance=appeal)
        formset = AppealSupplyItemFormSet(request.POST, instance=appeal, prefix='items')

        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            messages.success(request, 'Donation appeal saved successfully!')
            return redirect(reverse('admin_site_settings') + '?panel=home-page')
    else:
        form = DonationAppealForm(instance=appeal)
        formset = AppealSupplyItemFormSet(instance=appeal, prefix='items')

    return render(request, 'admin/admin_appeal_form.html', {
        'form': form, 'formset': formset, 'page_title': 'Edit Story', 'appeal': appeal
    })


@admin_required
def admin_appeal_delete(request, appeal_id):
    """Deletes a donation appeal (and its supply items) after confirmation."""
    appeal = get_object_or_404(DonationAppeal, id=appeal_id)

    if request.method == 'POST':
        appeal.delete()
        messages.success(request, 'Donation appeal deleted.')
        return redirect(reverse('admin_site_settings') + '?panel=home-page')

    return render(request, 'admin/admin_appeal_delete.html', {'appeal': appeal})


# ==========================================================
# ADMIN: CONTACT MESSAGES
# ==========================================================
@admin_required
def admin_contact_list(request):
    """Shows every message submitted through the public Contact Us page."""
    contact_list = ContactMessage.objects.all()
    paginator = Paginator(contact_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'admin/admin_contact_list.html', {'page_obj': page_obj})


@admin_required
def admin_contact_view(request, message_id):
    """Shows one message's full detail and marks it as read."""
    contact_message = get_object_or_404(ContactMessage, id=message_id)
    if not contact_message.is_read:
        contact_message.is_read = True
        contact_message.save()
    return render(request, 'admin/admin_contact_detail.html', {'contact_message': contact_message})


@admin_required
def admin_contact_delete(request, message_id):
    """Deletes a contact message after confirmation."""
    contact_message = get_object_or_404(ContactMessage, id=message_id)

    if request.method == 'POST':
        contact_message.delete()
        messages.success(request, 'Message deleted.')
        return redirect('admin_contact_list')

    return render(request, 'admin/admin_contact_delete.html', {'contact_message': contact_message})


# ==========================================================
# ADMIN: HELP REQUESTS
# ==========================================================
@admin_required
def admin_request_list(request):
    """Shows every submission from the public 'Get Help' form on the homepage."""
    status_filter = request.GET.get('status')
    help_requests = HelpRequest.objects.all()
    if status_filter:
        help_requests = help_requests.filter(status=status_filter)

    paginator = Paginator(help_requests, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'status_choices': HelpRequest.STATUS_CHOICES,
        'selected_status': status_filter,
    }
    return render(request, 'admin/admin_request_list.html', context)


@admin_required
def admin_request_detail(request, request_id):
    """
    Shows one help request's full detail, including the attached document
    (if any) and lets staff update its status / add internal notes.
    Also allows the admin to send a custom email to the requester.
    """
    help_request = get_object_or_404(HelpRequest, id=request_id)

    if request.method == 'POST':
        action = request.POST.get('action', 'update_status')

        if action == 'send_email':
            email_subject = request.POST.get('email_subject', '').strip()
            email_message = request.POST.get('email_message', '').strip()

            if not email_subject or not email_message:
                messages.error(request, 'Both subject and message are required to send an email.')
            else:
                try:
                    send_mail(
                        subject=email_subject,
                        message=email_message,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[help_request.email],
                        fail_silently=False,
                    )
                    messages.success(request, f'Email sent successfully to {help_request.email}!')
                except Exception as e:
                    messages.error(request, f'Failed to send email: {e}')

            return redirect('admin_request_detail', request_id=help_request.id)

        else:
            new_status = request.POST.get('status')
            admin_notes = request.POST.get('admin_notes', '')

            if new_status in dict(HelpRequest.STATUS_CHOICES):
                help_request.status = new_status
            help_request.admin_notes = admin_notes
            help_request.save()

            messages.success(request, 'Request updated.')
            return redirect('admin_request_detail', request_id=help_request.id)

    context = {
        'help_request': help_request,
        'admin_email': settings.DEFAULT_FROM_EMAIL,
    }
    return render(request, 'admin/admin_request_detail.html', context)


@admin_required
def admin_request_delete(request, request_id):
    """Deletes a help request (and its attached document) after confirmation."""
    help_request = get_object_or_404(HelpRequest, id=request_id)

    if request.method == 'POST':
        help_request.delete()
        messages.success(request, 'Request deleted.')
        return redirect('request')

    return render(request, 'admin/admin_request_delete.html', {'help_request': help_request})


# ==========================================================
# ADMIN: NOTIFICATIONS
# ==========================================================
@admin_required
def admin_notifications_list(request):
    """Shows all notifications for the admin, latest unread first."""
    notification_list = Notification.objects.order_by('is_read', '-created_at')
    paginator = Paginator(notification_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'admin/admin_notifications_list.html', {'page_obj': page_obj})


@admin_required
def admin_notification_mark_read(request, notification_id):
    """Marks a single notification as read and redirects to its URL."""
    notification = get_object_or_404(Notification, id=notification_id)
    notification.is_read = True
    notification.save()
    return redirect(notification.url)


@admin_required
def admin_notifications_mark_all_read(request):
    """Marks all notifications as read and redirects back."""
    Notification.objects.filter(is_read=False).update(is_read=True)
    messages.success(request, 'All notifications marked as read.')
    return redirect('admin_notifications_list')


@admin_required
def admin_notification_mark_read_ajax(request, notification_id):
    """AJAX: marks a single notification as read and returns updated counts."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)

    notification = get_object_or_404(Notification, id=notification_id)
    notification.is_read = True
    notification.save()

    unread_count = Notification.objects.filter(is_read=False).count()

    return JsonResponse({
        'success': True,
        'unread_count': unread_count,
        'notification_id': notification.id,
        'url': notification.url,
    })


@admin_required
def admin_notifications_mark_all_read_ajax(request):
    """AJAX: marks all notifications as read and returns updated counts."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)

    Notification.objects.filter(is_read=False).update(is_read=True)
    return JsonResponse({
        'success': True,
        'unread_count': 0,
    })