"""
Email OTP delivery using SMTP credentials.
Based on PHP SMTP configuration from smtpcodesphp.md
"""

import logging
from django.conf import settings

logger = logging.getLogger(__name__)


def _get_smtp_settings():
    """
    Get SMTP settings from Django settings or use defaults from PHP configuration.
    
    PHP Configuration (from smtpcodesphp.md):
    - smtp_host: smtp.hostinger.com
    - smtp_port: 465
    - smtp_username: registration@sabkapaisa.com
    - smtp_password: Admin$12345
    - smtp_encryption: ssl
    """
    return {
        'host': getattr(settings, 'EMAIL_HOST', 'smtp.hostinger.com'),
        'port': getattr(settings, 'EMAIL_PORT', 465),
        'username': getattr(settings, 'EMAIL_HOST_USER', 'registration@sabkapaisa.com'),
        'password': getattr(settings, 'EMAIL_HOST_PASSWORD', 'Admin$12345'),
        'use_tls': getattr(settings, 'EMAIL_USE_TLS', False),
        'use_ssl': getattr(settings, 'EMAIL_USE_SSL', True),
        'from_email': getattr(
            settings, 
            'DEFAULT_FROM_EMAIL', 
            'SabkaPaisa <registration@sabkapaisa.com>'
        ),
    }


def _render_otp_email_subject():
    """Generate OTP email subject."""
    site_title = getattr(settings, 'SITE_TITLE', 'SabkaPaisa')
    return f"Your OTP for {site_title} - Password Reset"


def _render_otp_email_body(otp, to_name="User"):
    """
    Generate HTML email body for OTP.
    Based on PHP email template from smtpcodesphp.md
    """
    site_title = getattr(settings, 'SITE_TITLE', 'SabkaPaisa')
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset='UTF-8'>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
            .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
            .otp-box {{ display: inline-block; padding: 20px 40px; background: #667eea; color: white; font-size: 32px; font-weight: bold; border-radius: 5px; margin: 20px 0; letter-spacing: 5px; }}
            .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 12px; }}
            .warning {{ background: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0; }}
        </style>
    </head>
    <body>
        <div class='container'>
            <div class='header'>
                <h1>🔐 Your OTP Code</h1>
            </div>
            <div class='content'>
                <p>Hello <strong>{to_name}</strong>,</p>
                
                <p>You requested a One-Time Password (OTP) for your account.</p>
                
                <p>Use the following OTP to complete your verification:</p>
                
                <div style='text-align: center;'>
                    <div class='otp-box'>{otp}</div>
                </div>
                
                <div class='warning'>
                    <strong>⚠️ Security Notice:</strong>
                    <ul>
                        <li>This OTP is valid for 10 minutes only</li>
                        <li>Do not share this code with anyone</li>
                        <li>If you didn't request this, please ignore this email</li>
                    </ul>
                </div>
                
                <p>If you have any questions or concerns, please contact our support team.</p>
                
                <p>Best regards,<br><strong>{site_title} Team</strong></p>
            </div>
            <div class='footer'>
                <p>This is an automated email. Please do not reply to this message.</p>
                <p>&copy; {site_title}. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Plain text fallback
    plain_text = f"""
    Hello {to_name},
    
    You requested a One-Time Password (OTP) for your account.
    
    Your OTP is: {otp}
    
    This OTP is valid for 10 minutes only.
    
    Do not share this code with anyone.
    
    If you didn't request this, please ignore this email.
    
    Best regards,
    {site_title} Team
    """
    
    return html_content, plain_text


def send_otp_email(to_email, otp, to_name="User"):
    """
    Send OTP via email using SMTP settings.

    Args:
        to_email: Recipient email address
        otp: OTP code to send
        to_name: Recipient name (default: "User")

    Returns:
        tuple: (success: bool, error_message: str)
    """
    try:
        smtp_settings = _get_smtp_settings()

        # Check if using console backend (for development)
        backend_path = getattr(settings, 'EMAIL_BACKEND', '')
        if 'console' in backend_path.lower():
            # Log to console for development/testing
            logger.info("=" * 60)
            logger.info(f"OTP EMAIL (Console Backend)")
            logger.info(f"To: {to_email}")
            logger.info(f"Name: {to_name}")
            logger.info(f"OTP: {otp}")
            logger.info(f"Subject: {_render_otp_email_subject()}")
            logger.info("=" * 60)
            return True, ""

        # Check if SMTP is configured
        if not smtp_settings['host'] or not smtp_settings['username']:
            logger.warning("SMTP not configured. Using console backend for OTP.")
            logger.info(f"OTP for {to_email} is: {otp}")
            return True, ""

        # Generate email content
        subject = _render_otp_email_subject()
        html_body, plain_body = _render_otp_email_body(otp, to_name)

        # Send email using Django's send_mail
        from django.core.mail import EmailMultiAlternatives
        
        msg = EmailMultiAlternatives(
            subject=subject,
            body=plain_body,
            from_email=smtp_settings['from_email'],
            to=[to_email],
        )
        msg.attach_alternative(html_body, "text/html")
        
        sent_count = msg.send()
        
        if sent_count > 0:
            logger.info(f"OTP email sent successfully to {to_email}")
            return True, ""
        else:
            logger.error(f"Failed to send OTP email to {to_email}")
            return False, "Failed to send OTP email. Please check SMTP settings."
            
    except Exception as e:
        logger.exception(f"Error sending OTP email to {to_email}: {str(e)}")
        return False, f"SMTP Error: {str(e)}"


def verify_smtp_connection():
    """
    Test SMTP connection with current settings.
    
    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        smtp_settings = _get_smtp_settings()
        
        backend = EmailBackend(
            host=smtp_settings['host'],
            port=smtp_settings['port'],
            username=smtp_settings['username'],
            password=smtp_settings['password'],
            use_tls=smtp_settings['use_tls'],
            use_ssl=smtp_settings['use_ssl'],
            fail_silently=False,
        )
        
        connection = backend.open()
        if connection:
            backend.close()
            return True, "SMTP connection successful!"
        else:
            return False, "Could not open SMTP connection."
            
    except Exception as e:
        return False, f"SMTP connection failed: {str(e)}"
