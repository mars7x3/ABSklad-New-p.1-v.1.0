import argparse

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from notification.utils import generate_vapid_keys


class Command(BaseCommand):
    help = "Generating pywebpush keys"

    def add_arguments(self, parser):
        parser.add_argument(
            '-s',
            '--save',
            type=bool,
            default=False,
            action=argparse.BooleanOptionalAction
        )

    def handle(self, *args, **options):
        keys = generate_vapid_keys()
        self.stdout.write(
            self.style.SUCCESS(
                'Public key: {public}\nPrivate key: {private}\nPublic Base64: {public_base64}'.format(**keys)
            )
        )

        if options.get("save"):
            with open(settings.VAPID_PUBLIC, 'w') as file:
                file.write(keys["public"])

            with open(settings.VAPID_PRIVATE, 'w') as file:
                file.write(keys["private"])

            with open(settings.VAPID_PUBLIC_BASE64, 'w') as file:
                file.write(keys["public_base64"])

            self.stdout.write(self.style.SUCCESS('Successfully saved'))
