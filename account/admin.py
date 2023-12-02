from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from .models import *


admin.site.register(MyUser)
admin.site.register(DealerProfile)
admin.site.register(StaffProfile)

admin.site.register(DealerStatus)
admin.site.register(Notification)
admin.site.register(Wallet)

admin.site.register(BalancePlus)

