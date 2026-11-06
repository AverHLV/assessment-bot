from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest

from api.mcp import models


@admin.register(models.OAuthClient)
class OAuthClientAdmin(admin.ModelAdmin):
    list_display = ('client_id',)
    search_fields = ('client_id',)
    ordering = ('client_id',)
    show_full_result_count = False

    def get_queryset(self, request: HttpRequest) -> QuerySet[models.OAuthClient]:
        queryset = super().get_queryset(request)
        if request.resolver_match and request.resolver_match.url_name == 'mcp_oauthclient_changelist':
            return queryset.only('client_id')
        return queryset


@admin.register(models.OAuthNonce)
class OAuthNonceAdmin(admin.ModelAdmin):
    list_display = 'digest', 'purpose', 'expires_at', 'consumed'
    list_filter = 'purpose', 'consumed'
    search_fields = ('digest',)
    ordering = ('-expires_at',)
    show_full_result_count = False
