from django.contrib import admin
from django.utils import timezone

from datetime import timedelta

from api.assessment import models
from core.admin import DictionaryAdmin

dictionary_models = (models.MediaCategory,)


@admin.register(*dictionary_models)
class AssessmentDictionaryAdmin(DictionaryAdmin):
    pass


@admin.action(description='Start assessment for the selected media (1 week)')
def start_assessment_for_1_week(_modeladmin, _request, queryset):
    queryset.update(
        assessment_status=queryset.model.AssessmentStatus.IN_PROGRESS,
        assessment_until_dt=timezone.now() + timedelta(days=8),
    )


@admin.action(description='Finish assessment for the selected media')
def finish_assessment(_modeladmin, _request, queryset):
    queryset.update(assessment_status=queryset.model.AssessmentStatus.COMPLETED)


@admin.register(models.Media)
class MediaAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'name',
        'create_dt',
        'update_dt',
        'assessment_status',
        'assessment_until_dt',
        'category',
        'display_creator',
    )
    list_display_links = list_display
    list_select_related = 'category', 'creator'
    list_filter = 'assessment_status', 'category', 'creator'
    search_fields = ('name',)
    readonly_fields = 'id', 'create_dt', 'update_dt'
    ordering = '-update_dt', '-create_dt'
    actions = start_assessment_for_1_week, finish_assessment

    def display_creator(self, obj: models.Media) -> str:
        return obj.creator.username

    display_creator.short_description = 'Creator'

    def get_queryset(self, request):
        only_fields = (
            'create_dt',
            'update_dt',
            'name',
            'url',
            'description',
            'assessment_status',
            'assessment_until_dt',
            'category_id',
            'category__name',
            'creator_id',
            'creator__username',
        )
        return super().get_queryset(request).only(*only_fields)


@admin.register(models.Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    list_display = 'id', 'mark', 'partial', 'create_dt', 'display_media', 'display_user'
    list_display_links = list_display
    list_select_related = 'media', 'user'
    list_filter = ('user',)
    search_fields = ('media__name',)
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


class VoteInline(admin.TabularInline):
    model = models.Vote
    ordering = ('voter__username',)


@admin.register(models.Poll)
class PollAdmin(admin.ModelAdmin):
    list_display = 'id', 'name', 'create_dt', 'update_dt', 'status', 'display_winner'
    list_display_links = list_display
    list_select_related = ('winner',)
    list_filter = ('status',)
    search_fields = ('name',)
    readonly_fields = 'id', 'create_dt', 'update_dt'
    ordering = ('-create_dt',)
    filter_horizontal = ('candidates',)
    inlines = (VoteInline,)

    def display_winner(self, obj: models.Poll) -> str:
        return obj.winner.name if obj.winner_id else '-'

    display_winner.short_description = 'Winner'

    def get_queryset(self, request):
        only_fields = 'name', 'create_dt', 'update_dt', 'status', 'winner_id', 'winner__name'
        return super().get_queryset(request).only(*only_fields)
