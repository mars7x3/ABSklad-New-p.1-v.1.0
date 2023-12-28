from django.db import models

from account.models import MyUser
from product.models import Category, AsiaProduct


class CRMTask(models.Model):
    STATUS = (
        ('created', 'created'),
        ('completed', 'completed'),
        ('not_completed', 'not_completed'),
        ('wait', 'wait'),
    )
    status = models.CharField(max_length=20, choices=STATUS, default='created')
    title = models.CharField(max_length=300)
    text = models.TextField()
    end_date = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    creator = models.ForeignKey(MyUser, on_delete=models.CASCADE, related_name='tasks')
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ('-id',)


class CRMTaskFile(models.Model):
    task = models.ForeignKey(CRMTask, on_delete=models.CASCADE, related_name='files')
    file = models.FileField(upload_to='tasks')


class CRMTaskGrade(models.Model):
    title = models.CharField(max_length=50)


class CRMTaskResponse(models.Model):
    task = models.ForeignKey(CRMTask, on_delete=models.CASCADE, related_name='task_responses')
    executor = models.ForeignKey(MyUser, on_delete=models.CASCADE, related_name='task_responses')
    text = models.TextField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)
    grade = models.ForeignKey(CRMTaskGrade, on_delete=models.SET_NULL, blank=True, null=True, related_name='tasks')
    is_done = models.BooleanField(default=False)

    class Meta:
        ordering = ('-id',)


class CRMTaskResponseFile(models.Model):
    task = models.ForeignKey(CRMTaskResponse, on_delete=models.CASCADE, related_name='response_files')
    file = models.FileField(upload_to='response')


class KPI(models.Model):
    STATUS = (
        (1, 'product'),
        (2, 'category'),
        (3, 'money'),
    )
    author = models.ForeignKey(MyUser, on_delete=models.CASCADE, related_name='author_kpis')
    executor = models.ForeignKey(MyUser, on_delete=models.CASCADE, related_name='executor_kpis')
    status = models.IntegerField(choices=STATUS)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ('-id',)


class KPIItem(models.Model):
    STATUS = (
        (1, 'count'),
        (2, 'money'),
    )
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.IntegerField(choices=STATUS)
    kpi = models.ForeignKey(KPI, on_delete=models.CASCADE, related_name='kpi_items')
    products = models.ManyToManyField(AsiaProduct, related_name='kpi_items')
    categories = models.ManyToManyField(Category, related_name='kpi_items')
    amount = models.IntegerField()

