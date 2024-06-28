#!/bin/bash

echo 'Collecting static files...'
python manage.py collectstatic --no-input

echo 'Making migrations...'
python manage.py makemigrations --no-input
echo 'Migrate...'
python manage.py migrate --no-input

echo 'Running server...'
gunicorn absklad_commerce.wsgi:application --bind 0.0.0.0:8000
