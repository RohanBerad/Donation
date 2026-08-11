from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Testimonial


class AdminDashboardTest(TestCase):
    def test_admin_dashboard_exposes_testimonial_statistics(self):
        user = User.objects.create_superuser('admin', 'admin@example.com', 'password123')
        self.client.login(username='admin', password='password123')

        Testimonial.objects.create(
            donor_name='Asha',
            email='asha@example.com',
            donor_role='Regular Donor',
            message='A short but useful story that can be shown publicly.',
            rating=5,
            is_active=True,
            is_approved=True,
            display_order=1,
        )
        Testimonial.objects.create(
            donor_name='Pending Story',
            email='pending@example.com',
            donor_role='Volunteer',
            message='This story is waiting for approval and hidden right now.',
            rating=4,
            is_active=False,
            is_approved=False,
            display_order=2,
        )

        response = self.client.get(reverse('admin_dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_testimonials'], 2)
        self.assertEqual(response.context['active_testimonials'], 1)
        self.assertEqual(response.context['approved_testimonials'], 1)
        self.assertEqual(response.context['pending_testimonials'], 1)
