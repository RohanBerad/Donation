# Helping Hands Donation Platform

A complete, beginner-friendly **Donation & Charity Management Website** built with Django,
Bootstrap 5, HTML, CSS, JavaScript and SQLite.

**Everything on the public website -- the hero text, impact stats, mission section, footer
contact info, testimonials, and of course all campaigns -- is dynamic and fully editable
from your own custom admin panel.** No code changes needed to update site content.

This has been built and tested end-to-end: home page, campaign browsing, the full
donation → payment gateway → success → receipt flow, registration/login, the sidebar
donor dashboard, and every admin panel CRUD screen all run correctly.

---

## 1. Folder Structure

```
charity_project/
│
├── manage.py                        # Django's command-line utility
├── requirements.txt                  # Python packages needed
├── db.sqlite3                        # created automatically after migrate
│
├── charity_project/                  # Project settings folder
│   ├── settings.py                   # Main configuration (apps, database, static/media, etc.)
│   ├── urls.py                       # Root URL routing
│   ├── wsgi.py / asgi.py             # Deployment entry points
│
├── charity_app/                      # Our main app (all the business logic)
│   ├── models.py                     # Campaign, Donation, UserProfile, SiteSettings, Testimonial
│   ├── views.py                      # All page logic (function-based views)
│   ├── urls.py                       # App-level URL routing
│   ├── forms.py                      # DonationForm, RegisterForm, CampaignForm, SiteSettingsForm, etc.
│   ├── admin.py                      # Explains why Django's default admin isn't used (see below)
│   ├── context_processors.py         # Makes site_settings available on every page automatically
│   ├── migrations/                   # Auto-generated database migration files
│   │
│   ├── templates/charity_app/        # Public website pages
│   │   ├── base.html                  # Shared layout (light navbar + footer)
│   │   ├── home.html                  # Hero, stats, mission, featured campaigns, testimonials -- ALL dynamic
│   │   ├── campaign_list.html
│   │   ├── campaign_detail.html       # Goal / Raised / Donors / Days Left stat cards
│   │   ├── donate.html                # Step 1: donor details + payment method, with a LIVE preview sidebar
│   │   ├── payment_gateway.html       # Step 2: UPI QR code / card / net-banking confirmation screen
│   │   ├── success.html               # Step 3: Thank-you page with transaction details
│   │   ├── receipt.html               # Styled, printable receipt (Print/Save-as-PDF button)
│   │   ├── login.html / register.html
│   │   │
│   │   ├── dashboard_base.html        # Shared LIGHT sidebar layout for the donor dashboard
│   │   ├── dashboard_overview.html    # Stats + recent donations
│   │   ├── dashboard_donations.html   # Full donation history
│   │   ├── dashboard_receipts.html    # Download any past receipt
│   │   ├── dashboard_profile.html     # Edit phone number / address
│   │   ├── dashboard_change_password.html
│   │   │
│   │   └── admin/                     # CUSTOM admin panel templates (NOT Django's default admin)
│   │       ├── admin_base.html         # Shared DARK sidebar layout for the admin panel
│   │       ├── admin_login.html
│   │       ├── admin_dashboard.html
│   │       ├── admin_campaign_list.html
│   │       ├── admin_campaign_form.html    # used for both Add and Edit
│   │       ├── admin_campaign_delete.html
│   │       ├── admin_donation_list.html
│   │       ├── admin_donor_list.html
│   │       ├── admin_site_settings.html    # Edit ALL homepage content from here
│   │       ├── admin_testimonial_list.html
│   │       ├── admin_testimonial_form.html
│   │       └── admin_testimonial_delete.html
│   │
│   └── static/
│       ├── css/style.css              # Public site styling (light theme, green accent)
│       ├── css/dashboard_style.css     # Donor dashboard sidebar styling (light)
│       ├── css/admin_style.css         # Admin panel sidebar styling (dark)
│       └── js/script.js                # Small JS enhancements
│
├── templates/                        # (reserved for any project-wide templates)
└── media/
    ├── campaign_images/                # Uploaded campaign images
    ├── site_settings/                  # Uploaded hero/mission images
    └── testimonials/                   # Uploaded testimonial photos
```

---

## 2. What Makes This Site "Dynamic"

Two new models power every editable piece of content on the public site:

### `SiteSettings` (a "singleton" -- there is always exactly one row)
Controls the **Home Page**: NGO name, hero heading + subtitle + image, the 4 impact
statistics (Campaigns / Lives Impacted / Funds Raised / Donors), the Mission section
text, and the footer's about-text + contact address/email/phone.

Edit it at: **`/myadmin/settings/`**

### `Testimonial`
Each row is one donor quote shown in the "What Our Donors Say" section, with a name,
role, message, star rating, an optional photo, an `is_active` toggle (hide without
deleting), and a `display_order` for sorting.

Manage them at: **`/myadmin/testimonials/`**

### Campaigns, Donations, Donors
Already fully dynamic from Day 1 -- managed at `/myadmin/campaigns/`, viewed at
`/myadmin/donations/` and `/myadmin/donors/`. Campaign detail pages now also show
**live Donor Count** and **Days Left**, computed automatically from the database.

> **In short:** every piece of text and every image on the public homepage can be
> changed by a staff member through the admin panel -- no code editing required.

---

## 3. This Project Uses a CUSTOM Admin Panel (NOT Django's default `/admin/`)

Django's built-in admin site (`django.contrib.admin`) is intentionally **removed** from
`INSTALLED_APPS`, and there is **no `/admin/` route**. Instead, a fully custom admin
panel was built from scratch and styled to match the site:

| URL | Purpose |
|---|---|
| `/myadmin/login/` | Separate staff login page (independent from the donor login page) |
| `/myadmin/` | Admin dashboard -- quick stats + recent donations |
| `/myadmin/campaigns/` | List / Add / Edit / Delete campaigns |
| `/myadmin/donations/` | View every donation made on the platform |
| `/myadmin/donors/` | De-duplicated donor list with totals given |
| `/myadmin/testimonials/` | List / Add / Edit / Delete homepage testimonials |
| `/myadmin/settings/` | Edit ALL homepage content (hero, stats, mission, footer) |
| `/myadmin/logout/` | Staff logout |

**Access control:** any account created with `python manage.py createsuperuser`
automatically has `is_staff=True`, which is the only thing that unlocks `/myadmin/...`.
Regular donor accounts (from `/register/`) do **not** have `is_staff=True`, so they are
redirected back to the admin login page if they ever try to visit a `/myadmin/...` URL.
This is enforced by one small decorator in `views.py`:

```python
admin_required = user_passes_test(lambda u: u.is_authenticated and u.is_staff, login_url='admin_login')
```

The admin panel uses a dark sidebar layout (`admin_base.html` + `admin_style.css`) so
staff always know they're in the admin area. A small "Staff Login" link is tucked into
the public site's footer.

---

## 4. The Donation Flow (3 Steps + Receipt)

1. **`/donate/<campaign_id>/`** -- Donor fills in name, email, amount, and picks a
   payment method (UPI / Credit Card / Debit Card / Net Banking). A live sidebar preview
   (powered by a small bit of JavaScript) updates the campaign progress bar and "Your
   Contribution" total as they type -- no page reload needed.
2. **`/payment/`** -- A "Payment Gateway" confirmation screen. If UPI was chosen, a real
   QR code (generated via a free QR API) and a UPI ID are shown; for cards / net banking
   a simple placeholder screen is shown instead. Clicking **"I Have Completed the
   Payment"** finalizes everything:
   - Saves the `Donation` record (auto-generating a fake `transaction_id` like `TXN8F3K92LP`)
   - Increases the campaign's `raised_amount`
3. **`/success/<donation_id>/`** -- Thank-you page with the transaction details and a
   **Download Receipt** button.
4. **`/receipt/<donation_id>/`** -- A nicely styled, printable receipt page (use the
   browser's Print button to save it as a PDF) plus a plain-text download option.

> **Note:** No real payment gateway is integrated -- this is a demo flow only, as
> requested. To go live, you would plug in a real gateway (e.g. Razorpay, Stripe) inside
> the `payment_gateway()` view in `views.py`, right before the `Donation` is saved.

---

## 5. The Donor Dashboard (Sidebar Layout)

Logged-in donors get their own sidebar-based account area, separate from the admin panel:

| URL | Purpose |
|---|---|
| `/dashboard/` | Overview: total donated, donation count, campaigns supported, member since |
| `/dashboard/donations/` | Full donation history table |
| `/dashboard/receipts/` | Download any past receipt |
| `/dashboard/profile/` | Edit phone number / address |
| `/dashboard/change-password/` | Change account password (stays logged in afterwards) |

---

## 6. How To Run This Project

### Step 1 — Install Python packages
```bash
cd charity_project
pip install -r requirements.txt
```

### Step 2 — Create the database tables (migrations)
```bash
python manage.py makemigrations
python manage.py migrate
```

### Step 3 — Create a staff (admin) account
```bash
python manage.py createsuperuser
```
This account will have `is_staff=True`, which is what unlocks the custom admin panel.

### Step 4 — Run the development server
```bash
python manage.py runserver
```

Then open your browser to:
- **Website:** http://127.0.0.1:8000/
- **Custom Admin Panel Login:** http://127.0.0.1:8000/myadmin/login/

### Step 5 — Set up your site content
1. Log in at `/myadmin/login/`
2. Go to **Website Content** and fill in your NGO name, hero text, stats, mission text,
   and contact details
3. Go to **Campaigns → Add New Campaign** to create your first fundraiser
4. Go to **Testimonials → Add New Testimonial** to add a donor quote to the home page

---

## 7. Media & Static File Configuration (already set up in `settings.py`)

```python
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'charity_app' / 'static']

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'
```

Uploaded images (campaign photos, hero/mission images, testimonial photos) are saved
inside `media/` and served automatically while `DEBUG = True`.

---

## 8. Deployment Notes (for when you're ready to go live)

- Set `DEBUG = False` in `settings.py` and add your real domain to `ALLOWED_HOSTS`.
- Replace the SQLite database with PostgreSQL/MySQL for production.
- Serve static files with `python manage.py collectstatic` + a real web server (Nginx) or
  a service like WhiteNoise.
- Store `SECRET_KEY` in an environment variable instead of hard-coding it.
- Use a real payment gateway instead of the fake transaction ID generator.
- Consider adding a proper PDF library (e.g. `xhtml2pdf` or `WeasyPrint`) if you want true
  PDF receipts instead of the browser Print-to-PDF / plain-text options provided.

---

## 9. Quick Command Reference

```bash
# Install dependencies
pip install -r requirements.txt

# Create migration files (only needed after changing models.py)
python manage.py makemigrations

# Apply migrations to the database
python manage.py migrate

# Create a staff/admin account
python manage.py createsuperuser

# Run the site locally
python manage.py runserver
```
