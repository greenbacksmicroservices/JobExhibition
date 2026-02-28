import json
import logging
import re
import urllib.error
import urllib.request
from urllib.parse import urlencode

from django.conf import settings


logger = logging.getLogger(__name__)
NON_DIGITS = re.compile(r"\D+")


def _normalize_mobile_number(mobile):
    digits = NON_DIGITS.sub("", mobile or "")
    # Fast2SMS usually expects 10-digit Indian numbers.
    if len(digits) == 12 and digits.startswith("91"):
        return digits[2:]
    return digits


def _render_otp_message(otp):
    template = getattr(
        settings,
        "OTP_SMS_MESSAGE_TEMPLATE",
        "Your OTP for JobExhibition is {otp}. It is valid for 10 minutes.",
    )
    ttl_minutes = 10
    try:
        return template.format(otp=otp, ttl_minutes=ttl_minutes)
    except (KeyError, ValueError):
        logger.warning("Invalid OTP_SMS_MESSAGE_TEMPLATE format. Falling back to default template.")
        return f"Your OTP for JobExhibition is {otp}. It is valid for {ttl_minutes} minutes."


def _provider_error_message(response_text, fallback):
    parsed = {}
    try:
        parsed = json.loads(response_text or "{}")
    except json.JSONDecodeError:
        parsed = {}

    provider_message = ""
    if isinstance(parsed, dict):
        provider_message = str(parsed.get("message") or "").strip()
    if not provider_message:
        provider_message = (response_text or "").strip()

    lower_msg = provider_message.lower()
    if "invalid authentication" in lower_msg or "authorization key" in lower_msg:
        return "Invalid OTP API key. Please check OTP_SMS_API_KEY."
    if "complete one transaction of 100" in lower_msg or "100 inr" in lower_msg:
        return "Fast2SMS account me minimum INR 100 transaction required hai before API OTP route use."
    if provider_message:
        return provider_message
    return fallback


def _send_fast2sms_otp(mobile, otp):
    api_key = (getattr(settings, "OTP_SMS_API_KEY", "") or "").strip()
    if not api_key:
        return False, "OTP service is not configured (missing API key)."

    mobile_number = _normalize_mobile_number(mobile)
    if not mobile_number or len(mobile_number) < 10:
        return False, "Enter a valid mobile number to receive OTP."

    route = (getattr(settings, "OTP_FAST2SMS_ROUTE", "dlt") or "dlt").strip().lower()
    if route == "dlt":
        return _send_fast2sms_dlt_otp(api_key, mobile_number, otp)

    payload = {
        "route": route,
        "message": _render_otp_message(otp),
        "language": getattr(settings, "OTP_FAST2SMS_LANGUAGE", "english"),
        "flash": int(getattr(settings, "OTP_FAST2SMS_FLASH", 0) or 0),
        "numbers": mobile_number,
    }

    sender_id = (getattr(settings, "OTP_FAST2SMS_SENDER_ID", "") or "").strip()
    entity_id = (getattr(settings, "OTP_FAST2SMS_ENTITY_ID", "") or "").strip()
    template_id = (getattr(settings, "OTP_FAST2SMS_TEMPLATE_ID", "") or "").strip()

    if sender_id:
        payload["sender_id"] = sender_id
    if entity_id:
        payload["entity_id"] = entity_id
    if template_id:
        payload["template_id"] = template_id

    req = urllib.request.Request(
        (getattr(settings, "OTP_SMS_API_URL", "") or "https://www.fast2sms.com/dev/bulkV2"),
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
    )
    req.add_header("authorization", api_key)
    req.add_header("content-type", "application/json")

    timeout_seconds = int(getattr(settings, "OTP_SMS_TIMEOUT_SECONDS", 10) or 10)

    try:
        with urllib.request.urlopen(req, timeout=timeout_seconds) as response:
            status_code = response.getcode() or 0
            response_text = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        logger.error("OTP HTTP error from Fast2SMS: %s, body=%s", exc.code, body)
        return False, _provider_error_message(
            body,
            f"OTP service rejected the request (HTTP {exc.code}). Please try again.",
        )
    except urllib.error.URLError as exc:
        logger.error("OTP URL error from Fast2SMS: %s", exc)
        return False, "Unable to reach OTP service right now. Please try again."
    except Exception:
        logger.exception("Unexpected error while sending OTP via Fast2SMS.")
        return False, "Unable to send OTP right now. Please try again."

    if status_code < 200 or status_code >= 300:
        logger.error("OTP non-success status from Fast2SMS: %s body=%s", status_code, response_text)
        return False, _provider_error_message(
            response_text,
            f"OTP service is temporarily unavailable (HTTP {status_code}). Please try again.",
        )

    try:
        parsed = json.loads(response_text) if response_text else {}
    except json.JSONDecodeError:
        parsed = {}

    if isinstance(parsed, dict):
        if parsed.get("return") is False or parsed.get("success") is False:
            logger.error("Fast2SMS response reported failure: %s", parsed)
            return False, _provider_error_message(
                response_text,
                "OTP could not be delivered. Please try again.",
            )

    return True, ""


def _send_fast2sms_dlt_otp(api_key, mobile_number, otp):
    sender_id = (getattr(settings, "OTP_FAST2SMS_SENDER_ID", "") or "").strip()
    message_id = (
        (getattr(settings, "OTP_FAST2SMS_MESSAGE_ID", "") or "").strip()
        or (getattr(settings, "OTP_FAST2SMS_TEMPLATE_ID", "") or "").strip()
    )
    if not sender_id:
        return False, "OTP sender ID missing. Set OTP_FAST2SMS_SENDER_ID for DLT route."
    if not message_id:
        return False, "OTP DLT template/message ID missing. Set OTP_FAST2SMS_MESSAGE_ID."

    variables_template = (getattr(settings, "OTP_FAST2SMS_VARIABLES_VALUES", "") or "").strip()
    variables_values = ""
    if variables_template:
        try:
            variables_values = variables_template.format(otp=otp, ttl_minutes=10)
        except (KeyError, ValueError):
            variables_values = variables_template

    query = {
        "authorization": api_key,
        "route": "dlt",
        "sender_id": sender_id,
        "message": message_id,
        "variables_values": variables_values,
        "numbers": mobile_number,
        "flash": str(int(getattr(settings, "OTP_FAST2SMS_FLASH", 0) or 0)),
    }
    schedule_time = (getattr(settings, "OTP_FAST2SMS_SCHEDULE_TIME", "") or "").strip()
    if schedule_time:
        query["schedule_time"] = schedule_time

    base_url = (getattr(settings, "OTP_SMS_API_URL", "") or "https://www.fast2sms.com/dev/bulkV2").strip()
    separator = "&" if "?" in base_url else "?"
    request_url = f"{base_url}{separator}{urlencode(query)}"

    req = urllib.request.Request(request_url, method="GET")
    req.add_header("authorization", api_key)

    timeout_seconds = int(getattr(settings, "OTP_SMS_TIMEOUT_SECONDS", 10) or 10)

    try:
        with urllib.request.urlopen(req, timeout=timeout_seconds) as response:
            status_code = response.getcode() or 0
            response_text = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        logger.error("OTP HTTP error from Fast2SMS DLT route: %s, body=%s", exc.code, body)
        return False, _provider_error_message(
            body,
            f"OTP service rejected the DLT request (HTTP {exc.code}). Please try again.",
        )
    except urllib.error.URLError as exc:
        logger.error("OTP URL error from Fast2SMS DLT route: %s", exc)
        return False, "Unable to reach OTP service right now. Please try again."
    except Exception:
        logger.exception("Unexpected error while sending OTP via Fast2SMS DLT route.")
        return False, "Unable to send OTP right now. Please try again."

    if status_code < 200 or status_code >= 300:
        logger.error("OTP non-success status from Fast2SMS DLT route: %s body=%s", status_code, response_text)
        return False, _provider_error_message(
            response_text,
            f"OTP service is temporarily unavailable (HTTP {status_code}). Please try again.",
        )

    try:
        parsed = json.loads(response_text) if response_text else {}
    except json.JSONDecodeError:
        parsed = {}

    if isinstance(parsed, dict):
        if parsed.get("return") is False or parsed.get("success") is False:
            logger.error("Fast2SMS DLT response reported failure: %s", parsed)
            return False, _provider_error_message(
                response_text,
                "OTP could not be delivered. Please try again.",
            )

    return True, ""


def send_otp_sms(mobile, otp):
    provider = (getattr(settings, "OTP_SMS_PROVIDER", "console") or "console").strip().lower()

    if provider in {"disabled", "off"}:
        logger.info("OTP sending disabled for mobile %s", mobile)
        return True, ""

    if provider == "console":
        logger.info("OTP for %s is %s", mobile, otp)
        return True, ""

    if provider == "fast2sms":
        return _send_fast2sms_otp(mobile, otp)

    logger.error("Unsupported OTP_SMS_PROVIDER configured: %s", provider)
    return False, "OTP provider is not configured correctly."
