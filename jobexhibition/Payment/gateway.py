import base64
import hashlib
import json
import time
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request

from django.urls import reverse

INTERNAL_PAYMENT_PROVIDER = "JobExhibition Payment System"
PHONEPE_PROVIDER = "PhonePe"

PHONEPE_SUCCESS_CODES = {"success", "completed", "captured", "payment_success", "pay_success"}
PHONEPE_PENDING_CODES = {
    "pending",
    "created",
    "initiated",
    "processing",
    "payment_pending",
    "payment_initiated",
    "in_progress",
}
PHONEPE_FAILURE_CODES = {"failed", "failure", "cancelled", "expired", "rejected", "payment_error", "declined"}

PHONEPE_V2_DEFAULT_PROD_PG_HOST = "https://api.phonepe.com/apis/pg"
PHONEPE_V2_DEFAULT_PROD_OAUTH_HOST = "https://api.phonepe.com/apis/identity-manager"
PHONEPE_V2_DEFAULT_PREPROD_PG_HOST = "https://api-preprod.phonepe.com/apis/pg-sandbox"
PHONEPE_V2_DEFAULT_PREPROD_OAUTH_HOST = "https://api-preprod.phonepe.com/apis/pg-sandbox"

PHONEPE_V2_DEFAULT_PAY_PATH = "/checkout/v2/pay"
PHONEPE_V2_DEFAULT_STATUS_PATH = "/checkout/v2/order/{merchant_transaction_id}/status"
PHONEPE_V2_OAUTH_TOKEN_PATH = "/v1/oauth/token"
PHONEPE_V2_OAUTH_GRANT_TYPE = "client_credentials"

PHONEPE_V1_DEFAULT_PAY_PATH = "/pg/v1/pay"
PHONEPE_V1_DEFAULT_STATUS_PATH = "/pg/v1/status/{merchant_id}/{merchant_transaction_id}"

_PHONEPE_OAUTH_TOKEN_CACHE = {}


def _safe_json_payload(raw_value):
    if not raw_value:
        return {}
    if isinstance(raw_value, (bytes, bytearray)):
        raw_value = raw_value.decode("utf-8", errors="ignore")
    if isinstance(raw_value, str):
        try:
            return json.loads(raw_value)
        except json.JSONDecodeError:
            return {}
    if isinstance(raw_value, dict):
        return raw_value
    return {}


def _normalize_path(path, default="/"):
    resolved = (path or "").strip()
    if not resolved:
        resolved = default
    if not resolved.startswith("/"):
        resolved = f"/{resolved}"
    return resolved


def _compose_url(base_url, path):
    base = (base_url or "").strip().rstrip("/")
    path_value = _normalize_path(path, default="/")
    return f"{base}{path_value}" if base else ""


def _is_preprod_env_label(value):
    label = (value or "").strip().lower()
    return label in {"uat", "sandbox", "preprod", "test", "testing"}


def _is_preprod_host(value):
    base = (value or "").strip().lower()
    return "api-preprod.phonepe.com" in base


def _normalize_phonepe_v2_pg_host(base_url, env_label):
    value = (base_url or "").strip().rstrip("/")
    if not value:
        return PHONEPE_V2_DEFAULT_PREPROD_PG_HOST if _is_preprod_env_label(env_label) else PHONEPE_V2_DEFAULT_PROD_PG_HOST

    lower = value.lower()
    if lower.endswith("/apis"):
        if _is_preprod_host(value) or _is_preprod_env_label(env_label):
            return f"{value}/pg-sandbox"
        return f"{value}/pg"
    return value


def _normalize_phonepe_v2_oauth_host(base_url, env_label):
    value = (base_url or "").strip().rstrip("/")
    if value:
        return value
    if _is_preprod_env_label(env_label):
        return PHONEPE_V2_DEFAULT_PREPROD_OAUTH_HOST
    return PHONEPE_V2_DEFAULT_PROD_OAUTH_HOST


def _normalize_phonepe_v2_pay_path(path):
    raw = (path or "").strip()
    if not raw:
        return PHONEPE_V2_DEFAULT_PAY_PATH
    normalized = _normalize_path(raw, default=PHONEPE_V2_DEFAULT_PAY_PATH)
    if normalized.lower() == PHONEPE_V1_DEFAULT_PAY_PATH:
        return PHONEPE_V2_DEFAULT_PAY_PATH
    return normalized


def _normalize_phonepe_v2_status_path(path):
    raw = (path or "").strip()
    if not raw:
        return PHONEPE_V2_DEFAULT_STATUS_PATH
    normalized = _normalize_path(raw, default=PHONEPE_V2_DEFAULT_STATUS_PATH)
    if "/pg/v1/status/" in normalized.lower():
        return PHONEPE_V2_DEFAULT_STATUS_PATH
    return normalized


def _phonepe_v2_config(settings):
    env_label = getattr(settings, "PHONEPE_ENV", "")
    pg_base_url = _normalize_phonepe_v2_pg_host(getattr(settings, "PHONEPE_BASE_URL", ""), env_label)
    oauth_base_url = _normalize_phonepe_v2_oauth_host(getattr(settings, "PHONEPE_OAUTH_BASE_URL", ""), env_label)
    pay_path = _normalize_phonepe_v2_pay_path(getattr(settings, "PHONEPE_PAY_PATH", ""))
    status_template = _normalize_phonepe_v2_status_path(getattr(settings, "PHONEPE_STATUS_PATH", ""))
    client_id = (
        getattr(settings, "PHONEPE_CLIENT_ID", "SU2508261540303520112151")
        or getattr(settings, "PHONEPE_MERCHANT_ID", "SU2508261540303520112151")
        or getattr(settings, "MERCHANT_ID", "SU2508261540303520112151")
        or ""
    ).strip()
    client_secret = (
        getattr(settings, "PHONEPE_CLIENT_SECRET", "")
        or getattr(settings, "PHONEPE_SALT_KEY", "")
        or getattr(settings, "SALT_KEY", "75dbd341-4f7f-4120-a056-856f295a3ecb")
        or ""
    ).strip()
    client_version = str(getattr(settings, "PHONEPE_CLIENT_VERSION", "1") or "1").strip()
    return {
        "pg_base_url": pg_base_url,
        "oauth_base_url": oauth_base_url,
        "pay_path": pay_path,
        "status_template": status_template,
        "client_id": client_id,
        "client_secret": client_secret,
        "client_version": client_version,
    }


def _phonepe_v1_config(settings):
    merchant_id = (
        getattr(settings, "PHONEPE_MERCHANT_ID", "")
        or getattr(settings, "PHONEPE_CLIENT_ID", "")
        or getattr(settings, "MERCHANT_ID", "")
        or ""
    ).strip()
    salt_key = (
        getattr(settings, "PHONEPE_SALT_KEY", "")
        or getattr(settings, "PHONEPE_CLIENT_SECRET", "")
        or getattr(settings, "SALT_KEY", "")
        or ""
    ).strip()
    salt_index = str(getattr(settings, "PHONEPE_SALT_INDEX", 1) or 1).strip()
    base_url = (getattr(settings, "PHONEPE_BASE_URL", "") or "").strip().rstrip("/")
    pay_path = _normalize_path(getattr(settings, "PHONEPE_PAY_PATH", PHONEPE_V1_DEFAULT_PAY_PATH), default=PHONEPE_V1_DEFAULT_PAY_PATH)
    status_template = (
        getattr(settings, "PHONEPE_STATUS_PATH", "")
        or PHONEPE_V1_DEFAULT_STATUS_PATH
    )
    return {
        "merchant_id": merchant_id,
        "salt_key": salt_key,
        "salt_index": salt_index,
        "base_url": base_url,
        "pay_path": pay_path,
        "status_template": status_template,
    }


def _is_phonepe_v2_configured(config):
    return bool(
        config.get("pg_base_url")
        and config.get("oauth_base_url")
        and config.get("client_id")
        and config.get("client_secret")
    )


def _is_phonepe_v1_configured(config):
    return bool(config.get("merchant_id") and config.get("salt_key") and config.get("base_url"))


def is_phonepe_configured(settings):
    return _is_phonepe_v2_configured(_phonepe_v2_config(settings)) or _is_phonepe_v1_configured(_phonepe_v1_config(settings))


def _phonepe_status_from_payload(payload):
    if not isinstance(payload, dict):
        return "pending"

    nested = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    instrument = nested.get("instrumentResponse") if isinstance(nested.get("instrumentResponse"), dict) else {}
    status_candidates = [
        payload.get("status"),
        payload.get("state"),
        payload.get("paymentStatus"),
        payload.get("payment_status"),
        payload.get("code"),
        payload.get("responseCode"),
        nested.get("status"),
        nested.get("state"),
        nested.get("paymentStatus"),
        nested.get("payment_status"),
        nested.get("code"),
        nested.get("responseCode"),
        instrument.get("status"),
        instrument.get("state"),
        instrument.get("code"),
    ]
    for value in status_candidates:
        normalized = (value or "").strip().lower()
        if not normalized:
            continue
        if normalized in PHONEPE_SUCCESS_CODES:
            return "success"
        if normalized in PHONEPE_FAILURE_CODES:
            return "failed"
        if normalized in PHONEPE_PENDING_CODES:
            return "pending"
    return "pending"


def _phonepe_http_json(url, method="POST", payload=None, headers=None, timeout_seconds=20):
    request_headers = dict(headers or {})
    body = None
    if payload is not None:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        request_headers.setdefault("Content-Type", "application/json")
    request_obj = urllib_request.Request(
        url=url,
        data=body,
        headers=request_headers,
        method=method,
    )
    try:
        with urllib_request.urlopen(request_obj, timeout=timeout_seconds) as response:
            raw = response.read()
            parsed = _safe_json_payload(raw)
            return {
                "ok": True,
                "status_code": getattr(response, "status", 200),
                "data": parsed,
                "error": "",
            }
    except urllib_error.HTTPError as exc:
        raw = exc.read() if hasattr(exc, "read") else b""
        parsed = _safe_json_payload(raw)
        return {
            "ok": False,
            "status_code": getattr(exc, "code", 500),
            "data": parsed,
            "error": parsed.get("message") or parsed.get("error") or str(exc),
        }
    except Exception as exc:
        return {
            "ok": False,
            "status_code": 500,
            "data": {},
            "error": str(exc),
        }


def _phonepe_http_form(url, form_payload, headers=None, timeout_seconds=20):
    request_headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "accept": "application/json",
    }
    request_headers.update(headers or {})
    body = urllib_parse.urlencode(form_payload).encode("utf-8")
    request_obj = urllib_request.Request(
        url=url,
        data=body,
        headers=request_headers,
        method="POST",
    )
    try:
        with urllib_request.urlopen(request_obj, timeout=timeout_seconds) as response:
            raw = response.read()
            parsed = _safe_json_payload(raw)
            return {
                "ok": True,
                "status_code": getattr(response, "status", 200),
                "data": parsed,
                "error": "",
            }
    except urllib_error.HTTPError as exc:
        raw = exc.read() if hasattr(exc, "read") else b""
        parsed = _safe_json_payload(raw)
        return {
            "ok": False,
            "status_code": getattr(exc, "code", 500),
            "data": parsed,
            "error": parsed.get("message") or parsed.get("error") or str(exc),
        }
    except Exception as exc:
        return {
            "ok": False,
            "status_code": 500,
            "data": {},
            "error": str(exc),
        }


def _oauth_cache_key(config):
    return (
        config.get("oauth_base_url", ""),
        config.get("client_id", ""),
        config.get("client_version", ""),
    )


def _oauth_cached_token(config):
    cache_key = _oauth_cache_key(config)
    cached = _PHONEPE_OAUTH_TOKEN_CACHE.get(cache_key) or {}
    token = (cached.get("token") or "").strip()
    expires_at = int(cached.get("expires_at") or 0)
    if token and expires_at > int(time.time()) + 30:
        return token
    return ""


def _cache_oauth_token(config, token, expires_at):
    cache_key = _oauth_cache_key(config)
    _PHONEPE_OAUTH_TOKEN_CACHE[cache_key] = {
        "token": token,
        "expires_at": int(expires_at or 0),
    }


def _fetch_phonepe_oauth_token(config, timeout_seconds=20, force_refresh=False):
    if not force_refresh:
        cached = _oauth_cached_token(config)
        if cached:
            return {"ok": True, "token": cached, "error": "", "response": {"cached": True}}

    oauth_url = _compose_url(config.get("oauth_base_url", ""), PHONEPE_V2_OAUTH_TOKEN_PATH)
    payload = {
        "client_id": config.get("client_id", ""),
        "client_secret": config.get("client_secret", ""),
        "client_version": config.get("client_version", "1"),
        "grant_type": PHONEPE_V2_OAUTH_GRANT_TYPE,
    }
    response = _phonepe_http_form(
        oauth_url,
        payload,
        timeout_seconds=timeout_seconds,
    )
    body = response.get("data") if isinstance(response.get("data"), dict) else {}
    access_token = (body.get("access_token") or body.get("encrypted_access_token") or "").strip()
    token_type = (body.get("token_type") or "Bearer").strip()
    if response.get("ok") and access_token:
        expires_at = int(body.get("expires_at") or 0)
        if not expires_at:
            expires_in = int(body.get("expires_in") or 0)
            expires_at = int(time.time()) + max(expires_in, 60)
        auth_token = f"{token_type} {access_token}"
        _cache_oauth_token(config, auth_token, expires_at)
        return {"ok": True, "token": auth_token, "error": "", "response": body}
    return {
        "ok": False,
        "token": "",
        "error": response.get("error", "") or body.get("message") or "Unable to fetch PhonePe OAuth token.",
        "response": body,
    }


def _unwrap_phonepe_data(payload):
    if not isinstance(payload, dict):
        return {}
    nested = payload.get("data")
    if isinstance(nested, dict):
        return nested
    return payload


def _merge_phonepe_error(primary_message, payload):
    message = (primary_message or "").strip()
    if message:
        return message
    if isinstance(payload, dict):
        return (payload.get("message") or payload.get("error") or payload.get("code") or "").strip()
    return ""


def _initiate_phonepe_v2_payment(config, payment, redirect_url="", timeout_seconds=20):
    token_result = _fetch_phonepe_oauth_token(config, timeout_seconds=timeout_seconds, force_refresh=False)
    if not token_result.get("ok"):
        return {
            "ok": False,
            "status": "failed",
            "error": token_result.get("error", ""),
            "response": token_result.get("response", {}),
            "redirect_url": "",
        }

    order_id = payment.payment_id
    payload = {
        "merchantOrderId": order_id,
        "amount": int(payment.amount or 0) * 100,
        "paymentFlow": {
            "type": "PG_CHECKOUT",
            "message": f"Subscription {order_id}",
            "merchantUrls": {"redirectUrl": redirect_url},
        },
    }
    headers = {
        "Content-Type": "application/json",
        "accept": "application/json",
        "Authorization": token_result.get("token", ""),
        "Source": "INTEGRATION",
        "x-source-version": "V2",
    }
    api_url = _compose_url(config.get("pg_base_url", ""), config.get("pay_path", PHONEPE_V2_DEFAULT_PAY_PATH))
    api_response = _phonepe_http_json(
        api_url,
        method="POST",
        payload=payload,
        headers=headers,
        timeout_seconds=timeout_seconds,
    )

    if not api_response.get("ok") and int(api_response.get("status_code") or 0) == 401:
        fresh_token = _fetch_phonepe_oauth_token(config, timeout_seconds=timeout_seconds, force_refresh=True)
        if fresh_token.get("ok"):
            headers["Authorization"] = fresh_token.get("token", "")
            api_response = _phonepe_http_json(
                api_url,
                method="POST",
                payload=payload,
                headers=headers,
                timeout_seconds=timeout_seconds,
            )

    body = api_response.get("data") if isinstance(api_response.get("data"), dict) else {}
    data = _unwrap_phonepe_data(body)
    redirect_value = (data.get("redirectUrl") or body.get("redirectUrl") or "").strip()
    resolved_status = _phonepe_status_from_payload(body)
    if resolved_status == "pending" and not api_response.get("ok"):
        resolved_status = "failed"
    return {
        "ok": bool(api_response.get("ok")),
        "status": resolved_status,
        "error": _merge_phonepe_error(api_response.get("error", ""), body),
        "response": body,
        "redirect_url": redirect_value,
        "gateway_order_id": data.get("orderId") or order_id,
        "gateway_payment_id": data.get("transactionId") or data.get("paymentId") or "",
        "gateway_reference": data.get("orderId") or data.get("transactionId") or "",
    }


def _fetch_phonepe_v2_payment_status(config, payment, timeout_seconds=20):
    token_result = _fetch_phonepe_oauth_token(config, timeout_seconds=timeout_seconds, force_refresh=False)
    if not token_result.get("ok"):
        return {
            "ok": False,
            "status": "pending",
            "error": token_result.get("error", ""),
            "response": token_result.get("response", {}),
        }

    status_template = config.get("status_template") or PHONEPE_V2_DEFAULT_STATUS_PATH
    status_path = status_template.format(
        merchant_id="",
        merchant_transaction_id=payment.payment_id,
    )
    status_path = _normalize_path(status_path, default=PHONEPE_V2_DEFAULT_STATUS_PATH.format(merchant_transaction_id=payment.payment_id))
    headers = {
        "accept": "application/json",
        "Authorization": token_result.get("token", ""),
        "Source": "INTEGRATION",
        "x-source-version": "V2",
    }
    api_url = _compose_url(config.get("pg_base_url", ""), status_path)
    api_response = _phonepe_http_json(
        api_url,
        method="GET",
        payload=None,
        headers=headers,
        timeout_seconds=timeout_seconds,
    )

    if not api_response.get("ok") and int(api_response.get("status_code") or 0) == 401:
        fresh_token = _fetch_phonepe_oauth_token(config, timeout_seconds=timeout_seconds, force_refresh=True)
        if fresh_token.get("ok"):
            headers["Authorization"] = fresh_token.get("token", "")
            api_response = _phonepe_http_json(
                api_url,
                method="GET",
                payload=None,
                headers=headers,
                timeout_seconds=timeout_seconds,
            )

    body = api_response.get("data") if isinstance(api_response.get("data"), dict) else {}
    data = _unwrap_phonepe_data(body)
    resolved_status = _phonepe_status_from_payload(body)
    if not api_response.get("ok") and resolved_status == "pending":
        resolved_status = "pending"
    return {
        "ok": bool(api_response.get("ok")),
        "status": resolved_status,
        "error": _merge_phonepe_error(api_response.get("error", ""), body),
        "response": body,
        "gateway_order_id": data.get("orderId") or payment.payment_id,
        "gateway_payment_id": data.get("transactionId") or data.get("paymentId") or "",
        "gateway_reference": data.get("orderId") or data.get("transactionId") or "",
    }


def _initiate_phonepe_v1_payment(config, payment, account_id_value="", redirect_url="", callback_url="", timeout_seconds=20):
    merchant_user_id = str(account_id_value or payment.account_email or payment.account_name or payment.payment_id)
    request_payload = {
        "merchantId": config["merchant_id"],
        "merchantTransactionId": payment.payment_id,
        "merchantUserId": merchant_user_id[:128],
        "amount": int(payment.amount or 0) * 100,
        "redirectUrl": redirect_url,
        "redirectMode": "REDIRECT",
        "callbackUrl": callback_url,
        "paymentInstrument": {"type": "PAY_PAGE"},
    }
    encoded_payload = base64.b64encode(
        json.dumps(request_payload, separators=(",", ":")).encode("utf-8")
    ).decode("utf-8")
    x_verify = (
        hashlib.sha256(f"{encoded_payload}{config['pay_path']}{config['salt_key']}".encode("utf-8")).hexdigest()
        + f"###{config['salt_index']}"
    )
    headers = {
        "Content-Type": "application/json",
        "accept": "application/json",
        "X-VERIFY": x_verify,
    }
    api_url = _compose_url(config["base_url"], config["pay_path"])
    api_response = _phonepe_http_json(
        api_url,
        method="POST",
        payload={"request": encoded_payload},
        headers=headers,
        timeout_seconds=timeout_seconds,
    )
    payload = api_response.get("data") if isinstance(api_response.get("data"), dict) else {}
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    instrument_response = data.get("instrumentResponse") if isinstance(data.get("instrumentResponse"), dict) else {}
    redirect_info = instrument_response.get("redirectInfo") if isinstance(instrument_response.get("redirectInfo"), dict) else {}
    redirect_value = (
        redirect_info.get("url")
        or instrument_response.get("url")
        or data.get("redirectUrl")
        or ""
    )

    resolved_status = _phonepe_status_from_payload(payload)
    if resolved_status == "pending" and not api_response.get("ok"):
        resolved_status = "failed"

    return {
        "ok": bool(api_response.get("ok")),
        "status": resolved_status,
        "error": _merge_phonepe_error(api_response.get("error", ""), payload),
        "response": payload,
        "redirect_url": redirect_value,
        "gateway_order_id": payment.payment_id,
        "gateway_payment_id": data.get("transactionId") or data.get("providerReferenceId") or "",
        "gateway_reference": data.get("providerReferenceId") or data.get("transactionId") or "",
    }


def _fetch_phonepe_v1_payment_status(config, payment, timeout_seconds=20):
    status_template = config["status_template"]
    status_path = status_template.format(
        merchant_id=config["merchant_id"],
        merchant_transaction_id=payment.payment_id,
    )
    status_path = _normalize_path(status_path, default=PHONEPE_V1_DEFAULT_STATUS_PATH.format(merchant_id=config["merchant_id"], merchant_transaction_id=payment.payment_id))
    x_verify = (
        hashlib.sha256(f"{status_path}{config['salt_key']}".encode("utf-8")).hexdigest()
        + f"###{config['salt_index']}"
    )
    headers = {
        "Content-Type": "application/json",
        "accept": "application/json",
        "X-VERIFY": x_verify,
        "X-MERCHANT-ID": config["merchant_id"],
    }
    api_url = _compose_url(config["base_url"], status_path)
    api_response = _phonepe_http_json(
        api_url,
        method="GET",
        payload=None,
        headers=headers,
        timeout_seconds=timeout_seconds,
    )
    payload = api_response.get("data") if isinstance(api_response.get("data"), dict) else {}
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    resolved_status = _phonepe_status_from_payload(payload)
    if not api_response.get("ok") and resolved_status == "pending":
        resolved_status = "pending"
    return {
        "ok": bool(api_response.get("ok")),
        "status": resolved_status,
        "error": _merge_phonepe_error(api_response.get("error", ""), payload),
        "response": payload,
        "gateway_order_id": payment.payment_id,
        "gateway_payment_id": data.get("transactionId") or data.get("providerReferenceId") or "",
        "gateway_reference": data.get("providerReferenceId") or data.get("transactionId") or "",
    }


def initiate_phonepe_payment(
    settings,
    payment,
    account_id_value="",
    redirect_url="",
    callback_url="",
    timeout_seconds=20,
):
    v2_config = _phonepe_v2_config(settings)
    v1_config = _phonepe_v1_config(settings)

    v2_error = ""
    if _is_phonepe_v2_configured(v2_config):
        v2_response = _initiate_phonepe_v2_payment(
            v2_config,
            payment,
            redirect_url=redirect_url,
            timeout_seconds=timeout_seconds,
        )
        if v2_response.get("ok") or (v2_response.get("status") or "").lower() == "success":
            return v2_response
        v2_error = (v2_response.get("error") or "").strip()
        if "api mapping not found" not in v2_error.lower() and not _is_phonepe_v1_configured(v1_config):
            return v2_response
        if "authorization failed" in v2_error.lower() and not _is_phonepe_v1_configured(v1_config):
            return v2_response

    if _is_phonepe_v1_configured(v1_config):
        v1_response = _initiate_phonepe_v1_payment(
            v1_config,
            payment,
            account_id_value=account_id_value,
            redirect_url=redirect_url,
            callback_url=callback_url,
            timeout_seconds=timeout_seconds,
        )
        if not v1_response.get("error") and v2_error:
            v1_response["error"] = v2_error
        return v1_response

    if v2_error:
        return {
            "ok": False,
            "status": "failed",
            "error": v2_error,
            "response": {},
            "redirect_url": "",
        }

    return {
        "ok": False,
        "status": "failed",
        "error": "PhonePe credentials are not configured.",
        "response": {},
        "redirect_url": "",
    }


def fetch_phonepe_payment_status(settings, payment, timeout_seconds=20):
    v2_config = _phonepe_v2_config(settings)
    v1_config = _phonepe_v1_config(settings)

    v2_error = ""
    if _is_phonepe_v2_configured(v2_config):
        v2_response = _fetch_phonepe_v2_payment_status(
            v2_config,
            payment,
            timeout_seconds=timeout_seconds,
        )
        if v2_response.get("ok"):
            return v2_response
        v2_error = (v2_response.get("error") or "").strip()
        if "api mapping not found" not in v2_error.lower() and not _is_phonepe_v1_configured(v1_config):
            return v2_response

    if _is_phonepe_v1_configured(v1_config):
        v1_response = _fetch_phonepe_v1_payment_status(
            v1_config,
            payment,
            timeout_seconds=timeout_seconds,
        )
        if not v1_response.get("error") and v2_error:
            v1_response["error"] = v2_error
        return v1_response

    if v2_error:
        return {
            "ok": False,
            "status": "pending",
            "error": v2_error,
            "response": {},
        }

    return {
        "ok": False,
        "status": "pending",
        "error": "PhonePe credentials are not configured.",
        "response": {},
    }


def build_internal_checkout_url(request, payment_id):
    checkout_path = reverse("dashboard:payment_system_checkout", args=[payment_id])
    try:
        return request.build_absolute_uri(checkout_path)
    except Exception:
        return checkout_path


def should_fallback_to_internal_gateway(error_text):
    value = (error_text or "").strip().lower()
    if not value:
        return False
    triggers = (
        "10061",
        "connection refused",
        "actively refused",
        "failed to establish a new connection",
        "timed out",
        "name or service not known",
        "temporary failure in name resolution",
        "connection reset",
    )
    return any(token in value for token in triggers)
