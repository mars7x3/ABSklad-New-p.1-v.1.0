from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import *


@admin.register(MyUser)
class MyUserAdmin(UserAdmin):
    search_fields = ("email", "username", "id")


admin.site.register(DealerProfile)
admin.site.register(StaffProfile)

admin.site.register(DealerStatus)
admin.site.register(Notification)
admin.site.register(Wallet)

admin.site.register(BalancePlus)

