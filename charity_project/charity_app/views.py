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
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.contrib import messages
from django.http import HttpResponse
from django.db.models import Sum
from decimal import Decimal

from .models import Campaign, Donation, SiteSettings, Testimonial, UserProfile
from .forms import (
    DonationForm, RegisterForm, CampaignForm, AdminLoginForm,
    SiteSettingsForm, TestimonialForm, ProfileForm,
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
    """
    site_settings = SiteSettings.load()

    # Show only 3 active campaigns as "Featured Campaigns" on the home page
    featured_campaigns = Campaign.objects.filter(status='active').order_by('-created_at')[:3]

    # Build the "Our Impact" cards dynamically from the Campaign category choices
    impact_cards = []
    for value, label in Campaign.CATEGORY_CHOICES:
        info = CATEGORY_ICONS.get(value, {'icon': 'bi-heart-fill', 'blurb': ''})
        impact_cards.append({'label': label, 'icon': info['icon'], 'blurb': info['blurb']})

    # Testimonials that staff have marked as active, in their chosen display order
    testimonials = Testimonial.objects.filter(is_active=True)

    context = {
        'settings': site_settings,
        'featured_campaigns': featured_campaigns,
        'impact_cards': impact_cards,
        'testimonials': testimonials,
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
# 4. DONATE PAGE (Donation Form) -- Step 1 of the payment flow
# ==========================================================
def donate(request, campaign_id=None):
    """
    Shows the donation form. If the donor arrived from a specific
    campaign's "Donate Now" button, that campaign is pre-selected in the
    dropdown; otherwise they can pick any active campaign themselves.

    On submit, we do NOT save the donation yet -- we temporarily store the
    submitted details in the session and send the donor to the Payment
    Gateway page (step 2), which is where the "payment" is confirmed and
    the Donation row is actually created.
    """
    preselected_campaign = None
    if campaign_id:
        preselected_campaign = get_object_or_404(Campaign, id=campaign_id)

    if request.method == 'POST':
        form = DonationForm(request.POST)
        if form.is_valid():
            # Temporarily remember the donor's details in the session.
            # Decimal amounts must be converted to strings to be stored in the session.
            request.session['pending_donation'] = {
                'campaign_id': form.cleaned_data['campaign'].id,
                'donor_name': form.cleaned_data['donor_name'],
                'email': form.cleaned_data['email'],
                'amount': str(form.cleaned_data['amount']),
                'payment_method': form.cleaned_data['payment_method'],
            }
            return redirect('payment_gateway')
    else:
        initial = {'campaign': preselected_campaign} if preselected_campaign else {}
        form = DonationForm(initial=initial)

    # Build a small lookup of every active campaign's details (as plain numbers/strings)
    # so donate.html's JavaScript can update the live preview card without a page reload.
    campaigns_json = {}
    for c in Campaign.objects.filter(status='active'):
        campaigns_json[str(c.id)] = {
            'name': c.campaign_name,
            'image': c.campaign_image.url if c.campaign_image else 'https://placehold.co/400x250/dcfce7/16a34a?text=' + c.campaign_name,
            'raised': str(c.raised_amount),
            'goal': str(c.goal_amount),
            'percent': str(c.progress_percentage()),
        }

    context = {'form': form, 'campaign': preselected_campaign, 'campaigns_json': campaigns_json}
    return render(request, 'website/donate.html', context)


# ==========================================================
# 5. PAYMENT GATEWAY PAGE -- Step 2 of the payment flow
# ==========================================================
def payment_gateway(request):
    """
    Shows a demo "Complete Your Payment" screen (UPI/Card/Net Banking tabs
    with a QR code) using the details stored in the session by donate().

    When the donor clicks "I Have Completed the Payment", we finally
    create the real Donation row, update the campaign's raised amount,
    and send them to the Success page.

    NOTE: This is a DEMO payment flow for a college/portfolio project.
    No real money moves and no real payment gateway is contacted.
    """
    pending = request.session.get('pending_donation')
    if not pending:
        messages.error(request, 'Your donation session expired. Please fill the form again.')
        return redirect('campaign_list')

    campaign = get_object_or_404(Campaign, id=pending['campaign_id'])

    if request.method == 'POST':
        donation = Donation(
            campaign=campaign,
            donor_name=pending['donor_name'],
            email=pending['email'],
            amount=Decimal(pending['amount']),
            payment_method=pending['payment_method'],
        )
        if request.user.is_authenticated:
            donation.user = request.user

        # transaction_id is generated automatically inside models.py -> save()
        donation.save()

        # Update the campaign's raised amount
        campaign.raised_amount += donation.amount
        campaign.save()

        # Clear the pending donation from the session -- it's been "paid" now
        del request.session['pending_donation']

        return redirect('success', donation_id=donation.id)

    context = {
        'campaign': campaign,
        'pending': pending,
        # A fake UPI QR code image, generated on the fly for the demo flow
        'qr_data': f"upi://pay?pa=helpinghands@upi&am={pending['amount']}&cu=INR&tn=Donation-{campaign.id}",
    }
    return render(request, 'website/payment_gateway.html', context)


# ==========================================================
# 6. PAYMENT SUCCESS PAGE
# ==========================================================
def success(request, donation_id):
    """
    Shown right after a donation is submitted.
    Displays Thank You message, transaction ID, amount, campaign name.
    """
    donation = get_object_or_404(Donation, id=donation_id)
    context = {'donation': donation}
    return render(request, 'website/success.html', context)


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
Campaign       : {donation.campaign.campaign_name}
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
            UserProfile.objects.create(user=user)
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
    """
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('dashboard')
    else:
        form = AuthenticationForm()

    return render(request, 'website/login.html', {'form': form})


# ==========================================================
# 10. USER LOGOUT
# ==========================================================
def logout_view(request):
    """
    Logs the current user out and sends them back to the home page.
    """
    logout(request)
    return redirect('home')


# ==========================================================
# 11. DONOR DASHBOARD (split across a few pages, with a shared sidebar)
# ==========================================================
@login_required
def dashboard(request):
    """Overview page: profile summary card, quick stats, and recent donations."""
    donations = Donation.objects.filter(user=request.user).order_by('-donation_date')
    total_donated = donations.aggregate(total=Sum('amount'))['total'] or 0
    campaigns_supported = donations.values('campaign').distinct().count()

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
    donations = Donation.objects.filter(user=request.user).order_by('-donation_date')
    return render(request, 'website/dashboard_donations.html', {'donations': donations})


@login_required
def dashboard_receipts(request):
    """Shows every donation with a Download Receipt button next to it."""
    donations = Donation.objects.filter(user=request.user).order_by('-donation_date')
    return render(request, 'website/dashboard_receipts.html', {'donations': donations})


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
    return redirect('admin_login')


@admin_required
def admin_dashboard(request):
    """
    The main landing page of our custom admin panel.
    Shows quick stats and the most recent donations.
    """
    context = {
        'total_campaigns': Campaign.objects.count(),
        'active_campaigns': Campaign.objects.filter(status='active').count(),
        'total_donations': Donation.objects.count(),
        'total_raised': Donation.objects.aggregate(total=Sum('amount'))['total'] or 0,
        'total_donors': Donation.objects.values('email').distinct().count(),
        'recent_donations': Donation.objects.order_by('-donation_date')[:5],
    }
    return render(request, 'admin/admin_dashboard.html', context)


@admin_required
def admin_campaign_list(request):
    """Shows every campaign with quick Edit / Delete actions."""
    campaigns = Campaign.objects.all().order_by('-created_at')
    return render(request, 'admin/admin_campaign_list.html', {'campaigns': campaigns})


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
    donations = Donation.objects.select_related('campaign').order_by('-donation_date')
    return render(request, 'admin/admin_donation_list.html', {'donations': donations})


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

    return render(request, 'admin/admin_donor_list.html', {'donors': donor_list})


@admin_required
def admin_site_settings(request):
    """
    Lets NGO staff edit ALL of the Home Page's text and images:
    hero title/subtitle, impact stats, mission section, and footer contact
    info. This is what makes the public website's content fully dynamic.
    """
    site_settings = SiteSettings.load()

    if request.method == 'POST':
        form = SiteSettingsForm(request.POST, request.FILES, instance=site_settings)
        if form.is_valid():
            form.save()
            messages.success(request, 'Website content updated successfully! Check the home page.')
            return redirect('admin_site_settings')
    else:
        form = SiteSettingsForm(instance=site_settings)

    return render(request, 'admin/admin_site_settings.html', {'form': form})


@admin_required
def admin_testimonial_list(request):
    """Shows every testimonial with quick Edit / Delete actions."""
    testimonials = Testimonial.objects.all()
    return render(request, 'admin/admin_testimonial_list.html', {'testimonials': testimonials})


@admin_required
def admin_testimonial_add(request):
    """Lets a staff member add a new testimonial to show on the home page."""
    if request.method == 'POST':
        form = TestimonialForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Testimonial added successfully!')
            return redirect('admin_testimonial_list')
    else:
        form = TestimonialForm()

    return render(request, 'admin/admin_testimonial_form.html', {
        'form': form, 'page_title': 'Add New Testimonial'
    })


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
