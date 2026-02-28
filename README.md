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

## Production MySQL (Hostinger)

Set these env vars on your live server before starting Django:

```powershell
$env:DB_ENGINE="django.db.backends.mysql"
$env:DB_NAME="your_db_name"
$env:DB_USER="your_db_user"
$env:DB_PASSWORD="your_db_password"
$env:DB_HOST="srv685.hstgr.io"
$env:DB_PORT="3306"
```

Optional: if you want local SQLite instead, set:

```powershell
$env:DB_ENGINE="django.db.backends.sqlite3"
```

## VPS Deploy Checklist (Hostinger)

Use `.env.example` as reference and set all required env vars on VPS.

Every deploy run this order:

```bash
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput --clear
python manage.py check --deploy
```

Then restart app service (gunicorn/supervisor/systemd/nginx setup as per your VPS).

Or run:

```bash
chmod +x scripts/deploy_vps.sh
./scripts/deploy_vps.sh
```

Important for static cache:
- Increase `STATIC_ASSET_VERSION` on each deploy (`2`, `3`, `4`, ...)
- This forces browsers to fetch fresh JS/CSS/logo files.
- Keep `DJANGO_STATICFILES_STORAGE=whitenoise.storage.CompressedManifestStaticFilesStorage` in production.

Sidebar logo source file:
- `static/dashboard/img/je-logo.svg`

## Notes
- Only staff or superuser accounts can access the dashboard.
- The admin landing page is at `/admin-dashboard/`.

