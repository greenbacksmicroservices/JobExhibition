from datetime import datetime, time as dt_time, timedelta
from urllib.parse import urlencode

from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from .models import Application, AssignedJob, Candidate, Company, Consultancy, Interview, Message

MAX_STORED_SEEN_NOTIFICATION_IDS = 1000

ROLE_SEEN_SESSION_KEYS = {
    "candidate": "candidate_notifications_seen_at",
    "company": "company_notifications_seen_at",
    "consultancy": "consultancy_notifications_seen_at",
    "admin": "admin_notifications_seen_at",
}

ROLE_SEEN_ITEM_SESSION_KEYS = {
    "candidate": "candidate_notification_seen_ids",
    "company": "company_notification_seen_ids",
    "consultancy": "consultancy_notification_seen_ids",
    "admin": "admin_notification_seen_ids",
}


def _resolve_panel_role(request, explicit_role=None):
    if explicit_role in {"candidate", "company", "consultancy", "admin"}:
        return explicit_role, True

    if request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser):
        return "admin", True
    if request.session.get("candidate_id"):
        return "candidate", True
    if request.session.get("company_id"):
        return "company", True
    if request.session.get("consultancy_id"):
        return "consultancy", True
    return None, False


def _get_seen_at(request, role):
    key = ROLE_SEEN_SESSION_KEYS.get(role)
    raw_value = request.session.get(key) if key else None
    if raw_value:
        parsed = parse_datetime(raw_value)
        if parsed:
            if timezone.is_naive(parsed):
                return timezone.make_aware(parsed, timezone.get_current_timezone())
            return parsed
    return None


def _get_seen_item_ids(request, role):
    key = ROLE_SEEN_ITEM_SESSION_KEYS.get(role)
    raw_items = request.session.get(key) if key else []
    if not isinstance(raw_items, list):
        return set()
    return {str(item).strip() for item in raw_items if str(item).strip()}


def _append_seen_item_ids(request, role, item_ids):
    key = ROLE_SEEN_ITEM_SESSION_KEYS.get(role)
    if not key:
        return

    cleaned_ids = [str(item).strip() for item in (item_ids or []) if str(item).strip()]
    if not cleaned_ids:
        return

    existing = request.session.get(key)
    if not isinstance(existing, list):
        existing = []
    existing_clean = [str(item).strip() for item in existing if str(item).strip()]
    seen_set = set(existing_clean)

    for item_id in cleaned_ids:
        if item_id not in seen_set:
            existing_clean.append(item_id)
            seen_set.add(item_id)

    if len(existing_clean) > MAX_STORED_SEEN_NOTIFICATION_IDS:
        existing_clean = existing_clean[-MAX_STORED_SEEN_NOTIFICATION_IDS:]

    request.session[key] = existing_clean
    request.session.modified = True


def _mark_unread(created_at, seen_at, note_id, seen_item_ids):
    if note_id and note_id in seen_item_ids:
        return False
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


def _notification_id(prefix, primary_id, created_at=None, suffix=""):
    parts = [str(prefix or "note"), str(primary_id or "0")]
    if created_at:
        local_value = timezone.localtime(created_at) if timezone.is_aware(created_at) else created_at
        parts.append(local_value.strftime("%Y%m%d%H%M%S"))
    if suffix:
        parts.append(str(suffix))
    return ":".join(parts)


def _note(note_id, title, message, created_at, url="", unread=False):
    return {
        "id": str(note_id or "").strip(),
        "title": title,
        "message": message,
        "created_at": created_at,
        "created_label": _when_label(created_at),
        "url": url or "",
        "unread": bool(unread),
    }


def _append_query_params(url, params):
    filtered = {
        key: value
        for key, value in (params or {}).items()
        if value not in {None, ""}
    }
    if not filtered:
        return url
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}{urlencode(filtered)}"


def _application_status_to_filter(status):
    normalized = (status or "").strip()
    if normalized in {"Interview", "Interview Scheduled"}:
        return "Interview"
    if normalized in {"Selected", "Offer Issued", "Offer Received"}:
        return "Selected"
    return normalized or "all"


def _company_interview_url(interview):
    status = (getattr(interview, "status", "") or "").strip().lower()
    if status in {"completed"}:
        base_url = reverse("dashboard:company_interviews_completed")
    elif status in {"cancelled", "no_show"}:
        base_url = reverse("dashboard:company_interviews_cancelled")
    else:
        base_url = reverse("dashboard:company_interviews_upcoming")
    interview_id = getattr(interview, "id", None)
    if interview_id:
        return f"{base_url}#company-interview-{interview_id}"
    return base_url


def _interview_start_at(interview):
    interview_date = getattr(interview, "interview_date", None)
    if not interview_date:
        return None
    interview_time = getattr(interview, "interview_time", None) or dt_time(hour=9, minute=0)
    start_at = datetime.combine(interview_date, interview_time)
    if timezone.is_naive(start_at):
        return timezone.make_aware(start_at, timezone.get_current_timezone())
    return timezone.localtime(start_at)


def _interview_venue_label(interview):
    mode = (getattr(interview, "mode", "") or "").strip().lower()
    if mode == "offline":
        venue = (getattr(interview, "location", "") or "").strip() or (
            getattr(interview, "meeting_link", "") or ""
        ).strip()
        if venue:
            return f"Location: {venue}"
        return "Location details are available in interview section."
    join_link = (getattr(interview, "meeting_link", "") or "").strip() or (
        getattr(interview, "location", "") or ""
    ).strip()
    if join_link:
        return f"Join link: {join_link}"
    return "Join details are available in interview section."


def _append_interview_reminder_notes(
    feed,
    interview,
    note_prefix,
    seen_at,
    seen_item_ids,
    target_url,
):
    status = (getattr(interview, "status", "") or "").strip().lower()
    if status not in {"scheduled", "rescheduled"}:
        return

    start_at = _interview_start_at(interview)
    if not start_at:
        return

    now = timezone.localtime(timezone.now())
    if now >= start_at:
        return

    schedule_label = start_at.strftime("%d %b %Y, %I:%M %p")
    interview_title = (getattr(interview, "job_title", "") or "Interview").strip()
    venue_label = _interview_venue_label(interview)
    reminder_windows = [
        ("24h", timedelta(hours=24), "Interview in 24 hours"),
        ("1h", timedelta(hours=1), "Interview in 1 hour"),
    ]

    for window_key, offset, reminder_title in reminder_windows:
        due_at = start_at - offset
        if now < due_at:
            continue
        note_id = _notification_id(
            f"{note_prefix}-reminder-{window_key}",
            getattr(interview, "id", 0),
            due_at,
        )
        reminder_message = f"{interview_title} on {schedule_label}. {venue_label}"
        feed.append(
            _note(
                note_id=note_id,
                title=reminder_title,
                message=reminder_message,
                created_at=due_at,
                url=target_url or "",
                unread=_mark_unread(due_at, seen_at, note_id, seen_item_ids),
            )
        )


def _candidate_feed(candidate, seen_at, seen_item_ids):
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
        target_url = _append_query_params(
            reverse("dashboard:candidate_applications"),
            {
                "application_id": app.application_id,
                "mode": "timeline",
            },
        )
        if app.application_id:
            target_url = f"{target_url}#candidate-app-{app.application_id}"
        note_id = _notification_id("candidate-application", app.id, created_at)
        feed.append(
            _note(
                note_id=note_id,
                title=title,
                message=message,
                created_at=created_at,
                url=target_url,
                unread=_mark_unread(created_at, seen_at, note_id, seen_item_ids),
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
        interview_url = reverse("dashboard:candidate_interviews")
        if interview.id:
            interview_url = f"{interview_url}#candidate-interview-{interview.id}"
        note_id = _notification_id("candidate-interview", interview.id, created_at)
        feed.append(
            _note(
                note_id=note_id,
                title=title,
                message=message,
                created_at=created_at,
                url=interview_url,
                unread=_mark_unread(created_at, seen_at, note_id, seen_item_ids),
            )
        )
        _append_interview_reminder_notes(
            feed=feed,
            interview=interview,
            note_prefix="candidate-interview",
            seen_at=seen_at,
            seen_item_ids=seen_item_ids,
            target_url=interview_url,
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
        note_id = _notification_id("candidate-message", message.id, message.created_at)
        feed.append(
            _note(
                note_id=note_id,
                title=f"New message from {sender}",
                message=preview,
                created_at=message.created_at,
                url=message_url,
                unread=_mark_unread(message.created_at, seen_at, note_id, seen_item_ids),
            )
        )
    return feed


def _company_feed(company, seen_at, seen_item_ids):
    feed = []
    app_rows = Application.objects.filter(company__iexact=company.name).order_by("-updated_at", "-created_at")[:12]
    for app in app_rows:
        created_at = app.updated_at or app.created_at
        message = f"{app.candidate_name} for {app.job_title} ({app.status})"
        target_url = _append_query_params(
            reverse("dashboard:company_applications"),
            {
                "status": _application_status_to_filter(app.status),
                "application_id": app.application_id,
            },
        )
        if app.application_id:
            target_url = f"{target_url}#company-application-{app.application_id}"
        note_id = _notification_id("company-application", app.id, created_at)
        feed.append(
            _note(
                note_id=note_id,
                title="Application update",
                message=message,
                created_at=created_at,
                url=target_url,
                unread=_mark_unread(created_at, seen_at, note_id, seen_item_ids),
            )
        )

    interview_rows = Interview.objects.filter(company__iexact=company.name).order_by("-updated_at", "-created_at")[:8]
    for interview in interview_rows:
        created_at = interview.updated_at or interview.created_at
        message = f"{interview.candidate_name} - {interview.job_title} ({interview.status})"
        interview_url = _company_interview_url(interview)
        note_id = _notification_id("company-interview", interview.id, created_at)
        feed.append(
            _note(
                note_id=note_id,
                title="Interview update",
                message=message,
                created_at=created_at,
                url=interview_url,
                unread=_mark_unread(created_at, seen_at, note_id, seen_item_ids),
            )
        )
        _append_interview_reminder_notes(
            feed=feed,
            interview=interview,
            note_prefix="company-interview",
            seen_at=seen_at,
            seen_item_ids=seen_item_ids,
            target_url=interview_url,
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
        note_id = _notification_id("company-message", message.id, message.created_at)
        feed.append(
            _note(
                note_id=note_id,
                title=f"New message from {sender}",
                message=preview,
                created_at=message.created_at,
                url=message_url,
                unread=_mark_unread(message.created_at, seen_at, note_id, seen_item_ids),
            )
        )
    return feed


def _consultancy_feed(consultancy, seen_at, seen_item_ids):
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
        note_id = _notification_id("consultancy-assignment", assignment.id, created_at)
        feed.append(
            _note(
                note_id=note_id,
                title="Assigned job update",
                message=message,
                created_at=created_at,
                url=reverse("dashboard:consultancy_assigned_jobs"),
                unread=_mark_unread(created_at, seen_at, note_id, seen_item_ids),
            )
        )

    app_rows = Application.objects.filter(consultancy=consultancy).order_by("-updated_at", "-created_at")[:12]
    for app in app_rows:
        created_at = app.updated_at or app.created_at
        message = f"{app.candidate_name} - {app.job_title} ({app.status})"
        target_url = _append_query_params(
            reverse("dashboard:consultancy_applications"),
            {
                "status": _application_status_to_filter(app.status),
                "application_id": app.application_id,
            },
        )
        if app.application_id:
            target_url = f"{target_url}#consultancy-application-{app.application_id}"
        note_id = _notification_id("consultancy-application", app.id, created_at)
        feed.append(
            _note(
                note_id=note_id,
                title="Application update",
                message=message,
                created_at=created_at,
                url=target_url,
                unread=_mark_unread(created_at, seen_at, note_id, seen_item_ids),
            )
        )

    interview_rows = (
        Interview.objects.filter(application__consultancy=consultancy)
        .order_by("-updated_at", "-created_at")[:10]
    )
    consultancy_interview_status = {
        "scheduled": "Interview scheduled",
        "rescheduled": "Interview rescheduled",
        "completed": "Interview completed",
        "cancelled": "Interview cancelled",
        "no_show": "Interview marked no show",
    }
    for interview in interview_rows:
        created_at = interview.updated_at or interview.created_at
        interview_url = reverse("dashboard:consultancy_interviews")
        if interview.id:
            interview_url = f"{interview_url}?section=upcoming#consultancy-interview-{interview.id}"
        note_id = _notification_id("consultancy-interview", interview.id, created_at)
        message = f"{interview.candidate_name} - {interview.job_title} ({interview.status})"
        feed.append(
            _note(
                note_id=note_id,
                title=consultancy_interview_status.get(interview.status, "Interview update"),
                message=message,
                created_at=created_at,
                url=interview_url,
                unread=_mark_unread(created_at, seen_at, note_id, seen_item_ids),
            )
        )
        _append_interview_reminder_notes(
            feed=feed,
            interview=interview,
            note_prefix="consultancy-interview",
            seen_at=seen_at,
            seen_item_ids=seen_item_ids,
            target_url=interview_url,
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
        note_id = _notification_id("consultancy-message", message.id, message.created_at)
        feed.append(
            _note(
                note_id=note_id,
                title=f"New message from {sender}",
                message=preview,
                created_at=message.created_at,
                url=message_url,
                unread=_mark_unread(message.created_at, seen_at, note_id, seen_item_ids),
            )
        )
    return feed


def _admin_feed(admin_user, seen_at, seen_item_ids):
    feed = []

    def _append_registration_summary(model, title, label, url_name):
        registrations_qs = model.objects.all()
        if seen_at:
            registrations_qs = registrations_qs.filter(registration_date__gt=seen_at)
        registrations_qs = registrations_qs.order_by("-registration_date")
        total_new = registrations_qs.count()
        if not total_new:
            return
        latest_item = registrations_qs.first()
        latest_name = (getattr(latest_item, "name", "") or "").strip()
        created_at = getattr(latest_item, "registration_date", None)
        if total_new == 1 and latest_name:
            message = f"{latest_name} registered as {label}."
        else:
            message = f"{total_new} new {label} registrations."
            if latest_name:
                message = f"{message} Latest: {latest_name}."
        note_id = _notification_id(
            f"admin-{label}-registration",
            getattr(latest_item, "id", 0),
            created_at,
            suffix=str(total_new),
        )
        feed.append(
            _note(
                note_id=note_id,
                title=title,
                message=message,
                created_at=created_at,
                url=reverse(url_name),
                unread=_mark_unread(created_at, seen_at, note_id, seen_item_ids),
            )
        )

    _append_registration_summary(
        model=Candidate,
        title="Candidate registrations",
        label="candidate",
        url_name="dashboard:candidates",
    )
    _append_registration_summary(
        model=Company,
        title="Company registrations",
        label="company",
        url_name="dashboard:companies",
    )
    _append_registration_summary(
        model=Consultancy,
        title="Consultancy registrations",
        label="consultancy",
        url_name="dashboard:consultancies",
    )

    pending_apps = Application.objects.filter(status="Applied").order_by("-updated_at", "-created_at")
    pending_jobs = pending_apps.count()
    if pending_jobs:
        latest_pending = pending_apps.first()
        created_at = (latest_pending.updated_at or latest_pending.created_at) if latest_pending else None
        note_id = _notification_id(
            "admin-pending-applications",
            getattr(latest_pending, "id", 0),
            created_at,
            suffix=str(pending_jobs),
        )
        feed.append(
            _note(
                note_id=note_id,
                title="Applications waiting review",
                message=f"{pending_jobs} applications are currently in Applied status.",
                created_at=created_at,
                url=reverse("dashboard:applications"),
                unread=_mark_unread(created_at, seen_at, note_id, seen_item_ids),
            )
        )

    return feed


def build_panel_notifications(request, limit=8, only_unread=False):
    role = None
    account = None
    candidate_id = request.session.get("candidate_id")
    company_id = request.session.get("company_id")
    consultancy_id = request.session.get("consultancy_id")
    url_name = getattr(getattr(request, "resolver_match", None), "url_name", "") or ""

    if request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser):
        role = "admin"
        account = request.user
    elif url_name.startswith("candidate_") and candidate_id:
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

    seen_at = _get_seen_at(request, role)
    seen_item_ids = _get_seen_item_ids(request, role)
    if role == "candidate":
        items = _candidate_feed(account, seen_at, seen_item_ids)
    elif role == "company":
        items = _company_feed(account, seen_at, seen_item_ids)
    elif role == "consultancy":
        items = _consultancy_feed(account, seen_at, seen_item_ids)
    else:
        items = _admin_feed(account, seen_at, seen_item_ids)

    fallback_dt = timezone.make_aware(datetime(1970, 1, 1))
    items.sort(key=lambda row: row.get("created_at") or fallback_dt, reverse=True)
    if only_unread:
        unread_items = [row for row in items if row.get("unread")]
        unread_count = len(unread_items)
        items = unread_items[:limit]
    else:
        unread_count = sum(1 for row in items if row.get("unread"))
        items = items[:limit]
    return {"role": role, "items": items, "unread_count": unread_count}


def mark_panel_notification_items_seen(request, item_ids, role=None):
    selected_role, ok = _resolve_panel_role(request, explicit_role=role)
    if not ok:
        return
    _append_seen_item_ids(request, selected_role, item_ids)


def mark_panel_notifications_seen(request, role=None, item_ids=None):
    selected_role, ok = _resolve_panel_role(request, explicit_role=role)
    if not ok:
        return
    key = ROLE_SEEN_SESSION_KEYS.get(selected_role)
    if key:
        request.session[key] = timezone.now().isoformat()
    if item_ids:
        _append_seen_item_ids(request, selected_role, item_ids)
    request.session.modified = True
