from django.db.models import Q
from django.utils import timezone

from .models import Advertisement, AdminProfile, Candidate, Subscription


def admin_profile_context(request):
    if not request.user.is_authenticated:
        return {"admin_profile": None}
    if not (request.user.is_staff or request.user.is_superuser):
        return {"admin_profile": None}
    profile, _ = AdminProfile.objects.get_or_create(user=request.user)
    return {"admin_profile": profile}


def _candidate_subscription_segment(email):
    if not email:
        return "non_subscribed", None
    subscription = (
        Subscription.objects.filter(
            account_type__iexact="Candidate",
            contact__iexact=email,
        )
        .order_by("-expiry_date", "-updated_at")
        .first()
    )
    if not subscription:
        return "non_subscribed", None
    if subscription.payment_status != "Paid":
        return "non_subscribed", subscription
    if (subscription.plan or "").strip().lower() == "free":
        return "non_subscribed", subscription
    if subscription.expiry_date and subscription.expiry_date < timezone.localdate():
        return "non_subscribed", subscription
    return "subscribed", subscription


def _active_advertisement_for(audience, segment):
    ads = Advertisement.objects.filter(
        audience=audience,
        is_active=True,
    ).order_by("-created_at")
    scoped = ads.filter(Q(segment=segment) | Q(segment="") | Q(segment__isnull=True)).first()
    if scoped:
        return scoped
    generic = ads.filter(Q(segment="") | Q(segment__isnull=True)).first()
    return generic or ads.first()


def candidate_panel_context(request):
    candidate_id = request.session.get("candidate_id")
    if not candidate_id:
        return {
            "candidate_sidebar_ad": None,
            "candidate_subscription_info": None,
        }

    candidate = Candidate.objects.filter(id=candidate_id).first()
    if not candidate:
        return {
            "candidate_sidebar_ad": None,
            "candidate_subscription_info": None,
        }

    segment, subscription = _candidate_subscription_segment(candidate.email)
    sidebar_ad = _active_advertisement_for("candidate", segment)

    plan_name = "Free Candidate"
    expiry = None
    is_premium = False
    if subscription and segment == "subscribed":
        plan_name = "Premium Candidate"
        expiry = subscription.expiry_date
        is_premium = True

    return {
        "candidate_sidebar_ad": sidebar_ad,
        "candidate_subscription_info": {
            "plan_name": plan_name,
            "is_premium": is_premium,
            "segment": segment,
            "price_monthly": 199,
            "expiry": expiry,
        },
    }
