#!/usr/bin/env bash
set -euo pipefail

if [[ ! -f "manage.py" ]]; then
  echo "Run this script from project root (manage.py not found)."
  exit 1
fi

echo "Installing dependencies..."
pip install -r requirements.txt

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput --clear

echo "Running Django deployment checks..."
python manage.py check --deploy

echo "Deploy preparation completed successfully."
