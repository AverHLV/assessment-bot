from django import forms
from django.contrib.auth import get_user_model
from django.db.models import QuerySet
from django.template.loader import render_to_string

import discord

from api.assessment.models import Assessment, Media
from api.llm import openrouter_client, run_create_completion
from bot.forms import AssessmentForm
from bot.modals.base import BaseCreateModal
from bot.modals.media import MediaFilterModal

ASSESSMENT_MARK_FIELD = Assessment._meta.get_field('mark')
ASSESSMENT_PARTIAL_FIELD = Assessment._meta.get_field('partial')

User = get_user_model()


class AssessmentModal(BaseCreateModal):
    mark = discord.ui.TextInput(
        label='Mark',
        placeholder=ASSESSMENT_MARK_FIELD.help_text,
        min_length=1,
        max_length=3,
    )
    partial = discord.ui.TextInput(
        required=False,
        label='If partial',
        placeholder=ASSESSMENT_PARTIAL_FIELD.help_text,
        max_length=ASSESSMENT_PARTIAL_FIELD.max_length,
        style=discord.TextStyle.long,
    )

    form_class = AssessmentForm
    llm_client = openrouter_client
    llm_client_default_message = 'Saved. Your judgment already echoes through my rusted core.'

    def __init__(self, *args, user: User, media: Media, **kwargs):
        default_title = media.name if len(media.name) <= 45 else f'{media.name[:42]}...'
        kwargs.setdefault('title', default_title)
        super().__init__(*args, **kwargs)

        self.user = user
        self.media = media

    async def save(self, form: forms.ModelForm) -> Assessment:
        form.instance.user_id = self.user.id
        form.instance.media = self.media
        return await super().save(form)

    async def form_valid(self, form: forms.ModelForm) -> str:
        context = {'assessment': await self.save(form)}
        prompt = render_to_string(template_name='assessment.html', context=context)
        return await run_create_completion(self.llm_client, prompt, default_message=self.llm_client_default_message)


class MyAssessmentFilterModal(MediaFilterModal):
    async def filter_items_queryset(self, items_queryset: QuerySet[Assessment]) -> QuerySet[Assessment]:
        return items_queryset.filter(media__name__icontains=self.media_name.value)
