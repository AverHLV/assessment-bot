from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from api.user import models


@admin.register(models.User)
class UserAdmin(BaseUserAdmin):
    list_display = BaseUserAdmin.list_display + ('external_id', 'is_superuser')
    search_fields = BaseUserAdmin.search_fields + ('id', 'external_id')
    fieldsets = BaseUserAdmin.fieldsets + (
        (
            'Custom fields',
            {
                'fields': ('external_id',),
            },
        ),
    )
