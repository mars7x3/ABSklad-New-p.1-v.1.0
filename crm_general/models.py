from django.db import models

from account.models import MyUser


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


class CRMTaskFile(models.Model):
    task = models.ForeignKey(CRMTask, on_delete=models.CASCADE, related_name='files')
    file = models.ImageField(upload_to='tasks')


class CRMTaskGrade(models.Model):
    title = models.CharField(max_length=50)


class CRMTaskResponse(models.Model):
    task = models.ForeignKey(CRMTask, on_delete=models.CASCADE, related_name='task_responses')
    executor = models.ForeignKey(MyUser, on_delete=models.CASCADE, related_name='task_responses')
    text = models.TextField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)
    grade = models.ForeignKey(CRMTaskGrade, on_delete=models.SET_NULL, blank=True, null=True, related_name='tasks')


class CRMTaskResponseFile(models.Model):
    task = models.ForeignKey(CRMTaskResponse, on_delete=models.CASCADE, related_name='response_files')
    file = models.ImageField(upload_to='response')


class KPI(models.Model):
    user = models.ForeignKey(MyUser, on_delete=models.CASCADE, related_name='kpis')

