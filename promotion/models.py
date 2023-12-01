from django.db import models

from product.models import AsiaProduct


class Story(models.Model):
    is_active = models.BooleanField(default=False)
    title = models.CharField(max_length=300)
    slogan = models.CharField(max_length=300)
    text = models.TextField()
    image = models.FileField(upload_to='stories_files', blank=True, null=True)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    products = models.ManyToManyField(AsiaProduct, related_name='stories')




