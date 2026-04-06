# Job Exhibition Admin (Django)

## Quick Start

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open `http://127.0.0.1:8000/login/` and sign in with your admin account.

---

## 📧 SMTP Email Credentials (For OTP & Password Reset)

**These credentials are working and tested.** Used for sending OTP emails and password reset links.

### Gmail SMTP Configuration (From PHP makeMailer function)

| Setting | Value |
|---------|-------|
| **SMTP Host** | `smtp.gmail.com` |
| **SMTP Port** | `587` |
| **SMTP Username** | `jyotijrs9404j@gmail.com` |
| **SMTP Password** | `prsx sihj jdne qikf` |
| **Encryption** | `TLS (STARTTLS)` |
| **From Email** | `Job Exhibition <jyotijrs9404j@gmail.com>` |

### Environment Variables (.env file)

```bash
# Email (SMTP) Configuration - Gmail
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=jyotijrs9404j@gmail.com
EMAIL_HOST_PASSWORD=prsx sihj jdne qikf
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
DEFAULT_FROM_EMAIL=Job Exhibition <jyotijrs9404j@gmail.com>
SITE_TITLE=Job Exhibition
```

### Test the Email API

**Endpoint:** `http://localhost:8000/api/test-email-otp/`

**Using curl:**
```bash
curl -X POST http://localhost:8000/api/test-email-otp/ ^
  -H "Content-Type: application/json" ^
  -d "{\"email\": \"your-email@gmail.com\", \"name\": \"Your Name\"}"
```

**Using Postman:**
- **Method:** POST
- **URL:** `http://localhost:8000/api/test-email-otp/`
- **Headers:** `Content-Type: application/json`
- **Body (raw JSON):**
```json
{
    "email": "your-email@gmail.com",
    "name": "Your Name"
}
```

**Response:**
```json
{
    "success": true,
    "message": "OTP sent successfully to your-email@gmail.com",
    "debug_otp": "123456"
}
```

---

## Production MySQL (Hostinger)

Set these env vars on your live server before starting Django:

```bash
export DB_ENGINE=django.db.backends.mysql
export DB_NAME=your_db_name
export DB_USER=your_db_user
export DB_PASSWORD=your_db_password
export DB_HOST=srv685.hstgr.io
export DB_PORT=3306
```

Use SQLite only for local/dev:

```bash
export DB_ENGINE=django.db.backends.sqlite3
```

## VPS Deploy Checklist (Hostinger)

Use `.env.example` as reference and set all required env vars on VPS.

Critical for OTP + payment on production:

```bash
# SMTP
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-sender@gmail.com
EMAIL_HOST_PASSWORD=your-gmail-app-password

# Payment public URLs
PAYMENT_PUBLIC_BASE_URL=https://your-domain.com
MERCHANT_REDIRECT_URL=https://your-domain.com/payment/redirect/
MERCHANT_CALLBACK_URL=https://your-domain.com/api/payment/callback/

# Optional safety fallbacks
PAYMENT_GATEWAY_INTERNAL_FALLBACK=True
PAYMENT_FORCE_HTTPS_URLS=True
```

```bash
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate --noinput
python manage.py collectstatic --noinput --clear
python manage.py check --deploy
```

Then restart app service (gunicorn/supervisor/systemd/nginx as per your setup).

Or run:

```bash
chmod +x scripts/deploy_vps.sh
./scripts/deploy_vps.sh
```

## Git Update On VPS

From project root:

```bash
cd /path/to/Jobexhibition
git fetch --all
git checkout main
git pull --ff-only origin main
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate --noinput
python manage.py collectstatic --noinput --clear
python manage.py check --deploy
sudo systemctl restart gunicorn
sudo systemctl restart nginx
```

If your service names are different, restart those service names instead.

## Static Cache Notes

- `STATIC_ASSET_VERSION` is now auto-derived from deploy commit/hash when env var is not set.
- You can still override manually:

```bash
export STATIC_ASSET_VERSION=20260228_1
```

- Keep `DJANGO_STATICFILES_STORAGE=whitenoise.storage.CompressedManifestStaticFilesStorage` in production.

Sidebar logo source file:
- `static/dashboard/img/je-logo.svg`

## Notes

- Only staff or superuser accounts can access admin dashboard routes.
- Admin landing page is `/admin-dashboard/`.
