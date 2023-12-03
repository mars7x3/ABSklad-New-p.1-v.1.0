from django.contrib import admin

from .models import *

admin.site.register(Story)
admin.site.register(Target)
admin.site.register(TargetPresent)
