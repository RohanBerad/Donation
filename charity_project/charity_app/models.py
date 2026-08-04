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
import random
import string


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

    # ---------- Mission Section ----------
    mission_title = models.CharField(max_length=100, default="Our Mission")
    mission_text = models.TextField(
        default="We are committed to building a better tomorrow by supporting education, "
                "healthcare, animal welfare, and disaster relief initiatives. Together, we "
                "can bring hope and create lasting change."
    )
    mission_image = models.ImageField(upload_to='site/', blank=True, null=True)

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
    Stores donor testimonials shown in the "What People Say" section
    on the Home Page. Fully manageable (add/edit/delete/reorder) from
    our custom admin panel.
    """

    donor_name = models.CharField(max_length=100)
    donor_role = models.CharField(max_length=100, default="Regular Donor")
    message = models.TextField()
    rating = models.PositiveSmallIntegerField(default=5, help_text="A number from 1 to 5")
    photo = models.ImageField(upload_to='testimonials/', blank=True, null=True)
    is_active = models.BooleanField(default=True, help_text="Only active testimonials are shown on the home page")
    display_order = models.PositiveIntegerField(default=0, help_text="Lower numbers show first")

    class Meta:
        ordering = ['display_order', 'id']

    def __str__(self):
        return f"{self.donor_name} ({self.rating} stars)"

    def star_range(self):
        """Helper used in templates to draw filled stars easily."""
        return range(self.rating)
