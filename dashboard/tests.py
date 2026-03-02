from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import (
    Advertisement,
    Application,
    Candidate,
    Company,
    Consultancy,
    Job,
    LoginHistory,
    Message,
    MessageThread,
)


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

    @override_settings(LOGIN_OTP_REQUIRED=False)
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

    def test_consultancy_can_publish_job_and_candidate_can_see_posted_by_consultancy(self):
        consultancy = Consultancy.objects.create(
            name="TalentBridge",
            email="talentbridge@test.com",
            password=make_password("Secret123"),
            phone="+910000000101",
            account_type="Consultancy",
            kyc_status="Verified",
            account_status="Active",
        )
        candidate = Candidate.objects.create(
            name="Candidate One",
            email="candidate.one@test.com",
            password=make_password("Secret123"),
            account_status="Active",
            account_type="Candidate",
        )

        session = self.client.session
        session["consultancy_id"] = consultancy.id
        session["consultancy_name"] = consultancy.name
        session.save()

        post_response = self.client.post(
            reverse("dashboard:consultancy_jobs"),
            {
                "action": "publish",
                "title": "Python Developer",
                "company": "Acme Tech",
                "category": "IT",
                "location": "Remote",
                "job_type": "Full-time",
                "salary": "8 LPA",
                "experience": "2-4 years",
                "skills": "Python, Django",
                "description": "Build backend services",
                "requirements": "Django REST experience",
                "lifecycle_status": "Active",
            },
        )
        self.assertEqual(post_response.status_code, 302)
        self.assertEqual(post_response.url, reverse("dashboard:consultancy_jobs"))

        job = Job.objects.get(title="Python Developer")
        self.assertEqual(job.recruiter_name, consultancy.name)
        self.assertEqual(job.recruiter_email, consultancy.email)
        self.assertEqual(job.lifecycle_status, "Active")
        self.assertEqual(job.status, "Approved")

        candidate_session = self.client.session
        candidate_session["candidate_id"] = candidate.id
        candidate_session["candidate_name"] = candidate.name
        candidate_session.save()

        candidate_response = self.client.get(reverse("dashboard:candidate_job_search"))
        self.assertEqual(candidate_response.status_code, 200)
        self.assertContains(candidate_response, "Python Developer")
        self.assertContains(candidate_response, "Posted by Consultancy: TalentBridge")

    def test_consultancy_draft_job_not_visible_to_candidate_and_can_be_deleted(self):
        consultancy = Consultancy.objects.create(
            name="DraftConsult",
            email="draftconsult@test.com",
            password=make_password("Secret123"),
            account_type="Consultancy",
            kyc_status="Verified",
            account_status="Active",
        )
        candidate = Candidate.objects.create(
            name="Candidate Two",
            email="candidate.two@test.com",
            password=make_password("Secret123"),
            account_status="Active",
            account_type="Candidate",
        )

        session = self.client.session
        session["consultancy_id"] = consultancy.id
        session["consultancy_name"] = consultancy.name
        session.save()

        create_response = self.client.post(
            reverse("dashboard:consultancy_jobs"),
            {
                "action": "draft",
                "title": "Draft QA Engineer",
                "company": "Beta Corp",
                "category": "IT",
                "location": "Delhi",
                "job_type": "Full-time",
                "lifecycle_status": "Draft",
            },
        )
        self.assertEqual(create_response.status_code, 302)

        job = Job.objects.get(title="Draft QA Engineer")
        self.assertEqual(job.lifecycle_status, "Draft")
        self.assertEqual(job.status, "Pending")

        candidate_session = self.client.session
        candidate_session["candidate_id"] = candidate.id
        candidate_session["candidate_name"] = candidate.name
        candidate_session.save()

        candidate_response = self.client.get(reverse("dashboard:candidate_job_search"))
        self.assertEqual(candidate_response.status_code, 200)
        self.assertNotContains(candidate_response, "Draft QA Engineer")

        consultancy_session = self.client.session
        consultancy_session["consultancy_id"] = consultancy.id
        consultancy_session["consultancy_name"] = consultancy.name
        consultancy_session.save()

        delete_response = self.client.post(
            reverse("dashboard:consultancy_jobs"),
            {"action": "delete", "job_id": job.job_id},
        )
        self.assertEqual(delete_response.status_code, 302)
        self.assertFalse(Job.objects.filter(job_id=job.job_id).exists())

    def test_candidate_sidebar_hides_subscription_and_admin_advertisement_widgets(self):
        candidate = Candidate.objects.create(
            name="Candidate Side",
            email="candidate.side@test.com",
            password=make_password("Secret123"),
            account_status="Active",
            account_type="Candidate",
        )

        session = self.client.session
        session["candidate_id"] = candidate.id
        session["candidate_name"] = candidate.name
        session.save()

        response = self.client.get(reverse("dashboard:candidate_job_search"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Manage Plan")
        self.assertNotContains(response, "Premium Candidate")
        self.assertNotContains(response, "Admin Advertisement")

    def test_consultancy_commission_settings_are_editable_and_reflected_in_job_description(self):
        consultancy = Consultancy.objects.create(
            name="Commissions Lab",
            email="commissions@test.com",
            password=make_password("Secret123"),
            account_type="Consultancy",
            kyc_status="Verified",
            account_status="Active",
        )

        session = self.client.session
        session["consultancy_id"] = consultancy.id
        session["consultancy_name"] = consultancy.name
        session.save()

        update_response = self.client.post(
            reverse("dashboard:consultancy_placements"),
            {
                "action": "update_commission_models",
                "commission_fixed_fee": "30000",
                "commission_percentage": "12",
                "commission_milestone_notes": "Screening 30%, Interview 30%, Joining 40%",
            },
        )
        self.assertEqual(update_response.status_code, 302)

        consultancy.refresh_from_db()
        self.assertEqual(consultancy.commission_fixed_fee, 30000)
        self.assertEqual(consultancy.commission_percentage, 12)
        self.assertEqual(
            consultancy.commission_milestone_notes,
            "Screening 30%, Interview 30%, Joining 40%",
        )

        create_job_response = self.client.post(
            reverse("dashboard:consultancy_jobs"),
            {
                "action": "publish",
                "title": "Commission Linked Job",
                "company": "Hiring Co",
                "category": "IT",
                "location": "Remote",
                "job_type": "Full-time",
                "lifecycle_status": "Active",
                "description": "Core platform engineering role.",
            },
        )
        self.assertEqual(create_job_response.status_code, 302)

        job = Job.objects.get(title="Commission Linked Job")
        self.assertIn("Commission Models (Consultancy):", job.description)
        self.assertIn("Fixed Fee: INR 30,000 per hire", job.description)
        self.assertIn("Percentage Model: 12% of annual CTC", job.description)
        self.assertIn("Milestone Based: Screening 30%, Interview 30%, Joining 40%", job.description)

    def test_company_sidebar_job_management_has_click_navigation_url(self):
        company = Company.objects.create(
            name="Company Nav",
            email="company.nav@test.com",
            password=make_password("Secret123"),
            account_type="Company",
            account_status="Active",
            kyc_status="Verified",
        )
        session = self.client.session
        session["company_id"] = company.id
        session["company_name"] = company.name
        session.save()

        response = self.client.get(reverse("dashboard:company_dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-nav-url="/company/jobs/"')
        self.assertContains(response, 'data-nav-url="/company/communication/bulk-email/"')
        self.assertContains(response, 'data-nav-url="/company/interviews/schedule/"')
        self.assertContains(response, 'data-nav-url="/company/support/create/"')

    def test_company_can_delete_job_and_get_success_message(self):
        company = Company.objects.create(
            name="Delete Job Co",
            email="delete.job@test.com",
            password=make_password("Secret123"),
            account_type="Company",
            account_status="Active",
            kyc_status="Verified",
        )
        job = Job.objects.create(
            job_id="JOBDEL01",
            title="Delete Me",
            company=company.name,
            category="IT",
            location="Remote",
            status="Pending",
        )
        session = self.client.session
        session["company_id"] = company.id
        session["company_name"] = company.name
        session.save()

        response = self.client.post(
            reverse("dashboard:company_jobs"),
            {"action": "delete", "job_id": job.job_id},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Job.objects.filter(job_id=job.job_id).exists())
        self.assertContains(response, "Job deleted successfully")

    def test_candidate_dashboard_renders_admin_advertisement_section(self):
        candidate = Candidate.objects.create(
            name="Ad Candidate",
            email="ad.candidate@test.com",
            password=make_password("Secret123"),
            account_status="Active",
            account_type="Candidate",
        )
        Advertisement.objects.create(
            audience="candidate",
            segment="",
            title="Premium Resume Tips",
            message="Boost your profile visibility with updated resume keywords.",
            is_active=True,
            posted_by="admin",
        )

        session = self.client.session
        session["candidate_id"] = candidate.id
        session["candidate_name"] = candidate.name
        session.save()

        response = self.client.get(reverse("dashboard:candidate_dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Admin Advertisement")
        self.assertContains(response, "Premium Resume Tips")

    def test_communication_pages_show_custom_candidate_picker_with_search(self):
        admin_user = self.user_model.objects.create_user(
            username="admin_comm",
            email="admin.comm@test.com",
            password="StrongPass123!",
            is_staff=True,
        )
        Candidate.objects.create(
            name="Asha Candidate",
            email="asha@example.com",
            password=make_password("Secret123"),
            account_status="Active",
            account_type="Candidate",
        )
        self.client.force_login(admin_user)

        admin_response = self.client.get(reverse("dashboard:communication_whatsapp"))
        self.assertEqual(admin_response.status_code, 200)
        self.assertContains(admin_response, "Custom Candidate Selection")
        self.assertContains(admin_response, "Search candidate name, email, phone")
        self.assertContains(admin_response, "Asha Candidate")

        company = Company.objects.create(
            name="Comm Company",
            email="comm.company@test.com",
            password=make_password("Secret123"),
            account_type="Company",
            account_status="Active",
            kyc_status="Verified",
        )
        company_session = self.client.session
        company_session["company_id"] = company.id
        company_session["company_name"] = company.name
        company_session.save()

        company_response = self.client.get(reverse("dashboard:company_communication_whatsapp"))
        self.assertEqual(company_response.status_code, 200)
        self.assertContains(company_response, "Custom Candidate Selection")
        self.assertContains(company_response, "Search candidate name, email, phone")
        self.assertContains(company_response, "Asha Candidate")

    def test_company_communication_sections_render_successfully(self):
        company = Company.objects.create(
            name="Comm Sections Co",
            email="comm.sections@test.com",
            password=make_password("Secret123"),
            account_type="Company",
            account_status="Active",
            kyc_status="Verified",
        )
        session = self.client.session
        session["company_id"] = company.id
        session["company_name"] = company.name
        session.save()

        section_urls = [
            "dashboard:company_communication_bulk_email",
            "dashboard:company_communication_bulk_sms",
            "dashboard:company_communication_whatsapp",
            "dashboard:company_communication_notifications",
            "dashboard:company_communication_templates",
            "dashboard:company_communication_sent_history",
            "dashboard:company_communication_scheduled",
        ]
        for url_name in section_urls:
            response = self.client.get(reverse(url_name))
            self.assertEqual(response.status_code, 200, msg=f"Failed section: {url_name}")

    def test_login_page_contains_floating_job_animation_script(self):
        response = self.client.get(reverse("dashboard:login"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "skillsFloatContainer")
        self.assertContains(response, "floatingSkills")
        self.assertContains(response, "createFloatingSkill")
        self.assertContains(response, "iconPaths")
        self.assertContains(response, 'id="toggleRegisterLinks"')
        self.assertContains(response, 'id="registerLinks" hidden')

    def test_security_role_permissions_page_renders_subadmin_live_management(self):
        admin_user = self.user_model.objects.create_user(
            username="admin_roles",
            email="admin.roles@test.com",
            password="StrongPass123!",
            is_staff=True,
        )
        self.client.force_login(admin_user)

        response = self.client.get(reverse("dashboard:security_role_permissions"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="subadminForm"')
        self.assertContains(response, 'id="subadminTableBody"')
        self.assertContains(response, "subadmin-management.js")
        self.assertNotContains(response, "Permission Control")
        self.assertNotContains(response, "Assign Role")

    def test_subadmin_api_crud_flow_works_for_admin(self):
        admin_user = self.user_model.objects.create_user(
            username="admin_subcrud",
            email="admin.subcrud@test.com",
            password="StrongPass123!",
            is_staff=True,
        )
        self.client.force_login(admin_user)

        create_response = self.client.post(
            reverse("dashboard:api_subadmin_create"),
            {
                "name": "Riya Mehta",
                "username": "riya_subadmin",
                "email": "riya.subadmin@test.com",
                "phone": "+919999999901",
                "role": "Support Admin",
                "account_status": "Active",
                "password": "SubPass@123",
            },
        )
        self.assertEqual(create_response.status_code, 200)
        create_payload = create_response.json()
        self.assertTrue(create_payload["success"])
        subadmin_id = create_payload["item"]["id"]

        list_response = self.client.get(reverse("dashboard:api_subadmin_list"), {"search": "riya_subadmin"})
        self.assertEqual(list_response.status_code, 200)
        list_payload = list_response.json()
        self.assertTrue(list_payload["success"])
        self.assertGreaterEqual(list_payload["count"], 1)

        detail_response = self.client.get(reverse("dashboard:api_subadmin_detail", args=[subadmin_id]))
        self.assertEqual(detail_response.status_code, 200)
        detail_payload = detail_response.json()
        self.assertTrue(detail_payload["success"])
        self.assertEqual(detail_payload["item"]["username"], "riya_subadmin")

        update_response = self.client.post(
            reverse("dashboard:api_subadmin_update", args=[subadmin_id]),
            {
                "name": "Riya Updated",
                "username": "riya_subadmin_updated",
                "email": "riya.updated@test.com",
                "phone": "+919999999902",
                "role": "Payment Reviewer",
                "account_status": "Inactive",
                "password": "",
            },
        )
        self.assertEqual(update_response.status_code, 200)
        update_payload = update_response.json()
        self.assertTrue(update_payload["success"])
        self.assertEqual(update_payload["item"]["account_status"], "Inactive")
        self.assertEqual(update_payload["item"]["role"], "Payment Reviewer")

        delete_response = self.client.post(reverse("dashboard:api_subadmin_delete", args=[subadmin_id]))
        self.assertEqual(delete_response.status_code, 200)
        delete_payload = delete_response.json()
        self.assertTrue(delete_payload["success"])
        self.assertFalse(self.user_model.objects.filter(id=subadmin_id).exists())

    def test_subadmin_api_is_read_only_for_subadmin_accounts(self):
        admin_user = self.user_model.objects.create_user(
            username="admin_creator",
            email="admin.creator@test.com",
            password="StrongPass123!",
            is_staff=True,
        )
        self.client.force_login(admin_user)

        create_response = self.client.post(
            reverse("dashboard:api_subadmin_create"),
            {
                "name": "Read Only User",
                "username": "readonly_subadmin",
                "email": "readonly.subadmin@test.com",
                "role": "Content Moderator",
                "account_status": "Active",
                "password": "SubPass@123",
            },
        )
        self.assertEqual(create_response.status_code, 200)
        subadmin_id = create_response.json()["item"]["id"]
        subadmin_user = self.user_model.objects.get(id=subadmin_id)

        self.client.force_login(subadmin_user)
        create_as_subadmin = self.client.post(
            reverse("dashboard:api_subadmin_create"),
            {
                "name": "Blocked User",
                "username": "blocked_subadmin",
                "password": "SubPass@123",
            },
        )
        self.assertEqual(create_as_subadmin.status_code, 403)
        self.assertFalse(create_as_subadmin.json()["success"])

        delete_as_subadmin = self.client.post(reverse("dashboard:api_subadmin_delete", args=[admin_user.id]))
        self.assertEqual(delete_as_subadmin.status_code, 403)
        self.assertFalse(delete_as_subadmin.json()["success"])

    def test_candidate_notification_bell_shows_unread_feed_items(self):
        candidate = Candidate.objects.create(
            name="Notify Candidate",
            email="notify.candidate@test.com",
            password=make_password("Secret123"),
            account_status="Active",
            account_type="Candidate",
            email_verified=True,
        )
        company = Company.objects.create(
            name="Notify Company",
            email="notify.company@test.com",
            password=make_password("Secret123"),
            account_status="Active",
            account_type="Company",
            kyc_status="Verified",
            email_verified=True,
        )
        job = Job.objects.create(
            job_id="JOB9001",
            title="Notification Tester",
            company=company.name,
            category="IT",
            location="Remote",
            status="Approved",
        )
        application = Application.objects.create(
            application_id="APP9001",
            candidate_name=candidate.name,
            candidate_email=candidate.email,
            job_title=job.title,
            company=company.name,
            status="Shortlisted",
            job=job,
        )
        thread = MessageThread.objects.create(
            thread_type="candidate_company",
            candidate=candidate,
            company=company,
            application=application,
            job=job,
        )
        Message.objects.create(
            thread=thread,
            sender_role="company",
            sender_name=company.name,
            body="Please check your interview availability.",
            is_read=False,
        )

        session = self.client.session
        session["candidate_id"] = candidate.id
        session["candidate_name"] = candidate.name
        session.save()

        response = self.client.get(reverse("dashboard:candidate_job_search"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "notif-dot")
        self.assertContains(response, "New message from")
        self.assertGreater(response.context["panel_notification_unread_count"], 0)

        self.client.get(reverse("dashboard:candidate_notifications"))
        session = self.client.session
        self.assertIn("candidate_notifications_seen_at", session)
