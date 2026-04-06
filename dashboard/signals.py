import logging

from django.conf import settings
from django.db import connections
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import PaymentEventLog, SubscriptionPayment

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
