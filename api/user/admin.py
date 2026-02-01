from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from api.user import models


@admin.register(models.User)
class UserAdmin(BaseUserAdmin):
    list_display = BaseUserAdmin.list_display + ('is_superuser',)
