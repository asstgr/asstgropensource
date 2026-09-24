#!/bin/sh
set -e

SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-asstgrv7.settings.dev}"
DB_HOST="${DB_HOST_local:-db}"
DB_PORT="${DB_PORT_local:-5432}"

echo "⏳ Waiting for PostgreSQL on ${DB_HOST}:${DB_PORT}..."
until nc -z "$DB_HOST" "$DB_PORT"; do
  sleep 1
done
echo "✅ PostgreSQL is ready."

echo "📦 Applying migrations..."
python manage.py migrate --settings="$SETTINGS_MODULE" --noinput

echo "🗂  Collecting static files..."
python manage.py collectstatic --settings="$SETTINGS_MODULE" --noinput || true

# Automatically create a superuser if the variables are provided
if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ] && [ -n "$DJANGO_SUPERUSER_EMAIL" ]; then
  echo "👤 Checking / creating superuser '$DJANGO_SUPERUSER_USERNAME'..."
  python manage.py shell --settings="$SETTINGS_MODULE" -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='$DJANGO_SUPERUSER_USERNAME').exists():
    User.objects.create_superuser('$DJANGO_SUPERUSER_USERNAME', '$DJANGO_SUPERUSER_EMAIL', '$DJANGO_SUPERUSER_PASSWORD')
    print('Superuser created.')
else:
    print('Superuser already exists.')
"
fi

echo "🚀 Starting Django server on 0.0.0.0:8000..."
exec python manage.py runserver 0.0.0.0:8000 --settings="$SETTINGS_MODULE"