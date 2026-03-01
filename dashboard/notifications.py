from datetime import datetime

from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from .models import Application, AssignedJob, Candidate, Company, Consultancy, Interview, Message

ROLE_SEEN_SESSION_KEYS = {
    "candidate": "candidate_notifications_seen_at",
    "company": "company_notifications_seen_at",
    "consultancy": "consultancy_notifications_seen_at",
}


def _get_seen_at(request, role, account):
    key = ROLE_SEEN_SESSION_KEYS.get(role)
    raw_value = request.session.get(key) if key else None
    if raw_value:
        parsed = parse_datetime(raw_value)
        if parsed:
            if timezone.is_naive(parsed):
                return timezone.make_aware(parsed, timezone.get_current_timezone())
            return parsed
    if account and getattr(account, "last_login", None):
        return account.last_login
    return None


def _mark_unread(created_at, seen_at):
    if not created_at:
        return False
    if not seen_at:
        return True
    return created_at > seen_at


def _when_label(created_at):
    if not created_at:
        return "--"
    local_value = timezone.localtime(created_at) if timezone.is_aware(created_at) else created_at
    return local_value.strftime("%d %b %Y, %I:%M %p")


def _note(title, message, created_at, url="", unread=False):
    return {
        "title": title,
        "message": message,
        "created_at": created_at,
        "created_label": _when_label(created_at),
        "url": url or "",
        "unread": bool(unread),
    }


def _candidate_feed(candidate, seen_at):
    feed = []
    email = (candidate.email or "").strip()
    if not email:
        return feed

    status_map = {
        "Applied": "Application submitted",
        "Shortlisted": "You are shortlisted",
        "Interview": "Interview process started",
        "Interview Scheduled": "Interview scheduled",
        "Selected": "You are selected",
        "Offer Issued": "Offer issued",
        "Rejected": "Application update",
        "On Hold": "Application on hold",
        "Archived": "Application archived",
    }

    app_rows = Application.objects.filter(candidate_email__iexact=email).order_by("-updated_at", "-created_at")[:10]
    for app in app_rows:
        created_at = app.updated_at or app.created_at
        title = status_map.get(app.status, "Application update")
        message = f"{app.job_title} at {app.company} ({app.status})"
        feed.append(
            _note(
                title=title,
                message=message,
                created_at=created_at,
                url=reverse("dashboard:candidate_applications"),
                unread=_mark_unread(created_at, seen_at),
            )
        )

    interview_rows = (
        Interview.objects.filter(candidate_email__iexact=email).order_by("-updated_at", "-created_at")[:10]
    )
    interview_status = {
        "scheduled": "Interview scheduled",
        "rescheduled": "Interview rescheduled",
        "completed": "Interview completed",
        "cancelled": "Interview cancelled",
        "no_show": "Interview marked no show",
    }
    for interview in interview_rows:
        created_at = interview.updated_at or interview.created_at
        title = interview_status.get(interview.status, "Interview update")
        if interview.interview_date:
            message = f"{interview.job_title} on {interview.interview_date}"
        else:
            message = interview.job_title or "Interview status changed"
        feed.append(
            _note(
                title=title,
                message=message,
                created_at=created_at,
                url=reverse("dashboard:candidate_interviews"),
                unread=_mark_unread(created_at, seen_at),
            )
        )

    unread_messages = (
        Message.objects.filter(thread__candidate=candidate, is_read=False)
        .exclude(sender_role="candidate")
        .select_related("thread", "thread__company", "thread__consultancy", "thread__job")
        .order_by("-created_at")[:10]
    )
    for message in unread_messages:
        sender = "Recruiter"
        if message.thread and message.thread.company:
            sender = message.thread.company.name
        elif message.thread and message.thread.consultancy:
            sender = message.thread.consultancy.name
        preview = (message.body or "").strip()[:90] or "New message received."
        thread_id = message.thread_id
        message_url = reverse("dashboard:candidate_messages")
        if thread_id:
            message_url = f"{message_url}?thread={thread_id}"
        feed.append(
            _note(
                title=f"New message from {sender}",
                message=preview,
                created_at=message.created_at,
                url=message_url,
                unread=True,
            )
        )
    return feed


def _company_feed(company, seen_at):
    feed = []
    app_rows = Application.objects.filter(company__iexact=company.name).order_by("-updated_at", "-created_at")[:12]
    for app in app_rows:
        created_at = app.updated_at or app.created_at
        message = f"{app.candidate_name} for {app.job_title} ({app.status})"
        feed.append(
            _note(
                title="Application update",
                message=message,
                created_at=created_at,
                url=reverse("dashboard:company_applications"),
                unread=_mark_unread(created_at, seen_at),
            )
        )

    interview_rows = Interview.objects.filter(company__iexact=company.name).order_by("-updated_at", "-created_at")[:8]
    for interview in interview_rows:
        created_at = interview.updated_at or interview.created_at
        message = f"{interview.candidate_name} - {interview.job_title} ({interview.status})"
        feed.append(
            _note(
                title="Interview update",
                message=message,
                created_at=created_at,
                url=reverse("dashboard:company_interviews"),
                unread=_mark_unread(created_at, seen_at),
            )
        )

    unread_messages = (
        Message.objects.filter(thread__company=company, is_read=False)
        .exclude(sender_role="company")
        .select_related("thread", "thread__candidate", "thread__consultancy", "thread__job")
        .order_by("-created_at")[:10]
    )
    for message in unread_messages:
        sender = "Candidate"
        if message.thread and message.thread.candidate:
            sender = message.thread.candidate.name
        elif message.thread and message.thread.consultancy:
            sender = message.thread.consultancy.name
        preview = (message.body or "").strip()[:90] or "New message received."
        thread_id = message.thread_id
        message_url = reverse("dashboard:company_messages")
        if thread_id:
            message_url = f"{message_url}?thread={thread_id}"
        feed.append(
            _note(
                title=f"New message from {sender}",
                message=preview,
                created_at=message.created_at,
                url=message_url,
                unread=True,
            )
        )
    return feed


def _consultancy_feed(consultancy, seen_at):
    feed = []
    assignment_rows = (
        AssignedJob.objects.filter(consultancy=consultancy)
        .select_related("job")
        .order_by("-updated_at", "-assigned_date")[:10]
    )
    for assignment in assignment_rows:
        created_at = assignment.updated_at
        job_title = assignment.job.title if assignment.job else "Assigned job"
        company_name = assignment.job.company if assignment.job else "Company"
        message = f"{job_title} at {company_name} ({assignment.status})"
        feed.append(
            _note(
                title="Assigned job update",
                message=message,
                created_at=created_at,
                url=reverse("dashboard:consultancy_assigned_jobs"),
                unread=_mark_unread(created_at, seen_at),
            )
        )

    app_rows = Application.objects.filter(consultancy=consultancy).order_by("-updated_at", "-created_at")[:12]
    for app in app_rows:
        created_at = app.updated_at or app.created_at
        message = f"{app.candidate_name} - {app.job_title} ({app.status})"
        feed.append(
            _note(
                title="Application update",
                message=message,
                created_at=created_at,
                url=reverse("dashboard:consultancy_applications"),
                unread=_mark_unread(created_at, seen_at),
            )
        )

    unread_messages = (
        Message.objects.filter(thread__consultancy=consultancy, is_read=False)
        .exclude(sender_role="consultancy")
        .select_related("thread", "thread__candidate", "thread__company", "thread__job")
        .order_by("-created_at")[:10]
    )
    for message in unread_messages:
        sender = "Candidate"
        if message.thread and message.thread.candidate:
            sender = message.thread.candidate.name
        elif message.thread and message.thread.company:
            sender = message.thread.company.name
        preview = (message.body or "").strip()[:90] or "New message received."
        thread_id = message.thread_id
        message_url = reverse("dashboard:consultancy_messages")
        if thread_id:
            message_url = f"{message_url}?thread={thread_id}"
        feed.append(
            _note(
                title=f"New message from {sender}",
                message=preview,
                created_at=message.created_at,
                url=message_url,
                unread=True,
            )
        )
    return feed


def build_panel_notifications(request, limit=8):
    role = None
    account = None
    candidate_id = request.session.get("candidate_id")
    company_id = request.session.get("company_id")
    consultancy_id = request.session.get("consultancy_id")
    url_name = getattr(getattr(request, "resolver_match", None), "url_name", "") or ""

    if url_name.startswith("candidate_") and candidate_id:
        role = "candidate"
        account = Candidate.objects.filter(id=candidate_id).only("id", "email", "last_login").first()
    elif url_name.startswith("company_") and company_id:
        role = "company"
        account = Company.objects.filter(id=company_id).only("id", "name", "last_login").first()
    elif url_name.startswith("consultancy_") and consultancy_id:
        role = "consultancy"
        account = Consultancy.objects.filter(id=consultancy_id).only("id", "name", "last_login").first()
    elif candidate_id:
        role = "candidate"
        account = Candidate.objects.filter(id=candidate_id).only("id", "email", "last_login").first()
    elif company_id:
        role = "company"
        account = Company.objects.filter(id=company_id).only("id", "name", "last_login").first()
    elif consultancy_id:
        role = "consultancy"
        account = Consultancy.objects.filter(id=consultancy_id).only("id", "name", "last_login").first()

    if not role or not account:
        return {"role": None, "items": [], "unread_count": 0}

    seen_at = _get_seen_at(request, role, account)
    if role == "candidate":
        items = _candidate_feed(account, seen_at)
    elif role == "company":
        items = _company_feed(account, seen_at)
    else:
        items = _consultancy_feed(account, seen_at)

    fallback_dt = timezone.make_aware(datetime(1970, 1, 1))
    items.sort(key=lambda row: row.get("created_at") or fallback_dt, reverse=True)
    items = items[:limit]
    unread_count = sum(1 for row in items if row.get("unread"))
    return {"role": role, "items": items, "unread_count": unread_count}


def mark_panel_notifications_seen(request, role=None):
    selected_role = role
    if not selected_role:
        if request.session.get("candidate_id"):
            selected_role = "candidate"
        elif request.session.get("company_id"):
            selected_role = "company"
        elif request.session.get("consultancy_id"):
            selected_role = "consultancy"
    key = ROLE_SEEN_SESSION_KEYS.get(selected_role)
    if not key:
        return
    request.session[key] = timezone.now().isoformat()
    request.session.modified = True
