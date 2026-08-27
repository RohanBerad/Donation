"""
forms.py
--------
This file defines Django Forms used for user input across the whole site:
the public donation form, registration, the custom admin panel's forms
(Campaign, Site Settings, Testimonial) and the donor profile form.
"""

from django import forms
from django.forms import inlineformset_factory
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Donation, Campaign, SiteSettings, Testimonial, UserProfile, FAQ, ContactMessage, HelpRequest, Update, DonationAppeal, AppealSupplyItem, VolunteerMessage

import re

# ==========================================================
# SHARED VALIDATION HELPERS
# ----------------------------------------------------------
# Every form below reuses these so the "normal" rules (valid name,
# valid phone number, sane file size/type, positive money amounts,
# minimum text length) are enforced the same way everywhere on the site.
# ==========================================================

NAME_REGEX = re.compile(r"^[A-Za-z][A-Za-z.'\- ]{1,99}$")
PHONE_REGEX = re.compile(r"^\+?[0-9][0-9\s\-]{6,14}$")

ALLOWED_IMAGE_EXTENSIONS = ['jpg', 'jpeg', 'png', 'gif', 'webp']
ALLOWED_DOCUMENT_EXTENSIONS = ['pdf', 'jpg', 'jpeg', 'png', 'doc', 'docx']

MAX_IMAGE_SIZE_MB = 5
MAX_DOCUMENT_SIZE_MB = 10


def validate_name(value, field_label="Name"):
    """Letters, spaces, apostrophes, hyphens and periods only -- no digits or symbols."""
    value = (value or '').strip()
    if not NAME_REGEX.match(value):
        raise forms.ValidationError(
            f"{field_label} should contain only letters (and spaces/hyphens/apostrophes), "
            f"and be at least 2 characters long."
        )
    return value


def validate_phone(value):
    """Optional field -- only validated if the user actually typed something."""
    value = (value or '').strip()
    if value and not PHONE_REGEX.match(value):
        raise forms.ValidationError(
            "Enter a valid phone number (7-15 digits, may include +, spaces, or -)."
        )
    return value


def _is_newly_uploaded(f):
    """
    Distinguishes a freshly-uploaded file (InMemoryUploadedFile /
    TemporaryUploadedFile, which have .content_type) from an existing
    FieldFile already saved on the model (which doesn't) -- so we only
    re-validate size/type when the user actually picked a new file.
    """
    return bool(f) and hasattr(f, 'content_type')


def _file_extension(f):
    return f.name.rsplit('.', 1)[-1].lower() if f and '.' in f.name else ''


def validate_image_file(f, max_mb=MAX_IMAGE_SIZE_MB):
    if not _is_newly_uploaded(f):
        return
    if f.size > max_mb * 1024 * 1024:
        raise forms.ValidationError(f"Image is too large. Maximum allowed size is {max_mb}MB.")
    if _file_extension(f) not in ALLOWED_IMAGE_EXTENSIONS:
        raise forms.ValidationError("Unsupported image format. Please upload a JPG, PNG, GIF, or WEBP file.")


def validate_document_file(f, max_mb=MAX_DOCUMENT_SIZE_MB):
    if not _is_newly_uploaded(f):
        return
    if f.size > max_mb * 1024 * 1024:
        raise forms.ValidationError(f"File is too large. Maximum allowed size is {max_mb}MB.")
    if _file_extension(f) not in ALLOWED_DOCUMENT_EXTENSIONS:
        raise forms.ValidationError("Unsupported file type. Please upload a PDF, Word document, or image (JPG/PNG).")


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
        self.fields['campaign'].empty_label = 'General Donation (No specific fundraiser)'
        self.fields['campaign'].required = False
        self.fields['amount'].label = 'Donation Amount (Rs.)'

    def clean_donor_name(self):
        return validate_name(self.cleaned_data['donor_name'], "Name")

    def clean_amount(self):
        amount = self.cleaned_data['amount']
        if amount < 10:
            raise forms.ValidationError("Minimum donation amount is Rs. 10.")
        if amount > 1000000:
            raise forms.ValidationError("For donations above Rs. 10,00,000, please contact us directly.")
        return amount


class RegisterForm(UserCreationForm):
    """
    Extends Django's built-in UserCreationForm to also ask for an email address
    and whether the person wants to volunteer with us.
    """
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={
        'class': 'form-control',
        'placeholder': 'Enter your email'
    }))
    is_volunteer = forms.BooleanField(
        required=False,
        label="I'd like to volunteer with you",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

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

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if len(username) < 4:
            raise forms.ValidationError("Username must be at least 4 characters long.")
        return username

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
    as their profile picture, phone number, address, and bio.

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
    bio = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Tell us a little about yourself...'})
    )

    class Meta:
        model = UserProfile
        fields = ['profile_picture', 'phone_number', 'address', 'bio', 'is_volunteer']
        widgets = {
            'profile_picture': forms.FileInput(attrs={'class': 'profile-file-input', 'accept': 'image/*'}),
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'e.g. +91 98765 43210'
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3, 'placeholder': 'Your address'
            }),
            'is_volunteer': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
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
        username = self.cleaned_data['username'].strip()
        if len(username) < 3:
            raise forms.ValidationError('Username must be at least 3 characters long.')
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            raise forms.ValidationError('Username may only contain letters, digits, and underscores.')
        existing = User.objects.filter(username=username)
        if self.current_user:
            existing = existing.exclude(pk=self.current_user.pk)
        if existing.exists():
            raise forms.ValidationError('That username is already taken. Please choose another.')
        return username

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if not email:
            raise forms.ValidationError('Email address is required.')
        existing = User.objects.filter(email__iexact=email)
        if self.current_user:
            existing = existing.exclude(pk=self.current_user.pk)
        if existing.exists():
            raise forms.ValidationError('That email is already used by another account.')
        return email

    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number', '').strip()
        if not phone:
            raise forms.ValidationError('Phone number is required.')
        return validate_phone(phone)

    def clean_bio(self):
        bio = self.cleaned_data.get('bio', '').strip()
        if len(bio) > 500:
            raise forms.ValidationError('Bio must be 500 characters or fewer.')
        return bio

    def clean_address(self):
        address = self.cleaned_data.get('address', '').strip()
        if len(address) > 500:
            raise forms.ValidationError('Address must be 500 characters or fewer.')
        return address

    def clean_profile_picture(self):
        picture = self.cleaned_data.get('profile_picture')
        validate_image_file(picture)
        return picture


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

    def clean_campaign_name(self):
        name = self.cleaned_data['campaign_name'].strip()
        if len(name) < 5:
            raise forms.ValidationError("Campaign name should be at least 5 characters long.")
        return name

    def clean_description(self):
        description = self.cleaned_data['description'].strip()
        if len(description) < 20:
            raise forms.ValidationError("Please provide a more detailed description (at least 20 characters).")
        return description

    def clean_goal_amount(self):
        goal_amount = self.cleaned_data['goal_amount']
        if goal_amount <= 0:
            raise forms.ValidationError("Goal amount must be greater than zero.")
        return goal_amount

    def clean_raised_amount(self):
        raised_amount = self.cleaned_data['raised_amount']
        if raised_amount < 0:
            raise forms.ValidationError("Raised amount cannot be negative.")
        return raised_amount

    def clean_campaign_image(self):
        image = self.cleaned_data.get('campaign_image')
        validate_image_file(image)
        return image

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        goal_amount = cleaned_data.get('goal_amount')
        raised_amount = cleaned_data.get('raised_amount')

        if start_date and end_date and end_date <= start_date:
            self.add_error('end_date', "End date must be after the start date.")

        return cleaned_data


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
            'stat_campaigns', 'stat_lives_impacted', 'stat_funds_raised', 'stat_donors', 'stat_partners_volunteers',
            'about_heading', 'about_heading_highlight', 'about_text', 'about_image', 'about_video_url',
            'about_vision_text', 'about_story_image', 'about_story_quote', 'registration_number',
            'team_section_title', 'team_section_subtitle',
            'team_member_1_name', 'team_member_1_role', 'team_member_1_photo',
            'team_member_2_name', 'team_member_2_role', 'team_member_2_photo',
            'team_member_3_name', 'team_member_3_role', 'team_member_3_photo',
            'team_member_4_name', 'team_member_4_role', 'team_member_4_photo',
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
            'stat_partners_volunteers': forms.TextInput(attrs={'class': 'form-control'}),
            'about_heading': forms.TextInput(attrs={'class': 'form-control'}),
            'about_heading_highlight': forms.TextInput(attrs={'class': 'form-control'}),
            'about_text': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'about_image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'about_video_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://youtube.com/watch?v=...'}),
            'about_vision_text': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'about_story_image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'about_story_quote': forms.TextInput(attrs={'class': 'form-control'}),
            'registration_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. NGO/2019/00123'}),
            'team_section_title': forms.TextInput(attrs={'class': 'form-control'}),
            'team_section_subtitle': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'team_member_1_name': forms.TextInput(attrs={'class': 'form-control'}),
            'team_member_1_role': forms.TextInput(attrs={'class': 'form-control'}),
            'team_member_1_photo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'team_member_2_name': forms.TextInput(attrs={'class': 'form-control'}),
            'team_member_2_role': forms.TextInput(attrs={'class': 'form-control'}),
            'team_member_2_photo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'team_member_3_name': forms.TextInput(attrs={'class': 'form-control'}),
            'team_member_3_role': forms.TextInput(attrs={'class': 'form-control'}),
            'team_member_3_photo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'team_member_4_name': forms.TextInput(attrs={'class': 'form-control'}),
            'team_member_4_role': forms.TextInput(attrs={'class': 'form-control'}),
            'team_member_4_photo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'footer_about_text': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'contact_address': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'contact_phone': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean_contact_phone(self):
        return validate_phone(self.cleaned_data.get('contact_phone', ''))

    def clean_hero_image(self):
        image = self.cleaned_data.get('hero_image')
        validate_image_file(image)
        return image

    def clean_about_image(self):
        image = self.cleaned_data.get('about_image')
        validate_image_file(image)
        return image

    def clean_about_story_image(self):
        image = self.cleaned_data.get('about_story_image')
        validate_image_file(image)
        return image

    def clean_team_member_1_photo(self):
        image = self.cleaned_data.get('team_member_1_photo')
        validate_image_file(image)
        return image

    def clean_team_member_2_photo(self):
        image = self.cleaned_data.get('team_member_2_photo')
        validate_image_file(image)
        return image

    def clean_team_member_3_photo(self):
        image = self.cleaned_data.get('team_member_3_photo')
        validate_image_file(image)
        return image

    def clean_team_member_4_photo(self):
        image = self.cleaned_data.get('team_member_4_photo')
        validate_image_file(image)
        return image


class TestimonialSubmissionForm(forms.ModelForm):
    """
    The public "Share Your Story" form, shown inside a modal on the
    homepage (not inline on the page). Saves a new testimonial with
    is_active=False / is_approved=False and waits for admin approval.
    """

    class Meta:
        model = Testimonial
        fields = ['donor_name', 'email', 'donor_role', 'message', 'rating', 'photo']
        widgets = {
            'donor_name': forms.TextInput(attrs={
                'class': 'form-control hr-story-input', 'placeholder': 'Enter your full name'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control hr-story-input', 'placeholder': 'Enter your email'
            }),
            'donor_role': forms.Select(attrs={'class': 'form-select hr-story-input'}, choices=Testimonial.ROLE_CHOICES),
            'message': forms.Textarea(attrs={
                'class': 'form-control hr-story-input', 'rows': 5,
                'placeholder': 'Share your story, experience or message...'
            }),
            'rating': forms.Select(attrs={'class': 'form-select'}, choices=[(i, f'{i} Stars') for i in range(1, 6)]),
            'photo': forms.ClearableFileInput(attrs={'class': 'd-none', 'id': 'id_story_photo'}),
        }

    def clean_donor_name(self):
        return validate_name(self.cleaned_data['donor_name'], "Name")

    def clean_message(self):
        message = self.cleaned_data['message'].strip()
        if len(message) < 10:
            raise forms.ValidationError("Please share a bit more -- your story should be at least 10 characters long.")
        return message

    def clean_rating(self):
        rating = self.cleaned_data.get('rating')
        if rating not in (1, 2, 3, 4, 5):
            raise forms.ValidationError("Please select a rating between 1 and 5 stars.")
        return rating

    def clean_photo(self):
        photo = self.cleaned_data.get('photo')
        validate_image_file(photo)
        return photo


class TestimonialForm(forms.ModelForm):
    """Used in the custom admin panel to Add/Edit a donor testimonial."""

    class Meta:
        model = Testimonial
        fields = [
            'donor_name', 'email', 'donor_role', 'message', 'rating', 'photo',
            'story_title', 'category', 'is_active', 'is_approved', 'display_order',
        ]
        widgets = {
            'donor_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'donor_role': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Regular Donor'}),
            'message': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'rating': forms.Select(attrs={'class': 'form-select'}, choices=[(i, f'{i} Stars') for i in range(1, 6)]),
            'photo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'story_title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Optional headline for the story card'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_approved': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'display_order': forms.NumberInput(attrs={'class': 'form-control'}),
        }

    def clean_donor_name(self):
        return validate_name(self.cleaned_data['donor_name'], "Donor name")

    def clean_message(self):
        message = self.cleaned_data['message'].strip()
        if len(message) < 10:
            raise forms.ValidationError("Testimonial message should be at least 10 characters long.")
        return message

    def clean_photo(self):
        photo = self.cleaned_data.get('photo')
        validate_image_file(photo)
        return photo


class FAQForm(forms.ModelForm):
    """Used in the custom admin panel to Add/Edit a FAQ entry."""

    class Meta:
        model = FAQ
        fields = ['question', 'answer', 'is_active', 'display_order']
        widgets = {
            'question': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. How is my donation used?'}),
            'answer': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'display_order': forms.NumberInput(attrs={'class': 'form-control'}),
        }

    def clean_question(self):
        question = self.cleaned_data['question'].strip()
        if len(question) < 5:
            raise forms.ValidationError("Question should be at least 5 characters long.")
        return question

    def clean_answer(self):
        answer = self.cleaned_data['answer'].strip()
        if len(answer) < 10:
            raise forms.ValidationError("Answer should be at least 10 characters long.")
        return answer


class ContactForm(forms.ModelForm):
    """
    The public "Contact Us" form. A plain ModelForm around ContactMessage --
    every submission is saved so staff can review it from the admin panel.
    """

    class Meta:
        model = ContactMessage
        fields = ['name', 'email', 'subject', 'message']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your full name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Your email address'}),
            'subject': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'What is this about?'}),
            'message': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Write your message here...'}),
        }

    def clean_name(self):
        return validate_name(self.cleaned_data['name'], "Name")

    def clean_subject(self):
        subject = self.cleaned_data['subject'].strip()
        if len(subject) < 3:
            raise forms.ValidationError("Subject should be at least 3 characters long.")
        return subject

    def clean_message(self):
        message = self.cleaned_data['message'].strip()
        if len(message) < 10:
            raise forms.ValidationError("Message should be at least 10 characters long.")
        return message


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


class HelpRequestForm(forms.ModelForm):
    """
    Powers the "We're Here To Support You" glass-card form on the homepage.
    Diagnosis/condition is a plain free-typed text field (not a dropdown),
    per the client's request. Document upload is optional but recommended.
    """

    class Meta:
        model = HelpRequest
        fields = [
            'full_name', 'email', 'phone',
            'diagnosis_condition', 'funding_goal', 'treatment_stage', 'document',
        ]
        widgets = {
            'full_name': forms.TextInput(attrs={
                'class': 'form-control hr-glass-input', 'placeholder': 'Your full name'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control hr-glass-input',
                'placeholder': 'Your email address',
                'pattern': r'^[a-zA-Z0-9._%+-]+@gmail\.com$',
                'title': 'Please enter a valid Gmail address ending in @gmail.com'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control hr-glass-input', 'placeholder': 'Phone number (optional)'
            }),
            'diagnosis_condition': forms.TextInput(attrs={
                'class': 'form-control hr-glass-input', 'placeholder': 'e.g. Kidney Cancer'
            }),
            'funding_goal': forms.NumberInput(attrs={
                'class': 'form-control hr-glass-input', 'placeholder': '56000', 'step': '1'
            }),
            'treatment_stage': forms.RadioSelect(attrs={'class': 'd-none'}),
            'document': forms.ClearableFileInput(attrs={
                'class': 'form-control d-none',
                'id': 'id_document',
                'accept': '.pdf',
                'required': 'required'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['document'].required = True

    def clean_full_name(self):
        return validate_name(self.cleaned_data['full_name'], "Name")

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if not email.endswith('@gmail.com'):
            raise forms.ValidationError("Only Gmail addresses (ending with @gmail.com) are accepted for help requests.")
        return email

    def clean_phone(self):
        return validate_phone(self.cleaned_data.get('phone', ''))

    def clean_diagnosis_condition(self):
        condition = self.cleaned_data['diagnosis_condition'].strip()
        if len(condition) < 3:
            raise forms.ValidationError("Please describe the diagnosis or condition (at least 3 characters).")
        return condition

    def clean_funding_goal(self):
        funding_goal = self.cleaned_data['funding_goal']
        if funding_goal <= 0:
            raise forms.ValidationError("Funding goal must be greater than zero.")
        if funding_goal > 10000000:
            raise forms.ValidationError("For funding goals above Rs. 1,00,00,000, please contact us directly.")
        return funding_goal

    def clean_document(self):
        document = self.cleaned_data.get('document')
        if not document:
            raise forms.ValidationError("Supporting document is required.")
        ext = document.name.rsplit('.', 1)[-1].lower() if '.' in document.name else ''
        if ext != 'pdf':
            raise forms.ValidationError("Supporting document must be a PDF file.")
        validate_document_file(document)
        return document


class UpdateForm(forms.ModelForm):
    """Used in the custom admin panel to Add/Edit an 'Updates' card shown on the home page."""

    class Meta:
        model = Update
        fields = ['title', 'image', 'publish_date', 'link_url', 'is_active', 'display_order']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Adam Williams Celebrates Successful Remission'}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'publish_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'link_url': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'https:// (optional)'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'display_order': forms.NumberInput(attrs={'class': 'form-control'}),
        }

    def clean_title(self):
        title = self.cleaned_data['title'].strip()
        if len(title) < 5:
            raise forms.ValidationError("Title should be at least 5 characters long.")
        return title

    def clean_image(self):
        image = self.cleaned_data.get('image')
        validate_image_file(image)
        return image

    def clean_link_url(self):
        link_url = (self.cleaned_data.get('link_url') or '').strip()
        if link_url and not re.match(r'^https?://', link_url, re.IGNORECASE):
            raise forms.ValidationError("Link must be a full URL starting with http:// or https://.")
        return link_url


class DonationAppealForm(forms.ModelForm):
    """
    Used in the admin panel (Website Content -> Donation Appeals) to Add/Edit
    a rich donation appeal -- the "Story Title / Story Content / Story Image"
    form the client designed.
    """

    class Meta:
        model = DonationAppeal
        fields = ['title', 'content', 'image', 'image2', 'image3', 'image4', 'campaign', 'is_published', 'display_order']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'Enter a short and attractive title'
            }),
            'content': forms.Textarea(attrs={
                'class': 'form-control d-none', 'id': 'id_content_raw', 'rows': 6,
            }),
            'image': forms.ClearableFileInput(attrs={'class': 'd-none', 'id': 'id_image'}),
            'image2': forms.ClearableFileInput(attrs={'class': 'd-none', 'id': 'id_image2'}),
            'image3': forms.ClearableFileInput(attrs={'class': 'd-none', 'id': 'id_image3'}),
            'image4': forms.ClearableFileInput(attrs={'class': 'd-none', 'id': 'id_image4'}),
            'campaign': forms.Select(attrs={'class': 'form-select'}),
            'is_published': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'display_order': forms.NumberInput(attrs={'class': 'form-control'}),
        }

    def clean_title(self):
        title = self.cleaned_data['title'].strip()
        if len(title) < 5:
            raise forms.ValidationError("Title should be at least 5 characters long.")
        return title

    def clean_content(self):
        content = self.cleaned_data['content'].strip()
        if len(content) < 20:
            raise forms.ValidationError("Please write a fuller story (at least 20 characters).")
        return content

    def clean_image(self):
        image = self.cleaned_data.get('image')
        validate_image_file(image)
        return image

    def clean_image2(self):
        image = self.cleaned_data.get('image2')
        validate_image_file(image)
        return image

    def clean_image3(self):
        image = self.cleaned_data.get('image3')
        validate_image_file(image)
        return image

    def clean_image4(self):
        image = self.cleaned_data.get('image4')
        validate_image_file(image)
        return image


class AppealSupplyItemForm(forms.ModelForm):
    class Meta:
        model = AppealSupplyItem
        fields = ['item_name', 'quantity', 'unit']
        widgets = {
            'item_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Atta'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 250', 'step': '0.01'}),
            'unit': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean_quantity(self):
        quantity = self.cleaned_data.get('quantity')
        if quantity is not None and quantity <= 0:
            raise forms.ValidationError("Quantity must be greater than zero.")
        return quantity


AppealSupplyItemFormSet = inlineformset_factory(
    DonationAppeal, AppealSupplyItem,
    form=AppealSupplyItemForm,
    extra=5, can_delete=True,
)


class VolunteerMessageForm(forms.Form):
    """
    Used on the admin Volunteers page to compose a message that gets
    emailed to either one volunteer or every volunteer at once.
    """
    subject = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Subject'})
    )
    body = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 6, 'placeholder': 'Write your message to volunteers here...'})
    )

    def clean_subject(self):
        subject = self.cleaned_data['subject'].strip()
        if len(subject) < 3:
            raise forms.ValidationError("Subject should be at least 3 characters long.")
        return subject

    def clean_body(self):
        body = self.cleaned_data['body'].strip()
        if len(body) < 10:
            raise forms.ValidationError("Message should be at least 10 characters long.")
        return body
