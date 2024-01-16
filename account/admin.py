from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from .models import *


@admin.register(MyUser)
class MyUserAdmin(UserAdmin):
    list_display = ("username", "email", "id", "name", "phone", "is_active", "status")
    list_filter = ("is_staff", "is_superuser", "is_active", "status", "groups")
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
        (_("Personal info"), {"fields": ("email", "username", "password", "pwd", "status", "uid",
                                         "name", "phone", "image", 'firebase_token')}),
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
admin.site.register(DealerStore)

admin.site.register(DealerStatus)
admin.site.register(Notification)
admin.site.register(Wallet)

admin.site.register(BalancePlus)
admin.site.register(BalanceHistory)
admin.site.register(CRMNotification)
admin.site.register(VerifyCode)


@admin.register(StaffMagazine)
class StaffMagazineAdmin(admin.ModelAdmin):
    list_display = ("id", "user")
    list_display_links = ("id", "user")
