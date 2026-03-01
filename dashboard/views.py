import calendar
import csv
import json
import mimetypes
import os
import random
import re
import secrets
import zipfile
from datetime import date, timedelta
from itertools import zip_longest
from pathlib import Path
from functools import wraps
from io import BytesIO

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import check_password, identify_hasher, make_password
from django.core.files.base import ContentFile
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.db import IntegrityError, OperationalError, close_old_connections
from django.db.models import Q, Count, Sum, F
from django.http import FileResponse, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_time
from django.utils.html import escape
from django.views.decorators.http import require_http_methods

from .notifications import build_panel_notifications, mark_panel_notifications_seen
from .models import (
    AD_IMAGE_EXTENSIONS,
    AD_VIDEO_EXTENSIONS,
    APPLICATION_STATUS_CHOICES,
    CONSULTANCY_JOB_LIFECYCLE_CHOICES,
    PLACEMENT_STATUS_CHOICES,
    Advertisement,
    AdminProfile,
    Application,
    AssignedJob,
    Candidate,
    CandidateCertification,
    CandidateEducation,
    CandidateExperience,
    CandidateProject,
    CandidateResume,
    CandidateSkill,
    Company,
    CompanyKycDocument,
    Consultancy,
    ConsultancyKycDocument,
    EmailVerificationToken,
    Interview,
    LoginHistory,
    PasswordResetToken,
    Message,
    MessageThread,
    Job,
    Subscription,
    SubscriptionPlan,
    SubscriptionLog,
)
from .otp.sms import send_otp_sms

PIPELINE_STATUSES = [
    "Applied",
    "Shortlisted",
    "Interview",
    "Selected",
    "Rejected",
    "On Hold",
    "Archived",
]
INTERVIEW_STATUSES = ["Interview", "Interview Scheduled"]
SELECTED_STATUSES = ["Selected", "Offer Issued"]
FREE_EMAIL_DOMAINS = {
    "gmail.com",
    "yahoo.com",
    "outlook.com",
    "hotmail.com",
    "live.com",
    "aol.com",
    "icloud.com",
    "mail.com",
    "proton.me",
    "protonmail.com",
}
CAPTCHA_SESSION_PREFIX = "registration_captcha_"
OTP_SESSION_PREFIX = "registration_otp_"
LOGIN_OTP_SESSION_KEY = "login_otp_payload"
PASSWORD_RESET_OTP_SESSION_KEY = "password_reset_otp_payload"
OTP_TTL_SECONDS = 10 * 60
MIN_PROFILE_COMPLETION_TO_APPLY = 60
PASSWORD_RESET_TTL_MINUTES = 30
CONSULTANCY_JOB_LIFECYCLE_VALUES = {choice[0] for choice in CONSULTANCY_JOB_LIFECYCLE_CHOICES}
CONSULTANCY_JOB_LIFECYCLE_TO_STATUS = {
    "Draft": "Pending",
    "Active": "Approved",
    "Paused": "Pending",
    "Closed": "Rejected",
    "Expired": "Rejected",
    "Archived": "Reported",
}
STATUS_TO_CONSULTANCY_JOB_LIFECYCLE = {
    "Approved": "Active",
    "Pending": "Draft",
    "Rejected": "Closed",
    "Reported": "Archived",
}
COMMON_SKILL_KEYWORDS = [
    "python",
    "java",
    "javascript",
    "typescript",
    "react",
    "angular",
    "node",
    "django",
    "flask",
    "sql",
    "mysql",
    "postgresql",
    "excel",
    "power bi",
    "tableau",
    "aws",
    "azure",
    "docker",
    "kubernetes",
    "salesforce",
]

REGISTER_ROLE_GROUPS = [
    {
        "title": "IT Jobs",
        "roles": [
            "Software Engineer",
            "Web Developer",
            "Mobile App Developer",
            "Python Developer",
            "Java Developer",
            "PHP Developer",
            "React / Angular Developer",
            "Data Analyst",
            "Data Scientist",
            "Cybersecurity Analyst",
            "Cloud Engineer",
            "DevOps Engineer",
            "Network Engineer",
            "UI / UX Designer",
            "QA Engineer",
            "IT Support Engineer",
            "System Administrator",
            "Project Manager",
            "Product Manager",
        ],
    },
    {
        "title": "Non-IT Jobs",
        "roles": [
            "Accountant",
            "Relationship Manager",
            "Production Supervisor",
            "Nurse",
            "Lab Technician",
            "Sales Executive",
            "Digital Marketing Executive",
            "Store Manager",
            "Warehouse Executive",
            "Supply Chain Manager",
            "Civil Engineer",
            "Site Supervisor",
            "Teacher",
            "Receptionist",
            "Chef",
            "Automobile Engineer",
            "Government Jobs",
            "Driver",
            "Security Guard",
            "Housekeeping",
        ],
    },
    {
        "title": "Work Type",
        "roles": [
            "Full Time",
            "Part Time",
            "Work From Home",
            "Freelance",
            "Internship",
            "Contract",
        ],
    },
]


def _resolve_subscription_segment(plan_type, payment_status, plan_expiry):
    plan_type = (plan_type or "").strip()
    payment_status = (payment_status or "").strip()
    if payment_status and payment_status != "Paid":
        return "non_subscribed"
    if not plan_type or plan_type.lower() == "free":
        return "non_subscribed"
    if plan_expiry and plan_expiry < timezone.localdate():
        return "non_subscribed"
    return "subscribed"


def _resolve_subscription_segment_for_account(account_type, email, plan_type=None, payment_status=None, plan_expiry=None):
    subscription = None
    if account_type and email:
        subscription = (
            Subscription.objects.filter(
                account_type__iexact=account_type,
                contact__iexact=email,
            )
            .order_by("-expiry_date", "-updated_at")
            .first()
        )
    if subscription:
        if subscription.payment_status != "Paid":
            return "non_subscribed"
        if (subscription.plan or "").strip().lower() == "free":
            return "non_subscribed"
        if subscription.expiry_date and subscription.expiry_date < timezone.localdate():
            return "non_subscribed"
        return "subscribed"
    return _resolve_subscription_segment(plan_type, payment_status, plan_expiry)


def _active_advertisement_for(audience, segment=""):
    ads = Advertisement.objects.filter(
        audience=audience,
        is_active=True,
    ).order_by("-created_at")
    scoped = ads.filter(Q(segment=segment) | Q(segment="") | Q(segment__isnull=True)).first()
    if scoped:
        return scoped
    generic = ads.filter(Q(segment="") | Q(segment__isnull=True)).first()
    return generic or ads.first()


def _normalize_consultancy_job_lifecycle(status):
    candidate = (status or "").strip().title()
    if candidate in CONSULTANCY_JOB_LIFECYCLE_VALUES:
        return candidate
    return "Draft"


def _legacy_status_for_lifecycle(lifecycle_status):
    lifecycle = _normalize_consultancy_job_lifecycle(lifecycle_status)
    return CONSULTANCY_JOB_LIFECYCLE_TO_STATUS.get(lifecycle, "Pending")


def _consultancy_job_status(job):
    if not job:
        return "Draft"
    lifecycle = (getattr(job, "lifecycle_status", "") or "").strip()
    if lifecycle in CONSULTANCY_JOB_LIFECYCLE_VALUES:
        return lifecycle
    return STATUS_TO_CONSULTANCY_JOB_LIFECYCLE.get((job.status or "").strip(), "Draft")


def _consultancy_posted_jobs_queryset(consultancy):
    if not consultancy:
        return Job.objects.none()
    return Job.objects.filter(
        Q(recruiter_email__iexact=consultancy.email) | Q(recruiter_name__iexact=consultancy.name),
    )


def _communication_candidate_options(limit=500):
    options = []
    qs = Candidate.objects.order_by("name", "id").values("id", "name", "email", "phone")[:limit]
    for row in qs:
        name = (row.get("name") or "").strip() or "Candidate"
        email = (row.get("email") or "").strip()
        phone = (row.get("phone") or "").strip()
        search_text = " ".join([name, email, phone]).strip().lower()
        options.append(
            {
                "id": row.get("id"),
                "name": name,
                "email": email,
                "phone": phone,
                "search_text": search_text,
            }
        )
    return options


def _consultancy_application_status(status):
    status_map = {
        "Applied": "Submitted",
        "On Hold": "Under Review",
        "Shortlisted": "Shortlisted",
        "Interview": "Interview",
        "Interview Scheduled": "Interview",
        "Selected": "Selected",
        "Offer Issued": "Placed",
        "Rejected": "Rejected",
        "Archived": "Archived",
    }
    return status_map.get(status, status or "Submitted")


def _sync_placement_status(application_status, current_status=None):
    mapping = {
        "Selected": "Approved",
        "Offer Issued": "Pending Approval",
        "Rejected": "Cancelled",
    }
    return mapping.get(application_status, current_status)


def _parse_amount(value):
    if value is None:
        return 0
    numbers = re.findall(r"\d+", str(value))
    if not numbers:
        return 0
    return int("".join(numbers))


def _calculate_commission(assignment, application):
    if not assignment:
        return None
    if assignment.commission_type == "Percentage":
        base_amount = _parse_amount(application.offer_package or application.expected_salary)
        percent = _parse_amount(assignment.commission_value)
        if base_amount and percent:
            return int(base_amount * percent / 100)
    if assignment.commission_type == "Fixed":
        fixed_amount = _parse_amount(assignment.commission_value)
        if fixed_amount:
            return fixed_amount
    return None


def _consultancy_commission_defaults(consultancy):
    fixed_fee = getattr(consultancy, "commission_fixed_fee", 25000) or 25000
    percentage = getattr(consultancy, "commission_percentage", 10) or 10
    milestone_notes = (
        getattr(consultancy, "commission_milestone_notes", "") or "Stage-wise commission release"
    ).strip()
    return {
        "fixed_fee": fixed_fee,
        "percentage": percentage,
        "milestone_notes": milestone_notes,
    }


def _build_consultancy_commission_block(consultancy):
    defaults = _consultancy_commission_defaults(consultancy)
    return "\n".join(
        [
            "Commission Models (Consultancy):",
            f"- Fixed Fee: INR {defaults['fixed_fee']:,} per hire",
            f"- Percentage Model: {defaults['percentage']}% of annual CTC",
            f"- Milestone Based: {defaults['milestone_notes']}",
        ]
    )


def _inject_consultancy_commission_in_description(description, consultancy):
    cleaned = (description or "").strip()
    cleaned = re.sub(
        r"\n*Commission Models \(Consultancy\):[\s\S]*$",
        "",
        cleaned,
        flags=re.IGNORECASE,
    ).strip()
    commission_block = _build_consultancy_commission_block(consultancy)
    if cleaned:
        return f"{cleaned}\n\n{commission_block}"
    return commission_block


def _get_company_for_job(job):
    if not job:
        return None
    return Company.objects.filter(name__iexact=job.company).first()


def _get_or_create_thread(thread_type, application, job=None, candidate=None, company=None, consultancy=None):
    if not application:
        return None
    thread, created = MessageThread.objects.get_or_create(
        thread_type=thread_type,
        application=application,
        defaults={
            "job": job,
            "candidate": candidate,
            "company": company,
            "consultancy": consultancy,
        },
    )
    if not created:
        updated_fields = []
        if job and thread.job_id != job.id:
            thread.job = job
            updated_fields.append("job")
        if candidate and thread.candidate_id != candidate.id:
            thread.candidate = candidate
            updated_fields.append("candidate")
        if company and thread.company_id != company.id:
            thread.company = company
            updated_fields.append("company")
        if consultancy and thread.consultancy_id != consultancy.id:
            thread.consultancy = consultancy
            updated_fields.append("consultancy")
        if updated_fields:
            thread.save(update_fields=updated_fields)
    return thread


def _ensure_message_threads(application, job=None, candidate=None, company=None, consultancy=None):
    threads = []
    if candidate and company:
        thread = _get_or_create_thread(
            "candidate_company",
            application,
            job=job,
            candidate=candidate,
            company=company,
            consultancy=consultancy,
        )
        if thread:
            threads.append(thread)
    if candidate and consultancy:
        thread = _get_or_create_thread(
            "candidate_consultancy",
            application,
            job=job,
            candidate=candidate,
            company=company,
            consultancy=consultancy,
        )
        if thread:
            threads.append(thread)
    if company and consultancy:
        thread = _get_or_create_thread(
            "company_consultancy",
            application,
            job=job,
            candidate=candidate,
            company=company,
            consultancy=consultancy,
        )
        if thread:
            threads.append(thread)
    return threads


def _thread_partner_info(thread, role):
    if role == "candidate":
        if thread.thread_type == "candidate_company":
            partner = thread.company
            return (partner.name if partner else "Company", "Company")
        partner = thread.consultancy
        return (partner.name if partner else "Consultancy", "Consultancy")
    if role == "company":
        if thread.thread_type == "candidate_company":
            partner = thread.candidate
            return (partner.name if partner else "Candidate", "Candidate")
        partner = thread.consultancy
        return (partner.name if partner else "Consultancy", "Consultancy")
    if role == "consultancy":
        if thread.thread_type == "candidate_consultancy":
            partner = thread.candidate
            return (partner.name if partner else "Candidate", "Candidate")
        partner = thread.company
        return (partner.name if partner else "Company", "Company")
    candidate_name = thread.candidate.name if thread.candidate else "Candidate"
    company_name = thread.company.name if thread.company else "Company"
    consultancy_name = thread.consultancy.name if thread.consultancy else "Consultancy"
    if thread.thread_type == "candidate_company":
        return (f"{candidate_name} <-> {company_name}", "Candidate <-> Company")
    if thread.thread_type == "candidate_consultancy":
        return (f"{candidate_name} <-> {consultancy_name}", "Candidate <-> Consultancy")
    return (f"{company_name} <-> {consultancy_name}", "Company <-> Consultancy")


def _build_thread_cards(threads, role):
    cards = []
    for thread in threads:
        partner_name, partner_role = _thread_partner_info(thread, role)
        last_message = thread.messages.order_by("-created_at").first()
        preview = ""
        if last_message:
            preview = last_message.body or "Attachment"
        else:
            preview = "No messages yet."
        unread_count = 0
        if role in {"candidate", "company", "consultancy"}:
            unread_count = (
                Message.objects.filter(thread=thread, is_read=False)
                .exclude(sender_role=role)
                .count()
            )
        cards.append(
            {
                "thread": thread,
                "partner_name": partner_name,
                "partner_role": partner_role,
                "job_title": thread.job.title if thread.job else (thread.application.job_title if thread.application else "Job"),
                "application_id": thread.application.application_id if thread.application else "",
                "last_message": preview,
                "last_message_at": last_message.created_at if last_message else thread.created_at,
                "unread_count": unread_count,
            }
        )
    return cards


def welcome_view(request):
    """Display a 3-second welcome animation page after login"""
    # Check what type of user is logging in
    user_type = (request.GET.get("type") or request.COOKIES.get("welcome_type") or "candidate").strip().lower()
    next_url = request.GET.get("next") or request.COOKIES.get("welcome_next", "")

    # If no next URL is provided, determine it based on user type
    if not next_url:
        if user_type == "company":
            next_url = "dashboard:company_dashboard"
        elif user_type == "consultancy":
            next_url = "dashboard:consultancy_dashboard"
        elif user_type == "admin":
            next_url = "dashboard:dashboard"
        else:  # candidate
            next_url = "dashboard:candidate_job_search"

    next_url = reverse(next_url) if isinstance(next_url, str) and ":" in next_url else next_url

    display_name = ""
    if request.user.is_authenticated:
        display_name = (
            request.user.get_full_name().strip() or request.user.get_username()
        )

    if not display_name:
        session_key_by_role = {
            "company": "company_name",
            "consultancy": "consultancy_name",
            "candidate": "candidate_name",
        }
        display_name = (request.session.get(session_key_by_role.get(user_type, ""), "") or "").strip()

    if not display_name:
        role_fallback = {
            "company": "Company",
            "consultancy": "Consultancy",
            "candidate": "Candidate",
            "admin": "Admin",
        }
        display_name = role_fallback.get(user_type, "User")

    context = {
        "user_type": user_type,
        "next": next_url,
        "display_name": display_name,
    }
    return render(request, "dashboard/welcome.html", context)


def _is_hashed_password(value):
    if not value:
        return False
    try:
        identify_hasher(value)
        return True
    except ValueError:
        return False


def _hash_password(value):
    if not value:
        return value
    return value if _is_hashed_password(value) else make_password(value)


def _check_raw_password(raw_password, stored_password):
    if not raw_password or not stored_password:
        return False
    if _is_hashed_password(stored_password):
        return check_password(raw_password, stored_password)
    return stored_password == raw_password


def _parse_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _password_strength_errors(password):
    errors = []
    value = password or ""
    if len(value) < 8:
        errors.append("Password must be at least 8 characters long.")
    if not re.search(r"[A-Z]", value):
        errors.append("Password must include at least one uppercase letter.")
    if not re.search(r"[a-z]", value):
        errors.append("Password must include at least one lowercase letter.")
    if not re.search(r"[0-9]", value):
        errors.append("Password must include at least one number.")
    if not re.search(r"[^A-Za-z0-9]", value):
        errors.append("Password must include at least one special character.")
    return errors


def _is_official_company_email(email):
    email = (email or "").strip().lower()
    if "@" not in email:
        return False
    domain = email.split("@", 1)[1]
    return domain not in FREE_EMAIL_DOMAINS


def _set_registration_captcha(request, flow_key):
    left = random.randint(2, 9)
    right = random.randint(2, 9)
    session_key = f"{CAPTCHA_SESSION_PREFIX}{flow_key}"
    request.session[session_key] = {
        "question": f"{left} + {right} = ?",
        "answer": str(left + right),
        "created_at": int(timezone.now().timestamp()),
    }
    return request.session[session_key]["question"]


def _get_registration_captcha_question(request, flow_key):
    session_key = f"{CAPTCHA_SESSION_PREFIX}{flow_key}"
    payload = request.session.get(session_key) or {}
    question = payload.get("question")
    if question:
        return question
    return _set_registration_captcha(request, flow_key)


def _validate_registration_captcha(request, flow_key, answer):
    session_key = f"{CAPTCHA_SESSION_PREFIX}{flow_key}"
    payload = request.session.get(session_key) or {}
    expected = (payload.get("answer") or "").strip()
    return bool(expected and expected == (answer or "").strip())


def _mask_phone_number(phone):
    digits = re.sub(r"\D", "", phone or "")
    if len(digits) < 4:
        return "****"
    return f"{'*' * max(len(digits) - 4, 0)}{digits[-4:]}"


def _issue_session_otp(request, session_key, phone, extra_payload=None):
    clean_phone = (phone or "").strip()
    otp_value = f"{random.randint(100000, 999999)}"
    is_sent, error_message = send_otp_sms(clean_phone, otp_value)
    if not is_sent:
        request.session.pop(session_key, None)
        return "", error_message or "Unable to send OTP right now. Please try again."

    payload = {
        "phone": clean_phone,
        "otp": otp_value,
        "created_at": int(timezone.now().timestamp()),
    }
    if extra_payload:
        payload.update(extra_payload)
    request.session[session_key] = payload
    return otp_value, ""


def _validate_session_otp(request, session_key, phone, otp_value):
    payload = request.session.get(session_key) or {}
    expected_phone = (payload.get("phone") or "").strip()
    expected_otp = (payload.get("otp") or "").strip()
    created_at = int(payload.get("created_at") or 0)
    now_ts = int(timezone.now().timestamp())
    if not expected_phone or not expected_otp:
        return False
    if expected_phone != (phone or "").strip():
        return False
    if now_ts - created_at > OTP_TTL_SECONDS:
        return False
    return expected_otp == (otp_value or "").strip()


def _clear_session_otp(request, session_key):
    request.session.pop(session_key, None)


def _issue_registration_otp(request, flow_key, phone):
    session_key = f"{OTP_SESSION_PREFIX}{flow_key}"
    return _issue_session_otp(request, session_key, phone)


def _validate_registration_otp(request, flow_key, phone, otp_value):
    session_key = f"{OTP_SESSION_PREFIX}{flow_key}"
    return _validate_session_otp(request, session_key, phone, otp_value)


def _clear_registration_otp(request, flow_key):
    _clear_session_otp(request, f"{OTP_SESSION_PREFIX}{flow_key}")


def _client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return (request.META.get("REMOTE_ADDR") or "").strip()


def _record_login_history(request, account_type, username_or_email="", account_id=None, is_success=False, note=""):
    LoginHistory.objects.create(
        account_type=account_type or "unknown",
        account_id=account_id,
        username_or_email=(username_or_email or "")[:254],
        ip_address=_client_ip(request),
        user_agent=(request.META.get("HTTP_USER_AGENT") or "")[:255],
        is_success=bool(is_success),
        note=(note or "")[:255],
    )


def _create_email_verification_token(account_type, account_id, email):
    now = timezone.now()
    EmailVerificationToken.objects.filter(
        account_type=account_type,
        account_id=account_id,
        used_at__isnull=True,
    ).update(used_at=now)
    token_obj = EmailVerificationToken.objects.create(
        token=secrets.token_urlsafe(32),
        account_type=account_type,
        account_id=account_id,
        email=email,
        expires_at=now + timezone.timedelta(days=2),
    )
    return token_obj


def _send_email_verification_message(request, account, account_type):
    token_obj = _create_email_verification_token(account_type, account.id, account.email)
    verify_url = request.build_absolute_uri(
        reverse("dashboard:verify_email", args=[token_obj.token])
    )
    subject = "Verify your Job Exhibition account"
    body = (
        f"Hello {account.name},\n\n"
        f"Please verify your email by opening this link:\n{verify_url}\n\n"
        "This link expires in 48 hours."
    )
    sent_count = send_mail(
        subject=subject,
        message=body,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@jobexhibition.local"),
        recipient_list=[account.email],
        fail_silently=True,
    )
    return verify_url, bool(sent_count)


def _is_allowed_resume_file(file_obj):
    if not file_obj or "." not in file_obj.name:
        return False
    ext = file_obj.name.rsplit(".", 1)[1].lower()
    return ext in {"pdf", "doc", "docx"}


def _find_password_reset_account(identifier):
    value = (identifier or "").strip()
    if not value:
        return (None, None, "")

    if "@" in value:
        email = value.lower()
        user_model = get_user_model()
        admin_user = user_model.objects.filter(email__iexact=email).first()
        if admin_user:
            return ("admin", admin_user, admin_user.email)

        company = Company.objects.filter(email__iexact=email).first()
        if company:
            return ("company", company, company.email)

        consultancy = Consultancy.objects.filter(email__iexact=email).first()
        if consultancy:
            return ("consultancy", consultancy, consultancy.email)

        candidate = Candidate.objects.filter(email__iexact=email).first()
        if candidate:
            return ("candidate", candidate, candidate.email)
        return (None, None, "")

    phone = value
    company = Company.objects.filter(phone=phone).first()
    if company:
        return ("company", company, company.email)

    consultancy = Consultancy.objects.filter(Q(phone=phone) | Q(alt_phone=phone)).first()
    if consultancy:
        return ("consultancy", consultancy, consultancy.email)

    candidate = Candidate.objects.filter(Q(phone=phone) | Q(alt_phone=phone)).first()
    if candidate:
        return ("candidate", candidate, candidate.email)

    return (None, None, "")


def _resolve_account_phone(account_type, account):
    if not account:
        return ""
    account_type = (account_type or "").strip().lower()
    if account_type == "admin":
        try:
            profile = account.admin_profile
        except AdminProfile.DoesNotExist:
            profile = None
        return ((profile.phone if profile else "") or "").strip()
    if account_type == "company":
        return ((getattr(account, "phone", "") or getattr(account, "hr_phone", "")) or "").strip()
    if account_type == "consultancy":
        return (
            (
                getattr(account, "phone", "")
                or getattr(account, "alt_phone", "")
                or getattr(account, "owner_phone", "")
            )
            or ""
        ).strip()
    if account_type == "candidate":
        return ((getattr(account, "phone", "") or getattr(account, "alt_phone", "")) or "").strip()
    return ""


def _create_password_reset_token(account_type, account_id, email):
    now = timezone.now()
    PasswordResetToken.objects.filter(
        account_type=account_type,
        account_id=account_id,
        used_at__isnull=True,
    ).update(used_at=now)
    return PasswordResetToken.objects.create(
        token=secrets.token_urlsafe(32),
        account_type=account_type,
        account_id=account_id,
        email=email or "",
        expires_at=now + timezone.timedelta(minutes=PASSWORD_RESET_TTL_MINUTES),
    )


def _send_password_reset_link(request, account_type, account, email):
    token_obj = _create_password_reset_token(account_type, account.id, email)
    reset_url = request.build_absolute_uri(
        reverse("dashboard:password_reset_confirm", args=[token_obj.token])
    )
    if account_type == "admin":
        name = getattr(account, "username", "User")
    else:
        name = getattr(account, "name", "User")
    subject = "Reset your Job Exhibition password"
    body = (
        f"Hello {name},\n\n"
        "We received a password reset request for your account.\n"
        f"Reset link: {reset_url}\n\n"
        f"This link expires in {PASSWORD_RESET_TTL_MINUTES} minutes.\n"
        "If you did not request this, ignore this email."
    )
    send_mail(
        subject=subject,
        message=body,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@jobexhibition.local"),
        recipient_list=[email],
        fail_silently=True,
    )


def _resolve_password_reset_account(token_record):
    if not token_record:
        return None
    if token_record.account_type == "admin":
        return get_user_model().objects.filter(id=token_record.account_id).first()
    if token_record.account_type == "company":
        return Company.objects.filter(id=token_record.account_id).first()
    if token_record.account_type == "consultancy":
        return Consultancy.objects.filter(id=token_record.account_id).first()
    if token_record.account_type == "candidate":
        return Candidate.objects.filter(id=token_record.account_id).first()
    return None


def _set_account_password(account_type, account, raw_password):
    if account_type == "admin":
        account.set_password(raw_password)
        account.save(update_fields=["password"])
        return
    account.password = _hash_password(raw_password)
    account.save(update_fields=["password"])


def _extract_resume_text(file_obj):
    if not file_obj:
        return ""
    try:
        raw = file_obj.read()
        file_obj.seek(0)
    except Exception:
        return ""
    name = (file_obj.name or "").lower()
    if name.endswith(".docx"):
        try:
            with zipfile.ZipFile(BytesIO(raw)) as archive:
                xml_bytes = archive.read("word/document.xml")
            return xml_bytes.decode("utf-8", errors="ignore")
        except Exception:
            return ""
    return raw.decode("utf-8", errors="ignore")


def _extract_skills_from_resume(file_obj):
    text = _extract_resume_text(file_obj).lower()
    if not text:
        return []
    found = []
    for keyword in COMMON_SKILL_KEYWORDS:
        pattern = rf"\\b{re.escape(keyword.lower())}\\b"
        if re.search(pattern, text):
            found.append(keyword.title())
    return found


def register_options_view(request):
    return render(
        request,
        "dashboard/register_options.html",
        {
            "role_groups": REGISTER_ROLE_GROUPS,
        },
    )


def login_view(request):
    # If already authenticated as admin, redirect to dashboard
    if request.user.is_authenticated:
        return redirect("dashboard:dashboard")

    # If company already logged in, redirect to company dashboard
    if request.session.get("company_id"):
        return redirect("dashboard:company_dashboard")

    # If consultancy already logged in, redirect to consultancy dashboard
    if request.session.get("consultancy_id"):
        return redirect("dashboard:consultancy_dashboard")

    # If candidate already logged in, redirect to candidate dashboard
    if request.session.get("candidate_id"):
        return redirect("dashboard:candidate_job_search")

    form_data = {"username": "", "login_otp": "", "otp_mode": "0"}

    def _render_login():
        return render(request, "dashboard/login.html", {"form_data": form_data})

    if request.method == "POST":
        action = (request.POST.get("action") or "login").strip().lower()
        username = (request.POST.get("username") or "").strip()
        password = request.POST.get("password") or ""
        login_otp = (request.POST.get("login_otp") or "").strip()

        form_data = {
            "username": username,
            "login_otp": login_otp,
            "otp_mode": "1" if action in {"send_login_otp", "login_with_otp"} else "0",
        }

        user_model = get_user_model()

        def _login_admin(user):
            login(request, user)
            _record_login_history(
                request,
                "admin",
                username_or_email=user.email or user.username,
                account_id=user.id,
                is_success=True,
                note="login success",
            )
            _clear_session_otp(request, LOGIN_OTP_SESSION_KEY)
            response = redirect("dashboard:welcome")
            response.set_cookie("welcome_type", "admin", max_age=5, samesite="Lax")
            response.set_cookie("welcome_next", "dashboard:dashboard", max_age=5, samesite="Lax")
            return response

        def _send_login_otp_for(account_type, account):
            phone = _resolve_account_phone(account_type, account)
            if not phone:
                messages.error(request, "Mobile number not available for this account. Please update profile first.")
                return False
            if not re.match(r"^\+?\d{10,15}$", phone):
                messages.error(request, "Registered mobile number format is invalid. Please update your profile.")
                return False

            _, otp_error = _issue_session_otp(
                request,
                LOGIN_OTP_SESSION_KEY,
                phone,
                {
                    "account_type": (account_type or "").strip().lower(),
                    "account_id": str(account.id),
                },
            )
            if otp_error:
                messages.error(request, otp_error)
                return False
            messages.success(
                request,
                f"Login OTP sent to mobile ending {_mask_phone_number(phone)}.",
            )
            return True

        def _validate_login_otp_for(account_type, account, entered_otp):
            phone = _resolve_account_phone(account_type, account)
            if not phone:
                return False, "Mobile number not available for this account. Please update profile first."
            payload = request.session.get(LOGIN_OTP_SESSION_KEY) or {}
            if (
                (payload.get("account_type") or "").strip().lower() != (account_type or "").strip().lower()
                or str(payload.get("account_id") or "") != str(account.id)
            ):
                return False, "Please request OTP first."
            if not entered_otp:
                return False, "Please enter OTP."
            if not _validate_session_otp(request, LOGIN_OTP_SESSION_KEY, phone, entered_otp):
                return False, "Invalid or expired OTP. Please request a new OTP."
            return True, ""

        def _resolve_login_identifier(identifier):
            value = (identifier or "").strip()
            if not value:
                return (None, None)

            admin_user = user_model.objects.filter(
                Q(username__iexact=value) | Q(email__iexact=value),
            ).filter(Q(is_staff=True) | Q(is_superuser=True)).first()
            if admin_user:
                return ("admin", admin_user)

            company = Company.objects.filter(Q(name__iexact=value) | Q(email__iexact=value)).first()
            if company:
                return ("company", company)

            consultancy = Consultancy.objects.filter(Q(name__iexact=value) | Q(email__iexact=value)).first()
            if consultancy:
                return ("consultancy", consultancy)

            candidate = Candidate.objects.filter(Q(name__iexact=value) | Q(email__iexact=value)).first()
            if candidate:
                return ("candidate", candidate)

            return (None, None)

        def _check_account_access(account_type, account):
            if not account:
                return (False, "Invalid username/email.", "invalid identifier")
            if account_type == "company" and not account.email_verified:
                return (False, "Please verify your email before login.", "email not verified")
            if account_type == "consultancy" and account.kyc_status != "Verified":
                if account.kyc_status == "Rejected":
                    return (False, "Your account has been rejected. Please contact support.", "kyc rejected")
                return (False, "Your account is under review. Please wait for admin approval.", "kyc not verified")
            if account_type == "candidate" and not account.email_verified:
                return (False, "Please verify your email before login.", "email not verified")
            return (True, "", "")

        def _login_from_otp(account_type, account):
            if account_type == "admin":
                return _login_admin(account)
            if account_type == "company":
                return _login_company(account)
            if account_type == "consultancy":
                return _login_consultancy(account)
            if account_type == "candidate":
                return _login_candidate(account)
            messages.error(request, "Unsupported account type for OTP login.")
            return _render_login()

        def _login_company(company):
            if password and company.password and not _is_hashed_password(company.password):
                company.password = make_password(password)
                company.save(update_fields=["password"])
            company.last_login = timezone.now()
            company.save(update_fields=["last_login"])
            request.session["company_id"] = company.id
            request.session["company_name"] = company.name
            _record_login_history(
                request,
                "company",
                username_or_email=company.email or company.name,
                account_id=company.id,
                is_success=True,
                note="login success",
            )
            _clear_session_otp(request, LOGIN_OTP_SESSION_KEY)
            response = redirect("dashboard:welcome")
            response.set_cookie("welcome_type", "company", max_age=5, samesite="Lax")
            response.set_cookie("welcome_next", "dashboard:company_dashboard", max_age=5, samesite="Lax")
            return response

        def _login_consultancy(consultancy):
            if password and consultancy.password and not _is_hashed_password(consultancy.password):
                consultancy.password = make_password(password)
                consultancy.save(update_fields=["password"])
            consultancy.last_login = timezone.now()
            consultancy.save(update_fields=["last_login"])
            request.session["consultancy_id"] = consultancy.id
            request.session["consultancy_name"] = consultancy.name
            _record_login_history(
                request,
                "consultancy",
                username_or_email=consultancy.email or consultancy.name,
                account_id=consultancy.id,
                is_success=True,
                note="login success",
            )
            _clear_session_otp(request, LOGIN_OTP_SESSION_KEY)
            response = redirect("dashboard:welcome")
            response.set_cookie("welcome_type", "consultancy", max_age=5, samesite="Lax")
            response.set_cookie("welcome_next", "dashboard:consultancy_dashboard", max_age=5, samesite="Lax")
            return response

        def _login_candidate(candidate):
            if password and candidate.password and not _is_hashed_password(candidate.password):
                candidate.password = make_password(password)
                candidate.save(update_fields=["password"])
            completion = candidate.profile_completion or _calculate_candidate_completion(candidate)
            update_fields = ["last_login"]
            if completion != candidate.profile_completion:
                candidate.profile_completion = completion
                update_fields.append("profile_completion")
            candidate.last_login = timezone.now()
            candidate.save(update_fields=update_fields)
            request.session["candidate_id"] = candidate.id
            request.session["candidate_name"] = candidate.name
            _record_login_history(
                request,
                "candidate",
                username_or_email=candidate.email or candidate.name,
                account_id=candidate.id,
                is_success=True,
                note="login success",
            )
            _clear_session_otp(request, LOGIN_OTP_SESSION_KEY)
            response = redirect("dashboard:welcome")
            response.set_cookie("welcome_type", "candidate", max_age=5, samesite="Lax")
            response.set_cookie("welcome_next", "dashboard:candidate_job_search", max_age=5, samesite="Lax")
            return response

        if action in {"send_login_otp", "login_with_otp"}:
            if not username:
                messages.error(request, "Username/email is required for OTP login.")
                return _render_login()
            account_type, account = _resolve_login_identifier(username)
            allowed, error_message, audit_note = _check_account_access(account_type, account)
            if not allowed:
                messages.error(request, error_message)
                _record_login_history(
                    request,
                    account_type or "unknown",
                    username_or_email=username,
                    account_id=getattr(account, "id", None),
                    is_success=False,
                    note=audit_note or "otp login blocked",
                )
                return _render_login()

            if action == "send_login_otp":
                _send_login_otp_for(account_type, account)
                return _render_login()

            is_valid_otp, otp_error = _validate_login_otp_for(account_type, account, login_otp)
            if not is_valid_otp:
                messages.error(request, otp_error)
                _record_login_history(
                    request,
                    account_type or "unknown",
                    username_or_email=username,
                    account_id=getattr(account, "id", None),
                    is_success=False,
                    note="otp login failed",
                )
                return _render_login()
            return _login_from_otp(account_type, account)

        if not username or not password:
            messages.error(request, "Username/email and password are required.")
            _record_login_history(
                request,
                "unknown",
                username_or_email=username,
                is_success=False,
                note="missing credentials",
            )
            return _render_login()

        # Admin login by Django auth credentials
        user = authenticate(request, username=username, password=password)
        if user and (user.is_staff or user.is_superuser):
            return _login_admin(user)

        # Company login by username or email
        company = Company.objects.filter(Q(name__iexact=username) | Q(email__iexact=username)).first()
        if company and _check_raw_password(password, company.password):
            if not company.email_verified:
                messages.error(request, "Please verify your email before login.")
                _record_login_history(
                    request,
                    "company",
                    username_or_email=company.email or username,
                    account_id=company.id,
                    is_success=False,
                    note="email not verified",
                )
                return _render_login()
            return _login_company(company)

        # Demo company credentials
        if username == "company1" and password == "123456789":
            company = Company.objects.filter(name__iexact="company1").first()
            if not company:
                today = timezone.localdate()
                company = Company.objects.create(
                    name="company1",
                    email="company1@example.com",
                    password=make_password("123456789"),
                    account_type="Company",
                    kyc_status="Verified",
                    account_status="Active",
                    contact_position="Owner",
                    hr_name="Owner",
                    hr_designation="Owner",
                    hr_phone="+910000000000",
                    hr_email="company1@example.com",
                    terms_accepted=True,
                    plan_name="Premium",
                    plan_type="Premium",
                    payment_status="Paid",
                    plan_start=today,
                    plan_expiry=today + timezone.timedelta(days=30),
                    email_verified=True,
                    phone_verified=True,
                )
            elif not company.email_verified:
                company.email_verified = True
                company.phone_verified = True
                company.save(update_fields=["email_verified", "phone_verified"])
            return _login_company(company)

        # Consultancy login by username or email
        consultancy = Consultancy.objects.filter(
            Q(name__iexact=username) | Q(email__iexact=username)
        ).first()
        if consultancy and _check_raw_password(password, consultancy.password):
            if consultancy.kyc_status != "Verified":
                if consultancy.kyc_status == "Rejected":
                    messages.error(request, "Your account has been rejected. Please contact support.")
                else:
                    messages.error(request, "Your account is under review. Please wait for admin approval.")
                _record_login_history(
                    request,
                    "consultancy",
                    username_or_email=consultancy.email or username,
                    account_id=consultancy.id,
                    is_success=False,
                    note="kyc not verified",
                )
                return _render_login()
            return _login_consultancy(consultancy)

        # Demo consultancy credentials
        if username == "con1" and password == "123456789":
            consultancy = Consultancy.objects.filter(name__iexact="con1").first()
            if not consultancy:
                today = timezone.localdate()
                consultancy = Consultancy.objects.create(
                    name="con1",
                    email="con1@example.com",
                    password=make_password("123456789"),
                    account_type="Consultancy",
                    kyc_status="Verified",
                    account_status="Active",
                    contact_position="Owner",
                    plan_name="Premium",
                    plan_type="Premium",
                    payment_status="Paid",
                    plan_start=today,
                    plan_expiry=today + timezone.timedelta(days=30),
                    phone="+910000000010",
                )
            elif not consultancy.phone:
                consultancy.phone = "+910000000010"
                consultancy.save(update_fields=["phone"])
            return _login_consultancy(consultancy)

        # Candidate login by username or email
        candidate = Candidate.objects.filter(Q(name__iexact=username) | Q(email__iexact=username)).first()
        if candidate and _check_raw_password(password, candidate.password):
            if not candidate.email_verified:
                messages.error(request, "Please verify your email before login.")
                _record_login_history(
                    request,
                    "candidate",
                    username_or_email=candidate.email or username,
                    account_id=candidate.id,
                    is_success=False,
                    note="email not verified",
                )
                return _render_login()
            return _login_candidate(candidate)

        # Demo candidate credentials
        if username == "can1" and password == "123456789":
            candidate = Candidate.objects.filter(name__iexact="can1").first()
            if not candidate:
                today = timezone.localdate()
                candidate = Candidate.objects.create(
                    name="can1",
                    email="can1@example.com",
                    password=make_password("123456789"),
                    account_type="Candidate",
                    account_status="Active",
                    profile_completion=45,
                    registration_date=today,
                    email_verified=True,
                    phone_verified=True,
                    phone="+910000000001",
                )
            elif not candidate.email_verified:
                candidate.email_verified = True
                candidate.phone_verified = True
                if not candidate.phone:
                    candidate.phone = "+910000000001"
                    candidate.save(update_fields=["email_verified", "phone_verified", "phone"])
                else:
                    candidate.save(update_fields=["email_verified", "phone_verified"])
            elif not candidate.phone:
                candidate.phone = "+910000000001"
                candidate.save(update_fields=["phone"])
            return _login_candidate(candidate)

        messages.error(request, "Invalid username/email or password.")
        _record_login_history(
            request,
            "unknown",
            username_or_email=username,
            is_success=False,
            note="invalid credentials",
        )
        return _render_login()

    return _render_login()


def forgot_password_view(request):
    form_data = {"identifier": "", "mobile_otp": ""}

    if request.method == "POST":
        action = (request.POST.get("action") or "send_reset_link").strip().lower()
        identifier = (request.POST.get("identifier") or "").strip()
        mobile_otp = (request.POST.get("mobile_otp") or "").strip()
        form_data = {
            "identifier": identifier,
            "mobile_otp": mobile_otp,
        }
        if not identifier:
            messages.error(request, "Please enter your email address or mobile number.")
            return render(request, "dashboard/forgot_password.html", {"form_data": form_data})

        account_type, account, email = _find_password_reset_account(identifier)
        phone = _resolve_account_phone(account_type, account)

        if action == "send_otp":
            if not account:
                messages.success(
                    request,
                    "If account exists, OTP has been sent to the registered mobile number.",
                )
                return render(request, "dashboard/forgot_password.html", {"form_data": form_data})
            if not phone:
                messages.error(request, "No mobile number found for this account. Please contact support.")
                return render(request, "dashboard/forgot_password.html", {"form_data": form_data})
            if not re.match(r"^\+?\d{10,15}$", phone):
                messages.error(request, "Registered mobile number format is invalid.")
                return render(request, "dashboard/forgot_password.html", {"form_data": form_data})

            _, otp_error = _issue_session_otp(
                request,
                PASSWORD_RESET_OTP_SESSION_KEY,
                phone,
                {
                    "account_type": (account_type or "").strip().lower(),
                    "account_id": str(account.id),
                    "email": (email or "").strip().lower(),
                },
            )
            if otp_error:
                messages.error(request, otp_error)
            else:
                messages.success(
                    request,
                    f"OTP sent to mobile ending {_mask_phone_number(phone)}.",
                )
            return render(request, "dashboard/forgot_password.html", {"form_data": form_data})

        if account and email:
            requires_otp = getattr(settings, "FORGOT_PASSWORD_OTP_REQUIRED", True)
            if requires_otp:
                if not phone:
                    messages.error(request, "No mobile number found for this account. Please contact support.")
                    return render(request, "dashboard/forgot_password.html", {"form_data": form_data})
                payload = request.session.get(PASSWORD_RESET_OTP_SESSION_KEY) or {}
                if (
                    (payload.get("account_type") or "").strip().lower() != (account_type or "").strip().lower()
                    or str(payload.get("account_id") or "") != str(account.id)
                    or (payload.get("email") or "").strip().lower() != (email or "").strip().lower()
                ):
                    messages.error(request, "Please request OTP first.")
                    return render(request, "dashboard/forgot_password.html", {"form_data": form_data})
                if not mobile_otp:
                    messages.error(request, "Please enter OTP to continue.")
                    return render(request, "dashboard/forgot_password.html", {"form_data": form_data})
                if not _validate_session_otp(
                    request,
                    PASSWORD_RESET_OTP_SESSION_KEY,
                    phone,
                    mobile_otp,
                ):
                    messages.error(request, "Invalid or expired OTP. Please request a new OTP.")
                    return render(request, "dashboard/forgot_password.html", {"form_data": form_data})
            _clear_session_otp(request, PASSWORD_RESET_OTP_SESSION_KEY)
            _send_password_reset_link(request, account_type, account, email)
        messages.success(
            request,
            "If account exists, reset instructions have been sent to the registered email.",
        )
        return redirect("dashboard:forgot_password")

    return render(request, "dashboard/forgot_password.html", {"form_data": form_data})


def password_reset_confirm_view(request, token):
    token_record = PasswordResetToken.objects.filter(token=token).first()
    token_valid = bool(
        token_record
        and not token_record.used_at
        and token_record.expires_at >= timezone.now()
    )
    account = _resolve_password_reset_account(token_record) if token_valid else None
    if token_valid and not account:
        token_valid = False

    if request.method == "POST":
        if not token_valid:
            messages.error(request, "Reset link is invalid or expired. Please request a new one.")
            return redirect("dashboard:forgot_password")

        password = request.POST.get("password") or ""
        confirm_password = request.POST.get("confirm_password") or ""
        if not password or not confirm_password:
            messages.error(request, "New password and confirm password are required.")
            return render(
                request,
                "dashboard/reset_password.html",
                {"token_valid": token_valid},
            )
        if password != confirm_password:
            messages.error(request, "Password and confirm password do not match.")
            return render(
                request,
                "dashboard/reset_password.html",
                {"token_valid": token_valid},
            )
        password_errors = _password_strength_errors(password)
        if password_errors:
            for error in password_errors:
                messages.error(request, error)
            return render(
                request,
                "dashboard/reset_password.html",
                {"token_valid": token_valid},
            )

        _set_account_password(token_record.account_type, account, password)
        token_record.used_at = timezone.now()
        token_record.save(update_fields=["used_at"])
        messages.success(request, "Password reset successful. Please login with new password.")
        return redirect("dashboard:login")

    return render(
        request,
        "dashboard/reset_password.html",
        {"token_valid": token_valid},
    )


def company_register_view(request):
    flow_key = "company"
    form_data = {}
    captcha_question = _get_registration_captcha_question(request, flow_key)

    if request.method == "POST":
        action = (request.POST.get("action") or "register").strip().lower()
        name = (request.POST.get("name") or "").strip()
        email = (request.POST.get("email") or "").strip().lower()
        phone = (request.POST.get("phone") or "").strip()
        location = (request.POST.get("location") or "").strip()
        password = request.POST.get("password") or ""
        confirm_password = request.POST.get("confirm_password") or ""
        hr_name = (request.POST.get("hr_name") or "").strip()
        hr_designation = (request.POST.get("hr_designation") or "").strip()
        hr_phone = (request.POST.get("hr_phone") or "").strip()
        hr_email = (request.POST.get("hr_email") or "").strip().lower()
        contact_position = (request.POST.get("contact_position") or "").strip() or hr_designation
        mobile_otp = (request.POST.get("mobile_otp") or "").strip()
        captcha_answer = (request.POST.get("captcha_answer") or "").strip()
        terms_accepted = request.POST.get("terms_accepted") == "on"
        registration_source = "google" if request.POST.get("signup_with_google") == "1" else "manual"

        form_data = {
            "name": name,
            "email": email,
            "phone": phone,
            "location": location,
            "hr_name": hr_name,
            "hr_designation": hr_designation,
            "hr_phone": hr_phone,
            "hr_email": hr_email,
            "contact_position": contact_position,
            "mobile_otp": mobile_otp,
            "captcha_answer": captcha_answer,
            "terms_accepted": terms_accepted,
        }

        if action == "send_otp":
            if not phone:
                messages.error(request, "Please enter mobile number before requesting OTP.")
            elif not re.match(r"^\+?\d{10,15}$", phone):
                messages.error(request, "Enter a valid mobile number (10 to 15 digits).")
            else:
                _, otp_error = _issue_registration_otp(request, flow_key, phone)
                if otp_error:
                    messages.error(request, otp_error)
                else:
                    messages.success(request, "OTP sent successfully to your mobile number.")
            captcha_question = _set_registration_captcha(request, flow_key)
            return render(
                request,
                "dashboard/register_company.html",
                {"form_data": form_data, "captcha_question": captcha_question},
            )

        errors = []
        if not name or not email or not phone or not password or not confirm_password or not location:
            errors.append("Company name, official email, mobile number, password, and city/location are required.")

        if password != confirm_password:
            errors.append("Password and confirm password do not match.")

        errors.extend(_password_strength_errors(password))

        if Company.objects.filter(name__iexact=name).exists():
            errors.append("Company with this name already exists.")
        if Company.objects.filter(email__iexact=email).exists():
            errors.append("Company with this email already exists.")
        if Company.objects.filter(phone=phone).exists():
            errors.append("This mobile number is already used by another company account.")

        if not _validate_registration_otp(request, flow_key, phone, mobile_otp):
            errors.append("Invalid or expired mobile OTP. Please request a new OTP.")

        if not _validate_registration_captcha(request, flow_key, captcha_answer):
            errors.append("Invalid CAPTCHA answer.")

        if not terms_accepted:
            errors.append("You must agree to Terms & Conditions.")

        if errors:
            for error in errors:
                messages.error(request, error)
            captcha_question = _set_registration_captcha(request, flow_key)
            return render(
                request,
                "dashboard/register_company.html",
                {"form_data": form_data, "captcha_question": captcha_question},
            )

        company = Company.objects.create(
            name=name,
            email=email,
            password=_hash_password(password),
            phone=phone,
            location=location,
            contact_position=contact_position,
            hr_name=hr_name,
            hr_designation=hr_designation,
            hr_phone=hr_phone,
            hr_email=hr_email,
            account_type="Company",
            account_status="Active",
            email_verified=False,
            phone_verified=True,
            terms_accepted=terms_accepted,
            registration_source=registration_source,
        )

        verify_url, mail_sent = _send_email_verification_message(request, company, "company")

        if not _is_official_company_email(email):
            messages.warning(request, "Official domain email is recommended (example: hr@company.com).")

        if mail_sent:
            messages.success(request, "Company registered. Verification email sent. Please verify email before login.")
        else:
            messages.success(request, "Company registered. Please verify your email using the link below before login.")
        if settings.DEBUG:
            messages.info(request, f"Verification link: {verify_url}")

        _clear_registration_otp(request, flow_key)
        _set_registration_captcha(request, flow_key)
        return redirect("dashboard:login")

    return render(
        request,
        "dashboard/register_company.html",
        {"form_data": form_data, "captcha_question": captcha_question},
    )


def consultancy_register_view(request):
    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()
        email = (request.POST.get("email") or "").strip()
        password = request.POST.get("password") or ""
        if not name or not email or not password:
            messages.error(request, "Name, email, and password are required.")
        elif Consultancy.objects.filter(name__iexact=name).exists() or Consultancy.objects.filter(email__iexact=email).exists():
            messages.error(request, "Consultancy with this name or email already exists.")
        else:
            consultancy_types = request.POST.getlist("consultancy_types")
            address_line1 = (request.POST.get("address_line1") or "").strip()
            address_line2 = (request.POST.get("address_line2") or "").strip()
            city = (request.POST.get("city") or "").strip()
            state = (request.POST.get("state") or "").strip()
            pin_code = (request.POST.get("pin_code") or "").strip()
            country = (request.POST.get("country") or "").strip()
            full_address = ", ".join(part for part in [address_line1, address_line2, city, state, pin_code, country] if part)
            location = (request.POST.get("location") or "").strip() or city
            Consultancy.objects.create(
                name=name,
                email=email,
                password=_hash_password(password),
                phone=(request.POST.get("phone") or "").strip(),
                location=location,
                contact_position=(request.POST.get("owner_designation") or request.POST.get("contact_position") or "").strip(),
                company_type=(request.POST.get("company_type") or "").strip(),
                registration_number=(request.POST.get("registration_number") or "").strip(),
                gst_number=(request.POST.get("gst_number") or "").strip(),
                year_established=_parse_int(request.POST.get("year_established")),
                website_url=(request.POST.get("website_url") or "").strip(),
                alt_phone=(request.POST.get("alt_phone") or "").strip(),
                office_landline=(request.POST.get("office_landline") or "").strip(),
                address_line1=address_line1,
                address_line2=address_line2,
                city=city,
                state=state,
                pin_code=pin_code,
                country=country,
                address=full_address,
                owner_name=(request.POST.get("owner_name") or "").strip(),
                owner_designation=(request.POST.get("owner_designation") or "").strip(),
                owner_phone=(request.POST.get("owner_phone") or "").strip(),
                owner_email=(request.POST.get("owner_email") or "").strip(),
                owner_pan=(request.POST.get("owner_pan") or "").strip(),
                owner_aadhaar=(request.POST.get("owner_aadhaar") or "").strip(),
                consultancy_type=", ".join(t.strip() for t in consultancy_types if t.strip()),
                industries_served=(request.POST.get("industries_served") or "").strip(),
                service_charges=(request.POST.get("service_charges") or "").strip(),
                areas_of_operation=(request.POST.get("areas_of_operation") or "").strip(),
                registration_certificate=request.FILES.get("registration_certificate"),
                gst_certificate=request.FILES.get("gst_certificate"),
                pan_card=request.FILES.get("pan_card"),
                address_proof=request.FILES.get("address_proof"),
                profile_image=request.FILES.get("logo_upload") or request.FILES.get("profile_image"),
                account_type="Consultancy",
                account_status="Active",
                kyc_status="Pending",
            )
            messages.success(request, "Consultancy registered successfully. Please wait for admin approval.")
            return redirect("dashboard:login")
    return render(request, "dashboard/register_consultancy.html")


def candidate_register_view(request):
    flow_key = "candidate"
    preferred_role = (request.GET.get("role") or "").strip()
    form_data = {"current_job_title": preferred_role} if preferred_role else {}
    captcha_question = _get_registration_captcha_question(request, flow_key)

    if request.method == "POST":
        action = (request.POST.get("action") or "register").strip().lower()
        name = (request.POST.get("name") or "").strip()
        email = (request.POST.get("email") or "").strip().lower()
        phone = (request.POST.get("phone") or "").strip()
        password = request.POST.get("password") or ""
        confirm_password = request.POST.get("confirm_password") or ""
        mobile_otp = (request.POST.get("mobile_otp") or "").strip()
        captcha_answer = (request.POST.get("captcha_answer") or "").strip()

        date_of_birth_raw = (request.POST.get("date_of_birth") or "").strip()
        gender = (request.POST.get("gender") or "").strip()
        current_address = (request.POST.get("current_address") or "").strip()
        preferred_job_location = (request.POST.get("preferred_job_location") or "").strip()

        current_job_title = (request.POST.get("current_job_title") or "").strip()
        total_experience = (request.POST.get("total_experience") or "").strip()
        current_salary = (request.POST.get("current_salary") or "").strip()
        expected_salary = (request.POST.get("expected_salary") or "").strip()
        notice_period = (request.POST.get("notice_period") or "").strip()
        employment_type = (request.POST.get("employment_type") or "").strip()

        degree = (request.POST.get("degree") or "").strip()
        university = (request.POST.get("university") or "").strip()
        passing_year = (request.POST.get("passing_year") or "").strip()
        percentage = (request.POST.get("percentage") or "").strip()

        primary_skills = (request.POST.get("primary_skills") or "").strip()
        secondary_skills = (request.POST.get("secondary_skills") or "").strip()
        certifications = (request.POST.get("certifications") or "").strip()
        languages = (request.POST.get("languages") or "").strip()
        profile_visibility = (request.POST.get("profile_visibility") or "public").strip().lower()

        location = (request.POST.get("location") or preferred_job_location).strip()

        form_data = {
            "name": name,
            "email": email,
            "phone": phone,
            "location": location,
            "date_of_birth": date_of_birth_raw,
            "gender": gender,
            "current_address": current_address,
            "preferred_job_location": preferred_job_location,
            "current_job_title": current_job_title,
            "total_experience": total_experience,
            "current_salary": current_salary,
            "expected_salary": expected_salary,
            "notice_period": notice_period,
            "employment_type": employment_type,
            "degree": degree,
            "university": university,
            "passing_year": passing_year,
            "percentage": percentage,
            "primary_skills": primary_skills,
            "secondary_skills": secondary_skills,
            "certifications": certifications,
            "languages": languages,
            "profile_visibility": profile_visibility,
            "mobile_otp": mobile_otp,
            "captcha_answer": captcha_answer,
        }

        if action == "send_otp":
            if not phone:
                messages.error(request, "Please enter mobile number before requesting OTP.")
            elif not re.match(r"^\+?\d{10,15}$", phone):
                messages.error(request, "Enter a valid mobile number (10 to 15 digits).")
            else:
                _, otp_error = _issue_registration_otp(request, flow_key, phone)
                if otp_error:
                    messages.error(request, otp_error)
                else:
                    messages.success(request, "OTP sent successfully to your mobile number.")
            captcha_question = _set_registration_captcha(request, flow_key)
            return render(
                request,
                "dashboard/register_candidate.html",
                {"form_data": form_data, "captcha_question": captcha_question},
            )

        errors = []
        if not name or not email or not phone or not password or not confirm_password:
            errors.append("Name, email, mobile number, password, and confirm password are required.")

        if password != confirm_password:
            errors.append("Password and confirm password do not match.")

        errors.extend(_password_strength_errors(password))

        if Candidate.objects.filter(name__iexact=name).exists():
            errors.append("Candidate with this name already exists.")
        if Candidate.objects.filter(email__iexact=email).exists():
            errors.append("Candidate with this email already exists.")
        if Candidate.objects.filter(phone=phone).exists():
            errors.append("This mobile number is already used by another candidate account.")

        if not _validate_registration_otp(request, flow_key, phone, mobile_otp):
            errors.append("Invalid or expired mobile OTP. Please request a new OTP.")

        if not _validate_registration_captcha(request, flow_key, captcha_answer):
            errors.append("Invalid CAPTCHA answer.")

        profile_photo = request.FILES.get("profile_photo")
        primary_resume = request.FILES.get("resume")
        resume_versions = request.FILES.getlist("resume_versions")
        all_resumes = []
        if primary_resume:
            all_resumes.append(primary_resume)
        all_resumes.extend([file_obj for file_obj in resume_versions if file_obj])
        invalid_resumes = [file_obj.name for file_obj in all_resumes if not _is_allowed_resume_file(file_obj)]
        if invalid_resumes:
            errors.append("Only PDF/DOC/DOCX files are allowed for resume upload.")

        inferred_skills = []
        if not primary_skills and all_resumes:
            inferred_skills = _extract_skills_from_resume(all_resumes[0])
            if inferred_skills:
                primary_skills = ", ".join(inferred_skills)
                form_data["primary_skills"] = primary_skills

        if errors:
            for error in errors:
                messages.error(request, error)
            captcha_question = _set_registration_captcha(request, flow_key)
            return render(
                request,
                "dashboard/register_candidate.html",
                {"form_data": form_data, "captcha_question": captcha_question},
            )

        candidate = Candidate.objects.create(
            name=name,
            email=email,
            password=_hash_password(password),
            phone=phone,
            location=location,
            address=current_address,
            account_type="Candidate",
            account_status="Active",
            profile_completion=0,
            profile_image=profile_photo,
            date_of_birth=parse_date(date_of_birth_raw) if date_of_birth_raw else None,
            gender=gender,
            preferred_job_location=preferred_job_location,
            current_position=current_job_title,
            total_experience=total_experience,
            current_salary=current_salary,
            expected_salary=expected_salary,
            notice_period=notice_period,
            experience_type=employment_type,
            employment_type=employment_type,
            education=university,
            education_graduation=degree,
            education_other=(f"Passing Year: {passing_year} | Score: {percentage}" if passing_year or percentage else ""),
            skills=primary_skills,
            secondary_skills=secondary_skills,
            certifications=certifications,
            languages=languages,
            profile_visibility=profile_visibility != "private",
            email_verified=False,
            phone_verified=True,
        )

        if degree or university or passing_year or percentage:
            CandidateEducation.objects.create(
                candidate=candidate,
                qualification=degree,
                institution=university,
                passing_year=passing_year,
                score=percentage,
            )

        default_resume = None
        for index, resume_file in enumerate(all_resumes):
            title = "Resume" if index == 0 else f"Resume Version {index + 1}"
            resume_record = CandidateResume.objects.create(
                candidate=candidate,
                title=title,
                resume_file=resume_file,
                is_default=index == 0,
            )
            if index == 0:
                default_resume = resume_record

        if default_resume:
            candidate.resume = default_resume.resume_file
            candidate.save(update_fields=["resume"])

        candidate.profile_completion = _calculate_candidate_completion(candidate)
        candidate.save(update_fields=["profile_completion"])

        if inferred_skills:
            messages.info(
                request,
                f"Resume auto parsing detected skills: {', '.join(inferred_skills)}",
            )

        verify_url, mail_sent = _send_email_verification_message(request, candidate, "candidate")

        if mail_sent:
            messages.success(request, "Candidate registered. Verification email sent. Please verify email before login.")
        else:
            messages.success(request, "Candidate registered. Please verify your email using the link below before login.")
        if settings.DEBUG:
            messages.info(request, f"Verification link: {verify_url}")

        _clear_registration_otp(request, flow_key)
        _set_registration_captcha(request, flow_key)
        return redirect("dashboard:login")

    return render(
        request,
        "dashboard/register_candidate.html",
        {"form_data": form_data, "captcha_question": captcha_question},
    )


def verify_email_view(request, token):
    record = EmailVerificationToken.objects.filter(token=token).first()
    if not record:
        messages.error(request, "Invalid verification link.")
        return redirect("dashboard:login")

    if record.used_at:
        messages.info(request, "Email is already verified. Please login.")
        return redirect("dashboard:login")

    if record.expires_at < timezone.now():
        messages.error(request, "Verification link expired. Please register again.")
        return redirect("dashboard:login")

    account = None
    if record.account_type == "candidate":
        account = Candidate.objects.filter(id=record.account_id, email__iexact=record.email).first()
    elif record.account_type == "company":
        account = Company.objects.filter(id=record.account_id, email__iexact=record.email).first()

    if not account:
        messages.error(request, "Account not found for this verification link.")
        return redirect("dashboard:login")

    account.email_verified = True
    account.save(update_fields=["email_verified"])

    record.used_at = timezone.now()
    record.save(update_fields=["used_at"])

    messages.success(request, "Email verified successfully. You can login now.")
    return redirect("dashboard:login")


def company_login_required(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.session.get("company_id"):
            return redirect("dashboard:login")
        return view_func(request, *args, **kwargs)

    return _wrapped


def company_login_view(request):
    # Redirect to unified login page with company tab highlighted
    return redirect("dashboard:login")


def company_logout_view(request):
    request.session.pop("company_id", None)
    request.session.pop("company_name", None)
    return redirect("dashboard:login")


def consultancy_login_required(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.session.get("consultancy_id"):
            return redirect("dashboard:login")
        return view_func(request, *args, **kwargs)

    return _wrapped


def consultancy_logout_view(request):
    request.session.pop("consultancy_id", None)
    request.session.pop("consultancy_name", None)
    return redirect("dashboard:login")


def candidate_login_required(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.session.get("candidate_id"):
            return redirect("dashboard:login")
        return view_func(request, *args, **kwargs)

    return _wrapped


def candidate_logout_view(request):
    request.session.pop("candidate_id", None)
    request.session.pop("candidate_name", None)
    return redirect("dashboard:login")


@consultancy_login_required
def consultancy_dashboard_view(request):
    consultancy_id = request.session.get("consultancy_id")
    consultancy = Consultancy.objects.filter(id=consultancy_id).first()
    if not consultancy:
        request.session.pop("consultancy_id", None)
        request.session.pop("consultancy_name", None)
        return redirect("dashboard:login")

    assigned_qs = AssignedJob.objects.filter(consultancy=consultancy).select_related("job").order_by(
        "-assigned_date",
        "-created_at",
    )
    applications_qs = Application.objects.filter(consultancy=consultancy)
    interviews_qs = Interview.objects.filter(
        status__in=["scheduled", "rescheduled"],
        application__consultancy=consultancy,
    )
    placements_qs = applications_qs.filter(status__in=SELECTED_STATUSES)
    commission_rate = _consultancy_commission_defaults(consultancy)["fixed_fee"]

    metrics = {
        "assigned_jobs": assigned_qs.count(),
        "active_jobs": assigned_qs.filter(status__in=["Active", "Urgent"]).count(),
        "candidates": applications_qs.values("candidate_email").distinct().count(),
        "interviews": interviews_qs.count(),
        "placements": placements_qs.count(),
        "commission_total": placements_qs.count() * commission_rate,
        "pending_payments": placements_qs.count() * commission_rate,
    }

    assigned_jobs = []
    for assignment in assigned_qs[:4]:
        job = assignment.job
        applications_count = Application.objects.filter(
            consultancy=consultancy,
            job=job,
        ).count()
        assigned_jobs.append(
            {
                "job_id": job.job_id,
                "title": job.title,
                "company": job.company,
                "status": assignment.status,
                "applications": applications_count,
            }
        )

    today = timezone.localdate()
    interview_schedule = []
    for interview in Interview.objects.filter(
        interview_date=today,
        application__consultancy=consultancy,
    ).order_by("interview_time")[:4]:
        interview_schedule.append(
            {
                "candidate": interview.candidate_name,
                "role": interview.job_title,
                "time": interview.interview_time.strftime("%I:%M %p") if interview.interview_time else "TBD",
            }
        )

    placements = []
    assignment_map = {
        assignment.job_id: assignment
        for assignment in AssignedJob.objects.filter(consultancy=consultancy).select_related("job")
    }
    for app in placements_qs.order_by("-updated_at")[:5]:
        salary_value = app.offer_package or app.expected_salary or "--"
        assignment = assignment_map.get(app.job_id) if app.job_id else None
        commission_value = _calculate_commission(assignment, app)
        placement_status = "Pending" if app.status == "Offer Issued" else "In Review"
        placements.append(
            {
                "candidate": app.candidate_name,
                "company": app.company,
                "salary": salary_value,
                "commission": f"INR {commission_value:,}" if commission_value else f"INR {commission_rate:,}",
                "status": placement_status,
            }
        )

    pipeline = [
        {"key": "submitted", "label": "Submitted", "value": applications_qs.filter(status="Applied").count()},
        {"key": "under_review", "label": "Under Review", "value": applications_qs.filter(status="On Hold").count()},
        {"key": "shortlisted", "label": "Shortlisted", "value": applications_qs.filter(status="Shortlisted").count()},
        {"key": "interview", "label": "Interview", "value": applications_qs.filter(status__in=INTERVIEW_STATUSES).count()},
        {"key": "selected", "label": "Selected", "value": applications_qs.filter(status="Selected").count()},
        {"key": "placed", "label": "Placed", "value": applications_qs.filter(status="Offer Issued").count()},
    ]
    ad_segment = _resolve_subscription_segment_for_account(
        "Consultancy",
        consultancy.email,
        consultancy.plan_type,
        consultancy.payment_status,
        consultancy.plan_expiry,
    )
    advertisement = _active_advertisement_for("consultancy", ad_segment)

    context = {
        "consultancy": consultancy,
        "metrics": metrics,
        "assigned_jobs": assigned_jobs,
        "interview_schedule": interview_schedule,
        "placements": placements,
        "pipeline": pipeline,
        "advertisement": advertisement,
    }
    return render(request, "dashboard/consultancy/consultancy_dashboard.html", context)


@consultancy_login_required
@require_http_methods(["GET"])
def api_consultancy_metrics(request):
    consultancy_id = request.session.get("consultancy_id")
    consultancy = Consultancy.objects.filter(id=consultancy_id).first()
    if not consultancy:
        return JsonResponse({"error": "unauthorized"}, status=401)

    assigned_qs = AssignedJob.objects.filter(consultancy=consultancy)
    applications_qs = Application.objects.filter(consultancy=consultancy)
    interviews_qs = Interview.objects.filter(
        status__in=["scheduled", "rescheduled"],
        application__consultancy=consultancy,
    )
    placements_qs = applications_qs.filter(status__in=SELECTED_STATUSES)
    commission_rate = _consultancy_commission_defaults(consultancy)["fixed_fee"]
    placements_count = placements_qs.count()

    metrics = {
        "assigned_jobs": assigned_qs.count(),
        "active_jobs": assigned_qs.filter(status__in=["Active", "Urgent"]).count(),
        "candidates": applications_qs.values("candidate_email").distinct().count(),
        "interviews": interviews_qs.count(),
        "placements": placements_count,
        "pending_payments": placements_count * commission_rate,
    }

    pipeline = [
        {"key": "submitted", "value": applications_qs.filter(status="Applied").count()},
        {"key": "under_review", "value": applications_qs.filter(status="On Hold").count()},
        {"key": "shortlisted", "value": applications_qs.filter(status="Shortlisted").count()},
        {"key": "interview", "value": applications_qs.filter(status__in=INTERVIEW_STATUSES).count()},
        {"key": "selected", "value": applications_qs.filter(status="Selected").count()},
        {"key": "placed", "value": applications_qs.filter(status="Offer Issued").count()},
    ]

    return JsonResponse({"metrics": metrics, "pipeline": pipeline})


@consultancy_login_required
def consultancy_jobs_view(request):
    consultancy_id = request.session.get("consultancy_id")
    consultancy = Consultancy.objects.filter(id=consultancy_id).first()
    if not consultancy:
        return redirect("dashboard:login")

    filter_status = (request.GET.get("status") or "").strip().lower()
    action = (request.GET.get("action") or "").strip().lower()
    lifecycle_filters = {
        "draft": "Draft",
        "active": "Active",
        "paused": "Paused",
        "closed": "Closed",
        "expired": "Expired",
        "archived": "Archived",
    }
    base_qs = _consultancy_posted_jobs_queryset(consultancy).annotate(apply_count=Count("applications"))
    jobs_qs = base_qs
    if filter_status in lifecycle_filters:
        jobs_qs = jobs_qs.filter(lifecycle_status=lifecycle_filters[filter_status])
    jobs_qs = jobs_qs.order_by("-created_at", "-id")

    edit_job = None
    if request.method == "POST":
        post_action = (request.POST.get("action") or "").strip().lower()
        job_id = (request.POST.get("job_id") or "").strip()
        job_qs = _consultancy_posted_jobs_queryset(consultancy)

        if post_action == "delete":
            if not job_id:
                messages.error(request, "Unable to delete job: missing job id.")
            else:
                job = get_object_or_404(job_qs, job_id=job_id)
                title = job.title
                job.delete()
                messages.success(request, f"Job deleted: {title}.")
            return redirect("dashboard:consultancy_jobs")

        if job_id:
            edit_job = get_object_or_404(job_qs, job_id=job_id)
            job = edit_job
        else:
            job = Job()

        previous_applicants = job.applicants if job.pk else 0
        _apply_job_fields(job, request.POST)
        job.applicants = previous_applicants
        job.description = _inject_consultancy_commission_in_description(job.description, consultancy)
        job.recruiter_name = consultancy.name
        job.recruiter_email = consultancy.email
        job.recruiter_phone = consultancy.phone or consultancy.alt_phone or ""
        if not job.company:
            job.company = consultancy.name
        if not job.posted_date:
            job.posted_date = timezone.localdate()

        lifecycle_status = _normalize_consultancy_job_lifecycle(request.POST.get("lifecycle_status"))
        if post_action == "draft":
            lifecycle_status = "Draft"
        elif post_action == "publish":
            lifecycle_status = "Active"
        job.lifecycle_status = lifecycle_status
        job.status = _legacy_status_for_lifecycle(lifecycle_status)
        job.save()

        if not job.job_id:
            job.job_id = _generate_prefixed_id("JOB", 1001, Job, "job_id")
            job.save(update_fields=["job_id"])

        if post_action == "draft":
            messages.success(request, "Job saved in draft.")
        elif post_action == "publish":
            messages.success(request, "Job published and visible to candidates.")
        elif post_action == "update":
            messages.success(request, "Job updated successfully.")
        else:
            messages.success(request, "Job saved successfully.")
        return redirect("dashboard:consultancy_jobs")

    if action in {"edit", "view"}:
        selected_job_id = (request.GET.get("job_id") or "").strip()
        if selected_job_id:
            edit_job = base_qs.filter(job_id=selected_job_id).first()
        section_title = "Edit Job" if action == "edit" else "View Job"
    elif action == "new":
        section_title = "Post New Job"
    elif filter_status in lifecycle_filters:
        section_title = f"{filter_status.title()} Jobs"
    else:
        section_title = "All Posted Jobs"

    status_counts = {
        "all": base_qs.count(),
        "draft": base_qs.filter(lifecycle_status="Draft").count(),
        "active": base_qs.filter(lifecycle_status="Active").count(),
        "paused": base_qs.filter(lifecycle_status="Paused").count(),
        "closed": base_qs.filter(lifecycle_status="Closed").count(),
        "expired": base_qs.filter(lifecycle_status="Expired").count(),
        "archived": base_qs.filter(lifecycle_status="Archived").count(),
    }
    posted_jobs = []
    for job in jobs_qs:
        lifecycle_status = _consultancy_job_status(job)
        posted_jobs.append(
            {
                "job_id": job.job_id,
                "title": job.title,
                "company": job.company,
                "category": job.category,
                "applicants": getattr(job, "apply_count", 0),
                "posted_date": job.posted_date,
                "status": lifecycle_status,
            }
        )
    total_applications = Application.objects.filter(job__in=base_qs).count()

    return render(
        request,
        "dashboard/consultancy/consultancy_jobs.html",
        {
            "consultancy": consultancy,
            "posted_jobs": posted_jobs,
            "status_counts": status_counts,
            "filter_status": filter_status,
            "section_title": section_title,
            "action": action,
            "edit_job": edit_job,
            "form_mode": (
                "view"
                if action == "view"
                else "edit"
                if action == "edit"
                else "new"
                if action == "new"
                else "list"
            ),
            "assigned_jobs_count": AssignedJob.objects.filter(consultancy=consultancy).count(),
            "total_applications": total_applications,
        },
    )


@consultancy_login_required
def consultancy_job_detail_view(request, job_id):
    consultancy_id = request.session.get("consultancy_id")
    consultancy = Consultancy.objects.filter(id=consultancy_id).first()
    if not consultancy:
        return redirect("dashboard:login")

    assignment = (
        AssignedJob.objects.filter(consultancy=consultancy, job__job_id=job_id)
        .select_related("job")
        .first()
    )
    if not assignment:
        messages.error(request, "Job not assigned to this consultancy.")
        return redirect("dashboard:consultancy_jobs")

    job = assignment.job
    submissions = Application.objects.filter(consultancy=consultancy, job=job).count()
    commission_value = assignment.commission_value or ""
    if assignment.commission_type == "Percentage":
        commission_display = f"{commission_value}%"
    elif assignment.commission_type == "Fixed":
        commission_display = f"INR {commission_value}" if commission_value else "INR 0"
    else:
        commission_display = commission_value or "Milestone based"

    return render(
        request,
        "dashboard/consultancy/consultancy_job_detail.html",
        {
            "consultancy": consultancy,
            "job": job,
            "assignment": assignment,
            "submissions": submissions,
            "commission_display": commission_display,
        },
    )


@consultancy_login_required
def consultancy_assigned_jobs_view(request):
    consultancy_id = request.session.get("consultancy_id")
    consultancy = Consultancy.objects.filter(id=consultancy_id).first()
    if not consultancy:
        return redirect("dashboard:login")

    assigned_qs = AssignedJob.objects.filter(consultancy=consultancy).select_related("job")
    applications_qs = Application.objects.filter(consultancy=consultancy)

    assignment_rows = []
    jobs_with_no_submission = 0
    jobs_with_active_candidates = 0
    for assignment in assigned_qs.order_by("-assigned_date"):
        job = assignment.job
        job_apps = applications_qs.filter(job=job)
        total_submissions = job_apps.count()
        if total_submissions == 0:
            jobs_with_no_submission += 1
        else:
            active_exists = job_apps.exclude(status__in=["Rejected", "Archived", "Offer Issued"]).exists()
            if active_exists:
                jobs_with_active_candidates += 1
        shortlisted_count = job_apps.filter(status="Shortlisted").count()
        interview_count = job_apps.filter(status__in=INTERVIEW_STATUSES).count()
        selected_count = job_apps.filter(status="Selected").count()
        placed_count = job_apps.filter(status="Offer Issued").count()
        assignment_rows.append(
            {
                "job_id": job.job_id,
                "title": job.title,
                "company": job.company,
                "total_submissions": total_submissions,
                "shortlisted": shortlisted_count,
                "interview": interview_count,
                "selected": selected_count,
                "placed": placed_count,
                "status": assignment.status,
            }
        )

    assignment_stats = {
        "total_assigned": assigned_qs.count(),
        "jobs_no_submission": jobs_with_no_submission,
        "jobs_active_candidates": jobs_with_active_candidates,
        "jobs_closed": assigned_qs.filter(status="Closed").count(),
        "total_placements": applications_qs.filter(status__in=SELECTED_STATUSES).count(),
    }

    return render(
        request,
        "dashboard/consultancy/consultancy_assigned_jobs.html",
        {"consultancy": consultancy, "assignment_rows": assignment_rows, "assignment_stats": assignment_stats},
    )


@consultancy_login_required
def consultancy_candidate_pool_view(request):
    consultancy_id = request.session.get("consultancy_id")
    consultancy = Consultancy.objects.filter(id=consultancy_id).first()
    if not consultancy:
        return redirect("dashboard:login")

    if request.method == "POST":
        action = (request.POST.get("action") or "add_candidate").strip()
        if action == "submit_candidate":
            candidate_id = request.POST.get("candidate_id")
            assigned_job_id = request.POST.get("assigned_job_id")
            notes = (request.POST.get("notes") or "").strip()
            candidate = Candidate.objects.filter(id=candidate_id, source_consultancy=consultancy).first()
            assignment = AssignedJob.objects.filter(id=assigned_job_id, consultancy=consultancy).select_related("job").first()
            if not candidate or not assignment:
                messages.error(request, "Select a valid candidate and assigned job.")
            else:
                job = assignment.job
                existing = Application.objects.filter(
                    consultancy=consultancy,
                    candidate_email__iexact=candidate.email,
                    job=job,
                ).exists()
                if existing:
                    messages.info(request, "Candidate already submitted for this job.")
                else:
                      application = Application.objects.create(
                          application_id=_generate_prefixed_id("APP", 1001, Application, "application_id"),
                          candidate_name=candidate.name,
                          candidate_email=candidate.email,
                        candidate_phone=candidate.phone,
                        candidate_location=candidate.location,
                        education=candidate.education,
                        experience=candidate.experience,
                        skills=candidate.skills,
                        expected_salary=candidate.expected_salary,
                        job_title=job.title,
                        company=job.company,
                        status="Applied",
                        applied_date=timezone.localdate(),
                          resume=candidate.resume,
                          notes=notes,
                          job=job,
                          consultancy=consultancy,
                      )
                      Job.objects.filter(pk=job.pk).update(applicants=F("applicants") + 1)
                      company_ref = _get_company_for_job(job)
                      _ensure_message_threads(
                          application,
                          job=job,
                          candidate=candidate,
                          company=company_ref,
                          consultancy=consultancy,
                      )
                      messages.success(request, "Candidate submitted successfully.")
            return redirect("dashboard:consultancy_candidate_pool")

        name = (request.POST.get("candidate_name") or "").strip()
        email = (request.POST.get("candidate_email") or "").strip()
        if not name or not email:
            messages.error(request, "Candidate name and email are required.")
        else:
            candidate = Candidate.objects.filter(email__iexact=email).first()
            if candidate and candidate.source_consultancy and candidate.source_consultancy != consultancy:
                messages.error(request, "Candidate already belongs to another consultancy.")
                return redirect("dashboard:consultancy_candidate_pool")
            if not candidate:
                candidate = Candidate(
                    name=name,
                    email=email,
                    account_type="Candidate",
                    account_status="Active",
                )
            candidate.name = name
            candidate.email = email
            candidate.experience = (request.POST.get("experience") or "").strip()
            candidate.skills = (request.POST.get("skills") or "").strip()
            candidate.expected_salary = (request.POST.get("expected_salary") or "").strip()
            candidate.location = (request.POST.get("location") or "").strip()
            candidate.availability_status = (request.POST.get("status") or "").strip()
            candidate.source_consultancy = consultancy
            if request.FILES.get("resume"):
                candidate.resume = request.FILES["resume"]
            candidate.profile_completion = _calculate_candidate_completion(candidate)
            candidate.save()
            messages.success(request, "Candidate saved to pool.")
        return redirect("dashboard:consultancy_candidate_pool")

    candidates = []
    candidate_qs = Candidate.objects.filter(source_consultancy=consultancy).order_by("-registration_date")
    allowed_statuses = {"Active", "Shortlisted", "Interview", "Placed"}
    for candidate in candidate_qs[:50]:
        pool_status = candidate.availability_status if candidate.availability_status in allowed_statuses else "Active"
        candidates.append(
            {
                "id": candidate.id,
                "name": candidate.name,
                "experience": candidate.experience or "--",
                "skills": candidate.skills or "--",
                "salary": candidate.expected_salary or "--",
                "location": candidate.location or "--",
                "status": pool_status,
            }
        )

    selected_job_id = (request.GET.get("job_id") or "").strip()
    assigned_jobs = AssignedJob.objects.filter(consultancy=consultancy).select_related("job").order_by("-assigned_date")

    return render(
        request,
        "dashboard/consultancy/consultancy_candidate_pool.html",
        {
            "consultancy": consultancy,
            "candidates": candidates,
            "assigned_jobs": assigned_jobs,
            "selected_job_id": selected_job_id,
        },
    )


@consultancy_login_required
def consultancy_applications_view(request):
    consultancy_id = request.session.get("consultancy_id")
    consultancy = Consultancy.objects.filter(id=consultancy_id).first()
    if not consultancy:
        return redirect("dashboard:login")

    job_filter = (request.GET.get("job_id") or request.POST.get("job_id") or "").strip()

    if request.method == "POST":
        action = (request.POST.get("action") or "").strip()
        if action == "update_status":
            application_id = request.POST.get("application_id")
            new_status = request.POST.get("status")
            if application_id and new_status:
                app = Application.objects.filter(
                    application_id=application_id,
                    consultancy=consultancy,
                ).first()
                if app:
                    placement_status = _sync_placement_status(new_status, app.placement_status)
                    Application.objects.filter(pk=app.pk).update(
                        status=new_status,
                        placement_status=placement_status,
                        updated_at=timezone.now(),
                    )
                messages.success(request, "Application status updated.")
        if job_filter:
            return redirect(f"{request.path}?job_id={job_filter}")
        return redirect("dashboard:consultancy_applications")

    applications = []
    apps_qs = Application.objects.filter(consultancy=consultancy).order_by("-applied_date", "-created_at")
    if job_filter:
        job = Job.objects.filter(job_id=job_filter).first()
        if job:
            apps_qs = apps_qs.filter(job=job)
    for app in apps_qs[:80]:
        applications.append(
            {
                "application_id": app.application_id,
                "candidate": app.candidate_name,
                "job": app.job_title,
                "company": app.company,
                "display_status": _consultancy_application_status(app.status),
                "raw_status": app.status,
            }
        )

    return render(
        request,
        "dashboard/consultancy/consultancy_applications.html",
        {
            "consultancy": consultancy,
            "applications": applications,
            "status_choices": [choice[0] for choice in APPLICATION_STATUS_CHOICES],
            "job_filter": job_filter,
        },
    )


@consultancy_login_required
def consultancy_shortlisted_view(request):
    consultancy_id = request.session.get("consultancy_id")
    consultancy = Consultancy.objects.filter(id=consultancy_id).first()
    if not consultancy:
        return redirect("dashboard:login")

    shortlisted = []
    for app in Application.objects.filter(
        consultancy=consultancy,
        status__in=["Shortlisted", "Interview", "Interview Scheduled"],
    ).order_by("-updated_at")[:60]:
        shortlisted.append(
            {
                "candidate": app.candidate_name,
                "job": app.job_title,
                "company": app.company,
                "stage": _consultancy_application_status(app.status),
            }
        )

    return render(
        request,
        "dashboard/consultancy/consultancy_shortlisted.html",
        {"consultancy": consultancy, "shortlisted": shortlisted},
    )


@consultancy_login_required
def consultancy_interviews_view(request):
    consultancy_id = request.session.get("consultancy_id")
    consultancy = Consultancy.objects.filter(id=consultancy_id).first()
    if not consultancy:
        return redirect("dashboard:login")

    section = (request.GET.get("section") or "upcoming").strip().lower()

    if request.method == "POST":
        action = (request.POST.get("action") or "schedule_interview").strip()
        if action == "schedule_interview":
            candidate_name = (request.POST.get("candidate") or "").strip()
            job_title = (request.POST.get("job_title") or "").strip()
            interview_date = parse_date(request.POST.get("interview_date")) if request.POST.get("interview_date") else None
            interview_time = parse_time(request.POST.get("interview_time")) if request.POST.get("interview_time") else None
            mode = (request.POST.get("mode") or "Online").strip()
            meeting_link = (request.POST.get("meeting_link") or "").strip()
            interviewer = (request.POST.get("interviewer") or "").strip()
            round_name = (request.POST.get("round") or "").strip()
            notes = (request.POST.get("notes") or "").strip()

            if not candidate_name or not job_title:
                messages.error(request, "Candidate name and job title are required.")
            else:
                application = Application.objects.filter(
                    consultancy=consultancy,
                    candidate_name__iexact=candidate_name,
                    job_title__iexact=job_title,
                ).order_by("-updated_at").first()
                company_name = application.company if application else ""
                candidate_email = application.candidate_email if application else ""
                Interview.objects.create(
                    interview_id=_generate_prefixed_id("INT", 1001, Interview, "interview_id"),
                    application=application,
                    candidate_name=candidate_name,
                    candidate_email=candidate_email,
                    job_title=job_title,
                    company=company_name,
                    interview_date=interview_date,
                    interview_time=interview_time,
                    mode=mode or "Online",
                    meeting_link=meeting_link,
                    interviewer=interviewer,
                    round=round_name,
                    notes=notes,
                    status="scheduled",
                )
                if application:
                    Application.objects.filter(pk=application.pk).update(status="Interview Scheduled")
                messages.success(request, "Interview scheduled successfully.")
            return redirect(f"{request.path}?section={section}")

        if action == "update_status":
            interview_id = request.POST.get("interview_id")
            new_status = (request.POST.get("status") or "").strip()
            interview = Interview.objects.filter(id=interview_id, application__consultancy=consultancy).first()
            if interview and new_status:
                Interview.objects.filter(pk=interview.pk).update(status=new_status, updated_at=timezone.now())
                messages.success(request, "Interview status updated.")
            else:
                messages.error(request, "Unable to update interview status.")
            return redirect(f"{request.path}?section={section}")

        if action == "submit_feedback":
            interview_id = request.POST.get("interview_id")
            interview = Interview.objects.filter(id=interview_id, application__consultancy=consultancy).first()
            if not interview:
                messages.error(request, "Select a valid interview for feedback.")
            else:
                rating_value = request.POST.get("rating")
                rating = int(rating_value) if rating_value and str(rating_value).isdigit() else None
                Interview.objects.filter(pk=interview.pk).update(
                    feedback_rating=rating,
                    technical_skills=(request.POST.get("technical_skills") or "").strip(),
                    communication_skills=(request.POST.get("communication_skills") or "").strip(),
                    strengths=(request.POST.get("strengths") or "").strip(),
                    weakness=(request.POST.get("weakness") or "").strip(),
                    final_decision=(request.POST.get("final_decision") or "").strip(),
                    feedback_submitted_at=timezone.now(),
                    status="completed",
                )
                messages.success(request, "Interview feedback submitted.")
            return redirect(f"{request.path}?section=feedback")

    base_qs = Interview.objects.filter(application__consultancy=consultancy)
    today = timezone.localdate()
    upcoming_qs = base_qs.filter(
        interview_date__gt=today,
        status__in=["scheduled", "rescheduled"],
    )
    today_qs = base_qs.filter(
        interview_date=today,
        status__in=["scheduled", "rescheduled"],
    )
    completed_qs = base_qs.filter(status="completed")
    cancelled_qs = base_qs.filter(status__in=["cancelled", "no_show"])
    feedback_qs = completed_qs.filter(feedback_submitted_at__isnull=True)

    if section == "today":
        list_qs = today_qs
    elif section == "completed":
        list_qs = completed_qs
    elif section == "cancelled":
        list_qs = cancelled_qs
    elif section == "feedback":
        list_qs = feedback_qs
    else:
        section = "upcoming"
        list_qs = upcoming_qs

    interviews = []
    for interview in list_qs.order_by("-interview_date")[:80]:
        interview_date = interview.interview_date.strftime("%d %b %Y") if interview.interview_date else "--"
        interview_time = interview.interview_time.strftime("%I:%M %p") if interview.interview_time else "TBD"
        interviews.append(
            {
                "id": interview.id,
                "candidate": interview.candidate_name,
                "job": interview.job_title,
                "company": interview.company or "--",
                "date": interview_date,
                "time": interview_time,
                "mode": interview.mode,
                "round": interview.round or "--",
                "meeting_link": interview.meeting_link,
                "interviewer": interview.interviewer or "--",
                "status": interview.get_status_display() if hasattr(interview, "get_status_display") else interview.status,
            }
        )

    interview_counts = {
        "upcoming": upcoming_qs.count(),
        "today": today_qs.count(),
        "completed": completed_qs.count(),
        "cancelled": cancelled_qs.count(),
        "feedback": feedback_qs.count(),
    }

    feedback_queue = [
        {
            "id": interview.id,
            "label": f"{interview.candidate_name} - {interview.job_title}",
        }
        for interview in feedback_qs.order_by("-interview_date")[:20]
    ]

    return render(
        request,
        "dashboard/consultancy/consultancy_interviews.html",
        {
            "consultancy": consultancy,
            "interviews": interviews,
            "section": section,
            "interview_counts": interview_counts,
            "feedback_queue": feedback_queue,
        },
    )


@consultancy_login_required
def consultancy_placements_view(request):
    consultancy_id = request.session.get("consultancy_id")
    consultancy = Consultancy.objects.filter(id=consultancy_id).first()
    if not consultancy:
        return redirect("dashboard:login")

    filter_status = (request.GET.get("status") or "active").strip().lower()

    if request.method == "POST":
        action = (request.POST.get("action") or "").strip()
        if action == "update_placement_status":
            application_id = request.POST.get("application_id")
            new_status = (request.POST.get("placement_status") or "").strip()
            if application_id and new_status:
                Application.objects.filter(
                    application_id=application_id,
                    consultancy=consultancy,
                ).update(placement_status=new_status, updated_at=timezone.now())
                messages.success(request, "Placement status updated.")
            else:
                messages.error(request, "Select a valid placement status.")
        elif action == "update_commission_models":
            fixed_fee_raw = (request.POST.get("commission_fixed_fee") or "").strip()
            percentage_raw = (request.POST.get("commission_percentage") or "").strip()
            milestone_notes = (
                request.POST.get("commission_milestone_notes") or "Stage-wise commission release"
            ).strip()

            try:
                fixed_fee = max(0, int(fixed_fee_raw or "25000"))
            except ValueError:
                fixed_fee = 25000
            try:
                percentage = max(0, int(percentage_raw or "10"))
            except ValueError:
                percentage = 10

            consultancy.commission_fixed_fee = fixed_fee
            consultancy.commission_percentage = percentage
            consultancy.commission_milestone_notes = milestone_notes or "Stage-wise commission release"
            consultancy.save(
                update_fields=[
                    "commission_fixed_fee",
                    "commission_percentage",
                    "commission_milestone_notes",
                ]
            )

            # Keep posted job descriptions aligned with the latest commission model settings.
            posted_jobs = _consultancy_posted_jobs_queryset(consultancy)
            for job in posted_jobs:
                updated_description = _inject_consultancy_commission_in_description(job.description, consultancy)
                if job.description != updated_description:
                    job.description = updated_description
                    job.save(update_fields=["description", "updated_at"])

            messages.success(request, "Commission model values updated.")
        return redirect(f"{request.path}?status={filter_status}")

    commission_rate = _consultancy_commission_defaults(consultancy)["fixed_fee"]
    placements = []
    assignment_map = {
        assignment.job_id: assignment
        for assignment in AssignedJob.objects.filter(consultancy=consultancy).select_related("job")
    }
    placements_qs = Application.objects.filter(
        consultancy=consultancy,
        status__in=SELECTED_STATUSES + ["Rejected"],
    ).order_by("-updated_at")

    filtered_apps = []
    for app in placements_qs:
        placement_status = app.placement_status
        if not placement_status:
            if app.status == "Offer Issued":
                placement_status = "Pending Approval"
            elif app.status == "Selected":
                placement_status = "Approved"
            elif app.status == "Rejected":
                placement_status = "Cancelled"
            else:
                placement_status = "Pending Approval"

        if filter_status == "pending" and placement_status != "Pending Approval":
            continue
        if filter_status == "completed" and placement_status != "Paid":
            continue
        if filter_status == "cancelled" and placement_status != "Cancelled":
            continue
        if filter_status == "active" and placement_status not in ["Pending Approval", "Approved"]:
            continue
        filtered_apps.append((app, placement_status))

    for app, placement_status in filtered_apps[:80]:
        salary_value = app.offer_package or app.expected_salary or "--"
        assignment = assignment_map.get(app.job_id) if app.job_id else None
        commission_value = _calculate_commission(assignment, app)
        placements.append(
            {
                "candidate": app.candidate_name,
                "company": app.company,
                "job": app.job_title,
                "salary": salary_value,
                "joining_date": app.joining_date.strftime("%d %b %Y") if app.joining_date else "--",
                "commission": f"INR {commission_value:,}" if commission_value else f"INR {commission_rate:,}",
                "status": placement_status,
                "application_id": app.application_id,
            }
        )

    return render(
        request,
        "dashboard/consultancy/consultancy_placements.html",
        {
            "consultancy": consultancy,
            "placements": placements,
            "filter_status": filter_status,
            "placement_status_choices": [choice[0] for choice in PLACEMENT_STATUS_CHOICES],
            "commission_defaults": _consultancy_commission_defaults(consultancy),
        },
    )


@consultancy_login_required
def consultancy_earnings_view(request):
    consultancy_id = request.session.get("consultancy_id")
    consultancy = Consultancy.objects.filter(id=consultancy_id).first()
    if not consultancy:
        return redirect("dashboard:login")

    commission_rate = _consultancy_commission_defaults(consultancy)["fixed_fee"]
    today = timezone.localdate()
    first_of_month = today.replace(day=1)
    placements = Application.objects.filter(consultancy=consultancy, status__in=SELECTED_STATUSES)
    assignment_map = {
        assignment.job_id: assignment
        for assignment in AssignedJob.objects.filter(consultancy=consultancy).select_related("job")
    }
    monthly_counts = {}
    monthly_amounts = {}
    total_commission = 0
    paid_total = 0
    pending_total = 0
    approved_total = 0
    for app in placements:
        if not app.updated_at:
            continue
        key = app.updated_at.strftime("%b %Y")
        monthly_counts[key] = monthly_counts.get(key, 0) + 1
        assignment = assignment_map.get(app.job_id) if app.job_id else None
        commission_value = _calculate_commission(assignment, app) or commission_rate
        monthly_amounts[key] = monthly_amounts.get(key, 0) + commission_value
        total_commission += commission_value
        placement_status = app.placement_status or "Pending Approval"
        if placement_status == "Paid":
            paid_total += commission_value
        elif placement_status == "Approved":
            approved_total += commission_value
        else:
            pending_total += commission_value

    def shift_month(base_date, months):
        month_index = base_date.month - 1 + months
        year = base_date.year + month_index // 12
        month = month_index % 12 + 1
        return base_date.replace(year=year, month=month, day=1)

    earnings = []
    for offset in range(-5, 1):
        month_date = shift_month(first_of_month, offset)
        label = month_date.strftime("%b %Y")
        count = monthly_counts.get(label, 0)
        amount = monthly_amounts.get(label, 0)
        earnings.append(
            {
                "month": label,
                "placements": count,
                "commission": f"INR {amount:,}",
                "status": "Paid" if month_date < first_of_month else "Pending",
            }
        )

    current_label = first_of_month.strftime("%b %Y")
    summary = {
        "total_commission": total_commission,
        "pending_payments": pending_total,
        "approved_unpaid": approved_total,
        "paid_total": paid_total,
        "paid_this_month": monthly_amounts.get(current_label, 0),
    }

    return render(
        request,
        "dashboard/consultancy/consultancy_earnings.html",
        {"consultancy": consultancy, "earnings": earnings, "summary": summary},
    )


@consultancy_login_required
def consultancy_communication_view(request):
    consultancy_id = request.session.get("consultancy_id")
    consultancy = Consultancy.objects.filter(id=consultancy_id).first()
    if not consultancy:
        return redirect("dashboard:login")

    return render(
        request,
        "dashboard/consultancy/consultancy_communication.html",
        {"consultancy": consultancy},
    )


@consultancy_login_required
def consultancy_messages_view(request):
    consultancy_id = request.session.get("consultancy_id")
    consultancy = Consultancy.objects.filter(id=consultancy_id).first()
    if not consultancy:
        return redirect("dashboard:login")

    threads = (
        MessageThread.objects.filter(consultancy=consultancy)
        .select_related("job", "company", "candidate", "application")
        .order_by("-last_message_at", "-created_at")
    )
    active_thread = None
    thread_id = (request.GET.get("thread") or "").strip()
    if thread_id:
        active_thread = threads.filter(id=thread_id).first()
    if not active_thread and threads:
        active_thread = threads[0]

    if request.method == "POST":
        action = (request.POST.get("action") or "").strip()
        if action == "send_message":
            thread_id = (request.POST.get("thread_id") or "").strip()
            thread = MessageThread.objects.filter(id=thread_id, consultancy=consultancy).first()
            body = (request.POST.get("message_body") or "").strip()
            attachment = request.FILES.get("attachment")
            if not thread:
                messages.error(request, "Select a valid conversation.")
            elif not body and not attachment:
                messages.error(request, "Type a message or attach a file.")
            else:
                Message.objects.create(
                    thread=thread,
                    sender_role="consultancy",
                    sender_name=consultancy.name,
                    body=body,
                    attachment=attachment,
                )
                thread.last_message_at = timezone.now()
                thread.save(update_fields=["last_message_at"])
                return redirect(f"{request.path}?thread={thread.id}")

    thread_messages = []
    if active_thread:
        thread_messages = list(active_thread.messages.order_by("created_at"))
        Message.objects.filter(thread=active_thread, is_read=False).exclude(
            sender_role="consultancy"
        ).update(is_read=True)

    thread_cards = _build_thread_cards(threads, "consultancy")
    active_card = None
    if active_thread:
        active_card = next(
            (card for card in thread_cards if card["thread"].id == active_thread.id),
            None,
        )

    return render(
        request,
        "dashboard/consultancy/consultancy_messages.html",
        {
            "consultancy": consultancy,
            "threads": threads,
            "thread_cards": thread_cards,
            "active_card": active_card,
            "active_thread": active_thread,
            "thread_messages": thread_messages,
            "current_role": "consultancy",
        },
    )


@consultancy_login_required
def consultancy_reports_view(request):
    consultancy_id = request.session.get("consultancy_id")
    consultancy = Consultancy.objects.filter(id=consultancy_id).first()
    if not consultancy:
        return redirect("dashboard:login")

    applications = Application.objects.filter(consultancy=consultancy)
    total_apps = applications.count()
    interview_count = applications.filter(status__in=INTERVIEW_STATUSES).count()
    placements_qs = applications.filter(status__in=SELECTED_STATUSES)
    placements_count = placements_qs.count()
    commission_rate = _consultancy_commission_defaults(consultancy)["fixed_fee"]

    conversion_rate = f"{(placements_count / total_apps * 100):.0f}%" if total_apps else "0%"
    interview_to_selection = (
        f"{(placements_count / interview_count * 100):.0f}%" if interview_count else "0%"
    )

    placements_per_company = list(
        placements_qs.values("company")
        .annotate(count=Count("id"))
        .order_by("-count")[:5]
    )

    today = timezone.localdate()
    first_of_month = today.replace(day=1)
    assignment_map = {
        assignment.job_id: assignment
        for assignment in AssignedJob.objects.filter(consultancy=consultancy).select_related("job")
    }
    monthly_counts = {}
    monthly_amounts = {}
    for app in placements_qs:
        if not app.updated_at:
            continue
        key = app.updated_at.strftime("%b %Y")
        monthly_counts[key] = monthly_counts.get(key, 0) + 1
        assignment = assignment_map.get(app.job_id) if app.job_id else None
        commission_value = _calculate_commission(assignment, app) or commission_rate
        monthly_amounts[key] = monthly_amounts.get(key, 0) + commission_value

    def shift_month(base_date, months):
        month_index = base_date.month - 1 + months
        year = base_date.year + month_index // 12
        month = month_index % 12 + 1
        return base_date.replace(year=year, month=month, day=1)

    monthly_earnings = []
    for offset in range(-5, 1):
        month_date = shift_month(first_of_month, offset)
        label = month_date.strftime("%b %Y")
        count = monthly_counts.get(label, 0)
        amount = monthly_amounts.get(label, 0)
        monthly_earnings.append(
            {
                "month": label,
                "amount": f"{amount:,}",
            }
        )

    reports = {
        "conversion_rate": conversion_rate,
        "interview_to_selection": interview_to_selection,
        "placements_count": placements_count,
        "placements_per_company": placements_per_company,
        "monthly_earnings": monthly_earnings,
    }

    return render(
        request,
        "dashboard/consultancy/consultancy_reports.html",
        {"consultancy": consultancy, "reports": reports},
    )


@consultancy_login_required
def consultancy_profile_settings_view(request):
    consultancy_id = request.session.get("consultancy_id")
    consultancy = Consultancy.objects.filter(id=consultancy_id).first()
    if not consultancy:
        return redirect("dashboard:login")

    if request.method == "POST":
        action = (request.POST.get("action") or "update_profile").strip()
        if action == "upload_kyc":
            files = request.FILES.getlist("kyc_files")
            title = (request.POST.get("document_title") or "").strip()
            doc_type = (request.POST.get("document_type") or "").strip()
            if not files:
                messages.error(request, "Please upload at least one KYC document.")
            else:
                for upload in files:
                    fallback_title = os.path.splitext(upload.name)[0]
                    ConsultancyKycDocument.objects.create(
                        consultancy=consultancy,
                        document_title=title or fallback_title,
                        document_type=doc_type,
                        document_file=upload,
                    )
                messages.success(request, "KYC documents uploaded successfully.")
            return redirect("dashboard:consultancy_profile_settings")
        if action == "delete_kyc":
            doc_id = request.POST.get("doc_id")
            doc = ConsultancyKycDocument.objects.filter(id=doc_id, consultancy=consultancy).first()
            if doc:
                if doc.document_file:
                    doc.document_file.delete(save=False)
                doc.delete()
                messages.success(request, "KYC document removed.")
            else:
                messages.error(request, "Unable to remove that document.")
            return redirect("dashboard:consultancy_profile_settings")
        if action == "upload_photo":
            if request.FILES.get("profile_image"):
                consultancy.profile_image = request.FILES["profile_image"]
                consultancy.save(update_fields=["profile_image"])
                messages.success(request, "Profile photo updated.")
            else:
                messages.error(request, "Please choose an image to upload.")
            return redirect("dashboard:consultancy_profile_settings")
        if action == "remove_photo":
            if consultancy.profile_image:
                consultancy.profile_image.delete(save=False)
                consultancy.profile_image = None
                consultancy.save(update_fields=["profile_image"])
                messages.success(request, "Profile photo removed.")
            return redirect("dashboard:consultancy_profile_settings")

        consultancy.name = (request.POST.get("name") or consultancy.name).strip()
        consultancy.email = (request.POST.get("email") or consultancy.email).strip()
        consultancy.phone = (request.POST.get("phone") or "").strip()
        consultancy.location = (request.POST.get("location") or "").strip()
        consultancy.address = (request.POST.get("address") or "").strip()
        consultancy.contact_position = (request.POST.get("contact_position") or "").strip()
        if request.FILES.get("profile_image"):
            consultancy.profile_image = request.FILES["profile_image"]
        consultancy.save(update_fields=["name", "email", "phone", "location", "address", "contact_position", "profile_image"])
        messages.success(request, "Consultancy profile updated.")
        return redirect("dashboard:consultancy_profile_settings")

    kyc_documents = consultancy.kyc_documents.order_by("-uploaded_at")
    return render(
        request,
        "dashboard/consultancy/consultancy_profile_settings.html",
        {"consultancy": consultancy, "kyc_documents": kyc_documents},
    )


@consultancy_login_required
def consultancy_subscription_view(request):
    consultancy_id = request.session.get("consultancy_id")
    consultancy = Consultancy.objects.filter(id=consultancy_id).first()
    if not consultancy:
        return redirect("dashboard:login")

    return render(
        request,
        "dashboard/consultancy/consultancy_subscription.html",
        {"consultancy": consultancy},
    )


@consultancy_login_required
def consultancy_support_view(request, section="create", ticket_id=None):
    consultancy_id = request.session.get("consultancy_id")
    consultancy = Consultancy.objects.filter(id=consultancy_id).first()
    if not consultancy:
        return redirect("dashboard:login")

    section_map = {
        "create": ("Create Ticket", "Raise a new support ticket for any issue."),
        "my-tickets": ("My Tickets", "Track all support tickets submitted by your consultancy."),
        "open": ("Open Tickets", "Tickets that are open or waiting for response."),
        "closed": ("Closed Tickets", "Resolved and closed support requests."),
        "knowledge": ("Knowledge Base", "Self-help guides and FAQs."),
        "chat": ("Live Chat", "Real-time support chat with our team."),
        "details": ("Ticket Details", "Conversation, attachments, and timeline."),
    }
    page_title, page_subtitle = section_map.get(
        section, ("Customer Support", "Get help from our support team.")
    )

    return render(
        request,
        "dashboard/consultancy/consultancy_support.html",
        {
            "consultancy": consultancy,
            "support_section": section,
            "page_title": page_title,
            "page_subtitle": page_subtitle,
            "ticket_id": ticket_id or "SUP-1023",
        },
    )

def _calculate_candidate_completion(candidate):
    fields = [
        candidate.name,
        candidate.email,
        candidate.phone,
        candidate.location,
        candidate.gender,
        candidate.preferred_job_location,
        candidate.marital_status,
        candidate.nationality,
        candidate.bio,
        candidate.career_objective,
        candidate.skills,
        candidate.secondary_skills,
        candidate.alt_phone,
        candidate.experience_type,
        candidate.employment_type,
        candidate.experience,
        candidate.total_experience,
        candidate.current_job_status,
        candidate.current_company,
        candidate.current_salary,
        candidate.current_position,
        candidate.expected_salary,
        candidate.notice_period,
        candidate.preferred_industry,
        candidate.willing_to_relocate,
        candidate.education,
        candidate.education_10th,
        candidate.education_12th,
        candidate.education_graduation,
        candidate.education_post_graduation,
        candidate.education_other,
        candidate.certifications,
        candidate.languages,
        candidate.linkedin_url,
        candidate.github_url,
        candidate.portfolio_url,
        candidate.resume,
        candidate.profile_image,
    ]
    related_flags = [
        candidate.education_entries.exists(),
        candidate.experience_entries.exists(),
        candidate.skill_entries.exists(),
        candidate.project_entries.exists(),
        candidate.certification_files.exists(),
    ]
    fields.extend(related_flags)
    completed = sum(1 for value in fields if value)
    total = len(fields)
    return round((completed / total) * 100) if total else 0


def _calculate_ai_resume_score(candidate):
    checks = [
        {
            "label": "Basic Profile",
            "weight": 20,
            "complete": bool(candidate.name and candidate.email and candidate.phone),
            "tip": "Add full name, email, and mobile number.",
        },
        {
            "label": "Summary",
            "weight": 15,
            "complete": bool(candidate.bio and candidate.career_objective),
            "tip": "Add short bio and career objective.",
        },
        {
            "label": "Education",
            "weight": 15,
            "complete": bool(candidate.education_entries.exists() or candidate.education or candidate.education_graduation),
            "tip": "Add at least one education record.",
        },
        {
            "label": "Experience",
            "weight": 15,
            "complete": bool(
                candidate.experience_entries.exists()
                or candidate.current_position
                or candidate.total_experience
                or candidate.experience
            ),
            "tip": "Add work experience or current job details.",
        },
        {
            "label": "Skills",
            "weight": 15,
            "complete": bool(candidate.skill_entries.exists() or candidate.skills),
            "tip": "Add primary skills and skill entries.",
        },
        {
            "label": "Resume",
            "weight": 10,
            "complete": bool(candidate.resume or candidate.resumes.exists()),
            "tip": "Upload a resume in Resume Manager.",
        },
        {
            "label": "Professional Links",
            "weight": 5,
            "complete": bool(candidate.linkedin_url or candidate.github_url or candidate.portfolio_url),
            "tip": "Add LinkedIn, GitHub, or portfolio link.",
        },
        {
            "label": "Profile Photo",
            "weight": 5,
            "complete": bool(candidate.profile_image),
            "tip": "Upload profile photo for better recruiter trust.",
        },
    ]

    score = sum(item["weight"] for item in checks if item["complete"])
    missing = [item["tip"] for item in checks if not item["complete"]]
    strengths = [item["label"] for item in checks if item["complete"]]

    if score >= 85:
        band = "Excellent"
    elif score >= 70:
        band = "Good"
    elif score >= 50:
        band = "Average"
    else:
        band = "Needs Improvement"

    return {
        "score": score,
        "band": band,
        "checks": checks,
        "strengths": strengths,
        "missing": missing,
    }


def _build_ai_resume_context(candidate):
    educations = list(candidate.education_entries.all())
    experiences = list(candidate.experience_entries.all())
    skills = list(candidate.skill_entries.all())
    projects = list(candidate.project_entries.all())
    certifications = list(candidate.certification_files.all().order_by("-uploaded_at"))

    tech_skills = [s for s in skills if (s.category or "").lower().startswith("tech")]
    soft_skills = [s for s in skills if (s.category or "").lower().startswith("soft")]
    other_skills = [s for s in skills if s not in tech_skills and s not in soft_skills]

    profile_image_url = ""
    if candidate.profile_image:
        try:
            profile_image_url = candidate.profile_image.url
        except Exception:
            profile_image_url = ""

    return {
        "name": candidate.name or "Candidate Resume",
        "email": candidate.email or "-",
        "phone": candidate.phone or "-",
        "alt_phone": candidate.alt_phone or "-",
        "location": candidate.location or "-",
        "address": candidate.address or "-",
        "date_of_birth": candidate.date_of_birth.strftime("%d %B %Y") if candidate.date_of_birth else "-",
        "gender": candidate.gender or "-",
        "profile_image_url": profile_image_url,
        "summary": candidate.bio or "No summary added.",
        "objective": candidate.career_objective or "Not specified",
        "total_experience": candidate.total_experience or candidate.experience or "Not specified",
        "current_status": candidate.current_job_status or "Not specified",
        "expected_salary": candidate.expected_salary or "Not specified",
        "notice_period": candidate.notice_period or "Not specified",
        "preferred_industry": candidate.preferred_industry or "Not specified",
        "relocate": "Yes" if candidate.willing_to_relocate else "No",
        "education_text": candidate.education or "",
        "education_entries": educations,
        "experience_entries": experiences,
        "skill_entries": skills,
        "tech_skills": tech_skills,
        "soft_skills": soft_skills,
        "other_skills": other_skills,
        "projects": projects,
        "certifications": certifications,
        "languages": candidate.languages or "Not specified",
        "linkedin": candidate.linkedin_url or "-",
        "github": candidate.github_url or "-",
        "portfolio": candidate.portfolio_url or "-",
        "skills_text": candidate.skills or "",
        "secondary_skills": candidate.secondary_skills or "",
    }


def _render_resume_template(template_name, context):
    template_key = (template_name or "showcase").lower()
    templates = {
        "modern": {"accent": "#2563eb", "font": "Poppins, Arial, sans-serif"},
        "corporate": {"accent": "#0f172a", "font": "Inter, Arial, sans-serif"},
        "simple": {"accent": "#475569", "font": "Segoe UI, Arial, sans-serif"},
        "creative": {"accent": "#9333ea", "font": "Poppins, Arial, sans-serif"},
        "showcase": {"accent": "#0c7a52", "font": "Poppins, Arial, sans-serif"},
    }
    if template_key in {"premium", "designer"}:
        template_key = "showcase"
    if template_key not in templates:
        template_key = "showcase"

    def safe(value):
        if value is None:
            return "-"
        text = str(value).strip()
        return escape(text) if text else "-"

    def safe_attr(value):
        if value is None:
            return ""
        text = str(value).strip()
        return escape(text) if text else ""

    def split_values(value):
        if not value:
            return []
        if isinstance(value, str):
            parts = re.split(r"[,;|\n]+", value)
        else:
            parts = list(value)
        return [part.strip() for part in parts if str(part).strip()]

    def render_list(items):
        if not items:
            return "<p>Not specified</p>"
        return "<ul>" + "".join(f"<li>{safe(item)}</li>" for item in items) + "</ul>"

    def render_skills(items):
        if not items:
            return "<p>Not specified</p>"
        return (
            "<ul>"
            + "".join(
                f"<li>{safe(item.name)}"
                + (f" <span class='muted'>({safe(item.level)})</span>" if item.level else "")
                + "</li>"
                for item in items
            )
            + "</ul>"
        )

    def render_education(items):
        if not items:
            return "<p>Not specified</p>"
        return "<ul>" + "".join(
            "<li>"
            f"<strong>{safe(item.qualification)}</strong>"
            f"{' - ' + safe(item.course_name) if item.course_name else ''}"
            f"{' (' + safe(item.specialization) + ')' if item.specialization else ''}"
            f"<div class='muted'>{safe(item.institution)}"
            f"{' | ' + safe(item.passing_year) if item.passing_year else ''}"
            f"{' | ' + safe(item.score) if item.score else ''}"
            "</div>"
            "</li>"
            for item in items
        ) + "</ul>"

    def render_experience(items):
        if not items:
            return "<p>Not specified</p>"
        blocks = []
        for item in items:
            start = item.start_date.strftime("%b %Y") if item.start_date else "-"
            end = "Present" if item.is_current else (item.end_date.strftime("%b %Y") if item.end_date else "-")
            blocks.append(
                "<div class='entry'>"
                f"<strong>{safe(item.company_name)}</strong>"
                f"<div class='muted'>{safe(item.designation)}"
                f"{' | ' + safe(item.industry) if item.industry else ''}"
                f" | {safe(start)} - {safe(end)}</div>"
                f"<div>{safe(item.responsibilities)}</div>"
                f"<div class='muted'>{safe(item.achievements)}</div>"
                "</div>"
            )
        return "".join(blocks)

    def render_projects(items):
        if not items:
            return "<p>Not specified</p>"
        return "<ul>" + "".join(
            "<li>"
            f"<strong>{safe(item.title)}</strong>"
            f"{' - ' + safe(item.technology) if item.technology else ''}"
            f"<div class='muted'>{safe(item.description)}</div>"
            f"<div class='muted'>{safe(item.duration)}</div>"
            "</li>"
            for item in items
        ) + "</ul>"

    def render_certs(items):
        if not items:
            return "<p>Not specified</p>"
        return "<ul>" + "".join(
            "<li>"
            f"<strong>{safe(item.title)}</strong>"
            f"{' - ' + safe(item.issuing_org) if item.issuing_org else ''}"
            f"{' (' + safe(item.year) + ')' if item.year else ''}"
            "</li>"
            for item in items
        ) + "</ul>"

    def render_showcase_education_rows():
        items = context.get("education_entries") or []
        if items:
            rows = []
            for item in items:
                qualification = item.qualification or item.course_name or "Education"
                institute = item.institution or "-"
                year = item.passing_year or "-"
                score = item.score or "-"
                rows.append(
                    f"<tr><td>{safe(qualification)}</td><td>{safe(institute)}</td><td>{safe(year)}</td><td>{safe(score)}</td></tr>"
                )
            return "".join(rows)
        if context.get("education_text"):
            return f"<tr><td>{safe(context.get('education_text'))}</td><td>-</td><td>-</td><td>-</td></tr>"
        return "<tr><td colspan='4'>Add education details in profile to show here.</td></tr>"

    def render_showcase_experience():
        items = context.get("experience_entries") or []
        if items:
            cards = []
            for item in items:
                start = item.start_date.strftime("%b %Y") if item.start_date else "-"
                end = "Present" if item.is_current else (item.end_date.strftime("%b %Y") if item.end_date else "-")
                cards.append(
                    "<div class='xp-card'>"
                    f"<h4>{safe(item.designation or 'Role')}</h4>"
                    f"<p class='xp-company'>{safe(item.company_name or '-')} ({safe(start)} - {safe(end)})</p>"
                    f"<p>{safe(item.responsibilities or item.achievements or 'Responsibilities can be added in profile.')}</p>"
                    "</div>"
                )
            return "".join(cards)
        fallback_role = context.get("current_status") or "Fresher"
        return (
            "<div class='xp-card'>"
            f"<h4>{safe(fallback_role)}</h4>"
            f"<p class='xp-company'>Total Experience: {safe(context.get('total_experience'))}</p>"
            "<p>Add detailed experience entries in profile for richer resume output.</p>"
            "</div>"
        )

    def render_showcase_skills():
        skill_labels = []
        for skill in context.get("skill_entries") or []:
            if skill.name:
                skill_labels.append(skill.name)
        if not skill_labels:
            skill_labels.extend(split_values(context.get("skills_text")))
        if not skill_labels:
            skill_labels.extend(split_values(context.get("secondary_skills")))
        if not skill_labels:
            skill_labels = ["Communication", "Team Work", "Problem Solving", "Adaptability"]
        skill_labels = skill_labels[:6]

        rows = []
        for index, skill in enumerate(skill_labels):
            stars = 5 if index < 3 else 4
            rows.append(
                "<div class='skill-row'>"
                f"<span>{safe(skill)}</span>"
                f"<span class='stars'>{'&#9733;' * stars}{'&#9734;' * (5 - stars)}</span>"
                "</div>"
            )
        return "".join(rows)

    def render_showcase_strengths():
        strengths = []
        for skill in context.get("soft_skills") or []:
            if skill.name:
                strengths.append(skill.name)
        if not strengths:
            strengths.extend(split_values(context.get("secondary_skills")))
        if not strengths:
            strengths = ["Hardworking", "Punctual", "Quick Learner", "Team Player"]
        strengths = strengths[:5]
        return "".join(f"<li>{safe(item)}</li>" for item in strengths)

    def render_showcase_languages():
        labels = split_values(context.get("languages"))
        if not labels or labels == ["Not specified"]:
            labels = ["English"]
        return "".join(f"<span class='chip'>{safe(item)}</span>" for item in labels[:5])

    static_url = getattr(settings, "STATIC_URL", "/static/") or "/static/"
    logo_url = context.get("logo_url") or f"{static_url.rstrip('/')}/dashboard/img/je-logo.svg"
    if not str(logo_url).startswith(("http://", "https://", "/")):
        logo_url = "/" + str(logo_url).lstrip("/")

    profile_image_url = context.get("profile_image_url") or ""
    initials = "".join(part[0] for part in (context.get("name") or "C").split()[:2]).upper() or "C"
    photo_html = (
        f"<img src='{safe_attr(profile_image_url)}' alt='Profile Photo' />"
        if profile_image_url
        else f"<div class='avatar-fallback'>{safe(initials)}</div>"
    )
    watermark_logo_html = f"<img class='watermark-logo' src='{safe_attr(logo_url)}' alt='Job Exhibition Logo' />"

    if template_key == "showcase":
        return f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{safe(context['name'])} Resume</title>
  <style>
    :root {{
      --green: #0b7a53;
      --dark: #13233d;
      --gold: #f3b200;
      --ink: #1f2937;
      --line: #d6dce5;
    }}
    * {{ box-sizing: border-box; }}
    @page {{
      size: A4;
      margin: 0;
    }}
    body {{
      margin: 0;
      font-family: 'Poppins', Arial, sans-serif;
      color: var(--ink);
      background: radial-gradient(circle at 10% 10%, #edf5ef 0%, #f8fafc 45%, #e9eef7 100%);
      padding: 20px;
    }}
    .resume {{
      width: 210mm;
      max-width: 100%;
      min-height: 297mm;
      margin: 0 auto;
      background: #ffffff;
      border-radius: 20px;
      border: 2px solid #e5e7eb;
      overflow: hidden;
      box-shadow: 0 20px 40px rgba(15, 23, 42, 0.12);
      position: relative;
      isolation: isolate;
    }}
    .resume::before {{
      content: 'Job Exhibition';
      position: absolute;
      inset: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 84px;
      font-weight: 800;
      letter-spacing: 1px;
      color: rgba(12, 122, 82, 0.06);
      transform: rotate(-21deg);
      pointer-events: none;
      z-index: -1;
    }}
    .watermark-logo {{
      position: absolute;
      top: 14px;
      right: 16px;
      width: 78px;
      opacity: 0.05;
      pointer-events: none;
    }}
    .hero {{
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 18px;
      padding: 18px 20px 14px;
      background: linear-gradient(130deg, #f8fafc 0%, #eef4fb 55%, #deefe7 100%);
      border-bottom: 3px solid var(--green);
      position: relative;
    }}
    .logo-line {{
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 8px;
    }}
    .logo-dot {{
      width: 36px;
      height: 36px;
      border-radius: 10px;
      background: #ffffff;
      border: 1px solid #d6e7de;
      display: flex;
      align-items: center;
      justify-content: center;
      overflow: hidden;
      box-shadow: 0 6px 15px rgba(12, 122, 82, 0.18);
    }}
    .logo-dot img {{ width: 24px; height: 24px; }}
    .logo-text strong {{ display: block; color: #0f172a; letter-spacing: 0.5px; }}
    .logo-text span {{ color: #64748b; font-size: 12px; }}
    .name-title h1 {{
      margin: 0;
      font-size: 44px;
      line-height: 1;
      letter-spacing: 1px;
      color: var(--dark);
      text-transform: uppercase;
      padding-right: 130px;
    }}
    .name-title .summary-tag {{
      display: inline-block;
      margin-top: 8px;
      padding: 6px 14px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 700;
      color: #0f172a;
      background: linear-gradient(90deg, var(--gold), #ffd871);
    }}
    .contact-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(220px, 1fr));
      gap: 6px 12px;
      margin-top: 10px;
      font-size: 13px;
      color: #0f172a;
    }}
    .contact-grid strong {{ color: var(--green); }}
    .hero-photo {{
      position: relative;
      width: 98px;
      height: 112px;
      border-radius: 14px;
      border: 3px solid #ffffff;
      overflow: hidden;
      background: linear-gradient(145deg, #dbeafe, #d1fae5);
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 12px 24px rgba(2, 132, 199, 0.2);
      align-self: start;
    }}
    .hero-photo img {{ width: 100%; height: 100%; object-fit: cover; display: block; }}
    .avatar-fallback {{
      width: 66px;
      height: 66px;
      border-radius: 50%;
      background: linear-gradient(145deg, var(--green), #22c55e);
      color: #fff;
      font-size: 24px;
      font-weight: 800;
      display: flex;
      align-items: center;
      justify-content: center;
    }}
    .section-wrap {{ padding: 16px 20px 18px; }}
    .dual {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 14px;
      margin-bottom: 14px;
    }}
    .panel {{
      border: 1px solid var(--line);
      border-radius: 14px;
      overflow: hidden;
      background: #fff;
    }}
    .panel h3 {{
      margin: 0;
      padding: 10px 12px;
      color: #fff;
      font-size: 16px;
      background: linear-gradient(90deg, var(--green), #0f766e);
      letter-spacing: 0.2px;
    }}
    .panel-body {{ padding: 12px; font-size: 14px; }}
    .personal-grid {{ display: grid; grid-template-columns: 140px 1fr; gap: 6px 10px; }}
    .personal-grid span:nth-child(odd) {{ color: #64748b; font-weight: 600; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
    th, td {{ border: 1px solid #e5e7eb; padding: 7px 8px; text-align: left; }}
    th {{ background: #f8fafc; color: #0f172a; }}
    .skill-row {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 1px dashed #d1d5db;
      padding: 7px 0;
      font-size: 14px;
    }}
    .skill-row:last-child {{ border-bottom: none; }}
    .stars {{ color: #f59e0b; letter-spacing: 1px; font-size: 13px; }}
    .xp-card {{
      border: 1px dashed #cbd5e1;
      border-radius: 12px;
      padding: 10px;
      margin-bottom: 10px;
      background: #f8fafc;
    }}
    .xp-card h4 {{ margin: 0 0 4px; font-size: 16px; color: #0f172a; }}
    .xp-company {{ margin: 0 0 5px; color: var(--green); font-weight: 700; }}
    .strengths {{ margin: 0; padding-left: 20px; display: grid; gap: 6px; }}
    .languages {{ display: flex; flex-wrap: wrap; gap: 8px; }}
    .chip {{
      display: inline-flex;
      align-items: center;
      padding: 6px 10px;
      border-radius: 999px;
      background: #ecfeff;
      border: 1px solid #a5f3fc;
      color: #0c4a6e;
      font-size: 12px;
      font-weight: 700;
    }}
    .declaration {{
      margin-top: 14px;
      border-top: 2px solid #e5e7eb;
      padding-top: 10px;
      font-size: 14px;
    }}
    .sign {{ margin-top: 12px; text-align: right; font-weight: 700; font-size: 18px; color: var(--dark); }}
    .bottom-bar {{
      margin-top: 16px;
      padding: 10px 14px;
      color: #fff;
      font-size: 13px;
      background: linear-gradient(90deg, #0b7a53, #13233d);
      display: flex;
      flex-wrap: wrap;
      gap: 14px;
    }}
    @media (max-width: 900px) {{
      .hero {{ grid-template-columns: 1fr; }}
      .dual {{ grid-template-columns: 1fr; }}
      .contact-grid {{ grid-template-columns: 1fr; }}
      .name-title h1 {{ font-size: 34px; padding-right: 0; }}
      .hero-photo {{ width: 92px; height: 108px; }}
    }}
    @media print {{
      body {{
        background: #ffffff;
        padding: 0;
      }}
      .resume {{
        width: 210mm;
        min-height: 297mm;
        margin: 0;
        border-radius: 0;
        box-shadow: none;
      }}
    }}
  </style>
</head>
<body>
  <div class="resume">
    {watermark_logo_html}
    <header class="hero">
      <div>
        <div class="logo-line">
          <div class="logo-dot"><img src="{safe_attr(logo_url)}" alt="Job Exhibition Logo" /></div>
          <div class="logo-text">
            <strong>Job Exhibition</strong>
            <span>AI Resume Builder</span>
          </div>
        </div>
        <div class="name-title">
          <h1>{safe(context['name'])}</h1>
          <span class="summary-tag">PROFESSIONAL SUMMARY</span>
        </div>
        <div class="contact-grid">
          <div><strong>Mobile:</strong> {safe(context['phone'])}</div>
          <div><strong>Date of Birth:</strong> {safe(context['date_of_birth'])}</div>
          <div><strong>Email:</strong> {safe(context['email'])}</div>
          <div><strong>LinkedIn:</strong> {safe(context['linkedin'])}</div>
          <div><strong>Location:</strong> {safe(context['location'])}</div>
          <div><strong>Website:</strong> {safe(context['portfolio'])}</div>
        </div>
      </div>
      <div class="hero-photo">{photo_html}</div>
    </header>

    <div class="section-wrap">
      <div class="dual">
        <section class="panel">
          <h3>PERSONAL DETAILS</h3>
          <div class="panel-body personal-grid">
            <span>Full Name</span><span>{safe(context['name'])}</span>
            <span>Date of Birth</span><span>{safe(context['date_of_birth'])}</span>
            <span>Gender</span><span>{safe(context['gender'])}</span>
            <span>Address</span><span>{safe(context['address'])}</span>
            <span>Phone</span><span>{safe(context['phone'])}</span>
            <span>Email</span><span>{safe(context['email'])}</span>
          </div>
        </section>
        <section class="panel">
          <h3>CAREER OBJECTIVE</h3>
          <div class="panel-body">
            <p>{safe(context['objective'])}</p>
          </div>
        </section>
      </div>

      <section class="panel" style="margin-bottom: 14px;">
        <h3>EDUCATION QUALIFICATION</h3>
        <div class="panel-body" style="padding: 0;">
          <table>
            <thead>
              <tr><th>Qualification</th><th>Board/University</th><th>Year</th><th>Percentage / CGPA</th></tr>
            </thead>
            <tbody>
              {render_showcase_education_rows()}
            </tbody>
          </table>
        </div>
      </section>

      <div class="dual">
        <section class="panel">
          <h3>SKILLS</h3>
          <div class="panel-body">{render_showcase_skills()}</div>
        </section>
        <section class="panel">
          <h3>EXPERIENCE</h3>
          <div class="panel-body">{render_showcase_experience()}</div>
        </section>
      </div>

      <div class="dual">
        <section class="panel">
          <h3>STRENGTHS</h3>
          <div class="panel-body"><ul class="strengths">{render_showcase_strengths()}</ul></div>
        </section>
        <section class="panel">
          <h3>LANGUAGE</h3>
          <div class="panel-body"><div class="languages">{render_showcase_languages()}</div></div>
        </section>
      </div>

      <section class="declaration">
        <strong>DECLARATION</strong>
        <p>I hereby declare that all the above information is true to the best of my knowledge.</p>
        <div class="sign">{safe(context['name'])}</div>
      </section>

      <div class="bottom-bar">
        <span>{safe(context['phone'])}</span>
        <span>{safe(context['email'])}</span>
        <span>{safe(context['portfolio'])}</span>
      </div>
    </div>
  </div>
</body>
</html>
"""

    other_skills_html = (
        render_skills(context["other_skills"])
        if context.get("other_skills")
        else render_list([context["skills_fallback"]] if context.get("skills_fallback") else [])
    )
    skill_labels = split_values(context.get("skills_fallback"))
    if not skill_labels:
        skill_labels = split_values(context.get("skills_text"))
    if not skill_labels:
        skill_labels = split_values(context.get("secondary_skills"))
    if not skill_labels:
        skill_labels = ["Communication", "Teamwork", "Problem Solving", "Adaptability"]
    skill_chip_html = "".join(f"<span class='chip'>{safe(item)}</span>" for item in skill_labels[:10])

    if template_key == "modern":
        return f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{safe(context['name'])} Resume</title>
  <style>
    * {{ box-sizing: border-box; }}
    @page {{
      size: A4;
      margin: 0;
    }}
    body {{
      font-family: 'Poppins', Arial, sans-serif;
      color: #1f2937;
      margin: 0;
      padding: 10mm;
      background: linear-gradient(140deg, #dbeafe, #f1f5f9);
    }}
    .resume {{
      width: 210mm;
      max-width: 100%;
      min-height: 297mm;
      margin: 0 auto;
      background: #ffffff;
      border-radius: 18px;
      overflow: hidden;
      box-shadow: 0 18px 38px rgba(37, 99, 235, 0.2);
      display: grid;
      grid-template-columns: 280px 1fr;
      position: relative;
      isolation: isolate;
    }}
    .resume::before {{
      content: 'Job Exhibition';
      position: absolute;
      inset: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 88px;
      color: rgba(30, 64, 175, 0.06);
      font-weight: 800;
      transform: rotate(-20deg);
      pointer-events: none;
      z-index: -1;
    }}
    .watermark-logo {{
      position: absolute;
      top: 12px;
      right: 14px;
      width: 74px;
      opacity: 0.08;
      pointer-events: none;
    }}
    .side {{
      background: linear-gradient(180deg, #1d4ed8, #1e3a8a);
      color: #e2e8f0;
      padding: 18px 16px;
    }}
    .side .profile-photo {{
      width: 86px;
      height: 96px;
      border-radius: 14px;
      border: 3px solid rgba(255,255,255,0.8);
      overflow: hidden;
      margin-bottom: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
    }}
    .side .profile-photo img {{ width: 100%; height: 100%; object-fit: cover; display: block; }}
    .avatar-fallback {{
      width: 58px;
      height: 58px;
      border-radius: 50%;
      background: rgba(255,255,255,0.25);
      color: #ffffff;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 800;
    }}
    .side h1 {{ margin: 0; font-size: 24px; line-height: 1.2; }}
    .side p {{ margin: 7px 0; font-size: 13px; }}
    .content {{ padding: 18px 20px; }}
    .headline {{
      border-left: 4px solid #2563eb;
      background: #eff6ff;
      padding: 10px 12px;
      border-radius: 10px;
      margin-bottom: 12px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
    }}
    .card {{
      border: 1px solid #dbeafe;
      border-radius: 12px;
      padding: 12px;
      background: #ffffff;
      margin-bottom: 12px;
    }}
    .card h2 {{ margin: 0 0 8px; font-size: 15px; color: #1d4ed8; }}
    .entry {{ border-top: 1px dashed #cbd5e1; padding-top: 8px; margin-top: 8px; }}
    .entry:first-child {{ border-top: 0; padding-top: 0; margin-top: 0; }}
    .chip {{
      display: inline-flex;
      align-items: center;
      padding: 5px 9px;
      border-radius: 999px;
      border: 1px solid #bfdbfe;
      background: #eff6ff;
      color: #1d4ed8;
      font-size: 12px;
      margin: 4px 4px 0 0;
    }}
    .muted {{ color: #64748b; font-size: 12px; }}
    ul {{ margin: 0; padding-left: 18px; }}
    li {{ margin-bottom: 6px; }}
    @media (max-width: 900px) {{
      .resume {{ grid-template-columns: 1fr; }}
      .grid {{ grid-template-columns: 1fr; }}
    }}
    @media print {{
      body {{
        background: #ffffff;
        padding: 0;
      }}
      .resume {{
        width: 210mm;
        min-height: 297mm;
        margin: 0;
        border-radius: 0;
        box-shadow: none;
      }}
    }}
  </style>
</head>
<body>
  <div class="resume">
    {watermark_logo_html}
    <aside class="side">
      <div class="profile-photo">{photo_html}</div>
      <h1>{safe(context['name'])}</h1>
      <p>{safe(context['current_status'])}</p>
      <p><strong>Email:</strong> {safe(context['email'])}</p>
      <p><strong>Phone:</strong> {safe(context['phone'])}</p>
      <p><strong>Location:</strong> {safe(context['location'])}</p>
      <p><strong>LinkedIn:</strong> {safe(context['linkedin'])}</p>
      <p><strong>Portfolio:</strong> {safe(context['portfolio'])}</p>
    </aside>
    <main class="content">
      <section class="headline">
        <strong>Professional Summary</strong>
        <p>{safe(context['summary'])}</p>
      </section>
      <div class="grid">
        <section class="card">
          <h2>Career Objective</h2>
          <p>{safe(context['objective'])}</p>
        </section>
        <section class="card">
          <h2>Snapshot</h2>
          <p><strong>Total Experience:</strong> {safe(context['total_experience'])}</p>
          <p><strong>Expected Salary:</strong> {safe(context['expected_salary'])}</p>
          <p><strong>Notice Period:</strong> {safe(context['notice_period'])}</p>
        </section>
      </div>
      <section class="card">
        <h2>Work Experience</h2>
        {render_experience(context['experience_entries'])}
      </section>
      <div class="grid">
        <section class="card">
          <h2>Education</h2>
          {render_education(context['education_entries'])}
        </section>
        <section class="card">
          <h2>Skills</h2>
          <div>{skill_chip_html}</div>
          <div style="margin-top: 8px;">{other_skills_html}</div>
        </section>
      </div>
    </main>
  </div>
</body>
</html>
"""

    if template_key == "corporate":
        return f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{safe(context['name'])} Resume</title>
  <style>
    * {{ box-sizing: border-box; }}
    @page {{
      size: A4;
      margin: 0;
    }}
    body {{
      font-family: 'Inter', Arial, sans-serif;
      color: #0f172a;
      margin: 0;
      padding: 10mm;
      background: #edf2f7;
    }}
    .resume {{
      width: 210mm;
      max-width: 100%;
      min-height: 297mm;
      margin: 0 auto;
      background: #ffffff;
      border: 1px solid #d6deea;
      box-shadow: 0 16px 32px rgba(15, 23, 42, 0.12);
      position: relative;
      isolation: isolate;
      overflow: hidden;
    }}
    .resume::before {{
      content: 'Job Exhibition';
      position: absolute;
      inset: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 86px;
      color: rgba(15, 23, 42, 0.05);
      font-weight: 700;
      transform: rotate(-19deg);
      pointer-events: none;
      z-index: -1;
    }}
    .watermark-logo {{
      position: absolute;
      bottom: 14px;
      right: 14px;
      width: 74px;
      opacity: 0.08;
      pointer-events: none;
    }}
    .top {{
      background: linear-gradient(90deg, #0f172a, #1f2937);
      color: #f8fafc;
      padding: 16px 18px;
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 12px;
      align-items: center;
    }}
    .top h1 {{ margin: 0; font-size: 30px; }}
    .top .profile-photo {{
      width: 82px;
      height: 92px;
      border-radius: 10px;
      border: 2px solid rgba(255,255,255,0.75);
      overflow: hidden;
      display: flex;
      align-items: center;
      justify-content: center;
    }}
    .top .profile-photo img {{ width: 100%; height: 100%; object-fit: cover; display: block; }}
    .avatar-fallback {{
      width: 54px;
      height: 54px;
      border-radius: 50%;
      background: rgba(255,255,255,0.24);
      color: #ffffff;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 800;
    }}
    .content {{ padding: 16px 18px 18px; }}
    .stats {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 10px;
      margin-bottom: 12px;
    }}
    .stat {{
      border: 1px solid #dce4ef;
      border-radius: 8px;
      padding: 8px 10px;
      background: #f8fafc;
      font-size: 13px;
    }}
    .layout {{
      display: grid;
      grid-template-columns: 1.35fr 0.65fr;
      gap: 12px;
    }}
    .card {{
      border: 1px solid #dce4ef;
      border-radius: 10px;
      padding: 10px;
      margin-bottom: 10px;
      background: #ffffff;
    }}
    .card h2 {{
      margin: 0 0 8px;
      font-size: 14px;
      text-transform: uppercase;
      letter-spacing: 0.4px;
      color: #0f172a;
      border-bottom: 1px solid #e2e8f0;
      padding-bottom: 6px;
    }}
    .entry {{ border-top: 1px dashed #d1dae6; padding-top: 8px; margin-top: 8px; }}
    .entry:first-child {{ border-top: 0; padding-top: 0; margin-top: 0; }}
    .muted {{ color: #64748b; font-size: 12px; }}
    ul {{ margin: 0; padding-left: 18px; }}
    li {{ margin-bottom: 6px; }}
    @media (max-width: 900px) {{
      .stats {{ grid-template-columns: 1fr; }}
      .layout {{ grid-template-columns: 1fr; }}
      .top {{ grid-template-columns: 1fr; }}
    }}
    @media print {{
      body {{
        background: #ffffff;
        padding: 0;
      }}
      .resume {{
        width: 210mm;
        min-height: 297mm;
        margin: 0;
        box-shadow: none;
      }}
    }}
  </style>
</head>
<body>
  <div class="resume">
    {watermark_logo_html}
    <header class="top">
      <div>
        <h1>{safe(context['name'])}</h1>
        <div>{safe(context['current_status'])}</div>
      </div>
      <div class="profile-photo">{photo_html}</div>
    </header>
    <div class="content">
      <div class="stats">
        <div class="stat"><strong>Email:</strong> {safe(context['email'])}</div>
        <div class="stat"><strong>Phone:</strong> {safe(context['phone'])}</div>
        <div class="stat"><strong>Location:</strong> {safe(context['location'])}</div>
      </div>
      <div class="layout">
        <div>
          <section class="card">
            <h2>Professional Summary</h2>
            <p>{safe(context['summary'])}</p>
          </section>
          <section class="card">
            <h2>Career Objective</h2>
            <p>{safe(context['objective'])}</p>
          </section>
          <section class="card">
            <h2>Work Experience</h2>
            {render_experience(context['experience_entries'])}
          </section>
          <section class="card">
            <h2>Education</h2>
            {render_education(context['education_entries'])}
          </section>
        </div>
        <aside>
          <section class="card">
            <h2>Skills</h2>
            {other_skills_html}
          </section>
          <section class="card">
            <h2>Certifications</h2>
            {render_certs(context['certifications'])}
          </section>
          <section class="card">
            <h2>Additional Details</h2>
            <p><strong>Preferred Industry:</strong> {safe(context['preferred_industry'])}</p>
            <p><strong>Willing to Relocate:</strong> {safe(context['relocate'])}</p>
            <p><strong>Languages:</strong> {safe(context['languages'])}</p>
            <p><strong>LinkedIn:</strong> {safe(context['linkedin'])}</p>
            <p><strong>GitHub:</strong> {safe(context['github'])}</p>
            <p><strong>Portfolio:</strong> {safe(context['portfolio'])}</p>
          </section>
        </aside>
      </div>
    </div>
  </div>
</body>
</html>
"""

    if template_key == "simple":
        return f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{safe(context['name'])} Resume</title>
  <style>
    * {{ box-sizing: border-box; }}
    @page {{
      size: A4;
      margin: 0;
    }}
    body {{
      font-family: 'Segoe UI', Arial, sans-serif;
      color: #111827;
      margin: 0;
      padding: 10mm;
      background: #f9fafb;
    }}
    .resume {{
      width: 210mm;
      max-width: 100%;
      min-height: 297mm;
      margin: 0 auto;
      background: #ffffff;
      border: 1px solid #e5e7eb;
      padding: 18px 20px;
      position: relative;
      isolation: isolate;
      overflow: hidden;
    }}
    .resume::before {{
      content: 'Job Exhibition';
      position: absolute;
      inset: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 82px;
      color: rgba(71, 85, 105, 0.07);
      font-weight: 700;
      transform: rotate(-18deg);
      pointer-events: none;
      z-index: -1;
    }}
    .watermark-logo {{
      position: absolute;
      top: 12px;
      right: 12px;
      width: 72px;
      opacity: 0.08;
      pointer-events: none;
    }}
    .header {{
      display: grid;
      grid-template-columns: auto 1fr;
      gap: 12px;
      align-items: center;
      border-bottom: 2px solid #334155;
      padding-bottom: 10px;
      margin-bottom: 10px;
    }}
    .profile-photo {{
      width: 70px;
      height: 80px;
      border-radius: 10px;
      border: 1px solid #cbd5e1;
      overflow: hidden;
      display: flex;
      align-items: center;
      justify-content: center;
    }}
    .profile-photo img {{ width: 100%; height: 100%; object-fit: cover; display: block; }}
    .avatar-fallback {{
      width: 44px;
      height: 44px;
      border-radius: 50%;
      background: #64748b;
      color: #ffffff;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 700;
    }}
    h1 {{ margin: 0; font-size: 30px; }}
    h2 {{
      margin: 12px 0 7px;
      font-size: 14px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      border-bottom: 1px solid #dbe2ea;
      padding-bottom: 4px;
    }}
    .muted {{ color: #64748b; font-size: 12px; }}
    .entry {{ border-top: 1px dashed #d1d5db; padding-top: 7px; margin-top: 7px; }}
    .entry:first-child {{ border-top: 0; padding-top: 0; margin-top: 0; }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
    }}
    ul {{ margin: 0; padding-left: 18px; }}
    li {{ margin-bottom: 5px; }}
    @media (max-width: 860px) {{
      .header {{ grid-template-columns: 1fr; }}
      .grid {{ grid-template-columns: 1fr; }}
    }}
    @media print {{
      body {{
        background: #ffffff;
        padding: 0;
      }}
      .resume {{
        width: 210mm;
        min-height: 297mm;
        margin: 0;
        box-shadow: none;
      }}
    }}
  </style>
</head>
<body>
  <div class="resume">
    {watermark_logo_html}
    <header class="header">
      <div class="profile-photo">{photo_html}</div>
      <div>
        <h1>{safe(context['name'])}</h1>
        <div>{safe(context['email'])} | {safe(context['phone'])} | {safe(context['location'])}</div>
      </div>
    </header>
    <h2>Professional Summary</h2>
    <p>{safe(context['summary'])}</p>
    <h2>Career Objective</h2>
    <p>{safe(context['objective'])}</p>
    <div class="grid">
      <section>
        <h2>Experience</h2>
        {render_experience(context['experience_entries'])}
      </section>
      <section>
        <h2>Education</h2>
        {render_education(context['education_entries'])}
      </section>
    </div>
    <div class="grid">
      <section>
        <h2>Skills</h2>
        {other_skills_html}
      </section>
      <section>
        <h2>Projects</h2>
        {render_projects(context['projects'])}
      </section>
    </div>
  </div>
</body>
</html>
"""

    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{safe(context['name'])} Resume</title>
  <style>
    * {{ box-sizing: border-box; }}
    @page {{
      size: A4;
      margin: 0;
    }}
    body {{
      font-family: 'Poppins', Arial, sans-serif;
      color: #1f2937;
      margin: 0;
      padding: 10mm;
      background: radial-gradient(circle at 10% 8%, #fff1f2, #faf5ff 45%, #eef2ff 100%);
    }}
    .resume {{
      width: 210mm;
      max-width: 100%;
      min-height: 297mm;
      margin: 0 auto;
      background: #ffffff;
      border-radius: 20px;
      border: 1px solid #e9d5ff;
      overflow: hidden;
      box-shadow: 0 18px 36px rgba(124, 58, 237, 0.15);
      position: relative;
      isolation: isolate;
    }}
    .resume::before {{
      content: 'Job Exhibition';
      position: absolute;
      inset: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 90px;
      color: rgba(147, 51, 234, 0.06);
      font-weight: 800;
      transform: rotate(-19deg);
      pointer-events: none;
      z-index: -1;
    }}
    .watermark-logo {{
      position: absolute;
      top: 12px;
      right: 14px;
      width: 74px;
      opacity: 0.08;
      pointer-events: none;
    }}
    .hero {{
      background: linear-gradient(120deg, #7c3aed, #ec4899 65%, #f59e0b);
      color: #ffffff;
      padding: 16px 18px;
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 12px;
      align-items: center;
    }}
    .hero h1 {{ margin: 0; font-size: 32px; text-transform: uppercase; }}
    .hero p {{ margin: 6px 0 0; font-size: 13px; color: rgba(255,255,255,0.9); }}
    .hero .profile-photo {{
      width: 84px;
      height: 84px;
      border-radius: 50%;
      border: 4px solid rgba(255,255,255,0.85);
      overflow: hidden;
      display: flex;
      align-items: center;
      justify-content: center;
    }}
    .hero .profile-photo img {{ width: 100%; height: 100%; object-fit: cover; display: block; }}
    .avatar-fallback {{
      width: 56px;
      height: 56px;
      border-radius: 50%;
      background: rgba(255,255,255,0.3);
      color: #ffffff;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 800;
    }}
    .content {{ padding: 16px 18px 18px; }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
    }}
    .card {{
      border: 1px solid #e9d5ff;
      border-radius: 12px;
      padding: 12px;
      margin-bottom: 12px;
      background: #ffffff;
    }}
    .card h2 {{ margin: 0 0 8px; font-size: 14px; color: #7c3aed; text-transform: uppercase; }}
    .chip {{
      display: inline-flex;
      align-items: center;
      padding: 6px 10px;
      border-radius: 999px;
      border: 1px solid #d8b4fe;
      background: #faf5ff;
      color: #6d28d9;
      font-size: 12px;
      margin: 4px 4px 0 0;
    }}
    .entry {{ border-top: 1px dashed #ddd6fe; padding-top: 8px; margin-top: 8px; }}
    .entry:first-child {{ border-top: 0; padding-top: 0; margin-top: 0; }}
    .muted {{ color: #6b7280; font-size: 12px; }}
    ul {{ margin: 0; padding-left: 18px; }}
    li {{ margin-bottom: 6px; }}
    @media (max-width: 900px) {{
      .hero {{ grid-template-columns: 1fr; }}
      .grid {{ grid-template-columns: 1fr; }}
    }}
    @media print {{
      body {{
        background: #ffffff;
        padding: 0;
      }}
      .resume {{
        width: 210mm;
        min-height: 297mm;
        margin: 0;
        border-radius: 0;
        box-shadow: none;
      }}
    }}
  </style>
</head>
<body>
  <div class="resume">
    {watermark_logo_html}
    <header class="hero">
      <div>
        <h1>{safe(context['name'])}</h1>
        <p>{safe(context['current_status'])} | Experience: {safe(context['total_experience'])}</p>
      </div>
      <div class="profile-photo">{photo_html}</div>
    </header>
    <div class="content">
      <section class="card">
        <h2>Professional Summary</h2>
        <p>{safe(context['summary'])}</p>
      </section>
      <div class="grid">
        <section class="card">
          <h2>Career Objective</h2>
          <p>{safe(context['objective'])}</p>
          <h2 style="margin-top: 12px;">Top Skills</h2>
          <div>{skill_chip_html}</div>
        </section>
        <section class="card">
          <h2>Education</h2>
          {render_education(context['education_entries'])}
        </section>
      </div>
      <div class="grid">
        <section class="card">
          <h2>Experience</h2>
          {render_experience(context['experience_entries'])}
        </section>
        <section class="card">
          <h2>Projects & Certifications</h2>
          {render_projects(context['projects'])}
          <div style="margin-top: 10px;">{render_certs(context['certifications'])}</div>
        </section>
      </div>
    </div>
  </div>
</body>
</html>
"""


def _build_ai_resume_text(candidate, template_name="showcase"):
    context = _build_ai_resume_context(candidate)
    if not context["tech_skills"] and not context["soft_skills"] and (candidate.skills or candidate.secondary_skills):
        fallback_values = [value for value in [candidate.skills, candidate.secondary_skills] if value]
        context["skills_fallback"] = ", ".join(fallback_values)
    else:
        context["skills_fallback"] = ""
    return _render_resume_template(template_name, context)


def _get_or_create_ai_resume(candidate, template_name="showcase"):
    existing = CandidateResume.objects.filter(
        candidate=candidate, title__iexact="Job Exhibition Resume"
    ).order_by("-created_at").first()
    content = _build_ai_resume_text(candidate, template_name)
    filename = f"job-exhibition-resume-{candidate.id}.html"

    if existing:
        existing.template_name = template_name
        existing.resume_file.save(filename, ContentFile(content.encode("utf-8")), save=True)
        existing.save(update_fields=["template_name"])
        return existing

    resume = CandidateResume(candidate=candidate, title="Job Exhibition Resume", template_name=template_name, is_default=False)
    resume.resume_file.save(filename, ContentFile(content.encode("utf-8")), save=True)
    return resume


@candidate_login_required
def candidate_dashboard_view(request):
    candidate_id = request.session.get("candidate_id")
    candidate = Candidate.objects.filter(id=candidate_id).first()
    if not candidate:
        request.session.pop("candidate_id", None)
        request.session.pop("candidate_name", None)
        return redirect("dashboard:login")

    applications = Application.objects.filter(candidate_email__iexact=candidate.email)
    shortlisted = applications.filter(status="Shortlisted").count()
    interviews = Interview.objects.filter(
        candidate_email__iexact=candidate.email,
        status__in=["scheduled", "rescheduled"],
    ).count()
    saved_jobs = 0
    recommended_jobs = list(Job.objects.filter(status="Approved").order_by("-created_at")[:6])

    metrics = {
        "profile_completion": candidate.profile_completion,
        "total_applications": applications.count(),
        "shortlisted": shortlisted,
        "interviews": interviews,
        "saved_jobs": saved_jobs,
        "recommended_jobs": len(recommended_jobs),
    }
    metric_cards = [
        {
            "label": "Total Applications",
            "value": metrics["total_applications"],
            "sub": "All submitted",
            "metric_id": "metricTotalApplications",
            "metric_key": "total_applications",
        },
        {
            "label": "Shortlisted",
            "value": metrics["shortlisted"],
            "sub": "In progress",
            "metric_id": "metricShortlisted",
            "metric_key": "shortlisted",
        },
        {
            "label": "Interviews Scheduled",
            "value": metrics["interviews"],
            "sub": "Upcoming",
            "metric_id": "metricInterviews",
            "metric_key": "interviews",
        },
        {
            "label": "Saved Jobs",
            "value": metrics["saved_jobs"],
            "sub": "To apply later",
            "metric_id": "metricSavedJobs",
            "metric_key": "saved_jobs",
        },
        {
            "label": "Recommended Jobs",
            "value": metrics["recommended_jobs"],
            "sub": "Matched roles",
            "metric_id": "metricRecommendedJobs",
            "metric_key": "recommended_jobs",
        },
    ]
    metrics_max = max([item["value"] for item in metric_cards] + [1])
    for item in metric_cards:
        item["width"] = max(8, round((item["value"] / metrics_max) * 100)) if metrics_max else 8

    ad_segment = _resolve_subscription_segment_for_account(
        "Candidate",
        candidate.email,
    )

    context = {
        "candidate": candidate,
        "metrics": metrics,
        "metric_cards": metric_cards,
        "recommended_jobs": recommended_jobs,
        "applications": applications[:5],
        "advertisement": _active_advertisement_for("candidate", ad_segment),
    }
    return render(request, "dashboard/candidate/candidate_dashboard.html", context)


@candidate_login_required
def candidate_profile_view(request):
    candidate_id = request.session.get("candidate_id")
    candidate = Candidate.objects.filter(id=candidate_id).first()
    if not candidate:
        return redirect("dashboard:login")

    if request.method == "POST":
        action = (request.POST.get("action") or "").strip()
        if action == "update_profile":
            name = (request.POST.get("name") or "").strip()
            email = (request.POST.get("email") or "").strip()
            if not name or not email:
                messages.error(request, "Name and email are required.")
            else:
                candidate.name = name
                candidate.email = email
                candidate.phone = (request.POST.get("phone") or "").strip()
                candidate.alt_phone = (request.POST.get("alt_phone") or "").strip()
                candidate.date_of_birth = parse_date(request.POST.get("date_of_birth")) if request.POST.get("date_of_birth") else None
                candidate.gender = (request.POST.get("gender") or "").strip()
                candidate.preferred_job_location = (request.POST.get("preferred_job_location") or "").strip()
                candidate.marital_status = (request.POST.get("marital_status") or "").strip()
                candidate.nationality = (request.POST.get("nationality") or "").strip()
                candidate.location = (request.POST.get("location") or "").strip()
                if "address" in request.POST:
                    candidate.address = (request.POST.get("address") or "").strip()
                candidate.bio = (request.POST.get("bio") or "").strip()
                candidate.career_objective = (request.POST.get("career_objective") or "").strip()
                candidate.skills = (request.POST.get("skills") or "").strip()
                if "secondary_skills" in request.POST:
                    candidate.secondary_skills = (request.POST.get("secondary_skills") or "").strip()
                candidate.experience_type = (request.POST.get("experience_type") or "").strip()
                if "employment_type" in request.POST:
                    candidate.employment_type = (request.POST.get("employment_type") or "").strip()
                candidate.experience = (request.POST.get("experience") or "").strip()
                candidate.total_experience = (request.POST.get("total_experience") or "").strip()
                candidate.current_job_status = (request.POST.get("current_job_status") or "").strip()
                candidate.current_company = (request.POST.get("current_company") or "").strip()
                candidate.current_salary = (request.POST.get("current_salary") or "").strip()
                candidate.current_position = (request.POST.get("current_position") or "").strip()
                candidate.expected_salary = (request.POST.get("expected_salary") or "").strip()
                candidate.notice_period = (request.POST.get("notice_period") or "").strip()
                candidate.preferred_industry = (request.POST.get("preferred_industry") or "").strip()
                candidate.willing_to_relocate = (request.POST.get("willing_to_relocate") or "").strip().lower() in {"yes", "true", "on"}
                if "education_10th" in request.POST:
                    candidate.education_10th = (request.POST.get("education_10th") or "").strip()
                if "education_12th" in request.POST:
                    candidate.education_12th = (request.POST.get("education_12th") or "").strip()
                if "education_graduation" in request.POST:
                    candidate.education_graduation = (request.POST.get("education_graduation") or "").strip()
                if "education_post_graduation" in request.POST:
                    candidate.education_post_graduation = (request.POST.get("education_post_graduation") or "").strip()
                if "education_other" in request.POST:
                    candidate.education_other = (request.POST.get("education_other") or "").strip()
                if "certifications" in request.POST:
                    candidate.certifications = (request.POST.get("certifications") or "").strip()
                candidate.languages = (request.POST.get("languages") or "").strip()
                candidate.linkedin_url = (request.POST.get("linkedin_url") or "").strip()
                candidate.github_url = (request.POST.get("github_url") or "").strip()
                candidate.portfolio_url = (request.POST.get("portfolio_url") or "").strip()
                if "availability_status" in request.POST:
                    candidate.availability_status = (request.POST.get("availability_status") or "").strip()
                candidate.profile_visibility = request.POST.get("profile_visibility") == "on"
                if request.FILES.get("profile_image"):
                    candidate.profile_image = request.FILES["profile_image"]
                if request.FILES.get("portfolio_file"):
                    candidate.portfolio_file = request.FILES["portfolio_file"]
                if request.FILES.get("video_resume"):
                    candidate.video_resume = request.FILES["video_resume"]
                education_rows = list(zip_longest(
                    request.POST.getlist("edu_qualification"),
                    request.POST.getlist("edu_course"),
                    request.POST.getlist("edu_specialization"),
                    request.POST.getlist("edu_institution"),
                    request.POST.getlist("edu_year"),
                    request.POST.getlist("edu_score"),
                    fillvalue="",
                ))
                if any(any(str(cell).strip() for cell in row) for row in education_rows):
                    CandidateEducation.objects.filter(candidate=candidate).delete()
                    education_summary = []
                    for qualification, course, specialization, institution, year, score in education_rows:
                        if not any([qualification, course, specialization, institution, year, score]):
                            continue
                        CandidateEducation.objects.create(
                            candidate=candidate,
                            qualification=qualification.strip(),
                            course_name=course.strip(),
                            specialization=specialization.strip(),
                            institution=institution.strip(),
                            passing_year=year.strip(),
                            score=score.strip(),
                        )
                        summary_parts = [qualification.strip(), course.strip(), institution.strip()]
                        education_summary.append(" - ".join([part for part in summary_parts if part]))
                    if education_summary:
                        candidate.education = "; ".join(education_summary)

                experience_rows = list(zip_longest(
                    request.POST.getlist("exp_company"),
                    request.POST.getlist("exp_designation"),
                    request.POST.getlist("exp_industry"),
                    request.POST.getlist("exp_start"),
                    request.POST.getlist("exp_end"),
                    request.POST.getlist("exp_current"),
                    request.POST.getlist("exp_responsibilities"),
                    request.POST.getlist("exp_achievements"),
                    fillvalue="",
                ))
                if any(any(str(cell).strip() for cell in row) for row in experience_rows):
                    CandidateExperience.objects.filter(candidate=candidate).delete()
                    for company, designation, industry, start, end, current, responsibilities, achievements in experience_rows:
                        if not any([company, designation, industry, start, end, responsibilities, achievements]):
                            continue
                        CandidateExperience.objects.create(
                            candidate=candidate,
                            company_name=company.strip(),
                            designation=designation.strip(),
                            industry=industry.strip(),
                            start_date=parse_date(start.strip()) if start else None,
                            end_date=parse_date(end.strip()) if end else None,
                            is_current=str(current).lower() == "yes",
                            responsibilities=responsibilities.strip(),
                            achievements=achievements.strip(),
                        )

                skill_rows = list(zip_longest(
                    request.POST.getlist("skill_name"),
                    request.POST.getlist("skill_category"),
                    request.POST.getlist("skill_level"),
                    fillvalue="",
                ))
                if any(any(str(cell).strip() for cell in row) for row in skill_rows):
                    CandidateSkill.objects.filter(candidate=candidate).delete()
                    skill_names = []
                    for name_value, category_value, level_value in skill_rows:
                        if not any([name_value, category_value, level_value]):
                            continue
                        CandidateSkill.objects.create(
                            candidate=candidate,
                            name=name_value.strip(),
                            category=category_value.strip(),
                            level=level_value.strip(),
                        )
                        if name_value.strip():
                            skill_names.append(name_value.strip())
                    if not candidate.skills and skill_names:
                        candidate.skills = ", ".join(skill_names)

                project_rows = list(zip_longest(
                    request.POST.getlist("project_title"),
                    request.POST.getlist("project_tech"),
                    request.POST.getlist("project_desc"),
                    request.POST.getlist("project_duration"),
                    fillvalue="",
                ))
                if any(any(str(cell).strip() for cell in row) for row in project_rows):
                    CandidateProject.objects.filter(candidate=candidate).delete()
                    for title, tech, desc, duration in project_rows:
                        if not any([title, tech, desc, duration]):
                            continue
                        CandidateProject.objects.create(
                            candidate=candidate,
                            title=title.strip(),
                            technology=tech.strip(),
                            description=desc.strip(),
                            duration=duration.strip(),
                        )

                cert_rows = list(zip_longest(
                    request.POST.getlist("cert_name"),
                    request.POST.getlist("cert_org"),
                    request.POST.getlist("cert_year"),
                    fillvalue="",
                ))
                cert_files = request.FILES.getlist("cert_file")
                has_cert_data = any(any(str(cell).strip() for cell in row) for row in cert_rows) or cert_files
                if has_cert_data:
                    CandidateCertification.objects.filter(candidate=candidate).delete()
                    for index, (cert_name, cert_org, cert_year) in enumerate(cert_rows):
                        file_obj = cert_files[index] if index < len(cert_files) else None
                        if not any([cert_name, cert_org, cert_year]) and not file_obj:
                            continue
                        CandidateCertification.objects.create(
                            candidate=candidate,
                            title=cert_name.strip(),
                            issuing_org=cert_org.strip(),
                            year=cert_year.strip(),
                            certificate_file=file_obj if file_obj else None,
                        )
                candidate.profile_completion = _calculate_candidate_completion(candidate)
                candidate.save()
                messages.success(request, "Profile updated successfully.")
        return redirect("dashboard:candidate_profile")

    return render(
        request,
        "dashboard/candidate/candidate_profile.html",
        {
            "candidate": candidate,
            "education_entries": candidate.education_entries.all(),
            "experience_entries": candidate.experience_entries.all(),
            "skill_entries": candidate.skill_entries.all(),
            "project_entries": candidate.project_entries.all(),
            "cert_entries": candidate.certification_files.all(),
        },
    )


@candidate_login_required
def candidate_resume_manager_view(request):
    candidate_id = request.session.get("candidate_id")
    candidate = Candidate.objects.filter(id=candidate_id).first()
    if not candidate:
        return redirect("dashboard:login")

    if request.method == "POST":
        action = (request.POST.get("action") or "").strip()
        if action == "upload_resume":
            resume_file = request.FILES.get("resume_file")
            if not resume_file:
                messages.error(request, "Please upload a resume file.")
            else:
                resume_title = (request.POST.get("resume_title") or "").strip()
                is_default = request.POST.get("make_default") == "on"
                resume = CandidateResume.objects.create(
                    candidate=candidate,
                    title=resume_title,
                    resume_file=resume_file,
                    is_default=is_default,
                )
                has_other_default = CandidateResume.objects.filter(candidate=candidate, is_default=True).exclude(id=resume.id).exists()
                if is_default or not has_other_default:
                    CandidateResume.objects.filter(candidate=candidate).exclude(id=resume.id).update(is_default=False)
                    if not resume.is_default:
                        resume.is_default = True
                        resume.save(update_fields=["is_default"])
                    candidate.resume = resume.resume_file
                    candidate.profile_completion = _calculate_candidate_completion(candidate)
                    candidate.save(update_fields=["resume", "profile_completion"])
                messages.success(request, "Resume uploaded successfully.")
        elif action == "generate_ai_resume":
            template_name = (request.POST.get("template_name") or "showcase").strip().lower()
            _get_or_create_ai_resume(candidate, template_name)
            messages.success(request, "Job Exhibition resume generated.")
        elif action == "set_default":
            resume_id = request.POST.get("resume_id")
            resume = CandidateResume.objects.filter(candidate=candidate, id=resume_id).first()
            if resume:
                CandidateResume.objects.filter(candidate=candidate).update(is_default=False)
                resume.is_default = True
                resume.save(update_fields=["is_default"])
                candidate.resume = resume.resume_file
                candidate.save(update_fields=["resume"])
                messages.success(request, "Default resume updated.")
        elif action == "run_ai_score":
            score_data = _calculate_ai_resume_score(candidate)
            messages.info(
                request,
                f"AI Resume Score: {score_data['score']}/100 ({score_data['band']}).",
            )
        return redirect("dashboard:candidate_resume_manager")

    resumes = CandidateResume.objects.filter(candidate=candidate).order_by("-created_at")
    ai_resume = resumes.filter(title__iexact="Job Exhibition Resume").first()
    ai_score_data = _calculate_ai_resume_score(candidate)
    return render(
        request,
        "dashboard/candidate/candidate_resume_manager.html",
        {
            "candidate": candidate,
            "resumes": resumes,
            "ai_resume": ai_resume,
            "ai_template": (ai_resume.template_name if ai_resume else "showcase"),
            "ai_score_data": ai_score_data,
        },
    )


@candidate_login_required
def candidate_job_search_view(request):
    candidate_id = request.session.get("candidate_id")
    candidate = Candidate.objects.filter(id=candidate_id).first()
    if not candidate:
        return redirect("dashboard:login")

    jobs = Job.objects.filter(status="Approved")
    search = (request.GET.get("search") or "").strip()
    location = (request.GET.get("location") or "").strip()
    salary = (request.GET.get("salary") or "").strip()
    experience = (request.GET.get("experience") or "").strip()
    skills = (request.GET.get("skills") or "").strip()
    job_type = (request.GET.get("job_type") or "").strip()
    sort = (request.GET.get("sort") or "latest").strip()

    if search:
        jobs = jobs.filter(Q(title__icontains=search) | Q(company__icontains=search))
    if location:
        jobs = jobs.filter(location__icontains=location)
    if salary:
        jobs = jobs.filter(salary__icontains=salary)
    if experience:
        jobs = jobs.filter(experience__icontains=experience)
    if skills:
        jobs = jobs.filter(skills__icontains=skills)
    if job_type:
        jobs = jobs.filter(job_type__iexact=job_type)

    if sort == "salary_high":
        jobs = jobs.order_by("-salary")
    else:
        jobs = jobs.order_by("-created_at")

    context = {
        "candidate": candidate,
        "jobs": jobs,
        "filters": {
            "search": search,
            "location": location,
            "salary": salary,
            "experience": experience,
            "skills": skills,
            "job_type": job_type,
            "sort": sort,
        },
    }
    return render(request, "dashboard/candidate/candidate_job_search.html", context)


@candidate_login_required
def candidate_job_detail_view(request, job_id):
    candidate_id = request.session.get("candidate_id")
    candidate = Candidate.objects.filter(id=candidate_id).first()
    if not candidate:
        return redirect("dashboard:login")

    latest_completion = _calculate_candidate_completion(candidate)
    if latest_completion != candidate.profile_completion:
        candidate.profile_completion = latest_completion
        candidate.save(update_fields=["profile_completion"])
    can_apply = candidate.profile_completion >= MIN_PROFILE_COMPLETION_TO_APPLY

    job = get_object_or_404(Job, job_id=job_id, status="Approved")
    company = Company.objects.filter(name__iexact=job.company).first()
    similar_jobs = Job.objects.filter(status="Approved", category=job.category).exclude(job_id=job_id)[:4]
    candidate_resumes = list(candidate.resumes.order_by("-created_at"))
    ai_resume = next((resume for resume in candidate_resumes if (resume.title or "").lower() == "job exhibition resume"), None)
    default_resume = next((resume for resume in candidate_resumes if resume.is_default), None)
    application = (
        Application.objects.filter(
            candidate_email__iexact=candidate.email,
            job_title=job.title,
            company=job.company,
        )
        .order_by("-applied_date", "-created_at", "-id")
        .first()
    )
    has_applied = application is not None
    chat_thread_id = None
    if application:
        thread = MessageThread.objects.filter(
            application=application,
            thread_type="candidate_company",
        ).first()
        if thread:
            chat_thread_id = thread.id

    if request.method == "POST":
        action = (request.POST.get("action") or "").strip()
        if action == "apply":
            if not can_apply:
                messages.error(
                    request,
                    f"Please complete at least {MIN_PROFILE_COMPLETION_TO_APPLY}% profile before applying.",
                )
                return redirect("dashboard:candidate_profile")
            if has_applied:
                messages.info(request, "You already applied to this job.")
            else:
                expected_salary = (request.POST.get("expected_salary") or "").strip()
                years_experience = (request.POST.get("years_experience") or "").strip()
                current_company = (request.POST.get("current_company") or "").strip()
                recent_salary = (request.POST.get("recent_salary") or "").strip()
                resume_choice = (request.POST.get("resume_choice") or "").strip()
                resume_upload = request.FILES.get("resume")
                selected_resume = None

                if resume_choice:
                    if resume_choice == "jobexhibition":
                        template_name = ai_resume.template_name if ai_resume and ai_resume.template_name else "showcase"
                        selected_resume = _get_or_create_ai_resume(candidate, template_name).resume_file
                    elif resume_choice == "default" and default_resume:
                        selected_resume = default_resume.resume_file
                    else:
                        selected = candidate.resumes.filter(id=resume_choice).first()
                        if selected:
                            selected_resume = selected.resume_file

                consultancy_source = None
                if job.recruiter_name:
                    consultancy_source = Consultancy.objects.filter(name__iexact=job.recruiter_name).first()
                if not consultancy_source:
                    assignment = AssignedJob.objects.filter(job=job).select_related("consultancy")
                    if assignment.count() == 1:
                        consultancy_source = assignment.first().consultancy

                application = Application.objects.create(
                    application_id=_generate_prefixed_id("APP", 1001, Application, "application_id"),
                    candidate_name=candidate.name,
                    candidate_email=candidate.email,
                    candidate_phone=candidate.phone,
                    candidate_location=candidate.location,
                    education=candidate.education,
                    experience=years_experience or candidate.experience,
                    skills=candidate.skills,
                    expected_salary=expected_salary or candidate.expected_salary,
                    recent_salary=recent_salary,
                    current_company=current_company,
                    job_title=job.title,
                    company=job.company,
                    status="Applied",
                    applied_date=timezone.localdate(),
                    resume=resume_upload or selected_resume or candidate.resume,
                    job=job,
                    consultancy=consultancy_source,
                )
                Job.objects.filter(pk=job.pk).update(applicants=F("applicants") + 1)
                _ensure_message_threads(
                    application,
                    job=job,
                    candidate=candidate,
                    company=company,
                    consultancy=consultancy_source,
                )
                messages.success(request, "Application submitted successfully.")
        return redirect("dashboard:candidate_job_detail", job_id=job_id)

    return render(
        request,
        "dashboard/candidate/candidate_job_detail.html",
        {
            "candidate": candidate,
            "job": job,
            "company": company,
            "similar_jobs": similar_jobs,
            "candidate_resumes": candidate_resumes,
            "ai_resume": ai_resume,
            "default_resume": default_resume,
              "has_applied": has_applied,
              "can_apply": can_apply,
              "profile_completion_required": MIN_PROFILE_COMPLETION_TO_APPLY,
              "chat_thread_id": chat_thread_id,
          },
      )


@candidate_login_required
def candidate_saved_jobs_view(request):
    candidate_id = request.session.get("candidate_id")
    candidate = Candidate.objects.filter(id=candidate_id).first()
    if not candidate:
        return redirect("dashboard:login")

    saved_jobs = []
    return render(
        request,
        "dashboard/candidate/candidate_saved_jobs.html",
        {"candidate": candidate, "saved_jobs": saved_jobs},
    )


@candidate_login_required
def candidate_applications_view(request):
    candidate_id = request.session.get("candidate_id")
    candidate = Candidate.objects.filter(id=candidate_id).first()
    if not candidate:
        return redirect("dashboard:login")

    applications = Application.objects.filter(candidate_email__iexact=candidate.email).order_by("-applied_date", "-created_at")
    status_flow = [
        "Applied",
        "Under Review",
        "Shortlisted",
        "Interview Scheduled",
        "Selected",
        "Offer Received",
        "Rejected",
    ]
    for app in applications:
        current_status = app.status
        if current_status == "Interview":
            current_status = "Interview Scheduled"
        if current_status == "Offer Issued":
            current_status = "Offer Received"
        app.current_step = status_flow.index(current_status) + 1 if current_status in status_flow else 1

    return render(
        request,
        "dashboard/candidate/candidate_applications.html",
        {"candidate": candidate, "applications": applications, "status_flow": status_flow},
    )


@candidate_login_required
def candidate_interviews_view(request):
    candidate_id = request.session.get("candidate_id")
    candidate = Candidate.objects.filter(id=candidate_id).first()
    if not candidate:
        return redirect("dashboard:login")

    interviews = Interview.objects.filter(candidate_email__iexact=candidate.email).order_by("-interview_date")
    return render(
        request,
        "dashboard/candidate/candidate_interviews.html",
        {"candidate": candidate, "interviews": interviews},
    )


@candidate_login_required
def candidate_messages_view(request):
    candidate_id = request.session.get("candidate_id")
    candidate = Candidate.objects.filter(id=candidate_id).first()
    if not candidate:
        return redirect("dashboard:login")

    threads = (
        MessageThread.objects.filter(candidate=candidate)
        .select_related("job", "company", "consultancy", "application")
        .order_by("-last_message_at", "-created_at")
    )
    active_thread = None
    thread_id = (request.GET.get("thread") or "").strip()
    if thread_id:
        active_thread = threads.filter(id=thread_id).first()
    if not active_thread and threads:
        active_thread = threads[0]

    if request.method == "POST":
        action = (request.POST.get("action") or "").strip()
        if action == "send_message":
            thread_id = (request.POST.get("thread_id") or "").strip()
            thread = MessageThread.objects.filter(id=thread_id, candidate=candidate).first()
            body = (request.POST.get("message_body") or "").strip()
            attachment = request.FILES.get("attachment")
            if not thread:
                messages.error(request, "Select a valid conversation.")
            elif not body and not attachment:
                messages.error(request, "Type a message or attach a file.")
            else:
                Message.objects.create(
                    thread=thread,
                    sender_role="candidate",
                    sender_name=candidate.name,
                    body=body,
                    attachment=attachment,
                )
                thread.last_message_at = timezone.now()
                thread.save(update_fields=["last_message_at"])
                return redirect(f"{request.path}?thread={thread.id}")

    thread_messages = []
    if active_thread:
        thread_messages = list(active_thread.messages.order_by("created_at"))
        Message.objects.filter(thread=active_thread, is_read=False).exclude(
            sender_role="candidate"
        ).update(is_read=True)

    thread_cards = _build_thread_cards(threads, "candidate")
    active_card = None
    if active_thread:
        active_card = next(
            (card for card in thread_cards if card["thread"].id == active_thread.id),
            None,
        )

    return render(
        request,
        "dashboard/candidate/candidate_messages.html",
        {
            "candidate": candidate,
            "threads": threads,
            "thread_cards": thread_cards,
            "active_card": active_card,
            "active_thread": active_thread,
            "thread_messages": thread_messages,
            "current_role": "candidate",
        },
    )


@candidate_login_required
def candidate_notifications_view(request):
    candidate_id = request.session.get("candidate_id")
    candidate = Candidate.objects.filter(id=candidate_id).first()
    if not candidate:
        return redirect("dashboard:login")

    ad_segment = _resolve_subscription_segment_for_account(
        "Candidate",
        candidate.email,
    )
    advertisement = _active_advertisement_for("candidate", ad_segment)

    payload = build_panel_notifications(request, limit=40)
    notifications = payload.get("items", [])
    mark_panel_notifications_seen(request, role="candidate")
    return render(
        request,
        "dashboard/candidate/candidate_notifications.html",
        {
            "candidate": candidate,
            "notifications": notifications,
            "advertisement": advertisement,
        },
    )


@candidate_login_required
def candidate_settings_view(request):
    candidate_id = request.session.get("candidate_id")
    candidate = Candidate.objects.filter(id=candidate_id).first()
    if not candidate:
        return redirect("dashboard:login")

    if request.method == "POST":
        action = (request.POST.get("action") or "").strip()
        if action == "change_password":
            password = (request.POST.get("password") or "").strip()
            confirm = (request.POST.get("confirm_password") or "").strip()
            if not password or password != confirm:
                messages.error(request, "Passwords do not match.")
            else:
                candidate.password = _hash_password(password)
                candidate.save(update_fields=["password"])
                messages.success(request, "Password updated.")
        elif action == "update_settings":
            email = (request.POST.get("email") or "").strip()
            candidate.email = email or candidate.email
            candidate.profile_visibility = request.POST.get("profile_visibility") == "on"
            candidate.save(update_fields=["email", "profile_visibility"])
            messages.success(request, "Settings updated.")
        return redirect("dashboard:candidate_settings")

    return render(request, "dashboard/candidate/candidate_settings.html", {"candidate": candidate})


@candidate_login_required
def candidate_subscription_view(request):
    candidate_id = request.session.get("candidate_id")
    candidate = Candidate.objects.filter(id=candidate_id).first()
    if not candidate:
        return redirect("dashboard:login")

    subscription = (
        Subscription.objects.filter(
            account_type__iexact="Candidate",
            contact__iexact=candidate.email,
        )
        .order_by("-expiry_date", "-updated_at")
        .first()
    )

    if request.method == "POST":
        action = (request.POST.get("action") or "").strip()
        today = timezone.localdate()
        if action == "upgrade_premium":
            if not subscription:
                subscription = Subscription.objects.create(
                    subscription_id=_generate_prefixed_id("SUB", 901, Subscription, "subscription_id"),
                    name=candidate.name,
                    account_type="Candidate",
                    plan="Basic",
                    payment_status="Paid",
                    start_date=today,
                    expiry_date=today + timezone.timedelta(days=30),
                    contact=candidate.email,
                    monthly_revenue=199,
                    auto_renew=True,
                )
            else:
                subscription.plan = "Basic"
                subscription.payment_status = "Paid"
                subscription.start_date = today
                subscription.expiry_date = today + timezone.timedelta(days=30)
                subscription.monthly_revenue = 199
                subscription.auto_renew = True
                subscription.name = candidate.name
                subscription.contact = candidate.email
                subscription.save()
            messages.success(request, "Premium Candidate plan activated (Demo).")
        elif action == "downgrade_free":
            if not subscription:
                subscription = Subscription.objects.create(
                    subscription_id=_generate_prefixed_id("SUB", 901, Subscription, "subscription_id"),
                    name=candidate.name,
                    account_type="Candidate",
                    plan="Free",
                    payment_status="Free",
                    start_date=today,
                    expiry_date=None,
                    contact=candidate.email,
                    monthly_revenue=0,
                    auto_renew=False,
                )
            else:
                subscription.plan = "Free"
                subscription.payment_status = "Free"
                subscription.start_date = today
                subscription.expiry_date = None
                subscription.monthly_revenue = 0
                subscription.auto_renew = False
                subscription.name = candidate.name
                subscription.contact = candidate.email
                subscription.save()
            messages.success(request, "Moved to Free Candidate plan.")
        return redirect("dashboard:candidate_subscription")

    ad_segment = _resolve_subscription_segment_for_account(
        "Candidate",
        candidate.email,
    )
    is_premium = ad_segment == "subscribed"
    expiry = subscription.expiry_date if subscription else None

    return render(
        request,
        "dashboard/candidate/candidate_subscription.html",
        {
            "candidate": candidate,
            "subscription": subscription,
            "is_premium": is_premium,
            "expiry": expiry,
        },
    )


@candidate_login_required
def candidate_support_view(request):
    candidate_id = request.session.get("candidate_id")
    candidate = Candidate.objects.filter(id=candidate_id).first()
    if not candidate:
        return redirect("dashboard:login")

    if request.method == "POST":
        messages.success(request, "Support ticket created. Our team will respond shortly.")
        return redirect("dashboard:candidate_support")

    tickets = []
    return render(
        request,
        "dashboard/candidate/candidate_support.html",
        {"candidate": candidate, "tickets": tickets},
    )


@candidate_login_required
def api_candidate_metrics(request):
    candidate_id = request.session.get("candidate_id")
    candidate = Candidate.objects.filter(id=candidate_id).first()
    if not candidate:
        return JsonResponse({"error": "unauthorized"}, status=401)

    applications = Application.objects.filter(candidate_email__iexact=candidate.email)
    shortlisted = applications.filter(status="Shortlisted").count()
    interviews = Interview.objects.filter(
        candidate_email__iexact=candidate.email,
        status__in=["scheduled", "rescheduled"],
    ).count()
    data = {
        "profile_completion": candidate.profile_completion,
        "total_applications": applications.count(),
        "shortlisted": shortlisted,
        "interviews": interviews,
        "saved_jobs": 0,
        "recommended_jobs": Job.objects.filter(status="Approved").count(),
    }
    return JsonResponse(data)


@company_login_required
def company_dashboard_view(request):
    company_id = request.session.get("company_id")
    company = Company.objects.filter(id=company_id).first()
    if not company:
        request.session.pop("company_id", None)
        request.session.pop("company_name", None)
        return redirect("dashboard:login")

    company_name = company.name
    job_qs = Job.objects.filter(company__iexact=company_name)
    applications = Application.objects.filter(company__iexact=company_name)

    metrics = {
        "active_jobs": job_qs.filter(status="Approved").count(),
        "total_applications": applications.count(),
        "shortlisted": applications.filter(status="Shortlisted").count(),
        "interviews": applications.filter(status__in=INTERVIEW_STATUSES).count(),
        "on_hold": applications.filter(status="On Hold").count(),
        "rejected": applications.filter(status="Rejected").count(),
        "job_views": job_qs.aggregate(total=Sum("applicants")).get("total") or 0,
    }

    plan_label = company.plan_type or company.plan_name or "Premium"
    plan_expiry = (
        company.plan_expiry.strftime("%d %b %Y") if company.plan_expiry else "12 Mar 2026"
    )

    recent_applicants = applications.order_by("-applied_date", "-id")[:4]
    ad_segment = _resolve_subscription_segment_for_account(
        "Company",
        company.email,
        company.plan_type,
        company.payment_status,
        company.plan_expiry,
    )
    advertisement = _active_advertisement_for("company", ad_segment)

    return render(
        request,
        "dashboard/company_dashboard.html",
        {
            "company": company,
            "metrics": metrics,
            "plan_label": plan_label,
            "plan_expiry": plan_expiry,
            "recent_applicants": recent_applicants,
            "advertisement": advertisement,
        },
    )


@company_login_required
@require_http_methods(["GET"])
def api_company_metrics(request):
    company_id = request.session.get("company_id")
    company = Company.objects.filter(id=company_id).first()
    if not company:
        return JsonResponse({"error": "unauthorized"}, status=401)

    company_name = company.name
    job_qs = Job.objects.filter(company__iexact=company_name)
    applications = Application.objects.filter(company__iexact=company_name)

    metrics = {
        "active_jobs": job_qs.filter(status="Approved").count(),
        "total_jobs": job_qs.count(),
        "total_applications": applications.count(),
        "shortlisted": applications.filter(status="Shortlisted").count(),
        "interviews": applications.filter(status__in=INTERVIEW_STATUSES).count(),
        "on_hold": applications.filter(status="On Hold").count(),
        "rejected": applications.filter(status="Rejected").count(),
    }
    return JsonResponse(metrics)


@company_login_required
def company_profile_view(request):
    company_id = request.session.get("company_id")
    company = Company.objects.filter(id=company_id).first()
    if not company:
        return redirect("dashboard:login")

    if request.method == "POST":
        action = (request.POST.get("action") or "").strip()
        if action == "update_info":
            company.name = (request.POST.get("name") or company.name).strip()
            company.email = (request.POST.get("email") or company.email).strip()
            company.phone = (request.POST.get("phone") or "").strip()
            company.location = (request.POST.get("location") or "").strip()
            company.address = (request.POST.get("address") or "").strip()
            company.contact_position = (request.POST.get("contact_position") or "").strip()
            company.save(update_fields=["name", "email", "phone", "location", "address", "contact_position"])
            messages.success(request, "Company information updated.")
        elif action == "upload_logo":
            if request.FILES.get("profile_image"):
                company.profile_image = request.FILES["profile_image"]
                company.save(update_fields=["profile_image"])
                messages.success(request, "Logo updated successfully.")
            else:
                messages.error(request, "Please choose a logo file to upload.")
        elif action == "remove_logo":
            if company.profile_image:
                company.profile_image.delete(save=False)
                company.profile_image = None
                company.save(update_fields=["profile_image"])
                messages.success(request, "Logo removed.")
        elif action == "update_kyc":
            company.gst_number = (request.POST.get("gst_number") or "").strip()
            company.cin_number = (request.POST.get("cin_number") or "").strip()
            primary_doc = request.FILES.get("registration_document")
            extra_docs = [doc for doc in request.FILES.getlist("kyc_documents") if doc]
            uploaded_docs = []

            if primary_doc:
                company.registration_document = primary_doc
                uploaded_docs.append(primary_doc)
            uploaded_docs.extend(extra_docs)

            company.save(update_fields=["gst_number", "cin_number", "registration_document"])

            doc_titles = [(item or "").strip() for item in request.POST.getlist("kyc_document_title")]
            doc_types = [(item or "").strip() for item in request.POST.getlist("kyc_document_type")]
            allowed_types = {choice[0] for choice in CompanyKycDocument.DOCUMENT_TYPE_CHOICES}
            uploaded_count = 0

            for index, upload in enumerate(uploaded_docs):
                title = doc_titles[index] if index < len(doc_titles) else ""
                doc_type = doc_types[index] if index < len(doc_types) else "other"
                if doc_type not in allowed_types:
                    doc_type = "other"
                CompanyKycDocument.objects.create(
                    company=company,
                    title=title or os.path.basename(upload.name or ""),
                    document_type=doc_type,
                    file=upload,
                )
                uploaded_count += 1

            if uploaded_count:
                messages.success(request, f"KYC details updated. {uploaded_count} document(s) uploaded.")
            else:
                messages.success(request, "KYC details updated.")
        return redirect("dashboard:company_profile")

    kyc_documents = company.kyc_documents.order_by("-uploaded_at")
    return render(
        request,
        "dashboard/company/company_profile.html",
        {
            "company": company,
            "kyc_documents": kyc_documents,
        },
    )


@company_login_required
def company_jobs_view(request):
    company_id = request.session.get("company_id")
    company = Company.objects.filter(id=company_id).first()
    if not company:
        return redirect("dashboard:login")
    
    company_name = company.name
    base_jobs = Job.objects.filter(company__iexact=company_name).order_by("-created_at")
    jobs = base_jobs
    status_filter = (request.GET.get("status") or "").strip().lower()
    action = (request.GET.get("action") or "").strip().lower()
    mode = (request.GET.get("mode") or "").strip().lower()
    edit_job = None

    if request.method == "POST":
        action = (request.POST.get("action") or "").strip().lower()
        job_id = (request.POST.get("job_id") or "").strip()
        if action == "delete":
            if not job_id:
                messages.error(request, "Job delete failed: missing job id.")
                return redirect("dashboard:company_jobs")
            job = Job.objects.filter(job_id=job_id, company__iexact=company_name).first()
            if not job:
                messages.error(request, "Job not found for delete action.")
                return redirect("dashboard:company_jobs")
            job_title = job.title
            job.delete()
            messages.success(request, f"Job deleted successfully: {job_title}.")
            return redirect("dashboard:company_jobs")

        if job_id:
            edit_job = get_object_or_404(Job, job_id=job_id, company__iexact=company_name)
            job = edit_job
            is_new_job = False
        else:
            job = Job(company=company_name)
            is_new_job = True

        _apply_job_fields(job, request.POST)
        job.company = company_name

        if action in ["draft", "publish"]:
            job.status = "Pending"
            if not job.posted_date:
                job.posted_date = timezone.localdate()
        job.save()

        if not job.job_id:
            job.job_id = _generate_prefixed_id("JOB", 1001, Job, "job_id")
            job.save(update_fields=["job_id"])

        if action == "draft":
            messages.success(
                request,
                "Job draft created successfully." if is_new_job else "Job draft updated successfully.",
            )
        elif action == "publish":
            messages.success(
                request,
                "New job submitted for approval." if is_new_job else "Job updated and submitted for approval.",
            )
        else:
            messages.success(
                request,
                "Job created successfully." if is_new_job else "Job updated successfully.",
            )
        return redirect("dashboard:company_jobs")

    status_map = {
        "active": "Approved",
        "draft": "Pending",
        "paused": "Pending",
        "closed": "Rejected",
        "expired": "Rejected",
        "archived": "Reported",
    }
    if status_filter:
        mapped_status = status_map.get(status_filter)
        if mapped_status:
            jobs = jobs.filter(status=mapped_status)

    if action in ["edit", "view"]:
        job_id = (request.GET.get("job_id") or "").strip()
        if job_id:
            edit_job = Job.objects.filter(job_id=job_id, company__iexact=company_name).first()
        section_title = "Edit Job" if action == "edit" else "View Job"
    elif action == "new":
        section_title = "Post New Job"
    elif status_filter:
        section_title = f"{status_filter.replace('-', ' ').title()} Jobs"
    else:
        section_title = "All Jobs"

    applications = Application.objects.filter(company__iexact=company_name)
    total_views = jobs.aggregate(total=Sum("applicants")).get("total") or 0
    total_applications = applications.count()
    shortlisted = applications.filter(status="Shortlisted").count()
    conversion_rate = (
        f"{(shortlisted / total_applications * 100):.0f}%" if total_applications else "0%"
    )
    
    return render(request, "dashboard/company/company_jobs.html", {
        "company": company,
        "jobs": jobs,
        "total_jobs": base_jobs.count(),
        "approved_jobs": base_jobs.filter(status="Approved").count(),
        "pending_jobs": base_jobs.filter(status="Pending").count(),
        "rejected_jobs": base_jobs.filter(status="Rejected").count(),
        "action": action,
        "section_title": section_title,
        "job_analytics": {
            "total_views": total_views,
            "total_applications": total_applications,
            "shortlisted": shortlisted,
            "conversion_rate": conversion_rate,
        },
        "edit_job": edit_job,
        "form_mode": "view" if action == "view" else "edit" if action == "edit" else "new" if action == "new" else "list",
    })


@company_login_required
def company_applications_view(request):
    company_id = request.session.get("company_id")
    company = Company.objects.filter(id=company_id).first()
    if not company:
        return redirect("dashboard:login")

    company_name = company.name
    base_qs = Application.objects.filter(company__iexact=company_name)

    def get_experience_years(value):
        if not value:
            return None
        match = re.search(r"\d+", value)
        return int(match.group(0)) if match else None

    def experience_in_range(value, range_key):
        years = get_experience_years(value)
        if years is None:
            return False
        ranges = {
            "0-2": (0, 2),
            "3-5": (3, 5),
            "6-10": (6, 10),
            "10+": (10, None),
        }
        if range_key not in ranges:
            return True
        start, end = ranges[range_key]
        if end is None:
            return years >= start
        return start <= years <= end

    def resolve_resume(app, candidate_map):
        if app.resume:
            return app.resume
        candidate = candidate_map.get(app.candidate_email.lower()) if app.candidate_email else None
        if candidate and candidate.resume:
            return candidate.resume
        return None

    def build_resume_zip(apps):
        emails = [app.candidate_email.lower() for app in apps if app.candidate_email]
        candidate_map = {
            cand.email.lower(): cand
            for cand in Candidate.objects.filter(email__in=emails)
        }
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for app in apps:
                resume_file = resolve_resume(app, candidate_map)
                if not resume_file:
                    continue
                filename = os.path.basename(resume_file.name) or f"{app.application_id}.pdf"
                prefix = app.candidate_name or app.application_id
                safe_prefix = re.sub(r"[^a-zA-Z0-9_-]+", "_", prefix)
                safe_name = f"{safe_prefix}_{filename}"
                try:
                    with resume_file.open("rb") as handle:
                        zip_file.writestr(safe_name, handle.read())
                except OSError:
                    continue
        zip_buffer.seek(0)
        response = HttpResponse(zip_buffer.getvalue(), content_type="application/zip")
        response["Content-Disposition"] = 'attachment; filename="resumes.zip"'
        return response

    if request.method == "POST":
        action = (request.POST.get("action") or "").strip()
        next_url = request.POST.get("next") or request.get_full_path()

        if action == "update_status":
            application_id = request.POST.get("application_id")
            new_status = (request.POST.get("status") or "").strip()
            rejection_remark = (request.POST.get("rejection_remark") or "").strip()
            if application_id and new_status:
                if new_status == "Rejected" and not rejection_remark:
                    messages.error(request, "Please add rejection remark before marking candidate as Rejected.")
                    return redirect(next_url)

                update_fields = {
                    "status": new_status,
                    "updated_at": timezone.now(),
                }
                if new_status == "Rejected":
                    update_fields["notes"] = rejection_remark

                updated = Application.objects.filter(
                    company__iexact=company_name,
                    application_id=application_id,
                ).update(**update_fields)
                if updated:
                    messages.success(request, "Application status updated.")
                else:
                    messages.error(request, "Unable to update application status.")

        elif action == "schedule_interview":
            application_id = request.POST.get("application_id")
            interview_date = parse_date(request.POST.get("interview_date")) if request.POST.get("interview_date") else None
            interview_time = (request.POST.get("interview_time") or "").strip()
            interview_mode = (request.POST.get("interview_mode") or "").strip()
            meeting_link = (request.POST.get("meeting_link") or "").strip()
            interviewer = (request.POST.get("interviewer") or "").strip()
            feedback = (request.POST.get("interview_feedback") or "").strip()
            if application_id:
                Application.objects.filter(
                    company__iexact=company_name,
                    application_id=application_id,
                ).update(
                    interview_date=interview_date,
                    interview_time=interview_time,
                    interview_mode=interview_mode,
                    meeting_link=meeting_link,
                    interviewer=interviewer,
                    interview_feedback=feedback,
                    status="Interview",
                    updated_at=timezone.now(),
                )
                app = Application.objects.filter(
                    company__iexact=company_name,
                    application_id=application_id,
                ).first()
                if app:
                    existing = Interview.objects.filter(application=app).order_by("-created_at").first()
                    if existing:
                        existing.interview_date = interview_date
                        existing.interview_time = parse_time(interview_time) if interview_time else None
                        existing.mode = interview_mode or existing.mode
                        existing.meeting_link = meeting_link
                        existing.interviewer = interviewer
                        existing.notes = feedback
                        existing.status = "rescheduled" if existing.status in ["scheduled", "rescheduled"] else "scheduled"
                        existing.save(update_fields=[
                            "interview_date",
                            "interview_time",
                            "mode",
                            "meeting_link",
                            "interviewer",
                            "notes",
                            "status",
                            "updated_at",
                        ])
                    else:
                        interview = Interview.objects.create(
                            application=app,
                            candidate_name=app.candidate_name,
                            candidate_email=app.candidate_email,
                            job_title=app.job_title,
                            company=company_name,
                            interview_date=interview_date,
                            interview_time=parse_time(interview_time) if interview_time else None,
                            mode=interview_mode or "Online",
                            meeting_link=meeting_link,
                            interviewer=interviewer,
                            notes=feedback,
                            status="scheduled",
                        )
                        if not interview.interview_id:
                            interview.interview_id = _generate_prefixed_id("INT", 2001, Interview, "interview_id")
                            interview.save(update_fields=["interview_id"])
                    messages.success(request, f"Interview schedule saved for {app.candidate_name}.")
                else:
                    messages.error(request, "Unable to schedule interview: application not found.")
            else:
                messages.error(request, "Unable to schedule interview: missing application id.")

        elif action == "save_notes":
            application_id = request.POST.get("application_id")
            internal_notes = (request.POST.get("internal_notes") or "").strip()
            interview_feedback = (request.POST.get("interview_feedback") or "").strip()
            if application_id:
                updated = Application.objects.filter(
                    company__iexact=company_name,
                    application_id=application_id,
                ).update(
                    internal_notes=internal_notes,
                    interview_feedback=interview_feedback,
                    updated_at=timezone.now(),
                )
                if updated:
                    messages.success(request, "Application notes saved successfully.")
                else:
                    messages.error(request, "Unable to save notes: application not found.")
            else:
                messages.error(request, "Unable to save notes: missing application id.")

        elif action == "bulk":
            selected_ids = request.POST.getlist("selected_ids")
            bulk_action = (request.POST.get("bulk_action") or "").strip()
            bulk_rejection_remark = (request.POST.get("bulk_rejection_remark") or "").strip()
            if not selected_ids:
                messages.error(request, "Please select at least one application.")
                return redirect(next_url)

            scoped_qs = Application.objects.filter(
                company__iexact=company_name,
                application_id__in=selected_ids,
            )

            if bulk_action == "shortlist":
                scoped_qs.update(status="Shortlisted", updated_at=timezone.now())
                messages.success(request, "Selected applications moved to Shortlisted.")
            elif bulk_action == "reject":
                if not bulk_rejection_remark:
                    messages.error(request, "Please add rejection remark for bulk reject action.")
                    return redirect(next_url)
                scoped_qs.update(
                    status="Rejected",
                    notes=bulk_rejection_remark,
                    updated_at=timezone.now(),
                )
                messages.success(request, "Selected applications rejected with remark.")
            elif bulk_action == "archive":
                scoped_qs.update(status="Archived", updated_at=timezone.now())
                messages.success(request, "Selected applications archived.")
            elif bulk_action == "email":
                response = HttpResponse(content_type="text/csv")
                response["Content-Disposition"] = 'attachment; filename="bulk_emails.csv"'
                writer = csv.writer(response)
                writer.writerow(["Email"])
                for email in scoped_qs.values_list("candidate_email", flat=True):
                    if email:
                        writer.writerow([email])
                return response
            elif bulk_action == "download":
                apps = list(scoped_qs)
                return build_resume_zip(apps)

        return redirect(next_url)

    applications = base_qs.order_by("-applied_date", "-created_at", "-id")

    search = (request.GET.get("search") or "").strip()
    if search:
        applications = applications.filter(
            Q(candidate_name__icontains=search)
            | Q(candidate_email__icontains=search)
            | Q(job_title__icontains=search)
            | Q(skills__icontains=search)
            | Q(cover_letter__icontains=search)
            | Q(internal_notes__icontains=search)
            | Q(interview_feedback__icontains=search)
            | Q(notes__icontains=search)
        )

    job_filter = (request.GET.get("job") or "").strip()
    if job_filter:
        applications = applications.filter(job_title__iexact=job_filter)

    status_filter = (request.GET.get("status") or "").strip()
    if status_filter and status_filter.lower() != "all":
        if status_filter.lower() == "interview":
            applications = applications.filter(status__in=INTERVIEW_STATUSES)
        elif status_filter.lower() == "selected":
            applications = applications.filter(status__in=SELECTED_STATUSES)
        else:
            applications = applications.filter(status__iexact=status_filter)

    experience_filter = (request.GET.get("experience") or "").strip()
    skills_filter = (request.GET.get("skills") or "").strip()
    if skills_filter:
        applications = applications.filter(skills__icontains=skills_filter)

    location_filter = (request.GET.get("location") or "").strip()
    if location_filter:
        applications = applications.filter(candidate_location__icontains=location_filter)

    date_from = parse_date(request.GET.get("date_from") or "")
    date_to = parse_date(request.GET.get("date_to") or "")
    if date_from:
        applications = applications.filter(created_at__date__gte=date_from)
    if date_to:
        applications = applications.filter(created_at__date__lte=date_to)

    applications = list(applications)
    if experience_filter:
        applications = [
            app for app in applications if experience_in_range(app.experience, experience_filter)
        ]

    emails = [app.candidate_email.lower() for app in applications if app.candidate_email]
    candidate_map = {
        cand.email.lower(): cand
        for cand in Candidate.objects.filter(email__in=emails)
    }
    job_map = {
        job.title.lower(): job.skills
        for job in Job.objects.filter(company__iexact=company_name)
        if job.title
    }

    def split_skills(value):
        return [item.strip() for item in (value or "").split(",") if item.strip()]

    for app in applications:
        candidate = candidate_map.get(app.candidate_email.lower()) if app.candidate_email else None
        app.profile_image_url = candidate.profile_image.url if candidate and candidate.profile_image else ""
        resume_file = resolve_resume(app, candidate_map)
        app.has_resume = bool(resume_file)
        app.resume_filename = os.path.basename(resume_file.name) if resume_file else ""
        if app.status == "Interview Scheduled":
            app.display_status = "Interview"
        elif app.status == "Offer Issued":
            app.display_status = "Selected"
        else:
            app.display_status = app.status
        app.rejection_remark = app.notes if app.status == "Rejected" else ""
        app.skill_tags = split_skills(app.skills)[:3]
        app.all_skill_tags = split_skills(app.skills)
        app.skill_match = None

        job_key = (app.job_title or "").lower()
        job_skills = split_skills(job_map.get(job_key))
        if app.all_skill_tags and job_skills:
            intersection = set(map(str.lower, app.all_skill_tags)) & set(map(str.lower, job_skills))
            app.skill_match = round((len(intersection) / max(len(job_skills), 1)) * 100)

    total_applications = base_qs.count()
    new_since = timezone.now() - timezone.timedelta(days=7)
    new_applications = base_qs.filter(created_at__gte=new_since).count()
    shortlisted_applications = base_qs.filter(status="Shortlisted").count()
    interview_applications = base_qs.filter(status__in=INTERVIEW_STATUSES).count()
    selected_applications = base_qs.filter(status__in=SELECTED_STATUSES).count()

    job_titles = list(
        base_qs.values_list("job_title", flat=True).order_by("job_title").distinct()
    )

    return render(
        request,
        "dashboard/company/company_applications.html",
        {
            "company": company,
            "applications": applications,
            "total_applications": total_applications,
            "new_applications": new_applications,
            "shortlisted_applications": shortlisted_applications,
            "interview_applications": interview_applications,
            "selected_applications": selected_applications,
            "job_titles": [title for title in job_titles if title],
            "status_choices": PIPELINE_STATUSES,
            "experience_choices": ["0-2", "3-5", "6-10", "10+"],
            "star_range": range(1, 6),
            "filters": {
                "search": search,
                "job": job_filter,
                "status": status_filter or "all",
                "experience": experience_filter,
                "skills": skills_filter,
                "location": location_filter,
                "date_from": request.GET.get("date_from") or "",
                "date_to": request.GET.get("date_to") or "",
            },
        },
    )


@company_login_required
def company_messages_view(request):
    company_id = request.session.get("company_id")
    company = Company.objects.filter(id=company_id).first()
    if not company:
        return redirect("dashboard:login")

    threads = (
        MessageThread.objects.filter(company=company)
        .select_related("job", "candidate", "consultancy", "application")
        .order_by("-last_message_at", "-created_at")
    )
    active_thread = None
    thread_id = (request.GET.get("thread") or "").strip()
    if thread_id:
        active_thread = threads.filter(id=thread_id).first()
    if not active_thread and threads:
        active_thread = threads[0]

    if request.method == "POST":
        action = (request.POST.get("action") or "").strip()
        if action == "send_message":
            thread_id = (request.POST.get("thread_id") or "").strip()
            thread = MessageThread.objects.filter(id=thread_id, company=company).first()
            body = (request.POST.get("message_body") or "").strip()
            attachment = request.FILES.get("attachment")
            if not thread:
                messages.error(request, "Select a valid conversation.")
            elif not body and not attachment:
                messages.error(request, "Type a message or attach a file.")
            else:
                Message.objects.create(
                    thread=thread,
                    sender_role="company",
                    sender_name=company.name,
                    body=body,
                    attachment=attachment,
                )
                thread.last_message_at = timezone.now()
                thread.save(update_fields=["last_message_at"])
                messages.success(request, "Message sent successfully.")
                return redirect(f"{request.path}?thread={thread.id}")

    thread_messages = []
    if active_thread:
        thread_messages = list(active_thread.messages.order_by("created_at"))
        Message.objects.filter(thread=active_thread, is_read=False).exclude(
            sender_role="company"
        ).update(is_read=True)

    thread_cards = _build_thread_cards(threads, "company")
    active_card = None
    if active_thread:
        active_card = next(
            (card for card in thread_cards if card["thread"].id == active_thread.id),
            None,
        )

    return render(
        request,
        "dashboard/company/company_messages.html",
        {
            "company": company,
            "threads": threads,
            "thread_cards": thread_cards,
            "active_card": active_card,
            "active_thread": active_thread,
            "thread_messages": thread_messages,
            "current_role": "company",
        },
    )


@company_login_required
def company_communication_view(request, section="bulk-email"):
    company_id = request.session.get("company_id")
    company = Company.objects.filter(id=company_id).first()
    if not company:
        return redirect("dashboard:login")

    section_map = {
        "bulk-email": ("Bulk Email", "Send bulk emails with templates and scheduling."),
        "bulk-sms": ("Bulk SMS", "Send short SMS alerts with delivery tracking."),
        "whatsapp": ("WhatsApp Alerts", "Approved template-based WhatsApp messaging."),
        "notifications": ("In-App Notifications", "Bell icon alerts and status updates."),
        "templates": ("Message Templates", "Reusable templates with dynamic variables."),
        "sent-history": ("Sent History", "Delivery status across all channels."),
        "scheduled": ("Scheduled Messages", "Plan future sends and reminders."),
    }
    page_title, page_subtitle = section_map.get(
        section, ("Communication Center", "Bulk messaging tools for candidates.")
    )

    return render(
        request,
        "dashboard/company/company_communication.html",
        {
            "company": company,
            "comm_section": section,
            "page_title": page_title,
            "page_subtitle": page_subtitle,
            "communication_candidates": _communication_candidate_options(),
        },
    )


@company_login_required
def company_application_resume_view(request, application_id):
    company_id = request.session.get("company_id")
    company = Company.objects.filter(id=company_id).first()
    if not company:
        return redirect("dashboard:login")

    app = get_object_or_404(
        Application,
        company__iexact=company.name,
        application_id=application_id,
    )
    resume_file = app.resume
    if not resume_file and app.candidate_email:
        candidate = Candidate.objects.filter(email__iexact=app.candidate_email).first()
        if candidate and candidate.resume:
            resume_file = candidate.resume
    if not resume_file:
        return HttpResponse("Resume not available.", status=404)

    download = request.GET.get("download") == "1"
    content_type, _ = mimetypes.guess_type(resume_file.name)
    response = FileResponse(
        resume_file.open("rb"),
        as_attachment=download,
        filename=os.path.basename(resume_file.name),
    )
    if content_type:
        response["Content-Type"] = content_type
    response["X-Content-Type-Options"] = "nosniff"
    return response


@company_login_required
def company_interviews_view(request, section="schedule"):
    company_id = request.session.get("company_id")
    company = Company.objects.filter(id=company_id).first()
    if not company:
        return redirect("dashboard:login")

    company_name = company.name
    interviews_qs = Interview.objects.filter(company__iexact=company_name)
    shortlisted_apps = Application.objects.filter(
        company__iexact=company_name,
        status="Shortlisted",
    ).order_by("-applied_date", "-id")

    if request.method == "POST":
        action = (request.POST.get("action") or "").strip()
        next_url = request.POST.get("next") or request.get_full_path()

        if action == "schedule":
            application_id = (request.POST.get("application_id") or "").strip()
            candidate_name = (request.POST.get("candidate_name") or "").strip()
            candidate_email = (request.POST.get("candidate_email") or "").strip()
            job_title = (request.POST.get("job_title") or "").strip()
            interview_date = parse_date(request.POST.get("interview_date") or "")
            interview_time = parse_time(request.POST.get("interview_time") or "")
            duration_minutes = int(request.POST.get("duration_minutes") or 30)
            mode = (request.POST.get("mode") or "Online").strip()
            meeting_link = (request.POST.get("meeting_link") or "").strip()
            location = (request.POST.get("location") or "").strip()
            interviewer = (request.POST.get("interviewer") or "").strip()
            panel_interviewers = (request.POST.get("panel_interviewers") or "").strip()
            notes = (request.POST.get("notes") or "").strip()

            linked_app = None
            if application_id:
                linked_app = Application.objects.filter(
                    company__iexact=company_name,
                    application_id=application_id,
                ).first()
                if linked_app:
                    candidate_name = linked_app.candidate_name
                    candidate_email = linked_app.candidate_email
                    job_title = linked_app.job_title

            interview = Interview.objects.create(
                application=linked_app,
                candidate_name=candidate_name or (linked_app.candidate_name if linked_app else ""),
                candidate_email=candidate_email or (linked_app.candidate_email if linked_app else ""),
                job_title=job_title or (linked_app.job_title if linked_app else ""),
                company=company_name,
                interview_date=interview_date,
                interview_time=interview_time,
                duration_minutes=duration_minutes,
                mode=mode or "Online",
                meeting_link=meeting_link,
                location=location,
                interviewer=interviewer,
                panel_interviewers=panel_interviewers,
                notes=notes,
                status="scheduled",
            )
            if not interview.interview_id:
                interview.interview_id = _generate_prefixed_id("INT", 2001, Interview, "interview_id")
                interview.save(update_fields=["interview_id"])

            if linked_app:
                linked_app.status = "Interview"
                linked_app.interview_date = interview_date
                if interview_time:
                    linked_app.interview_time = interview_time.strftime("%H:%M")
                linked_app.interviewer = interviewer
                linked_app.interview_mode = mode
                linked_app.meeting_link = meeting_link
                linked_app.save(update_fields=[
                    "status",
                    "interview_date",
                    "interview_time",
                    "interviewer",
                    "interview_mode",
                    "meeting_link",
                    "updated_at",
                ])
            messages.success(
                request,
                f"Interview scheduled for {interview.candidate_name or 'candidate'}.",
            )

        elif action == "reschedule":
            interview_id = request.POST.get("interview_id")
            new_date = parse_date(request.POST.get("interview_date") or "")
            new_time = parse_time(request.POST.get("interview_time") or "")
            updated = Interview.objects.filter(
                company__iexact=company_name,
                id=interview_id,
            ).update(
                interview_date=new_date,
                interview_time=new_time,
                status="rescheduled",
                updated_at=timezone.now(),
            )
            if updated:
                messages.success(request, "Interview rescheduled successfully.")
            else:
                messages.error(request, "Unable to reschedule interview.")

        elif action == "cancel":
            interview_id = request.POST.get("interview_id")
            updated = Interview.objects.filter(
                company__iexact=company_name,
                id=interview_id,
            ).update(status="cancelled", updated_at=timezone.now())
            if updated:
                messages.success(request, "Interview cancelled successfully.")
            else:
                messages.error(request, "Unable to cancel interview.")

        elif action == "no_show":
            interview_id = request.POST.get("interview_id")
            updated = Interview.objects.filter(
                company__iexact=company_name,
                id=interview_id,
            ).update(status="no_show", updated_at=timezone.now())
            if updated:
                messages.success(request, "Candidate marked as no show.")
            else:
                messages.error(request, "Unable to update no-show status.")

        elif action == "mark_completed":
            interview_id = request.POST.get("interview_id")
            updated = Interview.objects.filter(
                company__iexact=company_name,
                id=interview_id,
            ).update(status="completed", updated_at=timezone.now())
            if updated:
                messages.success(request, "Interview marked as completed.")
            else:
                messages.error(request, "Unable to mark interview as completed.")

        elif action == "send_reminder":
            interview_id = request.POST.get("interview_id")
            updated = Interview.objects.filter(
                company__iexact=company_name,
                id=interview_id,
            ).update(updated_at=timezone.now())
            if updated:
                messages.success(request, "Interview reminder sent successfully.")
            else:
                messages.error(request, "Unable to send interview reminder.")

        elif action == "feedback":
            interview_id = request.POST.get("interview_id")
            feedback_rating = request.POST.get("feedback_rating")
            updated = Interview.objects.filter(
                company__iexact=company_name,
                id=interview_id,
            ).update(
                feedback_rating=int(feedback_rating) if feedback_rating and str(feedback_rating).isdigit() else None,
                technical_skills=(request.POST.get("technical_skills") or "").strip(),
                communication_skills=(request.POST.get("communication_skills") or "").strip(),
                strengths=(request.POST.get("strengths") or "").strip(),
                weakness=(request.POST.get("weakness") or "").strip(),
                final_decision=(request.POST.get("final_decision") or "").strip(),
                notes=(request.POST.get("notes") or "").strip(),
                status="completed",
                feedback_submitted_at=timezone.now(),
                updated_at=timezone.now(),
            )
            if updated:
                messages.success(request, "Interview feedback submitted successfully.")
            else:
                messages.error(request, "Unable to submit interview feedback.")

        return redirect(next_url)

    upcoming_interviews = interviews_qs.filter(status__in=["scheduled", "rescheduled"]).order_by(
        "interview_date",
        "interview_time",
    )
    completed_interviews = interviews_qs.filter(status="completed").order_by(
        "-interview_date",
        "-interview_time",
    )
    cancelled_interviews = interviews_qs.filter(status__in=["cancelled", "no_show"]).order_by(
        "-interview_date",
        "-interview_time",
    )

    today = timezone.localdate()
    today_count = interviews_qs.filter(
        interview_date=today,
        status__in=["scheduled", "rescheduled"],
    ).count()

    feedback_targets = interviews_qs.filter(
        status__in=["scheduled", "rescheduled", "completed"]
    ).order_by("-interview_date", "-interview_time")

    return render(
        request,
        "dashboard/company/company_interviews.html",
        {
            "company": company,
            "shortlisted_apps": shortlisted_apps,
            "upcoming_interviews": upcoming_interviews,
            "completed_interviews": completed_interviews,
            "cancelled_interviews": cancelled_interviews,
            "total_upcoming": upcoming_interviews.count(),
            "total_today": today_count,
            "total_completed": completed_interviews.count(),
            "duration_choices": [30, 60],
            "feedback_targets": feedback_targets,
            "interview_section": section,
            "reschedule_requests": [],
        },
    )


@company_login_required
def company_reports_view(request):
    company_id = request.session.get("company_id")
    company = Company.objects.filter(id=company_id).first()
    if not company:
        return redirect("dashboard:login")
    
    company_name = company.name
    job_qs = Job.objects.filter(company__iexact=company_name)
    applications = Application.objects.filter(company__iexact=company_name)
    
    return render(request, "dashboard/company/company_reports.html", {
        "company": company,
        "total_jobs": job_qs.count(),
        "total_applications": applications.count(),
        "conversion_rate": round((applications.filter(status__in=SELECTED_STATUSES).count() / max(applications.count(), 1)) * 100, 2),
        "avg_time_to_hire": "15 days",
    })


@company_login_required
def company_billing_view(request):
    company_id = request.session.get("company_id")
    company = Company.objects.filter(id=company_id).first()
    if not company:
        return redirect("dashboard:login")
    
    return render(request, "dashboard/company/company_billing.html", {"company": company})


@company_login_required
def company_grievance_view(request):
    company_id = request.session.get("company_id")
    company = Company.objects.filter(id=company_id).first()
    if not company:
        return redirect("dashboard:login")
    
    return render(request, "dashboard/company/company_grievance.html", {"company": company})


@company_login_required
def company_settings_view(request):
    company_id = request.session.get("company_id")
    company = Company.objects.filter(id=company_id).first()
    if not company:
        return redirect("dashboard:login")

    if request.method == "POST":
        action = (request.POST.get("action") or "").strip()
        if action == "update_settings":
            company.name = (request.POST.get("name") or company.name).strip()
            company.email = (request.POST.get("email") or company.email).strip()
            company.phone = (request.POST.get("phone") or "").strip()
            company.location = (request.POST.get("location") or "").strip()
            company.save(update_fields=["name", "email", "phone", "location"])
            messages.success(request, "Settings updated successfully.")
        elif action == "change_password":
            current_password = request.POST.get("current_password") or ""
            new_password = request.POST.get("new_password") or ""
            confirm_password = request.POST.get("confirm_password") or ""
            if not _check_raw_password(current_password, company.password or ""):
                messages.error(request, "Current password is incorrect.")
            elif not new_password:
                messages.error(request, "New password cannot be empty.")
            elif new_password != confirm_password:
                messages.error(request, "New password and confirmation do not match.")
            else:
                company.password = _hash_password(new_password)
                company.save(update_fields=["password"])
                messages.success(request, "Password updated successfully.")
        return redirect("dashboard:company_settings")
    
    return render(request, "dashboard/company/company_settings.html", {"company": company})


@company_login_required
def company_security_view(request):
    company_id = request.session.get("company_id")
    company = Company.objects.filter(id=company_id).first()
    if not company:
        return redirect("dashboard:login")
    
    return render(request, "dashboard/company/company_security.html", {"company": company})


@company_login_required
def company_support_view(request, section="create", ticket_id=None):
    company_id = request.session.get("company_id")
    company = Company.objects.filter(id=company_id).first()
    if not company:
        return redirect("dashboard:login")

    section_map = {
        "create": ("Create Ticket", "Raise a new support ticket for any issue."),
        "my-tickets": ("My Tickets", "Track all support tickets submitted by your company."),
        "open": ("Open Tickets", "Tickets that are open or waiting for response."),
        "closed": ("Closed Tickets", "Resolved and closed support requests."),
        "knowledge": ("Knowledge Base", "Self-help guides and FAQs."),
        "chat": ("Live Chat", "Real-time support chat with our team."),
        "details": ("Ticket Details", "Conversation, attachments, and timeline."),
    }
    page_title, page_subtitle = section_map.get(
        section, ("Customer Support", "Get help from our support team.")
    )

    return render(
        request,
        "dashboard/company/company_support.html",
        {
            "company": company,
            "support_section": section,
            "page_title": page_title,
            "page_subtitle": page_subtitle,
            "ticket_id": ticket_id or "SUP-1023",
        },
    )


@login_required
def support_center_view(request, section="dashboard"):
    section_map = {
        "dashboard": ("Support Dashboard", "Overview of tickets, SLAs, and workload."),
        "all": ("All Tickets", "Every support ticket across companies."),
        "high": ("High Priority", "Tickets flagged as urgent."),
        "assigned": ("Assigned Tickets", "Tickets already owned by agents."),
        "unassigned": ("Unassigned Tickets", "Tickets waiting for assignment."),
        "closed": ("Closed Tickets", "Resolved and archived tickets."),
        "analytics": ("Support Analytics", "Performance and response metrics."),
    }
    page_title, page_subtitle = section_map.get(
        section, ("Support Dashboard", "Overview of tickets, SLAs, and workload.")
    )

    return render(
        request,
        "dashboard/support_center.html",
        {
            "support_section": section,
            "page_title": page_title,
            "page_subtitle": page_subtitle,
        },
    )


@login_required
def dashboard_view(request):
    return render(request, "dashboard/dashboard.html")


@login_required
def companies_view(request):
    return render(request, "dashboard/companies.html")


@login_required
def consultancies_view(request):
    return render(request, "dashboard/consultancies.html")


@login_required
def candidates_view(request):
    return render(request, "dashboard/candidates.html")


@login_required
def jobs_view(request):
    return render(request, "dashboard/jobs.html")


@login_required
def jobs_pending_view(request):
    return render(request, "dashboard/jobs_pending.html")


@login_required
def jobs_approved_view(request):
    return render(request, "dashboard/jobs_approved.html")


@login_required
def jobs_rejected_view(request):
    return render(request, "dashboard/jobs_rejected.html")


@login_required
def jobs_reported_view(request):
    return render(request, "dashboard/jobs_reported.html")


@login_required
def applications_view(request):
    return render(request, "dashboard/applications.html")


@login_required
def applications_interview_view(request):
    return render(request, "dashboard/applications_interview.html")


@login_required
def applications_selected_view(request):
    return render(request, "dashboard/applications_selected.html")


@login_required
def applications_rejected_view(request):
    return render(request, "dashboard/applications_rejected.html")


@login_required
def applications_offer_view(request):
    return render(request, "dashboard/applications_offer.html")


@login_required
def subscriptions_view(request):
    return render(
        request,
        "dashboard/subscriptions.html",
        {
            "section": "overview",
            "page_title": "Subscription Control Center",
            "page_subtitle": "Track active plans, expiry alerts, and revenue performance.",
        },
    )


@login_required
def subscriptions_free_paid_view(request):
    return render(
        request,
        "dashboard/subscriptions.html",
        {
            "section": "free-paid",
            "page_title": "Who is Free / Paid",
            "page_subtitle": "Company-wise subscription visibility.",
        },
    )


@login_required
def subscriptions_expiry_alerts_view(request):
    return render(
        request,
        "dashboard/subscriptions.html",
        {
            "section": "expiry-alerts",
            "page_title": "Expiry Alerts",
            "page_subtitle": "Plans expiring soon with contact details.",
        },
    )


@login_required
def subscriptions_revenue_view(request):
    return render(
        request,
        "dashboard/subscriptions.html",
        {
            "section": "revenue-charts",
            "page_title": "Revenue Charts",
            "page_subtitle": "Monthly recurring revenue snapshot.",
        },
    )


@login_required
def subscriptions_manual_assign_view(request):
    return render(
        request,
        "dashboard/subscriptions.html",
        {
            "section": "manual-assign",
            "page_title": "Manual Plan Assign",
            "page_subtitle": "Assign or upgrade plan manually.",
        },
    )


@login_required
def advertisement_management_view(request):
    if request.method == "POST":
        action = (request.POST.get("action") or "").strip()

        if action == "update_media":
            ad_id = (request.POST.get("ad_id") or "").strip()
            media_file = request.FILES.get("media_file")
            ad = Advertisement.objects.filter(id=ad_id).first()
            if not ad:
                messages.error(request, "Advertisement not found.")
                return redirect("dashboard:advertisement_management")
            if not media_file:
                messages.error(request, "Please choose an image or video to upload.")
                return redirect("dashboard:advertisement_management")

            content_type = (getattr(media_file, "content_type", "") or "").lower()
            ext = os.path.splitext(media_file.name)[1].lower()
            if not (
                content_type.startswith("image/")
                or content_type.startswith("video/")
                or ext in AD_IMAGE_EXTENSIONS
                or ext in AD_VIDEO_EXTENSIONS
            ):
                messages.error(request, "Only image or video files are allowed.")
                return redirect("dashboard:advertisement_management")

            ad.media_file = media_file
            ad.save(update_fields=["media_file"])
            messages.success(request, "Media uploaded successfully for this advertisement.")
            return redirect("dashboard:advertisement_management")

        audience = (request.POST.get("audience") or "").strip()
        segment = (request.POST.get("segment") or "").strip()
        message = (request.POST.get("message") or "").strip()
        title = (request.POST.get("title") or "").strip()
        media_file = request.FILES.get("media_file")
        has_error = False
        if not audience:
            messages.error(request, "Audience is required.")
            has_error = True
        elif audience not in ["company", "consultancy", "candidate"]:
            messages.error(request, "Invalid audience selected.")
            has_error = True
        elif not message and not media_file:
            messages.error(request, "Message or media is required.")
            has_error = True
        elif media_file:
            content_type = (getattr(media_file, "content_type", "") or "").lower()
            ext = os.path.splitext(media_file.name)[1].lower()
            if not (
                content_type.startswith("image/")
                or content_type.startswith("video/")
                or ext in AD_IMAGE_EXTENSIONS
                or ext in AD_VIDEO_EXTENSIONS
            ):
                messages.error(request, "Only image or video files are allowed.")
                has_error = True
                return redirect("dashboard:advertisement_management")
        if has_error:
            return redirect("dashboard:advertisement_management")

        current_ad_qs = Advertisement.objects.filter(
            audience=audience,
            is_active=True,
        )
        if segment:
            current_ad_qs = current_ad_qs.filter(segment=segment)
        else:
            current_ad_qs = current_ad_qs.filter(Q(segment="") | Q(segment__isnull=True))
        current_ad_qs.update(is_active=False)

        Advertisement.objects.create(
            audience=audience,
            segment=segment,
            title=title,
            message=message,
            media_file=media_file,
            is_active=True,
            posted_by=request.user.username or "Admin",
        )
        if media_file:
            messages.success(request, "Advertisement posted successfully with media.")
        else:
            messages.success(request, "Advertisement posted successfully.")
        return redirect("dashboard:advertisement_management")

    recent_ads = Advertisement.objects.filter(is_active=True).order_by("-created_at")[:10]
    return render(request, "dashboard/advertisement_management.html", {"recent_ads": recent_ads})


@login_required
def communication_center_view(request):
    return render(
        request,
        "dashboard/communication_center.html",
        {
            "comm_section": "bulk-email",
            "page_title": "Bulk Email",
            "page_subtitle": "Send email campaigns with subject, rich text editor, and attachments.",
            "communication_candidates": _communication_candidate_options(),
        },
    )


@login_required
def message_monitor_view(request):
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect("dashboard:login")

    threads = (
        MessageThread.objects.all()
        .select_related("job", "company", "candidate", "consultancy", "application")
        .order_by("-last_message_at", "-created_at")
    )
    active_thread = None
    thread_id = (request.GET.get("thread") or "").strip()
    if thread_id:
        active_thread = threads.filter(id=thread_id).first()
    if not active_thread and threads:
        active_thread = threads[0]

    thread_messages = []
    if active_thread:
        thread_messages = list(active_thread.messages.order_by("created_at"))

    thread_cards = _build_thread_cards(threads, "admin")
    active_card = None
    if active_thread:
        active_card = next(
            (card for card in thread_cards if card["thread"].id == active_thread.id),
            None,
        )

    return render(
        request,
        "dashboard/communication_center.html",
        {
            "comm_section": "chat-monitor",
            "page_title": "Chat Monitoring",
            "page_subtitle": "Read all conversations across roles.",
            "threads": threads,
            "thread_cards": thread_cards,
            "active_card": active_card,
            "active_thread": active_thread,
            "thread_messages": thread_messages,
            "current_role": "admin",
            "communication_candidates": _communication_candidate_options(),
        },
    )


@login_required
def communication_bulk_email_view(request):
    return render(
        request,
        "dashboard/communication_center.html",
        {
            "comm_section": "bulk-email",
            "page_title": "Bulk Email",
            "page_subtitle": "Send email campaigns with subject, rich text editor, and attachments.",
            "communication_candidates": _communication_candidate_options(),
        },
    )


@login_required
def communication_bulk_sms_view(request):
    return render(
        request,
        "dashboard/communication_center.html",
        {
            "comm_section": "bulk-sms",
            "page_title": "Bulk SMS",
            "page_subtitle": "Send SMS messages with character limits and delivery reports.",
            "communication_candidates": _communication_candidate_options(),
        },
    )


@login_required
def communication_notifications_view(request):
    return render(
        request,
        "dashboard/communication_center.html",
        {
            "comm_section": "notifications",
            "page_title": "Notifications",
            "page_subtitle": "In-app alerts with read/unread tracking.",
            "communication_candidates": _communication_candidate_options(),
        },
    )


@login_required
def communication_whatsapp_view(request):
    return render(
        request,
        "dashboard/communication_center.html",
        {
            "comm_section": "whatsapp",
            "page_title": "WhatsApp Alerts",
            "page_subtitle": "Send approved WhatsApp templates with delivery status.",
            "communication_candidates": _communication_candidate_options(),
        },
    )


@login_required
def communication_templates_view(request):
    return render(
        request,
        "dashboard/communication_center.html",
        {
            "comm_section": "templates",
            "page_title": "Message Templates",
            "page_subtitle": "Reusable templates with dynamic variables for faster outreach.",
            "communication_candidates": _communication_candidate_options(),
        },
    )


@login_required
def communication_sent_history_view(request):
    return render(
        request,
        "dashboard/communication_center.html",
        {
            "comm_section": "sent-history",
            "page_title": "Sent History",
            "page_subtitle": "Track email, SMS, WhatsApp, and notification delivery status.",
            "communication_candidates": _communication_candidate_options(),
        },
    )


@login_required
def communication_scheduled_view(request):
    return render(
        request,
        "dashboard/communication_center.html",
        {
            "comm_section": "scheduled",
            "page_title": "Scheduled Messages",
            "page_subtitle": "Plan future sends with automatic delivery and cancellation options.",
            "communication_candidates": _communication_candidate_options(),
        },
    )


@login_required
def admin_profile_view(request, section="all"):
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect("dashboard:login")

    profile, _ = AdminProfile.objects.get_or_create(user=request.user)
    section = (section or "all").strip().lower()
    valid_sections = {"all", "profile", "photo", "password", "last-login"}
    if section not in valid_sections:
        section = "all"

    if request.method == "POST":
        action = (request.POST.get("action") or "update_profile").strip()
        if action == "update_profile":
            request.user.first_name = (request.POST.get("first_name") or "").strip()
            request.user.last_name = (request.POST.get("last_name") or "").strip()
            request.user.email = (request.POST.get("email") or "").strip()
            request.user.save(update_fields=["first_name", "last_name", "email"])
            profile.phone = (request.POST.get("phone") or "").strip()
            profile.bio = (request.POST.get("bio") or "").strip()
            profile.save(update_fields=["phone", "bio"])
            messages.success(request, "Profile details updated.")
            return redirect(request.path)

        if action == "upload_photo":
            if request.FILES.get("photo"):
                profile.photo = request.FILES["photo"]
                profile.save(update_fields=["photo"])
                messages.success(request, "Profile photo updated.")
            else:
                messages.error(request, "Please choose a photo to upload.")
            return redirect(request.path)

        if action == "remove_photo":
            if profile.photo:
                profile.photo.delete(save=False)
                profile.photo = None
                profile.save(update_fields=["photo"])
                messages.success(request, "Profile photo removed.")
            return redirect(request.path)

        if action == "change_password":
            password = (request.POST.get("password") or "").strip()
            confirm = (request.POST.get("confirm_password") or "").strip()
            if not password or password != confirm:
                messages.error(request, "Passwords do not match.")
            else:
                request.user.set_password(password)
                request.user.save()
                update_session_auth_hash(request, request.user)
                messages.success(request, "Password updated successfully.")
            return redirect(request.path)

    section_map = {
        "all": ("Profile & Security", "Update personal details, password, and profile photo."),
        "profile": ("My Profile", "Update your personal admin details."),
        "photo": ("Upload Photo", "Update your admin profile photo."),
        "password": ("Change Password", "Update your admin login password."),
        "last-login": ("Last Login", "Review the latest login activity for this account."),
    }
    page_title, page_subtitle = section_map.get(
        section, ("Profile & Security", "Update personal details, password, and profile photo.")
    )

    return render(
        request,
        "dashboard/admin_profile.html",
        {
            "profile": profile,
            "profile_section": section,
            "page_title": page_title,
            "page_subtitle": page_subtitle,
        },
    )


@login_required
def grievance_reports_view(request):
    return render(
        request,
        "dashboard/grievance_reports.html",
        {
            "grievance_section": "complaints",
            "page_title": "User Complaints",
            "page_subtitle": "Track and resolve user account, payment, and login issues.",
        },
    )


@login_required
def grievance_complaints_view(request):
    return render(
        request,
        "dashboard/grievance_reports.html",
        {
            "grievance_section": "complaints",
            "page_title": "User Complaints",
            "page_subtitle": "Track and resolve user account, payment, and login issues.",
        },
    )


@login_required
def grievance_job_reports_view(request):
    return render(
        request,
        "dashboard/grievance_reports.html",
        {
            "grievance_section": "job-reports",
            "page_title": "Job Reports",
            "page_subtitle": "Review reported jobs and take action.",
        },
    )


@login_required
def grievance_abuse_fraud_view(request):
    return render(
        request,
        "dashboard/grievance_reports.html",
        {
            "grievance_section": "abuse-fraud",
            "page_title": "Abuse / Fraud",
            "page_subtitle": "Investigate fraud, harassment, and misuse cases.",
        },
    )


@login_required
def grievance_resolution_log_view(request):
    return render(
        request,
        "dashboard/grievance_reports.html",
        {
            "grievance_section": "resolution-log",
            "page_title": "Resolution Log",
            "page_subtitle": "Audit trail of actions and resolutions.",
        },
    )


@login_required
def security_login_history_view(request):
    login_qs = LoginHistory.objects.order_by("-created_at")
    total_logins = login_qs.count()
    success_count = login_qs.filter(is_success=True).count()
    failed_count = total_logins - success_count
    login_entries = login_qs[:100]
    return render(
        request,
        "dashboard/security_audit.html",
        {
            "audit_section": "login-history",
            "page_title": "Login History",
            "page_subtitle": "Track admin and user access sessions in real time.",
            "login_entries": login_entries,
            "total_logins": total_logins,
            "success_count": success_count,
            "failed_count": failed_count,
        },
    )


@login_required
def security_ip_logs_view(request):
    return render(
        request,
        "dashboard/security_audit.html",
        {
            "audit_section": "ip-logs",
            "page_title": "IP Logs",
            "page_subtitle": "Monitor IP activity for logins, jobs, payments, and complaints.",
        },
    )


@login_required
def security_admin_activity_view(request):
    return render(
        request,
        "dashboard/security_audit.html",
        {
            "audit_section": "admin-activity",
            "page_title": "Admin Activity Logs",
            "page_subtitle": "Review approvals, suspensions, and configuration changes.",
        },
    )


@login_required
def security_role_permissions_view(request):
    return render(
        request,
        "dashboard/security_audit.html",
        {
            "audit_section": "role-permissions",
            "page_title": "Role Permissions",
            "page_subtitle": "Manage sub-admin access and permission controls.",
        },
    )


@login_required
def settings_platform_view(request):
    return render(
        request,
        "dashboard/settings.html",
        {
            "settings_section": "platform",
            "page_title": "Platform Settings",
            "page_subtitle": "Manage branding, payments, communications, and security controls.",
        },
    )


@login_required
def settings_job_categories_view(request):
    return render(
        request,
        "dashboard/settings.html",
        {
            "settings_section": "job-categories",
            "page_title": "Job Categories",
            "page_subtitle": "Configure categories that appear in the job posting dropdown.",
        },
    )


@login_required
def settings_locations_view(request):
    return render(
        request,
        "dashboard/settings.html",
        {
            "settings_section": "locations",
            "page_title": "Locations",
            "page_subtitle": "Maintain country, state, and city data for posting and filtering.",
        },
    )


@login_required
def settings_skills_view(request):
    return render(
        request,
        "dashboard/settings.html",
        {
            "settings_section": "skills",
            "page_title": "Skills Library",
            "page_subtitle": "Centralize skills for employer selections and candidate matching.",
        },
    )


@login_required
def settings_experience_levels_view(request):
    return render(
        request,
        "dashboard/settings.html",
        {
            "settings_section": "experience-levels",
            "page_title": "Experience Levels",
            "page_subtitle": "Define experience ranges and report thresholds.",
        },
    )


def _get_model(user_type: str):
    return {
        "companies": Company,
        "consultancies": Consultancy,
        "candidates": Candidate,
    }.get(user_type)


def _serialize_user(obj, user_type: str):
    plan = getattr(obj, "plan_name", "") or "N/A"
    payload = {
        "id": obj.id,
        "name": obj.name,
        "email": obj.email,
        "phone": obj.phone,
        "location": obj.location,
        "contact_position": getattr(obj, "contact_position", ""),
        "owner_name": getattr(obj, "owner_name", ""),
        "kyc_status": obj.kyc_status,
        "account_status": obj.account_status,
        "subscription_plan": plan,
        "registered_date": obj.registration_date.strftime("%Y-%m-%d"),
    }
    if user_type == "consultancies":
        doc_fields = [
            getattr(obj, "registration_certificate", None),
            getattr(obj, "gst_certificate", None),
            getattr(obj, "pan_card", None),
            getattr(obj, "address_proof", None),
        ]
        payload["document_status"] = "Uploaded" if any(doc_fields) else "Missing"
    if user_type == "candidates":
        payload["resume_status"] = "Available" if getattr(obj, "resume", None) else "Missing"
    return payload


def _serialize_user_detail(obj, user_type: str):
    payload = {
        "id": obj.id,
        "name": obj.name,
        "email": obj.email,
        "phone": obj.phone,
        "location": obj.location,
        "address": obj.address,
        "account_type": obj.account_type,
        "profile_completion": obj.profile_completion,
        "kyc_status": obj.kyc_status,
        "account_status": obj.account_status,
        "warning_count": obj.warning_count,
        "suspension_reason": obj.suspension_reason,
        "registered_date": obj.registration_date.strftime("%Y-%m-%d"),
    }

    if user_type in ["companies", "consultancies"]:
        payload.update(
            {
                "plan_name": getattr(obj, "plan_name", ""),
                "plan_type": getattr(obj, "plan_type", ""),
                "plan_start": getattr(obj, "plan_start", None),
                "plan_expiry": getattr(obj, "plan_expiry", None),
                "payment_status": getattr(obj, "payment_status", ""),
                "auto_renew": getattr(obj, "auto_renew", False),
                "contact_position": getattr(obj, "contact_position", ""),
            }
        )
    if user_type == "consultancies":
        payload.update(
            {
                "company_type": getattr(obj, "company_type", ""),
                "registration_number": getattr(obj, "registration_number", ""),
                "gst_number": getattr(obj, "gst_number", ""),
                "year_established": getattr(obj, "year_established", None),
                "website_url": getattr(obj, "website_url", ""),
                "alt_phone": getattr(obj, "alt_phone", ""),
                "office_landline": getattr(obj, "office_landline", ""),
                "address_line1": getattr(obj, "address_line1", ""),
                "address_line2": getattr(obj, "address_line2", ""),
                "city": getattr(obj, "city", ""),
                "state": getattr(obj, "state", ""),
                "pin_code": getattr(obj, "pin_code", ""),
                "country": getattr(obj, "country", ""),
                "owner_name": getattr(obj, "owner_name", ""),
                "owner_designation": getattr(obj, "owner_designation", ""),
                "owner_phone": getattr(obj, "owner_phone", ""),
                "owner_email": getattr(obj, "owner_email", ""),
                "owner_pan": getattr(obj, "owner_pan", ""),
                "owner_aadhaar": getattr(obj, "owner_aadhaar", ""),
                "consultancy_type": getattr(obj, "consultancy_type", ""),
                "industries_served": getattr(obj, "industries_served", ""),
                "service_charges": getattr(obj, "service_charges", ""),
                "areas_of_operation": getattr(obj, "areas_of_operation", ""),
            }
        )

    if user_type == "companies":
        payload.update(
            {
                "gst_number": obj.gst_number,
                "cin_number": obj.cin_number,
            }
        )
    elif user_type == "consultancies":
        payload.update(
            {
                "license_number": obj.license_number,
            }
        )
    else:
        payload.update(
            {
                "date_of_birth": obj.date_of_birth,
                "resume_status": "Available" if getattr(obj, "resume", None) else "Missing",
            }
        )

    return payload


def _apply_common_fields(obj, data, files):
    obj.name = data.get("name", "").strip()
    obj.email = data.get("email", "").strip()
    obj.phone = data.get("phone", "").strip()
    password = data.get("password", "").strip()
    if password:
        obj.password = _hash_password(password)
    obj.location = data.get("location", "").strip()
    obj.address = data.get("address", "").strip()
    if hasattr(obj, "contact_position"):
        obj.contact_position = data.get("contact_position", "").strip()
    obj.account_type = data.get("account_type", "").strip()
    obj.profile_completion = int(data.get("profile_completion") or 0)
    obj.kyc_status = data.get("kyc_status", "Pending")
    obj.account_status = data.get("account_status", "Active")
    obj.warning_count = int(data.get("warning_count") or 0)
    obj.suspension_reason = data.get("suspension_reason", "").strip()

    profile_image = files.get("profile_image")
    if profile_image:
        obj.profile_image = profile_image


def _apply_user_subscription_fields(obj, data):
    obj.plan_name = data.get("plan_name", "").strip()
    obj.plan_type = data.get("plan_type", "").strip()
    obj.plan_start = parse_date(data.get("plan_start")) if data.get("plan_start") else None
    obj.plan_expiry = parse_date(data.get("plan_expiry")) if data.get("plan_expiry") else None
    obj.payment_status = data.get("payment_status", "").strip()
    obj.auto_renew = data.get("auto_renew") in ["on", "true", "1"]


@login_required
@require_http_methods(["GET"])
def api_user_list(request, user_type):
    model = _get_model(user_type)
    if not model:
        return JsonResponse({"error": "Invalid user type"}, status=400)

    qs = model.objects.all().order_by("-id")
    search = request.GET.get("search", "").strip()
    if search:
        qs = qs.filter(
            Q(name__icontains=search)
            | Q(email__icontains=search)
            | Q(phone__icontains=search)
            | Q(location__icontains=search)
        )

    kyc = request.GET.get("kyc", "all")
    if kyc != "all":
        qs = qs.filter(kyc_status=kyc)

    status = request.GET.get("status", "all")
    if status != "all":
        qs = qs.filter(account_status=status)

    plan = request.GET.get("plan", "all")
    if plan != "all" and user_type in ["companies", "consultancies"]:
        qs = qs.filter(plan_type=plan)

    page = int(request.GET.get("page", 1))
    page_size = int(request.GET.get("page_size", 10))
    paginator = Paginator(qs, page_size)
    page_obj = paginator.get_page(page)

    data = [_serialize_user(obj, user_type) for obj in page_obj.object_list]
    return JsonResponse(
        {
            "results": data,
            "page": page_obj.number,
            "pages": paginator.num_pages,
            "count": paginator.count,
        }
    )


@login_required
@require_http_methods(["POST"])
def api_user_create(request, user_type):
    model = _get_model(user_type)
    if not model:
        return JsonResponse({"success": False, "error": "Invalid user type"}, status=400)

    obj = model()
    _apply_common_fields(obj, request.POST, request.FILES)

    if user_type == "companies":
        obj.gst_number = request.POST.get("gst_number", "").strip()
        obj.cin_number = request.POST.get("cin_number", "").strip()
        doc = request.FILES.get("registration_document")
        if doc:
            obj.registration_document = doc
        _apply_user_subscription_fields(obj, request.POST)
    elif user_type == "consultancies":
        obj.license_number = request.POST.get("license_number", "").strip()
        obj.company_type = request.POST.get("company_type", "").strip()
        obj.registration_number = request.POST.get("registration_number", "").strip()
        obj.gst_number = request.POST.get("gst_number", "").strip()
        obj.year_established = _parse_int(request.POST.get("year_established"))
        obj.website_url = request.POST.get("website_url", "").strip()
        obj.alt_phone = request.POST.get("alt_phone", "").strip()
        obj.office_landline = request.POST.get("office_landline", "").strip()
        obj.address_line1 = request.POST.get("address_line1", "").strip()
        obj.address_line2 = request.POST.get("address_line2", "").strip()
        obj.city = request.POST.get("city", "").strip()
        obj.state = request.POST.get("state", "").strip()
        obj.pin_code = request.POST.get("pin_code", "").strip()
        obj.country = request.POST.get("country", "").strip()
        obj.owner_name = request.POST.get("owner_name", "").strip()
        obj.owner_designation = request.POST.get("owner_designation", "").strip()
        obj.owner_phone = request.POST.get("owner_phone", "").strip()
        obj.owner_email = request.POST.get("owner_email", "").strip()
        obj.owner_pan = request.POST.get("owner_pan", "").strip()
        obj.owner_aadhaar = request.POST.get("owner_aadhaar", "").strip()
        obj.consultancy_type = request.POST.get("consultancy_type", "").strip()
        obj.industries_served = request.POST.get("industries_served", "").strip()
        obj.service_charges = request.POST.get("service_charges", "").strip()
        obj.areas_of_operation = request.POST.get("areas_of_operation", "").strip()
        cert = request.FILES.get("registration_certificate")
        if cert:
            obj.registration_certificate = cert
        gst_cert = request.FILES.get("gst_certificate")
        if gst_cert:
            obj.gst_certificate = gst_cert
        pan_card = request.FILES.get("pan_card")
        if pan_card:
            obj.pan_card = pan_card
        address_proof = request.FILES.get("address_proof")
        if address_proof:
            obj.address_proof = address_proof
        _apply_user_subscription_fields(obj, request.POST)
    else:
        obj.date_of_birth = parse_date(request.POST.get("date_of_birth")) if request.POST.get("date_of_birth") else None
        resume = request.FILES.get("resume")
        if resume:
            obj.resume = resume
        id_proof = request.FILES.get("id_proof")
        if id_proof:
            obj.id_proof = id_proof

    obj.save()
    return JsonResponse({"success": True, "item": _serialize_user(obj, user_type)})


@login_required
@require_http_methods(["POST"])
def api_user_update(request, user_type, pk):
    model = _get_model(user_type)
    if not model:
        return JsonResponse({"success": False, "error": "Invalid user type"}, status=400)

    obj = get_object_or_404(model, pk=pk)
    _apply_common_fields(obj, request.POST, request.FILES)

    if user_type == "companies":
        obj.gst_number = request.POST.get("gst_number", "").strip()
        obj.cin_number = request.POST.get("cin_number", "").strip()
        doc = request.FILES.get("registration_document")
        if doc:
            obj.registration_document = doc
        _apply_user_subscription_fields(obj, request.POST)
    elif user_type == "consultancies":
        obj.license_number = request.POST.get("license_number", "").strip()
        obj.company_type = request.POST.get("company_type", "").strip()
        obj.registration_number = request.POST.get("registration_number", "").strip()
        obj.gst_number = request.POST.get("gst_number", "").strip()
        obj.year_established = _parse_int(request.POST.get("year_established"))
        obj.website_url = request.POST.get("website_url", "").strip()
        obj.alt_phone = request.POST.get("alt_phone", "").strip()
        obj.office_landline = request.POST.get("office_landline", "").strip()
        obj.address_line1 = request.POST.get("address_line1", "").strip()
        obj.address_line2 = request.POST.get("address_line2", "").strip()
        obj.city = request.POST.get("city", "").strip()
        obj.state = request.POST.get("state", "").strip()
        obj.pin_code = request.POST.get("pin_code", "").strip()
        obj.country = request.POST.get("country", "").strip()
        obj.owner_name = request.POST.get("owner_name", "").strip()
        obj.owner_designation = request.POST.get("owner_designation", "").strip()
        obj.owner_phone = request.POST.get("owner_phone", "").strip()
        obj.owner_email = request.POST.get("owner_email", "").strip()
        obj.owner_pan = request.POST.get("owner_pan", "").strip()
        obj.owner_aadhaar = request.POST.get("owner_aadhaar", "").strip()
        obj.consultancy_type = request.POST.get("consultancy_type", "").strip()
        obj.industries_served = request.POST.get("industries_served", "").strip()
        obj.service_charges = request.POST.get("service_charges", "").strip()
        obj.areas_of_operation = request.POST.get("areas_of_operation", "").strip()
        cert = request.FILES.get("registration_certificate")
        if cert:
            obj.registration_certificate = cert
        gst_cert = request.FILES.get("gst_certificate")
        if gst_cert:
            obj.gst_certificate = gst_cert
        pan_card = request.FILES.get("pan_card")
        if pan_card:
            obj.pan_card = pan_card
        address_proof = request.FILES.get("address_proof")
        if address_proof:
            obj.address_proof = address_proof
        _apply_user_subscription_fields(obj, request.POST)
    else:
        obj.date_of_birth = parse_date(request.POST.get("date_of_birth")) if request.POST.get("date_of_birth") else None
        resume = request.FILES.get("resume")
        if resume:
            obj.resume = resume
        id_proof = request.FILES.get("id_proof")
        if id_proof:
            obj.id_proof = id_proof

    obj.save()
    return JsonResponse({"success": True, "item": _serialize_user(obj, user_type)})


@login_required
@require_http_methods(["POST"])
def api_user_delete(request, user_type, pk):
    model = _get_model(user_type)
    if not model:
        return JsonResponse({"success": False, "error": "Invalid user type"}, status=400)
    obj = get_object_or_404(model, pk=pk)
    obj.delete()
    return JsonResponse({"success": True})


@login_required
@require_http_methods(["POST"])
def api_user_bulk_delete(request, user_type):
    model = _get_model(user_type)
    if not model:
        return JsonResponse({"success": False, "error": "Invalid user type"}, status=400)
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        payload = {}
    ids = payload.get("ids", [])
    model.objects.filter(id__in=ids).delete()
    return JsonResponse({"success": True})


@login_required
@require_http_methods(["POST"])
def api_user_status(request, user_type, pk):
    model = _get_model(user_type)
    if not model:
        return JsonResponse({"success": False, "error": "Invalid user type"}, status=400)
    obj = get_object_or_404(model, pk=pk)
    status = request.POST.get("account_status", "Active")
    obj.account_status = status
    obj.save(update_fields=["account_status"])
    return JsonResponse({"success": True})


@login_required
@require_http_methods(["POST"])
def api_user_kyc(request, user_type, pk):
    model = _get_model(user_type)
    if not model:
        return JsonResponse({"success": False, "error": "Invalid user type"}, status=400)
    obj = get_object_or_404(model, pk=pk)
    kyc_status = request.POST.get("kyc_status")
    if not kyc_status:
        return JsonResponse({"success": False, "error": "Missing KYC status"}, status=400)
    obj.kyc_status = kyc_status
    obj.save(update_fields=["kyc_status"])
    return JsonResponse({"success": True, "item": _serialize_user(obj, user_type)})


@login_required
@require_http_methods(["GET"])
def api_user_detail(request, user_type, pk):
    model = _get_model(user_type)
    if not model:
        return JsonResponse({"success": False, "error": "Invalid user type"}, status=400)
    obj = get_object_or_404(model, pk=pk)

    detail = _serialize_user_detail(obj, user_type)

    documents = []

    def _append_doc(label, field):
        if not field:
            return
        try:
            url = field.url
        except ValueError:
            url = ""
        documents.append({"label": label, "value": field.name, "url": url})

    _append_doc("Profile Image", obj.profile_image)
    if user_type == "companies":
        _append_doc("Registration Document", getattr(obj, "registration_document", None))
    if user_type == "consultancies":
        _append_doc("Registration Certificate", getattr(obj, "registration_certificate", None))
        _append_doc("GST Certificate", getattr(obj, "gst_certificate", None))
        _append_doc("PAN Card", getattr(obj, "pan_card", None))
        _append_doc("Office Address Proof", getattr(obj, "address_proof", None))
    if user_type == "candidates":
        _append_doc("Resume", getattr(obj, "resume", None))

    payload = {
        "item": detail,
        "documents": documents,
        "kyc_history": [],
        "status_history": [],
        "jobs": [],
        "payments": [],
        "complaints": [],
        "logins": [],
    }
    if user_type == "candidates":
        selections = []
        selected_apps = (
            Application.objects.filter(candidate_email__iexact=obj.email, status__in=SELECTED_STATUSES)
            .select_related("consultancy", "job")
            .order_by("-updated_at")
        )
        for app in selected_apps:
            selected_by = app.consultancy.name if app.consultancy else app.company
            salary = app.offer_package or (app.job.salary if app.job else "") or app.expected_salary
            selections.append(
                {
                    "selected_by": selected_by or "-",
                    "company": app.company or "-",
                    "position": app.job_title or "-",
                    "salary": salary or "-",
                    "status": app.status or "-",
                    "date": app.updated_at.strftime("%Y-%m-%d") if app.updated_at else "",
                }
            )
        payload["selections"] = selections
    return JsonResponse(payload)


@login_required
@require_http_methods(["GET"])
def api_user_export(request, user_type):
    model = _get_model(user_type)
    if not model:
        return JsonResponse({"success": False, "error": "Invalid user type"}, status=400)

    qs = model.objects.all().order_by("-id")
    search = request.GET.get("search", "").strip()
    if search:
        qs = qs.filter(
            Q(name__icontains=search)
            | Q(email__icontains=search)
            | Q(phone__icontains=search)
            | Q(location__icontains=search)
        )
    kyc = request.GET.get("kyc", "all")
    if kyc != "all":
        qs = qs.filter(kyc_status=kyc)
    status = request.GET.get("status", "all")
    if status != "all":
        qs = qs.filter(account_status=status)
    plan = request.GET.get("plan", "all")
    if plan != "all" and user_type in ["companies", "consultancies"]:
        qs = qs.filter(plan_type=plan)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename=\"{user_type}.csv\"'
    writer = csv.writer(response)
    writer.writerow(
        [
            "ID",
            "Name",
            "Email",
            "Phone",
            "Location",
            "KYC Status",
            "Account Status",
            "Subscription Plan",
            "Registered Date",
        ]
    )
    for obj in qs:
        row = _serialize_user(obj, user_type)
        writer.writerow(
            [
                row["id"],
                row["name"],
                row["email"],
                row["phone"],
                row["location"],
                row["kyc_status"],
                row["account_status"],
                row["subscription_plan"],
                row["registered_date"],
            ]
        )
    return response


def _generate_prefixed_id(prefix, base, model, field_name):
    last = model.objects.order_by("-id").first()
    if not last:
        return f"{prefix}-{base}"
    last_value = getattr(last, field_name, "") or ""
    if last_value.startswith(f"{prefix}-"):
        tail = last_value.split("-")[-1]
        if tail.isdigit():
            return f"{prefix}-{int(tail) + 1}"
    return f"{prefix}-{base + last.id}"


def _serialize_job(job):
    return {
        "id": job.job_id,
        "title": job.title,
        "company": job.company,
        "category": job.category,
        "location": job.location,
        "job_type": job.job_type,
        "salary": job.salary,
        "experience": job.experience,
        "skills": job.skills,
        "posted_date": job.posted_date.strftime("%Y-%m-%d") if job.posted_date else "",
        "status": job.status,
        "lifecycle_status": _consultancy_job_status(job),
        "applicants": job.applicants,
        "verification": job.verification,
        "featured": job.featured,
        "recruiter_name": job.recruiter_name,
        "recruiter_email": job.recruiter_email,
        "recruiter_phone": job.recruiter_phone,
        "description": job.description,
        "requirements": job.requirements,
    }


def _apply_job_fields(job, data):
    job.title = data.get("title", "").strip()
    job.company = data.get("company", "").strip()
    job.category = data.get("category", "").strip()
    job.location = data.get("location", "").strip()
    job.job_type = data.get("job_type", "Full-time").strip()
    job.salary = data.get("salary", "").strip()
    job.experience = data.get("experience", "").strip()
    job.skills = data.get("skills", "").strip()
    job.posted_date = parse_date(data.get("posted_date")) if data.get("posted_date") else None
    job.status = data.get("status", "Pending").strip()
    if "applicants" in data:
        job.applicants = int(data.get("applicants") or 0)
    elif not job.pk:
        job.applicants = 0
    job.verification = data.get("verification", "Pending").strip()
    job.featured = data.get("featured") in ["on", "true", "1"]
    job.recruiter_name = data.get("recruiter_name", "").strip()
    job.recruiter_email = data.get("recruiter_email", "").strip()
    job.recruiter_phone = data.get("recruiter_phone", "").strip()
    job.description = data.get("description", "").strip()
    job.requirements = data.get("requirements", "").strip()
    lifecycle_status = data.get("lifecycle_status")
    if lifecycle_status:
        job.lifecycle_status = _normalize_consultancy_job_lifecycle(lifecycle_status)
    elif not getattr(job, "lifecycle_status", ""):
        job.lifecycle_status = STATUS_TO_CONSULTANCY_JOB_LIFECYCLE.get(job.status, "Draft")


@login_required
@require_http_methods(["GET"])
def api_jobs_list(request):
    base_qs = Job.objects.all()
    qs = base_qs.order_by("-id")
    search = request.GET.get("search", "").strip()
    if search:
        qs = qs.filter(
            Q(title__icontains=search)
            | Q(company__icontains=search)
            | Q(category__icontains=search)
            | Q(location__icontains=search)
        )
    status = request.GET.get("status", "all")
    if status != "all":
        qs = qs.filter(status=status)

    page = int(request.GET.get("page", 1))
    page_size = int(request.GET.get("page_size", 8))
    paginator = Paginator(qs, page_size)
    page_obj = paginator.get_page(page)

    results = [_serialize_job(job) for job in page_obj.object_list]

    stats = {
        "total": base_qs.count(),
        "approved": base_qs.filter(status="Approved").count(),
        "pending": base_qs.filter(status="Pending").count(),
        "rejected": base_qs.filter(status="Rejected").count(),
        "reported": base_qs.filter(status="Reported").count(),
    }
    categories = list(
        base_qs.values("category")
        .annotate(count=Count("id"))
        .order_by("-count")[:5]
    )

    return JsonResponse(
        {
            "results": results,
            "page": page_obj.number,
            "pages": paginator.num_pages,
            "count": paginator.count,
            "stats": stats,
            "categories": categories,
        }
    )


@login_required
@require_http_methods(["POST"])
def api_jobs_create(request):
    job = Job()
    _apply_job_fields(job, request.POST)
    job.save()
    if not job.job_id:
        job.job_id = _generate_prefixed_id("JOB", 1001, Job, "job_id")
        job.save(update_fields=["job_id"])
    return JsonResponse({"success": True, "item": _serialize_job(job)})


@login_required
@require_http_methods(["POST"])
def api_jobs_update(request, job_id):
    job = get_object_or_404(Job, job_id=job_id)
    _apply_job_fields(job, request.POST)
    job.save()
    return JsonResponse({"success": True, "item": _serialize_job(job)})


@login_required
@require_http_methods(["POST"])
def api_jobs_delete(request, job_id):
    job = get_object_or_404(Job, job_id=job_id)
    job.delete()
    return JsonResponse({"success": True})


@login_required
@require_http_methods(["GET"])
def api_jobs_export(request):
    qs = Job.objects.all().order_by("-id")
    search = request.GET.get("search", "").strip()
    if search:
        qs = qs.filter(
            Q(title__icontains=search)
            | Q(company__icontains=search)
            | Q(category__icontains=search)
            | Q(location__icontains=search)
        )
    status = request.GET.get("status", "all")
    if status != "all":
        qs = qs.filter(status=status)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="jobs.csv"'
    writer = csv.writer(response)
    writer.writerow(
        [
            "Job ID",
            "Title",
            "Company",
            "Category",
            "Location",
            "Status",
            "Posted Date",
            "Applicants",
        ]
    )
    for job in qs:
        row = _serialize_job(job)
        writer.writerow(
            [
                row["id"],
                row["title"],
                row["company"],
                row["category"],
                row["location"],
                row["status"],
                row["posted_date"],
                row["applicants"],
            ]
        )
    return response


def _serialize_application(app):
    return {
        "id": app.application_id,
        "candidate_name": app.candidate_name,
        "candidate_email": app.candidate_email,
        "candidate_phone": app.candidate_phone,
        "candidate_location": app.candidate_location,
        "education": app.education,
        "experience": app.experience,
        "current_company": app.current_company,
        "notice_period": app.notice_period,
        "skills": app.skills,
        "expected_salary": app.expected_salary,
        "job_title": app.job_title,
        "company": app.company,
        "status": app.status,
        "applied_date": app.applied_date.strftime("%Y-%m-%d") if app.applied_date else "",
        "interview_date": app.interview_date.strftime("%Y-%m-%d") if app.interview_date else "",
        "interview_time": app.interview_time,
        "interviewer": app.interviewer,
        "interview_mode": app.interview_mode,
        "meeting_link": app.meeting_link,
        "offer_package": app.offer_package,
        "joining_date": app.joining_date.strftime("%Y-%m-%d") if app.joining_date else "",
        "notes": app.notes,
        "cover_letter": app.cover_letter,
        "internal_notes": app.internal_notes,
        "interview_feedback": app.interview_feedback,
        "rating": app.rating,
    }


def _apply_application_fields(app, data):
    app.candidate_name = data.get("candidate_name", "").strip()
    app.candidate_email = data.get("candidate_email", "").strip()
    app.candidate_phone = data.get("candidate_phone", "").strip()
    app.candidate_location = data.get("candidate_location", "").strip()
    app.education = data.get("education", "").strip()
    app.experience = data.get("experience", "").strip()
    app.current_company = data.get("current_company", "").strip()
    app.notice_period = data.get("notice_period", "").strip()
    app.skills = data.get("skills", "").strip()
    app.expected_salary = data.get("expected_salary", "").strip()
    app.job_title = data.get("job_title", "").strip()
    app.company = data.get("company", "").strip()
    app.status = data.get("status", "Applied").strip()
    placement_override = data.get("placement_status", "").strip()
    if placement_override:
        app.placement_status = placement_override
    else:
        app.placement_status = _sync_placement_status(app.status, app.placement_status)
    app.applied_date = parse_date(data.get("applied_date")) if data.get("applied_date") else None
    app.interview_date = parse_date(data.get("interview_date")) if data.get("interview_date") else None
    app.interview_time = data.get("interview_time", "").strip()
    app.interviewer = data.get("interviewer", "").strip()
    app.interview_mode = data.get("interview_mode", "").strip()
    app.meeting_link = data.get("meeting_link", "").strip()
    app.offer_package = data.get("offer_package", "").strip()
    app.joining_date = parse_date(data.get("joining_date")) if data.get("joining_date") else None
    app.notes = data.get("notes", "").strip()
    app.cover_letter = data.get("cover_letter", "").strip()
    app.internal_notes = data.get("internal_notes", "").strip()
    app.interview_feedback = data.get("interview_feedback", "").strip()
    rating_value = data.get("rating")
    app.rating = int(rating_value) if rating_value and str(rating_value).isdigit() else None


@login_required
@require_http_methods(["GET"])
def api_applications_list(request):
    base_qs = Application.objects.all()
    qs = base_qs.order_by("-id")
    search = request.GET.get("search", "").strip()
    if search:
        qs = qs.filter(
            Q(candidate_name__icontains=search)
            | Q(candidate_email__icontains=search)
            | Q(job_title__icontains=search)
            | Q(company__icontains=search)
            | Q(skills__icontains=search)
            | Q(cover_letter__icontains=search)
            | Q(internal_notes__icontains=search)
            | Q(interview_feedback__icontains=search)
            | Q(notes__icontains=search)
            | Q(current_company__icontains=search)
        )
    status = request.GET.get("status", "all")
    if status != "all":
        qs = qs.filter(status=status)

    page = int(request.GET.get("page", 1))
    page_size = int(request.GET.get("page_size", 8))
    paginator = Paginator(qs, page_size)
    page_obj = paginator.get_page(page)
    results = [_serialize_application(app) for app in page_obj.object_list]

    stats = {
        "total": base_qs.count(),
        "unique_jobs": base_qs.values("job_title").distinct().count(),
        "interview": base_qs.filter(status__in=INTERVIEW_STATUSES).count(),
        "selected": base_qs.filter(status__in=SELECTED_STATUSES).count(),
        "shortlisted": base_qs.filter(status="Shortlisted").count(),
        "rejected": base_qs.filter(status="Rejected").count(),
        "offer": base_qs.filter(status="Offer Issued").count(),
    }

    return JsonResponse(
        {
            "results": results,
            "page": page_obj.number,
            "pages": paginator.num_pages,
            "count": paginator.count,
            "stats": stats,
        }
    )


@login_required
@require_http_methods(["POST"])
def api_applications_create(request):
    app = Application()
    _apply_application_fields(app, request.POST)
    app.save()
    if not app.application_id:
        app.application_id = _generate_prefixed_id("APP", 1201, Application, "application_id")
        app.save(update_fields=["application_id"])
    return JsonResponse({"success": True, "item": _serialize_application(app)})


@login_required
@require_http_methods(["POST"])
def api_applications_update(request, application_id):
    app = get_object_or_404(Application, application_id=application_id)
    _apply_application_fields(app, request.POST)
    app.save()
    return JsonResponse({"success": True, "item": _serialize_application(app)})


@login_required
@require_http_methods(["POST"])
def api_applications_delete(request, application_id):
    app = get_object_or_404(Application, application_id=application_id)
    app.delete()
    return JsonResponse({"success": True})


@login_required
@require_http_methods(["GET"])
def api_applications_export(request):
    qs = Application.objects.all().order_by("-id")
    search = request.GET.get("search", "").strip()
    if search:
        qs = qs.filter(
            Q(candidate_name__icontains=search)
            | Q(candidate_email__icontains=search)
            | Q(job_title__icontains=search)
            | Q(company__icontains=search)
        )
    status = request.GET.get("status", "all")
    if status != "all":
        qs = qs.filter(status=status)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="applications.csv"'
    writer = csv.writer(response)
    writer.writerow(
        ["Application ID", "Candidate", "Email", "Job Title", "Company", "Status", "Applied Date"]
    )
    for app in qs:
        row = _serialize_application(app)
        writer.writerow(
            [
                row["id"],
                row["candidate_name"],
                row["candidate_email"],
                row["job_title"],
                row["company"],
                row["status"],
                row["applied_date"],
            ]
        )
    return response


def _serialize_subscription(sub):
    return {
        "id": sub.subscription_id,
        "name": sub.name,
        "account_type": sub.account_type,
        "plan": sub.plan,
        "payment_status": sub.payment_status,
        "start_date": sub.start_date.strftime("%Y-%m-%d") if sub.start_date else "",
        "expiry_date": sub.expiry_date.strftime("%Y-%m-%d") if sub.expiry_date else "",
        "contact": sub.contact,
        "monthly_revenue": sub.monthly_revenue,
        "auto_renew": sub.auto_renew,
    }


def _serialize_plan(plan):
    return {
        "id": plan.id,
        "name": plan.name,
        "plan_code": plan.plan_code,
        "price_monthly": plan.price_monthly,
        "price_quarterly": plan.price_quarterly,
        "job_posts": plan.job_posts,
        "job_validity": plan.job_validity,
        "resume_view": plan.resume_view,
        "resume_download": plan.resume_download,
        "candidate_chat": plan.candidate_chat,
        "interview_scheduler": plan.interview_scheduler,
        "auto_match": plan.auto_match,
        "shortlisting": plan.shortlisting,
        "candidate_ranking": plan.candidate_ranking,
        "candidate_pool_manager": plan.candidate_pool_manager,
        "featured_jobs": plan.featured_jobs,
        "company_branding": plan.company_branding,
        "analytics_dashboard": plan.analytics_dashboard,
        "support": plan.support,
        "dedicated_account_manager": plan.dedicated_account_manager,
    }


def _apply_plan_fields(plan, data):
    plan.name = data.get("name", "").strip()
    plan.plan_code = data.get("plan_code", "").strip()
    plan.price_monthly = int(data.get("price_monthly") or 0)
    plan.price_quarterly = int(data.get("price_quarterly") or 0)
    plan.job_posts = data.get("job_posts", "").strip()
    plan.job_validity = data.get("job_validity", "").strip()
    plan.resume_view = data.get("resume_view", "").strip()
    plan.resume_download = data.get("resume_download", "").strip()
    plan.candidate_chat = data.get("candidate_chat", "").strip()
    plan.interview_scheduler = data.get("interview_scheduler", "").strip()
    plan.auto_match = data.get("auto_match", "").strip()
    plan.shortlisting = data.get("shortlisting", "").strip()
    plan.candidate_ranking = data.get("candidate_ranking", "").strip()
    plan.candidate_pool_manager = data.get("candidate_pool_manager", "").strip()
    plan.featured_jobs = data.get("featured_jobs", "").strip()
    plan.company_branding = data.get("company_branding", "").strip()
    plan.analytics_dashboard = data.get("analytics_dashboard", "").strip()
    plan.support = data.get("support", "").strip()
    plan.dedicated_account_manager = data.get("dedicated_account_manager", "").strip()


def _apply_subscription_fields(sub, data):
    sub.name = data.get("name", "").strip()
    sub.account_type = data.get("account_type", "").strip()
    sub.plan = data.get("plan", "Free").strip()
    sub.payment_status = data.get("payment_status", "Free").strip()
    sub.start_date = parse_date(data.get("start_date")) if data.get("start_date") else None
    sub.expiry_date = parse_date(data.get("expiry_date")) if data.get("expiry_date") else None
    sub.contact = data.get("contact", "").strip()
    sub.monthly_revenue = int(data.get("monthly_revenue") or 0)
    sub.auto_renew = data.get("auto_renew") in ["on", "true", "1"]


@login_required
@require_http_methods(["GET"])
def api_plans_list(request):
    plans = SubscriptionPlan.objects.all().order_by("id")
    data = [_serialize_plan(plan) for plan in plans]
    return JsonResponse({"results": data})


@login_required
@require_http_methods(["POST"])
def api_plans_create(request):
    plan = SubscriptionPlan()
    _apply_plan_fields(plan, request.POST)
    if not plan.plan_code:
        return JsonResponse({"success": False, "error": "Plan code is required"}, status=400)
    try:
        plan.save()
    except IntegrityError:
        return JsonResponse({"success": False, "error": "Plan code already exists"}, status=400)
    return JsonResponse({"success": True, "item": _serialize_plan(plan)})


@login_required
@require_http_methods(["POST"])
def api_plans_update(request, plan_id):
    plan = get_object_or_404(SubscriptionPlan, pk=plan_id)
    _apply_plan_fields(plan, request.POST)
    if not plan.plan_code:
        return JsonResponse({"success": False, "error": "Plan code is required"}, status=400)
    try:
        plan.save()
    except IntegrityError:
        return JsonResponse({"success": False, "error": "Plan code already exists"}, status=400)
    return JsonResponse({"success": True, "item": _serialize_plan(plan)})


@login_required
@require_http_methods(["POST"])
def api_plans_delete(request, plan_id):
    plan = get_object_or_404(SubscriptionPlan, pk=plan_id)
    plan.delete()
    return JsonResponse({"success": True})


@login_required
@require_http_methods(["GET"])
def api_subscriptions_list(request):
    base_qs = Subscription.objects.all()
    qs = base_qs.order_by("-id")
    plan = request.GET.get("plan", "all")
    if plan != "all":
        qs = qs.filter(plan=plan)
    search = request.GET.get("search", "").strip()
    if search:
        qs = qs.filter(name__icontains=search)

    results = [_serialize_subscription(sub) for sub in qs]
    today = timezone.now().date()
    expiring = base_qs.filter(expiry_date__isnull=False, expiry_date__lte=today + timezone.timedelta(days=30)).count()
    stats = {
        "total": base_qs.count(),
        "paid": base_qs.exclude(plan="Free").count(),
        "free": base_qs.filter(plan="Free").count(),
        "expiring": expiring,
    }

    logs = SubscriptionLog.objects.select_related("subscription").order_by("-action_date")[:10]
    log_rows = [
        {
            "account": log.subscription.name,
            "old_plan": log.old_plan,
            "new_plan": log.new_plan,
            "admin": log.admin_name,
            "date": log.action_date.strftime("%Y-%m-%d"),
        }
        for log in logs
    ]

    return JsonResponse({"results": results, "stats": stats, "logs": log_rows})


@login_required
@require_http_methods(["POST"])
def api_subscriptions_create(request):
    sub = Subscription()
    _apply_subscription_fields(sub, request.POST)
    sub.save()
    if not sub.subscription_id:
        sub.subscription_id = _generate_prefixed_id("SUB", 401, Subscription, "subscription_id")
        sub.save(update_fields=["subscription_id"])
    return JsonResponse({"success": True, "item": _serialize_subscription(sub)})


@login_required
@require_http_methods(["POST"])
def api_subscriptions_update(request, subscription_id):
    sub = get_object_or_404(Subscription, subscription_id=subscription_id)
    old_plan = sub.plan
    _apply_subscription_fields(sub, request.POST)
    sub.save()
    if old_plan != sub.plan:
        SubscriptionLog.objects.create(
            subscription=sub,
            old_plan=old_plan,
            new_plan=sub.plan,
            admin_name=request.user.username or "Admin",
        )
    return JsonResponse({"success": True, "item": _serialize_subscription(sub)})


@login_required
@require_http_methods(["POST"])
def api_subscriptions_extend(request, subscription_id):
    sub = get_object_or_404(Subscription, subscription_id=subscription_id)
    months = int(request.POST.get("months") or 3)
    if sub.expiry_date:
        month = sub.expiry_date.month - 1 + months
        year = sub.expiry_date.year + month // 12
        month = month % 12 + 1
        day = min(sub.expiry_date.day, 28)
        sub.expiry_date = sub.expiry_date.replace(year=year, month=month, day=day)
        sub.save(update_fields=["expiry_date"])
    return JsonResponse({"success": True, "item": _serialize_subscription(sub)})


@login_required
@require_http_methods(["POST"])
def api_subscriptions_delete(request, subscription_id):
    sub = get_object_or_404(Subscription, subscription_id=subscription_id)
    sub.delete()
    return JsonResponse({"success": True})


@login_required
@require_http_methods(["GET"])
def api_dashboard_metrics(request):
    today = timezone.localdate()

    jobs = Job.objects.all()
    total_jobs = jobs.count()
    approved = jobs.filter(status="Approved").count()
    pending = jobs.filter(status="Pending").count()
    rejected = jobs.filter(status="Rejected").count()
    reported = jobs.filter(status="Reported").count()

    categories = list(
        jobs.values("category")
        .annotate(count=Count("id"))
        .order_by("-count")[:5]
    )

    applications = Application.objects.all()
    subscriptions = Subscription.objects.all()
    total_apps = applications.count()
    total_subs = subscriptions.count()

    total = max(total_jobs, 1)
    approved_pct = round((approved / total) * 100)
    pending_pct = round((pending / total) * 100)
    rejected_pct = max(0, 100 - approved_pct - pending_pct)

    company_count = Company.objects.count()
    consultancy_count = Consultancy.objects.count()
    candidate_count = Candidate.objects.count()
    recruiter_count = company_count + consultancy_count

    today_regs = (
        Company.objects.filter(registration_date__date=today).count()
        + Consultancy.objects.filter(registration_date__date=today).count()
        + Candidate.objects.filter(registration_date__date=today).count()
    )

    revenue_month = (
        subscriptions.exclude(plan="Free").aggregate(total=Sum("monthly_revenue")).get("total")
        or 0
    )

    def month_range(count=6):
        months = []
        year = today.year
        month = today.month
        for _ in range(count):
            months.append((year, month))
            month -= 1
            if month == 0:
                month = 12
                year -= 1
        months.reverse()
        return months

    def count_by_month(dates, months):
        counts = {key: 0 for key in months}
        for dt in dates:
            if not dt:
                continue
            key = (dt.year, dt.month)
            if key in counts:
                counts[key] += 1
        return [
            {"label": calendar.month_abbr[month], "count": counts[(year, month)]}
            for (year, month) in months
        ]

    months = month_range()
    job_dates = list(jobs.values_list("created_at", flat=True))
    candidate_dates = list(Candidate.objects.values_list("registration_date", flat=True))
    job_trend = count_by_month(job_dates, months)
    candidate_trend = count_by_month(candidate_dates, months)

    free_subs = subscriptions.filter(plan="Free").count()
    paid_subs = subscriptions.exclude(plan="Free").count()

    expiring_today = subscriptions.filter(expiry_date=today).count()
    suspicious_users = (
        Company.objects.filter(warning_count__gte=3).count()
        + Consultancy.objects.filter(warning_count__gte=3).count()
        + Candidate.objects.filter(warning_count__gte=3).count()
    )

    def format_dt(value):
        if not value:
            return ""
        if hasattr(value, "hour"):
            local_val = timezone.localtime(value) if timezone.is_aware(value) else value
            return local_val.strftime("%Y-%m-%d %H:%M")
        return value.strftime("%Y-%m-%d")

    latest_company = Company.objects.order_by("-registration_date").first()
    latest_consultancy = Consultancy.objects.order_by("-registration_date").first()
    latest_recruiter = None
    recruiter_candidates = [item for item in [latest_company, latest_consultancy] if item]
    if recruiter_candidates:
        latest_recruiter = max(recruiter_candidates, key=lambda item: item.registration_date)
    recruiter_url = (
        reverse("dashboard:consultancies")
        if isinstance(latest_recruiter, Consultancy)
        else reverse("dashboard:companies")
    )

    latest_job = Job.objects.order_by("-created_at").first()
    latest_payment_log = SubscriptionLog.objects.select_related("subscription").order_by(
        "-action_date",
        "-id",
    ).first()
    latest_paid_sub = subscriptions.exclude(plan="Free").order_by("-updated_at").first()

    payment_value = "-"
    payment_time = ""
    if latest_payment_log:
        payment_value = f"{latest_payment_log.subscription.name} -> {latest_payment_log.new_plan}"
        payment_time = format_dt(latest_payment_log.action_date)
    elif latest_paid_sub:
        payment_value = f"{latest_paid_sub.name} - {latest_paid_sub.plan}"
        payment_time = format_dt(latest_paid_sub.updated_at)

    recent_activity = [
        {
            "title": "New recruiter registered",
            "value": latest_recruiter.name if latest_recruiter else "-",
            "time": format_dt(latest_recruiter.registration_date) if latest_recruiter else "",
            "url": recruiter_url,
        },
        {
            "title": "New job posted",
            "value": latest_job.title if latest_job else "-",
            "time": format_dt(latest_job.created_at) if latest_job else "",
            "url": reverse("dashboard:jobs"),
        },
        {
            "title": "New payment",
            "value": payment_value,
            "time": payment_time,
            "url": reverse("dashboard:subscriptions"),
        },
        {
            "title": "New company",
            "value": latest_company.name if latest_company else "-",
            "time": format_dt(latest_company.registration_date) if latest_company else "",
            "url": reverse("dashboard:companies"),
        },
    ]

    return JsonResponse(
        {
            "jobs": {
                "total": total_jobs,
                "approved": approved,
                "pending": pending,
                "rejected": rejected,
                "reported": reported,
                "categories": categories,
            },
            "applications": {
            "total": total_apps,
            "interview": applications.filter(status__in=INTERVIEW_STATUSES).count(),
            "selected": applications.filter(status__in=SELECTED_STATUSES).count(),
            "shortlisted": applications.filter(status="Shortlisted").count(),
            "rejected": applications.filter(status="Rejected").count(),
            "offer": applications.filter(status="Offer Issued").count(),
        },
            "subscriptions": {
                "total": total_subs,
                "paid": paid_subs,
                "free": free_subs,
            },
            "status_percent": {
                "approved": approved_pct,
                "pending": pending_pct,
                "rejected": rejected_pct,
            },
            "overview": {
                "active_jobs": approved,
                "candidates": candidate_count,
                "recruiters": recruiter_count,
                "companies": company_count,
                "consultancies": consultancy_count,
                "todays_registrations": today_regs,
                "revenue_month": revenue_month,
            },
            "trends": {
                "job_postings": job_trend,
                "candidate_registrations": candidate_trend,
            },
            "conversion": {
                "free": free_subs,
                "paid": paid_subs,
            },
            "approval_ratio": {
                "approved": approved,
                "rejected": rejected,
            },
            "alerts": {
                "jobs_pending": pending,
                "complaints_waiting": 0,
                "expiring_today": expiring_today,
                "suspicious_users": suspicious_users,
            },
            "recent_activity": recent_activity,
        }
    )


def logout_view(request):
    logout(request)
    return redirect("dashboard:login")
