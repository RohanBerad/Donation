"""
models.py
---------
This file defines the database tables (models) for our Charity website.

We have 3 models:
1. Campaign      -> stores information about each donation campaign
2. Donation      -> stores information about each donation made by a donor
3. UserProfile   -> stores extra information about a registered user (donor)

Django ORM automatically converts these Python classes into database tables.
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import random
import string
from datetime import timedelta


# ==========================================================
# 1. CAMPAIGN MODEL
# ==========================================================
class Campaign(models.Model):
    """
    This model stores every donation campaign created by the admin.
    Example: "Help Build a School", "Save Street Dogs", etc.
    """

    # Choices for category field (dropdown options)
    CATEGORY_CHOICES = [
        ('education', 'Education Fund'),
        ('medical', 'Medical Help'),
        ('animal', 'Animal Rescue'),
        ('disaster', 'Disaster Relief'),
    ]

    # Choices for status field
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('upcoming', 'Upcoming'),
    ]

    campaign_name = models.CharField(max_length=200)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='education')
    description = models.TextField()
    goal_amount = models.DecimalField(max_digits=12, decimal_places=2)
    raised_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    campaign_image = models.ImageField(upload_to='campaign_images/', blank=True, null=True)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')

    # Automatically set when the campaign is created
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        # This controls how the object is displayed in Django Admin
        return self.campaign_name

    def progress_percentage(self):
        """
        Returns how much % of the goal has been raised.
        Used to show the Bootstrap progress bar on campaign detail page.
        """
        if self.goal_amount and self.goal_amount > 0:
            percent = (self.raised_amount / self.goal_amount) * 100
            return round(min(percent, 100), 1)  # cap at 100%
        return 0

    def donor_count(self):
        """Returns how many unique donors have contributed to this campaign."""
        return self.donations.values('email').distinct().count()

    def days_left(self):
        """
        Returns how many days remain until the campaign's end_date.
        Returns 0 if the campaign has already ended.
        """
        from django.utils import timezone
        remaining = (self.end_date - timezone.now().date()).days
        return max(remaining, 0)


# ==========================================================
# 2. DONATION MODEL
# ==========================================================
class Donation(models.Model):
    """
    This model stores every donation made by a donor.
    Each donation is linked (ForeignKey) to one Campaign.
    """

    PAYMENT_CHOICES = [
        ('upi', 'UPI'),
        ('credit_card', 'Credit Card'),
        ('debit_card', 'Debit Card'),
        ('net_banking', 'Net Banking'),
    ]

    # If a logged-in user donates, we save the link to their account (optional)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True)

    # ForeignKey = one campaign can have many donations
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='donations')

    donor_name = models.CharField(max_length=150)
    email = models.EmailField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_CHOICES)
    transaction_id = models.CharField(max_length=50, unique=True, blank=True)
    donation_date = models.DateTimeField(auto_now_add=True)  
    razorpay_payment_id = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    def save(self, *args, **kwargs):
        """
        We override the save() method to auto-generate a fake Transaction ID
        the first time the donation is created (only if it's empty).
        """
        if not self.transaction_id:
            self.transaction_id = self.generate_transaction_id()
        super().save(*args, **kwargs)

    @staticmethod
    def generate_transaction_id():
        """
        Generates a fake transaction ID like: TXN8F3K92LP
        This is only for demo purposes (no real payment gateway is used).
        """
        random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        return f"TXN{random_part}"

    def __str__(self):
        return f"{self.donor_name} - {self.amount} - {self.transaction_id}"


# ==========================================================
# 3. USER PROFILE MODEL
# ==========================================================
class UserProfile(models.Model):
    """
    This model stores extra information about a donor,
    linked one-to-one with Django's built-in User model.
    """

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True)
    phone_number = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)
    profile_created_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Profile of {self.user.username}"


# ==========================================================
# 4. SITE SETTINGS MODEL (Singleton)
# ==========================================================
class SiteSettings(models.Model):
    """
    Stores all the text/images shown on the Home Page (hero section, mission
    section, impact stats, footer contact info) so that NGO staff can edit
    the website's content from our custom admin panel, WITHOUT touching any code.

    This is a "singleton" model -- we only ever want ONE row in this table.
    See the save() method below, which enforces that.
    """

    # ---------- Hero Section ----------
    hero_title_line1 = models.CharField(max_length=100, default="Together We Can")
    hero_title_highlight = models.CharField(max_length=100, default="Create a Better World")
    hero_subtitle = models.TextField(
        default="Your small contribution can make a big difference in someone's life. "
                "Join us in our mission to help the needy."
    )
    hero_image = models.ImageField(upload_to='site/', blank=True, null=True)

    # ---------- Impact Statistics (shown right under the hero) ----------
    stat_campaigns = models.CharField(max_length=20, default="500+", help_text="e.g. 500+")
    stat_lives_impacted = models.CharField(max_length=20, default="50,000+")
    stat_funds_raised = models.CharField(max_length=20, default="Rs. 2.5 Cr+")
    stat_donors = models.CharField(max_length=20, default="10,000+")
    stat_partners_volunteers = models.CharField(max_length=20, default="250+")

    # ---------- Mission Section ----------
    mission_title = models.CharField(max_length=100, default="Our Mission")
    mission_text = models.TextField(
        default="We are committed to building a better tomorrow by supporting education, "
                "healthcare, animal welfare, and disaster relief initiatives. Together, we "
                "can bring hope and create lasting change."
    )
    mission_image = models.ImageField(upload_to='site/', blank=True, null=True)

    # ---------- About Page ----------
    about_heading = models.CharField(max_length=100, default="We stand with")
    about_heading_highlight = models.CharField(max_length=100, default="people in need.")
    about_text = models.TextField(
        default="Founded with a simple belief -- that everyone deserves a fair chance at "
                "a better life -- we have spent years working directly with communities on "
                "education, healthcare, animal welfare, and disaster relief. Every rupee "
                "donated here is tracked, and every campaign is reviewed by our team before "
                "it goes live."
    )
    about_image = models.ImageField(upload_to='site/', blank=True, null=True)
    about_video_url = models.URLField(
        blank=True, default="",
        help_text="Optional YouTube/Vimeo embed link for the 'Watch Our Story' button"
    )
    about_vision_text = models.TextField(
        default="To create a future where every person has access to basic needs, education, "
                "and opportunity -- no matter where they live. We envision a just and "
                "compassionate world where communities thrive with dignity."
    )
    about_story_image = models.ImageField(upload_to='site/', blank=True, null=True)
    about_story_quote = models.CharField(
        max_length=150, default="You Can Be the Reason Someone Smiles Today.",
        help_text="Short quote shown over the 'Our Story' photo"
    )
    registration_number = models.CharField(
        max_length=100, blank=True, default="",
        help_text="e.g. NGO Registration / 80G Number, shown on the About page"
    )

    # ---------- Team Section (About Page) ----------
    team_section_title = models.CharField(max_length=100, default="Meet the Team")
    team_section_subtitle = models.TextField(default="A dedicated mix of staff and volunteers driven by compassion and accountability.")
    team_member_1_name = models.CharField(max_length=100, default="Founder")
    team_member_1_role = models.CharField(max_length=100, default="Vision & Strategy")
    team_member_1_photo = models.ImageField(upload_to='team/', blank=True, null=True)
    team_member_2_name = models.CharField(max_length=100, default="Program Lead")
    team_member_2_role = models.CharField(max_length=100, default="Program Design & Impact")
    team_member_2_photo = models.ImageField(upload_to='team/', blank=True, null=True)
    team_member_3_name = models.CharField(max_length=100, default="Operations")
    team_member_3_role = models.CharField(max_length=100, default="Administration & Finance")
    team_member_3_photo = models.ImageField(upload_to='team/', blank=True, null=True)
    team_member_4_name = models.CharField(max_length=100, default="Volunteers")
    team_member_4_role = models.CharField(max_length=100, default="Community Champions")
    team_member_4_photo = models.ImageField(upload_to='team/', blank=True, null=True)

    # ---------- Footer / Contact Info ----------
    ngo_name = models.CharField(max_length=100, default="Helping Hands")
    footer_about_text = models.TextField(
        default="Together we can create a better world for everyone."
    )
    contact_address = models.CharField(max_length=200, default="123 Hope Street, Mumbai, India")
    contact_email = models.EmailField(default="contact@helpinghands.org")
    contact_phone = models.CharField(max_length=20, default="+91 98765 43210")

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "Website Content Settings"

    def save(self, *args, **kwargs):
        # Force this model to always use id=1, so there is only ever ONE row.
        self.pk = 1
        super().save(*args, **kwargs)

    @property
    def team_members(self):
        members = []
        for i in range(1, 5):
            members.append({
                'name': getattr(self, f'team_member_{i}_name'),
                'role': getattr(self, f'team_member_{i}_role'),
                'photo': getattr(self, f'team_member_{i}_photo'),
            })
        return members

    @classmethod
    def load(cls):
        """
        Convenient helper used in views.py to fetch the single settings row,
        creating it with default values the very first time it's needed.
        """
        obj, created = cls.objects.get_or_create(pk=1)
        return obj


# ==========================================================
# 5. TESTIMONIAL MODEL
# ==========================================================
class Testimonial(models.Model):
    """
    Stores donor testimonials shown in the "Stories of Impact" section
    on the Home Page. Public submissions are saved here first and then
    staff review them in the admin panel and approve them before they are
    allowed to appear on the public website.
    """

    ROLE_CHOICES = [
        ('Regular Donor', 'Regular Donor'),
        ('Volunteer', 'Volunteer'),
        ('Education Beneficiary', 'Education Beneficiary'),
        ('Medical Help Beneficiary', 'Medical Help Beneficiary'),
        ('Food & Shelter Beneficiary', 'Food & Shelter Beneficiary'),
        ('Animal Rescue Beneficiary', 'Animal Rescue Beneficiary'),
        ('Other', 'Other'),
    ]

    CATEGORY_CHOICES = [
        ('general', 'General'),
        ('education', 'Education'),
        ('medical', 'Medical Help'),
        ('animal', 'Animal Rescue'),
        ('disaster', 'Disaster Relief'),
        ('food_shelter', 'Food & Shelter'),
    ]

    donor_name = models.CharField(max_length=100)
    email = models.EmailField(blank=True, help_text="Not shown publicly -- used by staff to follow up if needed")
    donor_role = models.CharField(max_length=100, default="Regular Donor")
    message = models.TextField()
    rating = models.PositiveSmallIntegerField(default=5, help_text="A number from 1 to 5")
    photo = models.ImageField(upload_to='testimonials/', blank=True, null=True)

    story_title = models.CharField(
        max_length=150, blank=True,
        help_text="Optional headline shown on the story card. Staff can add this while approving a submission."
    )
    category = models.CharField(
        max_length=20, choices=CATEGORY_CHOICES, default='general', blank=True,
        help_text="Controls the colored badge shown on the story card."
    )

    is_active = models.BooleanField(default=False, help_text="Only active testimonials are shown on the home page")
    is_approved = models.BooleanField(default=False, help_text="Admin must approve a public testimonial before it can be published")
    display_order = models.PositiveIntegerField(default=0, help_text="Lower numbers show first")
    submitted_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    class Meta:
        ordering = ['display_order', 'id']

    def __str__(self):
        return f"{self.donor_name} ({self.rating} stars)"

    def star_range(self):
        """Helper used in templates to draw filled stars easily."""
        return range(self.rating)

    def display_title(self):
        """Falls back to the donor's role if staff haven't set a custom headline."""
        return self.story_title or self.donor_role

    def excerpt(self, length=140):
        """Short preview of the story used on the grid cards."""
        text = self.message.strip()
        return text if len(text) <= length else text[:length].rsplit(' ', 1)[0] + '...'


# ==========================================================
# 6. PASSWORD RESET OTP MODEL
# ==========================================================
class PasswordResetOTP(models.Model):
    """
    Stores OTP records for the forgot password flow.
    Each record links an email address to a 6-digit OTP code.
    """

    email = models.EmailField()
    otp_code = models.CharField(max_length=6)
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        """OTP expires after 10 minutes."""
        return timezone.now() > self.created_at + timedelta(minutes=10)

    def __str__(self):
        return f"OTP for {self.email} - {'Used' if self.is_used else 'Active'}"


# ==========================================================
# 7. FAQ MODEL
# ==========================================================
class FAQ(models.Model):
    """
    Stores one Frequently Asked Question + Answer pair, shown on the
    public FAQ page. Fully manageable (add/edit/delete/reorder) from
    our custom admin panel, just like Testimonials.
    """

    question = models.CharField(max_length=255)
    answer = models.TextField()
    is_active = models.BooleanField(default=True, help_text="Only active FAQs are shown on the FAQ page")
    display_order = models.PositiveIntegerField(default=0, help_text="Lower numbers show first")

    class Meta:
        ordering = ['display_order', 'id']
        verbose_name = "FAQ"
        verbose_name_plural = "FAQs"

    def __str__(self):
        return self.question


# ==========================================================
# 8. CONTACT MESSAGE MODEL
# ==========================================================
class ContactMessage(models.Model):
    """
    Stores every message submitted through the public Contact Us page,
    so NGO staff can read and follow up on them from the admin panel.
    """

    name = models.CharField(max_length=150)
    email = models.EmailField()
    subject = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-submitted_at']

    def __str__(self):
        return f"{self.name} - {self.subject}"


# ==========================================================
# 9. HELP REQUEST MODEL
# ==========================================================
def help_request_document_path(instance, filename):
    """Keeps uploaded medical/proof documents organised by submission date."""
    from django.utils import timezone
    ts = timezone.now().strftime('%Y%m%d%H%M%S')
    return f"help_requests/{ts}_{filename}"


class HelpRequest(models.Model):
    """
    Stores every submission from the public "We're Here To Support You"
    form on the homepage (Get Help section). Patients/families fill in
    their diagnosis, funding goal, treatment stage, and can attach a
    supporting document (medical report, bill, ID, etc). NGO staff review
    these from the admin panel and follow up / turn approved ones into a
    Campaign.
    """

    STAGE_CHOICES = [
        ('pre_op', 'Pre-op'),
        ('active', 'Active'),
        ('recovery', 'Recovery'),
    ]

    STATUS_CHOICES = [
        ('new', 'New'),
        ('reviewing', 'Reviewing'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    full_name = models.CharField(max_length=150)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)

    diagnosis_condition = models.CharField(
        max_length=200,
        help_text="Typed in freely by the requester, e.g. 'Kidney Cancer'"
    )
    funding_goal = models.DecimalField(max_digits=12, decimal_places=2)
    treatment_stage = models.CharField(max_length=10, choices=STAGE_CHOICES, default='active')

    document = models.FileField(
        upload_to=help_request_document_path,
        blank=True,
        null=True,
        help_text="Supporting document -- medical report, bill, prescription, etc."
    )

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='new')
    admin_notes = models.TextField(blank=True, help_text="Internal notes, not shown to the requester")

    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-submitted_at']

    def __str__(self):
        return f"{self.full_name} - {self.diagnosis_condition}"
