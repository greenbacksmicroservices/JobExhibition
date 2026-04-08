import logging
from datetime import date, datetime, time
from decimal import Decimal

from django.conf import settings
from django.db import connections
from django.db.models import Q
from django.db.models.signals import post_delete, post_save, pre_delete
from django.dispatch import receiver

from .models import (
    Application,
    AssignedJob,
    Candidate,
    CandidateCertification,
    CandidateEducation,
    CandidateExperience,
    CandidateProject,
    CandidateResume,
    CandidateSavedJob,
    CandidateSkill,
    Company,
    CompanyKycDocument,
    Consultancy,
    ConsultancyKycDocument,
    DeletedDataLog,
    Interview,
    Job,
    MessageThread,
    PaymentEventLog,
    Subscription,
    SubscriptionPayment,
)

logger = logging.getLogger(__name__)


def _payment_db_alias():
    if not getattr(settings, "PAYMENT_DB_ENABLED", False):
        return ""
    alias = (getattr(settings, "PAYMENT_DB_ALIAS", "payment") or "").strip()
    if not alias or alias == "default":
        return ""
    if alias not in connections.databases:
        return ""
    return alias


def _mirror_defaults(instance, excluded=None):
    excluded_fields = {"id"}
    if excluded:
        excluded_fields.update(excluded)
    defaults = {}
    for field in instance._meta.concrete_fields:
        field_name = field.attname
        if field_name in excluded_fields:
            continue
        defaults[field_name] = getattr(instance, field_name)
    return defaults


def _primitive(value):
    if value is None:
        return ""
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value
    return str(value)


def _file_snapshot(file_field):
    if not file_field:
        return {}
    try:
        file_url = file_field.url or ""
    except Exception:
        file_url = ""
    file_name = getattr(file_field, "name", "") or ""
    return {"name": file_name, "url": file_url}


def _model_snapshot(instance, exclude=None):
    excluded = set(exclude or [])
    payload = {}
    for field in instance._meta.concrete_fields:
        field_name = field.name
        if field_name in excluded:
            continue
        if field.is_relation:
            payload[field_name] = _primitive(getattr(instance, field.attname, ""))
            continue
        internal_type = (field.get_internal_type() or "").lower()
        if "file" in internal_type or "image" in internal_type:
            payload[field_name] = _file_snapshot(getattr(instance, field_name, None))
            continue
        payload[field_name] = _primitive(getattr(instance, field_name, None))
    return payload


def _payment_details_for(account_type, email):
    clean_email = (email or "").strip()
    if not clean_email:
        return {}

    subscription = (
        Subscription.objects.filter(
            account_type__iexact=account_type,
            contact__iexact=clean_email,
        )
        .order_by("-updated_at", "-id")
        .first()
    )
    payment_qs = SubscriptionPayment.objects.none()
    if subscription:
        payment_qs = SubscriptionPayment.objects.filter(subscription=subscription).order_by("-created_at")
    if not payment_qs.exists():
        payment_qs = SubscriptionPayment.objects.filter(
            account_type__iexact=account_type,
            account_email__iexact=clean_email,
        ).order_by("-created_at")

    recent_payments = []
    for payment in payment_qs[:12]:
        recent_payments.append(
            {
                "payment_id": payment.payment_id,
                "plan_code": payment.plan_code,
                "billing_cycle": payment.billing_cycle,
                "amount": payment.amount,
                "currency": payment.currency,
                "status": payment.status,
                "provider": payment.provider,
                "account_name": payment.account_name,
                "account_email": payment.account_email,
                "created_at": _primitive(payment.created_at),
                "paid_at": _primitive(payment.paid_at),
            }
        )

    return {
        "subscription": (
            {
                "subscription_id": subscription.subscription_id,
                "name": subscription.name,
                "plan": subscription.plan,
                "payment_status": subscription.payment_status,
                "start_date": _primitive(subscription.start_date),
                "expiry_date": _primitive(subscription.expiry_date),
                "auto_renew": subscription.auto_renew,
            }
            if subscription
            else {}
        ),
        "recent_payments": recent_payments,
    }


def _collect_company_documents(company):
    docs = []
    for doc in CompanyKycDocument.objects.filter(company=company).order_by("-uploaded_at"):
        docs.append(
            {
                "title": doc.title,
                "document_type": doc.document_type,
                "file": _file_snapshot(doc.file),
                "uploaded_at": _primitive(doc.uploaded_at),
            }
        )
    return docs


def _collect_consultancy_documents(consultancy):
    docs = []
    for doc in ConsultancyKycDocument.objects.filter(consultancy=consultancy).order_by("-uploaded_at"):
        docs.append(
            {
                "title": doc.document_title,
                "document_type": doc.document_type,
                "file": _file_snapshot(doc.document_file),
                "uploaded_at": _primitive(doc.uploaded_at),
            }
        )
    return docs


def _collect_candidate_full_details(candidate):
    resume_items = []
    for resume in CandidateResume.objects.filter(candidate=candidate).order_by("-created_at"):
        resume_items.append(
            {
                "title": resume.title,
                "template_name": resume.template_name,
                "resume_file": _file_snapshot(resume.resume_file),
                "is_default": resume.is_default,
                "created_at": _primitive(resume.created_at),
            }
        )

    certifications = []
    for cert in CandidateCertification.objects.filter(candidate=candidate):
        certifications.append(
            {
                "title": cert.title,
                "issuing_org": cert.issuing_org,
                "year": cert.year,
                "certificate_file": _file_snapshot(cert.certificate_file),
                "uploaded_at": _primitive(cert.uploaded_at),
            }
        )

    education_rows = []
    for row in CandidateEducation.objects.filter(candidate=candidate):
        education_rows.append(
            {
                "qualification": row.qualification,
                "course_name": row.course_name,
                "specialization": row.specialization,
                "institution": row.institution,
                "passing_year": row.passing_year,
                "score": row.score,
            }
        )

    experience_rows = []
    for row in CandidateExperience.objects.filter(candidate=candidate):
        experience_rows.append(
            {
                "company_name": row.company_name,
                "designation": row.designation,
                "industry": row.industry,
                "start_date": _primitive(row.start_date),
                "end_date": _primitive(row.end_date),
                "is_current": row.is_current,
                "responsibilities": row.responsibilities,
                "achievements": row.achievements,
            }
        )

    skill_rows = []
    for row in CandidateSkill.objects.filter(candidate=candidate):
        skill_rows.append({"name": row.name, "category": row.category, "level": row.level})

    project_rows = []
    for row in CandidateProject.objects.filter(candidate=candidate):
        project_rows.append(
            {
                "title": row.title,
                "technology": row.technology,
                "description": row.description,
                "duration": row.duration,
            }
        )

    return {
        "profile": _model_snapshot(candidate),
        "default_resume": _file_snapshot(getattr(candidate, "resume", None)),
        "resumes": resume_items,
        "certifications": certifications,
        "education": education_rows,
        "experience": experience_rows,
        "skills": skill_rows,
        "projects": project_rows,
        "saved_jobs_count": CandidateSavedJob.objects.filter(candidate=candidate).count(),
    }


def _candidate_snapshot_for_email(email_value):
    email_text = (email_value or "").strip()
    if not email_text:
        return {}
    candidate = Candidate.objects.filter(email__iexact=email_text).first()
    if not candidate:
        return {}
    snapshot = _collect_candidate_full_details(candidate)
    snapshot["id"] = candidate.id
    snapshot["name"] = candidate.name
    snapshot["email"] = candidate.email
    snapshot["phone"] = candidate.phone
    return snapshot


def _job_bundle_with_applications(job_qs, limit_jobs=40, limit_apps_per_job=30):
    rows = []
    applications_total = 0
    candidate_profiles = {}

    for job in job_qs.order_by("-created_at", "-id")[:limit_jobs]:
        app_qs = Application.objects.filter(Q(job=job) | Q(job_title__iexact=job.title, company__iexact=job.company))
        app_rows = []
        for app in app_qs.order_by("-updated_at", "-created_at")[:limit_apps_per_job]:
            app_rows.append(
                {
                    "application_id": app.application_id,
                    "candidate_name": app.candidate_name,
                    "candidate_email": app.candidate_email,
                    "candidate_phone": app.candidate_phone,
                    "status": app.status,
                    "placement_status": app.placement_status,
                    "applied_date": _primitive(app.applied_date),
                    "updated_at": _primitive(app.updated_at),
                }
            )
            candidate_email = (app.candidate_email or "").strip().lower()
            if candidate_email and candidate_email not in candidate_profiles and len(candidate_profiles) < 25:
                profile_snapshot = _candidate_snapshot_for_email(candidate_email)
                if profile_snapshot:
                    candidate_profiles[candidate_email] = profile_snapshot

        app_count = app_qs.count()
        applications_total += app_count
        rows.append(
            {
                "job_id": job.job_id,
                "title": job.title,
                "company": job.company,
                "category": job.category,
                "location": job.location,
                "status": job.status,
                "lifecycle_status": job.lifecycle_status,
                "posted_date": _primitive(job.posted_date),
                "created_at": _primitive(job.created_at),
                "applications_count": app_count,
                "applications": app_rows,
            }
        )

    return {
        "jobs": rows,
        "jobs_count": len(rows),
        "applications_total": applications_total,
        "candidate_profiles_count": len(candidate_profiles),
        "candidate_profiles": candidate_profiles,
    }


def _resolve_deleted_by(instance, default_label):
    deleted_by = (getattr(instance, "_deleted_by_label", "") or "").strip()
    if deleted_by:
        return deleted_by
    return default_label


def _resolve_delete_reason(instance, default_reason):
    reason = (getattr(instance, "_delete_reason", "") or "").strip()
    if reason:
        return reason
    return default_reason


def _create_deleted_log(
    *,
    category,
    entity_type,
    source_model,
    source_id,
    display_name,
    reference,
    details,
    instance=None,
    default_deleted_by="System",
    default_reason="",
):
    try:
        DeletedDataLog.objects.create(
            category=category,
            entity_type=entity_type,
            source_model=source_model,
            source_id=str(source_id or ""),
            display_name=(display_name or "")[:255],
            reference=(reference or "")[:255],
            deleted_by=_resolve_deleted_by(instance, default_deleted_by),
            reason=_resolve_delete_reason(instance, default_reason),
            details=details or {},
        )
    except Exception as exc:
        logger.warning("Deleted-data log create failed: %s", exc)


def _log_company_profile_delete(company):
    company_name = (company.name or "").strip()
    company_email = (company.email or "").strip()
    job_filter = Q()
    if company_name:
        job_filter |= Q(company__iexact=company_name)
    if company_email:
        job_filter |= Q(recruiter_email__iexact=company_email)
    job_qs = Job.objects.filter(job_filter).distinct() if job_filter else Job.objects.none()
    deleted_jobs_summary = _job_bundle_with_applications(job_qs, limit_jobs=60, limit_apps_per_job=30)
    details = {
        "profile": _model_snapshot(company),
        "kyc_documents": _collect_company_documents(company),
        "payment_details": _payment_details_for("Company", getattr(company, "email", "")),
        "job_counts": {
            "direct_jobs": Job.objects.filter(company__iexact=company_name).count(),
            "email_jobs": Job.objects.filter(recruiter_email__iexact=company_email).count(),
        },
        "deleted_jobs_summary": deleted_jobs_summary,
        "candidate_count": deleted_jobs_summary.get("candidate_profiles_count", 0),
    }
    _create_deleted_log(
        category="company",
        entity_type="company_profile",
        source_model="Company",
        source_id=company.id,
        display_name=company.name,
        reference=company.email,
        details=details,
        instance=company,
        default_deleted_by="System",
        default_reason="Company account deleted.",
    )


def _log_consultancy_profile_delete(consultancy):
    consultancy_name = (consultancy.name or "").strip()
    consultancy_email = (consultancy.email or "").strip()
    job_filter = Q()
    if consultancy_name:
        job_filter |= Q(company__iexact=consultancy_name) | Q(recruiter_name__iexact=consultancy_name)
    if consultancy_email:
        job_filter |= Q(recruiter_email__iexact=consultancy_email)
    job_qs = Job.objects.filter(job_filter).distinct() if job_filter else Job.objects.none()
    deleted_jobs_summary = _job_bundle_with_applications(job_qs, limit_jobs=60, limit_apps_per_job=30)
    details = {
        "profile": _model_snapshot(consultancy),
        "kyc_documents": _collect_consultancy_documents(consultancy),
        "payment_details": _payment_details_for("Consultancy", getattr(consultancy, "email", "")),
        "job_counts": {
            "direct_jobs": Job.objects.filter(company__iexact=consultancy_name).count(),
            "email_jobs": Job.objects.filter(recruiter_email__iexact=consultancy_email).count(),
        },
        "deleted_jobs_summary": deleted_jobs_summary,
        "candidate_count": deleted_jobs_summary.get("candidate_profiles_count", 0),
    }
    _create_deleted_log(
        category="consultancy",
        entity_type="consultancy_profile",
        source_model="Consultancy",
        source_id=consultancy.id,
        display_name=consultancy.name,
        reference=consultancy.email,
        details=details,
        instance=consultancy,
        default_deleted_by="System",
        default_reason="Consultancy account deleted.",
    )


def _log_candidate_profile_delete(candidate):
    details = _collect_candidate_full_details(candidate)
    details["payment_details"] = _payment_details_for("Candidate", getattr(candidate, "email", ""))
    _create_deleted_log(
        category="candidate",
        entity_type="candidate_profile",
        source_model="Candidate",
        source_id=candidate.id,
        display_name=candidate.name,
        reference=candidate.email,
        details=details,
        instance=candidate,
        default_deleted_by="System",
        default_reason="Candidate account deleted.",
    )


def _resolve_job_owner(job):
    recruiter_email = (getattr(job, "recruiter_email", "") or "").strip()
    recruiter_name = (getattr(job, "recruiter_name", "") or "").strip()
    company_name = (getattr(job, "company", "") or "").strip()

    company = None
    consultancy = None

    if recruiter_email:
        company = Company.objects.filter(email__iexact=recruiter_email).only("id", "name", "email").first()
        consultancy = Consultancy.objects.filter(email__iexact=recruiter_email).only("id", "name", "email").first()
    if not company and company_name:
        company = Company.objects.filter(name__iexact=company_name).only("id", "name", "email").first()
    if not consultancy and recruiter_name:
        consultancy = Consultancy.objects.filter(name__iexact=recruiter_name).only("id", "name", "email").first()
    if not consultancy and company_name:
        consultancy = Consultancy.objects.filter(name__iexact=company_name).only("id", "name", "email").first()

    if company:
        return ("company", company.name, company.email, company)
    if consultancy:
        return ("consultancy", consultancy.name, consultancy.email, consultancy)
    return ("company", company_name or recruiter_name or "Job Owner", recruiter_email, None)


def _log_job_delete(job):
    category, owner_name, owner_reference, owner_obj = _resolve_job_owner(job)
    applications = Application.objects.filter(Q(job=job) | Q(job_title__iexact=job.title, company__iexact=job.company))
    interviews = Interview.objects.filter(Q(job_title__iexact=job.title, company__iexact=job.company))
    application_items = []
    status_counts = {}
    candidate_profiles = {}

    for app in applications.order_by("-updated_at", "-created_at")[:80]:
        application_items.append(
            {
                "application_id": app.application_id,
                "candidate_name": app.candidate_name,
                "candidate_email": app.candidate_email,
                "candidate_phone": app.candidate_phone,
                "status": app.status,
                "placement_status": app.placement_status,
                "applied_date": _primitive(app.applied_date),
                "updated_at": _primitive(app.updated_at),
            }
        )
        status_key = (app.status or "Unknown").strip() or "Unknown"
        status_counts[status_key] = int(status_counts.get(status_key) or 0) + 1

        candidate_email = (app.candidate_email or "").strip().lower()
        if candidate_email and candidate_email not in candidate_profiles and len(candidate_profiles) < 30:
            snapshot = _candidate_snapshot_for_email(candidate_email)
            if snapshot:
                candidate_profiles[candidate_email] = snapshot

    details = {
        "job_details": _model_snapshot(job),
        "applications": {
            "count": applications.count(),
            "status_counts": status_counts,
            "items": application_items,
        },
        "interviews": {
            "count": interviews.count(),
            "items": list(
                interviews.order_by("-updated_at", "-created_at")
                .values(
                    "interview_id",
                    "candidate_name",
                    "candidate_email",
                    "status",
                    "interview_date",
                    "interview_time",
                    "created_at",
                    "updated_at",
                )[:50]
            ),
        },
        "candidate_profiles": candidate_profiles,
        "candidate_count": len(candidate_profiles),
    }
    if category == "company":
        details["payment_details"] = _payment_details_for("Company", owner_reference or getattr(owner_obj, "email", ""))
    elif category == "consultancy":
        details["payment_details"] = _payment_details_for("Consultancy", owner_reference or getattr(owner_obj, "email", ""))

    _create_deleted_log(
        category=category,
        entity_type="job",
        source_model="Job",
        source_id=job.job_id or job.id,
        display_name=job.title,
        reference=owner_reference or job.company,
        details=details,
        instance=job,
        default_deleted_by="System",
        default_reason="Job deleted.",
    )


def _cleanup_company_related_records(company):
    company_name = (getattr(company, "name", "") or "").strip()
    company_email = (getattr(company, "email", "") or "").strip()

    job_filter = Q()
    if company_name:
        job_filter |= Q(company__iexact=company_name)
    if company_email:
        job_filter |= Q(recruiter_email__iexact=company_email)

    job_ids = []
    jobs_qs = Job.objects.none()
    if job_filter:
        jobs_qs = Job.objects.filter(job_filter).distinct()
        job_ids = list(jobs_qs.values_list("id", flat=True))

    app_filter = Q()
    if company_name:
        app_filter |= Q(company__iexact=company_name)
    if job_ids:
        app_filter |= Q(job_id__in=job_ids)
    app_ids = []
    app_qs = Application.objects.none()
    if app_filter:
        app_qs = Application.objects.filter(app_filter)
        app_ids = list(app_qs.values_list("id", flat=True))

    interview_filter = Q()
    if company_name:
        interview_filter |= Q(company__iexact=company_name)
    if app_ids:
        interview_filter |= Q(application_id__in=app_ids)

    if job_ids:
        job_rows = list(jobs_qs)
        deleted_by_label = _resolve_deleted_by(company, "System")
        delete_reason = _resolve_delete_reason(company, "Deleted due to company profile deletion.")
        for job in job_rows:
            job._deleted_by_label = deleted_by_label
            job._delete_reason = delete_reason
            job.delete()

    if app_ids:
        app_qs.delete()
    if interview_filter:
        Interview.objects.filter(interview_filter).delete()

    MessageThread.objects.filter(company=company).delete()

    if company_email:
        Subscription.objects.filter(
            account_type__iexact="Company",
            contact__iexact=company_email,
        ).delete()


def _cleanup_consultancy_related_records(consultancy):
    consultancy_name = (getattr(consultancy, "name", "") or "").strip()
    consultancy_email = (getattr(consultancy, "email", "") or "").strip()

    job_filter = Q()
    if consultancy_name:
        job_filter |= Q(company__iexact=consultancy_name) | Q(recruiter_name__iexact=consultancy_name)
    if consultancy_email:
        job_filter |= Q(recruiter_email__iexact=consultancy_email)

    job_ids = []
    if job_filter:
        jobs_qs = Job.objects.filter(job_filter).distinct()
        job_ids = list(jobs_qs.values_list("id", flat=True))
        job_rows = list(jobs_qs)
        deleted_by_label = _resolve_deleted_by(consultancy, "System")
        delete_reason = _resolve_delete_reason(consultancy, "Deleted due to consultancy profile deletion.")
        for job in job_rows:
            job._deleted_by_label = deleted_by_label
            job._delete_reason = delete_reason
            job.delete()

    app_filter = Q(consultancy=consultancy)
    if job_ids:
        app_filter |= Q(job_id__in=job_ids)
    app_ids = list(Application.objects.filter(app_filter).values_list("id", flat=True))
    Application.objects.filter(app_filter).delete()
    if app_ids:
        Interview.objects.filter(application_id__in=app_ids).delete()

    AssignedJob.objects.filter(consultancy=consultancy).delete()
    MessageThread.objects.filter(consultancy=consultancy).delete()

    if consultancy_email:
        Subscription.objects.filter(
            account_type__iexact="Consultancy",
            contact__iexact=consultancy_email,
        ).delete()


def _cleanup_candidate_related_records(candidate):
    candidate_email = (getattr(candidate, "email", "") or "").strip()
    if candidate_email:
        app_qs = Application.objects.filter(candidate_email__iexact=candidate_email)
        app_ids = list(app_qs.values_list("id", flat=True))
        app_qs.delete()
        interview_qs = Interview.objects.filter(candidate_email__iexact=candidate_email)
        if app_ids:
            interview_qs = interview_qs | Interview.objects.filter(application_id__in=app_ids)
        interview_qs.delete()

    MessageThread.objects.filter(candidate=candidate).delete()
    CandidateSavedJob.objects.filter(candidate=candidate).delete()

    if candidate_email:
        Subscription.objects.filter(
            account_type__iexact="Candidate",
            contact__iexact=candidate_email,
        ).delete()


@receiver(pre_delete, sender=Company)
def cleanup_company_records_on_delete(sender, instance, using, **kwargs):
    if using != "default":
        return
    try:
        _log_company_profile_delete(instance)
    except Exception as exc:
        logger.warning(
            "Company delete log failed for %s (%s): %s",
            getattr(instance, "id", None),
            getattr(instance, "email", ""),
            exc,
        )
    try:
        _cleanup_company_related_records(instance)
    except Exception as exc:
        logger.warning(
            "Company cleanup failed for %s (%s): %s",
            getattr(instance, "id", None),
            getattr(instance, "email", ""),
            exc,
        )


@receiver(pre_delete, sender=Consultancy)
def cleanup_consultancy_records_on_delete(sender, instance, using, **kwargs):
    if using != "default":
        return
    try:
        _log_consultancy_profile_delete(instance)
    except Exception as exc:
        logger.warning(
            "Consultancy delete log failed for %s (%s): %s",
            getattr(instance, "id", None),
            getattr(instance, "email", ""),
            exc,
        )
    try:
        _cleanup_consultancy_related_records(instance)
    except Exception as exc:
        logger.warning(
            "Consultancy cleanup failed for %s (%s): %s",
            getattr(instance, "id", None),
            getattr(instance, "email", ""),
            exc,
        )


@receiver(pre_delete, sender=Candidate)
def cleanup_candidate_records_on_delete(sender, instance, using, **kwargs):
    if using != "default":
        return
    try:
        _log_candidate_profile_delete(instance)
    except Exception as exc:
        logger.warning(
            "Candidate delete log failed for %s (%s): %s",
            getattr(instance, "id", None),
            getattr(instance, "email", ""),
            exc,
        )
    try:
        _cleanup_candidate_related_records(instance)
    except Exception as exc:
        logger.warning(
            "Candidate cleanup failed for %s (%s): %s",
            getattr(instance, "id", None),
            getattr(instance, "email", ""),
            exc,
        )


@receiver(pre_delete, sender=Job)
def log_job_delete(sender, instance, using, **kwargs):
    if using != "default":
        return
    try:
        _log_job_delete(instance)
    except Exception as exc:
        logger.warning(
            "Job delete log failed for %s (%s): %s",
            getattr(instance, "job_id", None),
            getattr(instance, "title", ""),
            exc,
        )


@receiver(post_save, sender=SubscriptionPayment)
def mirror_subscription_payment(sender, instance, raw, using, **kwargs):
    if raw or using != "default":
        return
    alias = _payment_db_alias()
    if not alias:
        return
    try:
        sender.objects.using(alias).update_or_create(
            payment_id=instance.payment_id,
            defaults=_mirror_defaults(instance, excluded={"payment_id"}),
        )
    except Exception as exc:
        logger.warning(
            "Payment mirror sync failed for %s using '%s': %s",
            instance.payment_id,
            alias,
            exc,
        )


@receiver(post_save, sender=PaymentEventLog)
def mirror_payment_event_log(sender, instance, raw, using, **kwargs):
    if raw or using != "default":
        return
    alias = _payment_db_alias()
    if not alias:
        return
    try:
        sender.objects.using(alias).update_or_create(
            id=instance.id,
            defaults=_mirror_defaults(instance),
        )
    except Exception as exc:
        logger.warning(
            "Payment event mirror sync failed for %s using '%s': %s",
            instance.id,
            alias,
            exc,
        )


@receiver(post_delete, sender=SubscriptionPayment)
def remove_subscription_payment_mirror(sender, instance, using, **kwargs):
    if using != "default":
        return
    alias = _payment_db_alias()
    if not alias:
        return
    try:
        sender.objects.using(alias).filter(payment_id=instance.payment_id).delete()
    except Exception as exc:
        logger.warning(
            "Payment mirror delete failed for %s using '%s': %s",
            instance.payment_id,
            alias,
            exc,
        )


@receiver(post_delete, sender=PaymentEventLog)
def remove_payment_event_mirror(sender, instance, using, **kwargs):
    if using != "default":
        return
    alias = _payment_db_alias()
    if not alias:
        return
    try:
        sender.objects.using(alias).filter(id=instance.id).delete()
    except Exception as exc:
        logger.warning(
            "Payment event mirror delete failed for %s using '%s': %s",
            instance.id,
            alias,
            exc,
        )
