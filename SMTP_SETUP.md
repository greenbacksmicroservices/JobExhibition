# SMTP Email Configuration for OTP

## Overview

This document describes the SMTP email configuration for sending OTP (One-Time Password) emails in the Django JobExhibition project. The configuration is based on the existing PHP SMTP credentials from `smtpcodesphp.md`.

## SMTP Credentials (Hostinger)

Based on PHP configuration (`smtpcodesphp.md`):

| Setting | Value |
|---------|-------|
| **SMTP Host** | `smtp.hostinger.com` |
| **SMTP Port** | `465` |
| **SMTP Username** | `registration@sabkapaisa.com` |
| **SMTP Password** | `Admin$12345` |
| **Encryption** | `SSL` |
| **From Email** | `SabkaPaisa <registration@sabkapaisa.com>` |

## Files Modified/Created

### 1. New File: `dashboard/otp/email.py`

A dedicated email OTP module with the following features:

- **HTML Email Templates**: Beautiful, responsive email design matching the PHP template
- **SMTP Connection Management**: Proper connection handling and error recovery
- **Fallback Support**: Console logging if SMTP is not configured
- **Connection Testing**: Utility function to verify SMTP connectivity

#### Key Functions:

```python
# Send OTP email
send_otp_email(to_email, otp, to_name="User")

# Test SMTP connection
verify_smtp_connection()
```

### 2. Updated: `jobexhibition/settings.py`

Email configuration updated with PHP SMTP credentials as defaults:

```python
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.hostinger.com"
EMAIL_PORT = 465
EMAIL_HOST_USER = "registration@sabkapaisa.com"
EMAIL_HOST_PASSWORD = "Admin$12345"
EMAIL_USE_TLS = False
EMAIL_USE_SSL = True
DEFAULT_FROM_EMAIL = "SabkaPaisa <registration@sabkapaisa.com>"
SITE_TITLE = "SabkaPaisa"
```

### 3. Updated: `dashboard/views.py`

Modified `_issue_email_session_otp()` function to use the new HTML email module instead of plain text emails.

### 4. Updated: `.env.example`

Added SMTP configuration section with Hostinger settings.

## Environment Variables

You can override the default SMTP settings using environment variables in `.env` file:

```env
# Email (SMTP) for OTP / notifications
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.hostinger.com
EMAIL_PORT=465
EMAIL_HOST_USER=registration@sabkapaisa.com
EMAIL_HOST_PASSWORD=Admin$12345
EMAIL_USE_TLS=False
EMAIL_USE_SSL=True
DEFAULT_FROM_EMAIL=SabkaPaisa <registration@sabkapaisa.com>
SITE_TITLE=SabkaPaisa
```

## Email Template Features

The OTP email includes:

1. **Professional Design**: Gradient header with modern styling
2. **OTP Display**: Large, prominent OTP code in a styled box
3. **Security Notice**: Expiration time and security warnings
4. **Responsive Layout**: Works on desktop and mobile email clients
5. **Plain Text Fallback**: For email clients that don't support HTML

## Testing SMTP Connection

To test if your SMTP configuration is working:

```python
from dashboard.otp.email import verify_smtp_connection

success, message = verify_smtp_connection()
print(message)
```

## Usage in Views

The OTP email functionality is automatically used when issuing email-based OTPs:

```python
# In any view that needs email OTP
from dashboard.views import _issue_email_session_otp

otp, error = _issue_email_session_otp(
    request, 
    session_key='email_otp',
    email=user_email,
    extra_payload={'purpose': 'password_reset'}
)

if error:
    # Handle error
else:
    # OTP sent successfully
```

## Comparison: PHP vs Django Implementation

| Feature | PHP | Django |
|---------|-----|--------|
| **SMTP Host** | smtp.hostinger.com | smtp.hostinger.com |
| **Port** | 465 | 465 |
| **Encryption** | SSL | SSL |
| **Template** | HTML with gradient | HTML with gradient |
| **Fallback** | PHP mail() | Console logging |
| **Error Handling** | Try-catch | Exception handling |
| **Configuration** | Database settings | Django settings/.env |

## Troubleshooting

### Issue: "Connection timed out"
- Check if port 465 is open on your firewall
- Verify SMTP host is correct: `smtp.hostinger.com`

### Issue: "Authentication failed"
- Verify username and password in `.env` file
- Check if the email account exists on Hostinger

### Issue: "SSL connection error"
- Ensure `EMAIL_USE_SSL=True` and `EMAIL_USE_TLS=False`
- Port should be `465` for SSL

### Issue: Emails going to spam
- Verify domain SPF/DKIM records
- Use a proper from email address
- Consider setting up DMARC

## Security Notes

1. **Never commit `.env` file** to version control
2. **Use strong passwords** for email accounts
3. **Enable 2FA** on email accounts if available
4. **Monitor email sending limits** (Hostinger may have daily limits)
5. **Log email failures** for debugging but don't log OTP codes

## Migration from PHP

If you're migrating from the PHP implementation:

1. ✅ SMTP credentials are the same
2. ✅ Email template design matches PHP version
3. ✅ OTP validity period is 10 minutes (same as PHP)
4. ✅ Security notices and warnings included
5. ✅ HTML and plain text versions provided

## Additional Resources

- [Django Email Documentation](https://docs.djangoproject.com/en/4.2/topics/email/)
- [Hostinger SMTP Settings](https://www.hostinger.com/tutorials/how-to-use-free-smtp-service)
- `smtpcodesphp.md` - Original PHP implementation reference

---

**Last Updated:** March 11, 2026  
**Status:** ✅ Ready to Use  
**Based on:** PHP SMTP configuration from `smtpcodesphp.md`
