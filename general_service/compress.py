import io
import uuid

from PIL import Image
from django.core.files.base import ContentFile
from django.db import models
from django.db.models.fields.files import ImageFieldFile


class WEBPFieldFile(ImageFieldFile):
    def save(self, name, content, save=True):
        content.file.seek(0)
        image = Image.open(content.file)
        image_bytes = io.BytesIO()
        image.save(fp=image_bytes, format="WEBP")
        image_content_file = ContentFile(content=image_bytes.getvalue())
        super().save(name, image_content_file, save)


class WEBPField(models.ImageField):
    attr_class = WEBPFieldFile


def product_image_folder(instance, filename):
    return 'product-images/{}.webp'.format(uuid.uuid4().hex)


def banner_image_folder(instance, filename):
    return 'banner-images/{}.webp'.format(uuid.uuid4().hex)


def user_image_folder(instance, filename):
    return 'users/{}.webp'.format(uuid.uuid4().hex)


def notification_image_folder(instance, filename):
    return 'notifications/{}.webp'.format(uuid.uuid4().hex)
