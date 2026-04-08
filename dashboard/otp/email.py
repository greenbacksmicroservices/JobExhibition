"""Email OTP delivery helpers for JobExhibition registration and login flows."""

import logging
from html import escape

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection
from django.core.mail.backends.smtp import EmailBackend

logger = logging.getLogger(__name__)


def _normalize_smtp_password(value):
    """Normalize app-password values (supports spaced Gmail app passwords)."""
    return "".join(str(value or "").split())


def _get_primary_smtp_settings():
    """Read primary SMTP settings from Django settings."""
    username = (getattr(settings, "EMAIL_HOST_USER", "") or "").strip()
    password = _normalize_smtp_password(getattr(settings, "EMAIL_HOST_PASSWORD", "") or "")
    use_tls = bool(getattr(settings, "EMAIL_USE_TLS", False))
    use_ssl = bool(getattr(settings, "EMAIL_USE_SSL", False))

    # SMTP backends generally expect either TLS or SSL, not both.
    if use_tls and use_ssl:
        use_ssl = False

    return {
        "host": getattr(settings, "EMAIL_HOST", ""),
        "port": int(getattr(settings, "EMAIL_PORT", 0) or 0),
        "username": username,
        "password": password,
        "use_tls": use_tls,
        "use_ssl": use_ssl,
        "from_email": (
            getattr(settings, "DEFAULT_FROM_EMAIL", "")
            or username
            or "JobExhibition <no-reply@jobexhibition.com>"
        ),
    }


def _get_fallback_smtp_settings(primary_settings):
    """Optional fallback sender account (if configured)."""
    fallback_username = (getattr(settings, "EMAIL_FALLBACK_HOST_USER", "") or "").strip()
    fallback_password = _normalize_smtp_password(
        getattr(settings, "EMAIL_FALLBACK_HOST_PASSWORD", "") or ""
    )
    if not fallback_username or not fallback_password:
        return None

    use_tls = bool(
        getattr(settings, "EMAIL_FALLBACK_USE_TLS", primary_settings["use_tls"])
    )
    use_ssl = bool(
        getattr(settings, "EMAIL_FALLBACK_USE_SSL", primary_settings["use_ssl"])
    )
    if use_tls and use_ssl:
        use_ssl = False

    return {
        "host": getattr(settings, "EMAIL_FALLBACK_HOST", primary_settings["host"]),
        "port": int(
            getattr(settings, "EMAIL_FALLBACK_PORT", primary_settings["port"])
            or primary_settings["port"]
            or 0
        ),
        "username": fallback_username,
        "password": fallback_password,
        "use_tls": use_tls,
        "use_ssl": use_ssl,
        "from_email": (
            getattr(settings, "EMAIL_FALLBACK_FROM_EMAIL", "")
            or fallback_username
        ),
    }


def _render_otp_email_subject():
    site_title = getattr(settings, "SITE_TITLE", "JobExhibition")
    return f"{site_title} Verification OTP"


def _resolve_otp_email_logo():
    """Resolve logo source for OTP mails (external URL only, no attachments)."""
    custom_url = (getattr(settings, "OTP_EMAIL_LOGO_URL", "") or "").strip()
    if custom_url:
        return custom_url, ""
    return "", ""


def _render_otp_email_body(otp, to_name="User", logo_src="dashboard/img/je-logo.svg"):
    """Generate HTML + plain body for OTP mail using JobExhibition design."""
    site_title = getattr(settings, "SITE_TITLE", "JobExhibition")
    safe_name = escape((to_name or "User").strip() or "User")
    safe_otp = escape(str(otp or "").strip())
    safe_logo_src = escape(logo_src or "")
    header_logo_html = ""
    if safe_logo_src:
        header_logo_html = f"""
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" class="header-logo-table">
                    <tr>
                        <td style="padding:0;margin:0;line-height:0;">
                            <img src="{safe_logo_src}" alt="{site_title} Logo" class="header-logo" style="display:block;width:100%;max-width:600px;height:auto;border:0;outline:none;text-decoration:none;">
                        </td>
                    </tr>
                </table>
""".rstrip()
    else:
        header_logo_html = f"""
                <div class="header-logo-wrap">
                    <span class="header-logo-fallback">{site_title}</span>
                </div>
""".rstrip()

    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{site_title} Verification</title>
    <style>
        :root {{ color-scheme: light only; supported-color-schemes: light; }}
        body {{ font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; background-color: #f9fafb; margin: 0; padding: 0; }}
        .wrapper {{ width: 100%; table-layout: fixed; background-color: #f9fafb; padding-bottom: 40px; }}
        .main-container {{ max-width: 600px; background-color: #ffffff; margin: 40px auto; border-radius: 12px; overflow: hidden; box-shadow: 0 10px 25px rgba(0,0,0,0.05); border: 1px solid #eef0f2; }}
        .header {{ background: #ffffff; padding: 0; text-align: center; color: #111827; border-bottom: 1px solid #e2e8f0; line-height: 0; }}
        .header-logo-table {{ border-collapse: collapse; }}
        .header-logo-wrap {{ display: block; width: 100%; background: #ffffff; padding: 18px 14px; }}
        .header-logo {{ width: 100%; max-width: 600px; height: auto; display: block; }}
        .header-logo-fallback {{ display: inline-block; color: #1e3a8a; font-size: 24px; font-weight: 800; letter-spacing: 0.4px; }}
        .body-content {{ padding: 40px; text-align: center; }}
        .body-content h2 {{ color: #1e293b; font-size: 22px; margin-bottom: 10px; }}
        .body-content p {{ color: #64748b; font-size: 16px; line-height: 1.6; }}
        .otp-container {{ margin: 30px 0; padding: 20px; background-color: #f1f5f9; border-radius: 8px; border: 1px solid #e2e8f0; }}
        .otp-code {{ font-size: 40px; font-weight: bold; color: #2563eb; letter-spacing: 10px; margin: 0; }}
        .otp-brand-text {{ margin: 12px 0 0; font-size: 18px; font-weight: 800; color: #1e3a8a; letter-spacing: 0.3px; }}
        .footer {{ background-color: #ffffff; padding: 40px 30px; text-align: center; border-top: 1px solid #f1f5f9; }}
        .company-info {{ font-size: 15px; color: #475569; line-height: 1.6; font-weight: 500; }}
        .security-note {{ font-size: 12px; color: #94a3b8; margin-top: 25px; padding-top: 20px; }}
    </style>
</head>
<body>
    <div class="wrapper">
        <div class="main-container">
            <div class="header">
                {header_logo_html}
            </div>
            <div class="body-content">
                <h2>Verify Your Account</h2>
                <p>Namaste {safe_name},</p>
                <p>Use the following One-Time Password (OTP) to complete your secure login. This code is valid for 10 minutes.</p>
                <div class="otp-container">
                    <div class="otp-code">{safe_otp}</div>
                    <div class="otp-brand-text">{site_title}</div>
                </div>
                <p>If you did not request this code, please ignore this email or contact support if you have concerns.</p>
            </div>
            <div class="footer">
                <div class="company-info">
                    <strong>{site_title}</strong><br>
                    Connecting Talent with Opportunity<br>
                    Bhubaneswar, Odisha
                </div>
                <div class="security-note">
                    This is an automated message. Please do not reply directly to this email.
                </div>
            </div>
        </div>
    </div>
</body>
</html>
""".strip()

    plain_text = (
        f"Hello {to_name or 'User'},\n\n"
        f"Use this OTP to verify your account: {otp}\n"
        "This OTP is valid for 10 minutes.\n\n"
        "If you did not request this, please ignore this email.\n\n"
        f"Regards,\n{site_title} Team"
    )

    return html_content, plain_text


def _send_message(
    to_email,
    subject,
    plain_body,
    html_body,
    from_email,
    smtp_settings=None,
    inline_logo_path="",
):
    """Send an email using default backend or explicit SMTP connection."""
    connection = None
    if smtp_settings:
        connection = get_connection(
            backend="django.core.mail.backends.smtp.EmailBackend",
            host=smtp_settings["host"],
            port=smtp_settings["port"],
            username=smtp_settings["username"],
            password=smtp_settings["password"],
            use_tls=smtp_settings["use_tls"],
            use_ssl=smtp_settings["use_ssl"],
            fail_silently=False,
        )

    msg = EmailMultiAlternatives(
        subject=subject,
        body=plain_body,
        from_email=from_email,
        to=[to_email],
        connection=connection,
    )
    msg.attach_alternative(html_body, "text/html")

    return msg.send()


def send_otp_email(to_email, otp, to_name="User"):
    """
    Send OTP email.

    Returns:
        tuple[bool, str]: success flag and optional error message.
    """
    target_email = (to_email or "").strip().lower()
    if not target_email:
        return False, "Email address is required."

    backend_path = (getattr(settings, "EMAIL_BACKEND", "") or "").lower()
    if "console" in backend_path:
        logger.info("=" * 60)
        logger.info("OTP EMAIL (Console Backend)")
        logger.info("To: %s", target_email)
        logger.info("Name: %s", to_name or "User")
        logger.info("OTP: %s", otp)
        logger.info("Subject: %s", _render_otp_email_subject())
        logger.info("=" * 60)
        return True, ""

    primary = _get_primary_smtp_settings()
    if not primary["host"] or not primary["username"] or not primary["password"]:
        logger.error("Primary SMTP credentials are missing.")
        return False, "Email service is not configured. Please contact support."

    subject = _render_otp_email_subject()
    logo_src, inline_logo_path = _resolve_otp_email_logo()
    html_body, plain_body = _render_otp_email_body(otp, to_name, logo_src=logo_src)

    try:
        sent_count = _send_message(
            to_email=target_email,
            subject=subject,
            plain_body=plain_body,
            html_body=html_body,
            from_email=primary["from_email"],
            smtp_settings=primary,
            inline_logo_path=inline_logo_path,
        )
        if sent_count > 0:
            logger.info("OTP email sent successfully to %s (primary SMTP).", target_email)
            return True, ""
    except Exception:
        logger.exception("Primary SMTP send failed for %s.", target_email)

    fallback = _get_fallback_smtp_settings(primary)
    if fallback:
        try:
            sent_count = _send_message(
                to_email=target_email,
                subject=subject,
                plain_body=plain_body,
                html_body=html_body,
                from_email=fallback["from_email"],
                smtp_settings=fallback,
                inline_logo_path=inline_logo_path,
            )
            if sent_count > 0:
                logger.info("OTP email sent successfully to %s (fallback SMTP).", target_email)
                return True, ""
        except Exception:
            logger.exception("Fallback SMTP send failed for %s.", target_email)

    logger.error("Failed to send OTP email to %s.", target_email)
    return False, "Unable to send OTP email right now. Please try again."


def verify_smtp_connection():
    """
    Test SMTP connection with current primary settings.

    Returns:
        tuple[bool, str]: success flag and status message.
    """
    smtp_settings = _get_primary_smtp_settings()
    if not smtp_settings["host"] or not smtp_settings["username"] or not smtp_settings["password"]:
        return False, "SMTP credentials are missing."

    try:
        backend = EmailBackend(
            host=smtp_settings["host"],
            port=smtp_settings["port"],
            username=smtp_settings["username"],
            password=smtp_settings["password"],
            use_tls=smtp_settings["use_tls"],
            use_ssl=smtp_settings["use_ssl"],
            fail_silently=False,
        )
        connection = backend.open()
        if connection:
            backend.close()
            return True, "SMTP connection successful."
        return False, "Could not open SMTP connection."
    except Exception as exc:
        return False, f"SMTP connection failed: {exc}"
