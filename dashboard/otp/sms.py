import json
import logging
import re
import urllib.error
import urllib.request
from urllib.parse import urlencode

from django.conf import settings


logger = logging.getLogger(__name__)
NON_DIGITS = re.compile(r"\D+")
OTP_TTL_MINUTES = 10


def _normalize_otp_purpose(purpose):
    raw_value = (purpose or "").strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "register": "register",
        "registration": "register",
        "signup": "register",
        "sign_up": "register",
        "forgot": "forgot_password",
        "forgotpassword": "forgot_password",
        "forgot_password": "forgot_password",
        "password_reset": "forgot_password",
        "reset_password": "forgot_password",
        "delete": "account_delete",
        "delete_account": "account_delete",
        "account_delete": "account_delete",
        "login": "login",
        "otp": "otp",
    }
    return aliases.get(raw_value, "otp")


def _normalize_mobile_number(mobile):
    digits = NON_DIGITS.sub("", mobile or "")
    # Fast2SMS expects Indian 10-digit mobile numbers.
    if digits.startswith("00"):
        digits = digits[2:]
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    if len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    if len(digits) > 10:
        digits = digits[-10:]
    return digits


def _render_otp_message(otp, purpose="otp"):
    purpose_key = _normalize_otp_purpose(purpose)
    default_template = "Your OTP for JobExhibition is {otp}. It is valid for {ttl_minutes} minutes."
    template_key_by_purpose = {
        "register": "OTP_SMS_MESSAGE_TEMPLATE_REGISTER",
        "forgot_password": "OTP_SMS_MESSAGE_TEMPLATE_FORGOT_PASSWORD",
        "account_delete": "OTP_SMS_MESSAGE_TEMPLATE_ACCOUNT_DELETE",
        "login": "OTP_SMS_MESSAGE_TEMPLATE_LOGIN",
    }
    template_key = template_key_by_purpose.get(purpose_key, "OTP_SMS_MESSAGE_TEMPLATE")
    template = (getattr(settings, template_key, "") or "").strip()
    if not template:
        template = (getattr(settings, "OTP_SMS_MESSAGE_TEMPLATE", default_template) or default_template).strip()

    try:
        return template.format(otp=otp, ttl_minutes=OTP_TTL_MINUTES)
    except (KeyError, ValueError):
        logger.warning("Invalid %s format. Falling back to default template.", template_key)
        return default_template.format(otp=otp, ttl_minutes=OTP_TTL_MINUTES)


def _resolve_fast2sms_dlt_message_id(purpose):
    purpose_key = _normalize_otp_purpose(purpose)
    message_key_by_purpose = {
        "register": "OTP_FAST2SMS_REGISTER_MESSAGE_ID",
        "forgot_password": "OTP_FAST2SMS_FORGOT_PASSWORD_MESSAGE_ID",
        "account_delete": "OTP_FAST2SMS_ACCOUNT_DELETE_MESSAGE_ID",
        "login": "OTP_FAST2SMS_LOGIN_MESSAGE_ID",
    }
    purpose_message_key = message_key_by_purpose.get(purpose_key)
    if purpose_message_key:
        purpose_message_id = (getattr(settings, purpose_message_key, "") or "").strip()
        if purpose_message_id:
            return purpose_message_id

    return (
        (getattr(settings, "OTP_FAST2SMS_MESSAGE_ID", "") or "").strip()
        or (getattr(settings, "OTP_FAST2SMS_TEMPLATE_ID", "") or "").strip()
    )


def _resolve_fast2sms_dlt_variables_template(purpose):
    purpose_key = _normalize_otp_purpose(purpose)
    variables_key_by_purpose = {
        "register": "OTP_FAST2SMS_REGISTER_VARIABLES_VALUES",
        "forgot_password": "OTP_FAST2SMS_FORGOT_PASSWORD_VARIABLES_VALUES",
        "account_delete": "OTP_FAST2SMS_ACCOUNT_DELETE_VARIABLES_VALUES",
        "login": "OTP_FAST2SMS_LOGIN_VARIABLES_VALUES",
    }
    purpose_variables_key = variables_key_by_purpose.get(purpose_key)
    if purpose_variables_key and hasattr(settings, purpose_variables_key):
        raw_value = getattr(settings, purpose_variables_key, "")
        return str(raw_value or "").strip()
    return (getattr(settings, "OTP_FAST2SMS_VARIABLES_VALUES", "") or "").strip()


def _render_fast2sms_dlt_variables_values(variables_template, otp):
    if not variables_template:
        return ""
    try:
        rendered = variables_template.format(otp=otp, ttl_minutes=OTP_TTL_MINUTES)
    except (KeyError, ValueError):
        rendered = variables_template

    # For DLT templates shared as raw pipe-separated examples, keep the first slot
    # aligned with the runtime OTP so user-entered OTP validation does not break.
    if "{" not in variables_template and "|" in rendered:
        parts = rendered.split("|")
        if parts:
            parts[0] = str(otp)
            rendered = "|".join(parts)
    return rendered


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
    if (
        "invalid authentication" in lower_msg
        or "authorization key" in lower_msg
        or "invalid api key" in lower_msg
        or "invalid key" in lower_msg
        or "authentication failed" in lower_msg
    ):
        return "Invalid OTP API key. Please check OTP_SMS_API_KEY."
    if "complete one transaction of 100" in lower_msg or "100 inr" in lower_msg:
        return "Fast2SMS account me minimum INR 100 transaction required hai before API OTP route use."
    if provider_message:
        return provider_message
    return fallback


def _send_fast2sms_otp(mobile, otp, purpose="otp"):
    purpose_key = _normalize_otp_purpose(purpose)
    api_key = (getattr(settings, "OTP_SMS_API_KEY", "") or "").strip()
    if not api_key:
        return False, "OTP service is not configured. Please set OTP_SMS_API_KEY."

    mobile_number = _normalize_mobile_number(mobile)
    if not mobile_number or len(mobile_number) != 10:
        return False, "Enter a valid mobile number to receive OTP."

    route = (getattr(settings, "OTP_FAST2SMS_ROUTE", "dlt") or "dlt").strip().lower()
    if route == "dlt":
        return _send_fast2sms_dlt_otp(api_key, mobile_number, otp, purpose=purpose_key)

    payload = {
        "route": route,
        "message": _render_otp_message(otp, purpose=purpose_key),
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
        (getattr(settings, "OTP_SMS_API_URL", "https://www.fast2sms.com/dev/bulkV2") or "https://www.fast2sms.com/dev/bulkV2"),
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


def _send_fast2sms_dlt_otp(api_key, mobile_number, otp, purpose="otp"):
    purpose_key = _normalize_otp_purpose(purpose)
    sender_id = (getattr(settings, "OTP_FAST2SMS_SENDER_ID", "") or "").strip()
    message_id = _resolve_fast2sms_dlt_message_id(purpose_key)
    if not sender_id:
        return False, "OTP sender ID missing. Set OTP_FAST2SMS_SENDER_ID for DLT route."
    if not message_id:
        return False, "OTP DLT template/message ID missing. Set OTP_FAST2SMS_MESSAGE_ID."

    variables_template = _resolve_fast2sms_dlt_variables_template(purpose_key)
    variables_values = _render_fast2sms_dlt_variables_values(variables_template, otp)

    query = {
        "authorization": api_key,
        "route": "dlt",
        "sender_id": sender_id,
        "message": message_id,
        "variables_values": variables_values,
        "numbers": mobile_number,
        "schedule_time": (getattr(settings, "OTP_FAST2SMS_SCHEDULE_TIME", "") or "").strip(),
        "flash": str(int(getattr(settings, "OTP_FAST2SMS_FLASH", 0) or 0)),
    }

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


def send_otp_sms(mobile, otp, purpose="otp"):
    purpose_key = _normalize_otp_purpose(purpose)
    provider = (getattr(settings, "OTP_SMS_PROVIDER", "console") or "console").strip().lower()

    if provider in {"disabled", "off"}:
        logger.info("OTP sending disabled for mobile %s", mobile)
        return True, ""

    if provider == "console":
        logger.info("OTP for %s is %s (purpose=%s)", mobile, otp, purpose_key)
        return True, ""

    if provider == "fast2sms":
        return _send_fast2sms_otp(mobile, otp, purpose=purpose_key)

    logger.error("Unsupported OTP_SMS_PROVIDER configured: %s", provider)
    return False, "OTP provider is not configured correctly."
