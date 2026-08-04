"""
forms.py
--------
This file defines Django Forms used for user input across the whole site:
the public donation form, registration, the custom admin panel's forms
(Campaign, Site Settings, Testimonial) and the donor profile form.
"""

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Donation, Campaign, SiteSettings, Testimonial, UserProfile


class DonationForm(forms.ModelForm):
    """
    A ModelForm automatically creates form fields based on the Donation model.
    The donor picks WHICH campaign to donate to from a dropdown -- if they
    arrived via a specific campaign's "Donate Now" button, that campaign
    is pre-selected automatically (see views.py -> donate()).
    """

    class Meta:
        model = Donation
        fields = ['campaign', 'donor_name', 'email', 'amount', 'payment_method']

        # widgets let us add Bootstrap CSS classes to each input field
        widgets = {
            'campaign': forms.Select(attrs={'class': 'form-select', 'id': 'id_campaign'}),
            'donor_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your full name'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your email'
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter amount'
            }),
            'payment_method': forms.RadioSelect(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show campaigns that are currently active, so donors can't
        # accidentally donate to a completed/upcoming campaign.
        self.fields['campaign'].queryset = Campaign.objects.filter(status='active')
        self.fields['campaign'].label = 'Select Campaign'
        self.fields['amount'].label = 'Donation Amount (Rs.)'


class RegisterForm(UserCreationForm):
    """
    Extends Django's built-in UserCreationForm to also ask for an email address.
    """
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={
        'class': 'form-control',
        'placeholder': 'Enter your email'
    }))

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes to the default UserCreationForm fields too
        self.fields['username'].widget.attrs.update({
            'class': 'form-control', 'placeholder': 'Choose a username'
        })
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control', 'placeholder': 'Enter password'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control', 'placeholder': 'Confirm password'
        })

    def clean_email(self):
        """
        Makes sure two different accounts can never share the same email address.
        This matters a lot for this site because BOTH login and "Forgot Password"
        now look a user up by their email -- if two accounts shared an email,
        there would be no way to tell them apart.
        """
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('An account with this email already exists. Please sign in instead.')
        return email


class EmailLoginForm(forms.Form):
    """
    A login form that authenticates by EMAIL instead of username.

    Django's built-in AuthenticationForm only knows how to check the
    "username" field, so instead of using it we take the email + password
    here, look up which account owns that email in the view (see
    login_view() in views.py), and authenticate with that account's actual
    username behind the scenes -- the donor never needs to know or type
    their username to log in.
    """
    email = forms.EmailField(widget=forms.EmailInput(attrs={
        'class': 'form-control', 'placeholder': 'Enter your email'
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control', 'placeholder': 'Enter your password'
    }))


class ProfileForm(forms.ModelForm):
    """
    Lets a logged-in donor update their account info (username, email) as well
    as their profile picture, phone number and address.

    NOTE: username and email actually belong to Django's built-in User model,
    not UserProfile -- so they are added here as extra form fields and saved
    to request.user manually inside the dashboard_profile() view in views.py.
    """

    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = UserProfile
        fields = ['profile_picture', 'phone_number', 'address']
        widgets = {
            'profile_picture': forms.FileInput(attrs={'class': 'profile-file-input', 'accept': 'image/*'}),
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'e.g. +91 98765 43210'
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3, 'placeholder': 'Your address'
            }),
        }

    def __init__(self, *args, **kwargs):
        # We need to know WHICH user this profile belongs to, so we can:
        #   1) pre-fill the username/email fields with their current values
        #   2) make sure the "username already taken" check below ignores
        #      this same user (otherwise they'd never be able to save their
        #      own unchanged username!)
        self.current_user = kwargs.pop('current_user', None)
        super().__init__(*args, **kwargs)

        if self.current_user and not self.is_bound:
            self.fields['username'].initial = self.current_user.username
            self.fields['email'].initial = self.current_user.email

    def clean_username(self):
        username = self.cleaned_data['username']
        existing = User.objects.filter(username=username)
        if self.current_user:
            existing = existing.exclude(pk=self.current_user.pk)
        if existing.exists():
            raise forms.ValidationError('That username is already taken. Please choose another.')
        return username

    def clean_email(self):
        # Same idea as clean_username above -- but for email, since login and
        # "Forgot Password" both look accounts up by email address.
        email = self.cleaned_data['email'].strip().lower()
        existing = User.objects.filter(email__iexact=email)
        if self.current_user:
            existing = existing.exclude(pk=self.current_user.pk)
        if existing.exists():
            raise forms.ValidationError('That email is already used by another account.')
        return email


class CampaignForm(forms.ModelForm):
    """
    Used in our CUSTOM admin panel (not Django's default /admin/) to let
    the NGO staff Add / Edit a campaign through a normal Bootstrap form.
    """

    class Meta:
        model = Campaign
        fields = [
            'campaign_name', 'category', 'description',
            'goal_amount', 'raised_amount', 'campaign_image',
            'start_date', 'end_date', 'status',
        ]
        widgets = {
            'campaign_name': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'e.g. Educate a Child'
            }),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 5,
                'placeholder': 'Describe the campaign in detail'
            }),
            'goal_amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'raised_amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'campaign_image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }


class SiteSettingsForm(forms.ModelForm):
    """
    Used in the custom admin panel's "Website Content" page. Every field
    here controls something the visitor sees on the public Home Page --
    hero text, impact stats, mission section, and footer contact info.
    """

    class Meta:
        model = SiteSettings
        fields = [
            'ngo_name',
            'hero_title_line1', 'hero_title_highlight', 'hero_subtitle', 'hero_image',
            'stat_campaigns', 'stat_lives_impacted', 'stat_funds_raised', 'stat_donors',
            'mission_title', 'mission_text', 'mission_image',
            'footer_about_text', 'contact_address', 'contact_email', 'contact_phone',
        ]
        widgets = {
            'ngo_name': forms.TextInput(attrs={'class': 'form-control'}),
            'hero_title_line1': forms.TextInput(attrs={'class': 'form-control'}),
            'hero_title_highlight': forms.TextInput(attrs={'class': 'form-control'}),
            'hero_subtitle': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'hero_image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'stat_campaigns': forms.TextInput(attrs={'class': 'form-control'}),
            'stat_lives_impacted': forms.TextInput(attrs={'class': 'form-control'}),
            'stat_funds_raised': forms.TextInput(attrs={'class': 'form-control'}),
            'stat_donors': forms.TextInput(attrs={'class': 'form-control'}),
            'mission_title': forms.TextInput(attrs={'class': 'form-control'}),
            'mission_text': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'mission_image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'footer_about_text': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'contact_address': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'contact_phone': forms.TextInput(attrs={'class': 'form-control'}),
        }


class TestimonialForm(forms.ModelForm):
    """Used in the custom admin panel to Add/Edit a donor testimonial."""

    class Meta:
        model = Testimonial
        fields = ['donor_name', 'donor_role', 'message', 'rating', 'photo', 'is_active', 'display_order']
        widgets = {
            'donor_name': forms.TextInput(attrs={'class': 'form-control'}),
            'donor_role': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Regular Donor'}),
            'message': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'rating': forms.Select(attrs={'class': 'form-select'}, choices=[(i, f'{i} Stars') for i in range(1, 6)]),
            'photo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'display_order': forms.NumberInput(attrs={'class': 'form-control'}),
        }


class AdminLoginForm(forms.Form):
    """
    A simple separate login form for the custom admin panel.
    Kept apart from the donor-facing login form on purpose.
    """
    username = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-control', 'placeholder': 'Admin username'
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control', 'placeholder': 'Admin password'
    }))
