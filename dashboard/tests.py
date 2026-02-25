from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.test import TestCase
from django.urls import reverse

from .models import Candidate, Consultancy, LoginHistory


class DashboardViewTests(TestCase):
    def setUp(self):
        self.user_model = get_user_model()

    def test_security_login_history_view_renders_and_counts_without_slice_error(self):
        admin_user = self.user_model.objects.create_user(
            username="admin_test",
            email="admin@test.com",
            password="StrongPass123!",
            is_staff=True,
        )
        self.client.force_login(admin_user)

        for index in range(130):
            LoginHistory.objects.create(
                account_type="candidate",
                username_or_email=f"user{index}@example.com",
                is_success=index % 2 == 0,
                ip_address="127.0.0.1",
            )

        response = self.client.get(reverse("dashboard:security_login_history"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_logins"], 130)
        self.assertEqual(response.context["success_count"], 65)
        self.assertEqual(response.context["failed_count"], 65)
        self.assertEqual(len(response.context["login_entries"]), 100)

    def test_candidate_login_sets_welcome_target_to_job_search(self):
        Candidate.objects.create(
            name="can-login",
            email="can-login@example.com",
            password=make_password("Secret123"),
            email_verified=True,
            account_status="Active",
            account_type="Candidate",
        )

        response = self.client.post(
            reverse("dashboard:login"),
            {"username": "can-login", "password": "Secret123"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("dashboard:welcome"))
        self.assertEqual(
            response.cookies["welcome_next"].value,
            "dashboard:candidate_job_search",
        )

    def test_consultancy_metrics_api_returns_payload(self):
        consultancy = Consultancy.objects.create(
            name="consult-test",
            email="consult@test.com",
            password=make_password("Secret123"),
            account_type="Consultancy",
            kyc_status="Verified",
            account_status="Active",
        )

        session = self.client.session
        session["consultancy_id"] = consultancy.id
        session["consultancy_name"] = consultancy.name
        session.save()

        response = self.client.get(reverse("dashboard:consultancy_api_metrics"))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("metrics", payload)
        self.assertIn("pipeline", payload)
        self.assertIn("assigned_jobs", payload["metrics"])
        self.assertIsInstance(payload["pipeline"], list)
