from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from .models import *


@admin.register(MyUser)
class MyUserAdmin(UserAdmin):
    search_fields = ("email", "username", "id")
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("username", "email", "name", "password1", "password2"),
            }
        ),
        (
            _("Advanced options"),
            {
                "classes": ("wide",),
                "fields": ("status", "uid",),
            }
        )
    )
    fieldsets = (
        (_("Personal info"), {"fields": ("email", "username", "password", "pwd", "status", "uid")}),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )


admin.site.register(DealerProfile)
admin.site.register(RopProfile)
admin.site.register(ManagerProfile)
admin.site.register(WarehouseProfile)

admin.site.register(DealerStatus)
admin.site.register(Notification)
admin.site.register(Wallet)

admin.site.register(BalancePlus)
