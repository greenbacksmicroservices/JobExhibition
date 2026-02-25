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

## Notes
- Only staff or superuser accounts can access the dashboard.
- The admin landing page is at `/admin-dashboard/`.

