from django.contrib import admin

from api.assessment import models
from core.admin import DictionaryAdmin

dictionary_models = (models.MediaCategory,)


@admin.register(*dictionary_models)
class AssessmentDictionaryAdmin(DictionaryAdmin):
    pass


@admin.action(description='Finish assessment for the selected media')
def finish_assessment(_modeladmin, _request, queryset):
    queryset.update(assessment_status=queryset.model.AssessmentStatus.COMPLETED)


@admin.register(models.Media)
class MediaAdmin(admin.ModelAdmin):
    list_display = 'id', 'name', 'create_dt', 'update_dt', 'assessment_status', 'assessment_until_dt', 'category'
    list_display_links = list_display
    list_select_related = ('category',)
    list_filter = 'assessment_status', 'category'
    search_fields = 'code', 'name'
    readonly_fields = 'id', 'create_dt', 'update_dt'
    ordering = '-update_dt', '-create_dt'
    actions = (finish_assessment,)


@admin.register(models.Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    list_display = 'id', 'mark', 'partial', 'create_dt', 'display_media', 'display_user'
    list_display_links = list_display
    list_select_related = 'media', 'user'
    search_fields = 'media__name', 'user__username'
    readonly_fields = 'id', 'create_dt'
    ordering = ('-create_dt',)

    def display_media(self, obj: models.Assessment) -> str:
        return obj.media.name

    def display_user(self, obj: models.Assessment) -> str:
        return obj.user.username

    display_media.short_description = 'Media'
    display_user.short_description = 'User'

    def get_queryset(self, request):
        only_fields = 'mark', 'partial', 'create_dt', 'media_id', 'user_id', 'media__name', 'user__username'
        return super().get_queryset(request).only(*only_fields)
