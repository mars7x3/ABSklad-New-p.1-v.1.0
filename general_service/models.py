from django.db import models


class City(models.Model):
    title = models.CharField(max_length=20)
    slug = models.SlugField(max_length=30, unique=True)
    user_uid = models.CharField(max_length=40, blank=True, null=True)
    price_uid = models.CharField(max_length=40, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    is_show = models.BooleanField(default=True)

    def __str__(self):
        return self.title

    class Meta:
        indexes = [
            models.Index(fields=['slug'])
        ]


class Village(models.Model):
    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name='villages')
    title = models.CharField(max_length=20)
    slug = models.SlugField(max_length=30, unique=True)
    user_uid = models.CharField(max_length=40, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    is_show = models.BooleanField(default=True)

    def __str__(self):
        return self.title

    class Meta:
        indexes = [
            models.Index(fields=['slug'])
        ]


class Stock(models.Model):
    city = models.ForeignKey(City, on_delete=models.SET_NULL, blank=True, null=True, related_name='stocks')
    title = models.CharField(max_length=300, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    schedule = models.TextField(blank=True, null=True)
    uid = models.CharField(max_length=40, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    is_show = models.BooleanField(default=True)

    def __str__(self): 
        return f'{self.city.title} | {self.address}'


class CashBox(models.Model):
    stock = models.OneToOneField(Stock, on_delete=models.CASCADE, related_name='cash_box')
    title = models.CharField(max_length=30)
    uid = models.CharField(max_length=40, blank=True, null=True)

    def __str__(self):
        return self.title


class StockPhone(models.Model):
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, null=True, related_name='phones')
    phone = models.CharField(max_length=30)


class RequisiteCategory(models.Model):
    title = models.CharField(max_length=100)
    logo = models.FileField(upload_to='requisite_images', blank=True, null=True)
    is_active = models.BooleanField(default=True)


class Requisite(models.Model):
    category = models.ForeignKey(RequisiteCategory, on_delete=models.CASCADE, related_name='requisites')
    text = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)


class RequisiteCity(models.Model):
    requisite = models.ForeignKey(Requisite, on_delete=models.CASCADE, related_name='requisite_cities')
    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name='requisite_cities')


class PriceType(models.Model):
    title = models.CharField(max_length=20)
    uid = models.CharField(max_length=40, blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.title


