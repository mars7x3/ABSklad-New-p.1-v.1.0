import logging

from django.utils import timezone
from rest_framework.exceptions import ValidationError


def string_date_to_datetime(date_string: str):
    try:
        date = timezone.datetime.strptime(date_string, "%Y-%m-%d")
        return timezone.make_aware(date)
    except Exception as e:
        logging.error(e)
        raise ValidationError(detail="Wrong format of date %s " % date_string)
