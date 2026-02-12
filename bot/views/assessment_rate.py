from django import forms
from django.contrib.auth import get_user_model
from django.template.loader import render_to_string

import discord

from api.assessment.models import Assessment, Media
from api.llm import openrouter_client
from bot.forms import AssessmentForm
from bot.views.base import BaseCreateModal

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

        messages = [{'role': self.llm_client.Role.USER, 'content': prompt}]
        response = await self.llm_client.create_completion(messages=messages)
        return response['choices'][0]['message']['content']


class MediaSelect(discord.ui.Select):
    modal_class = AssessmentModal

    def __init__(self, *args, user: User, media: list[Media], **kwargs):
        kwargs.setdefault('placeholder', 'Pick a story... I`ll watch with you.')
        kwargs['options'] = [
            discord.SelectOption(
                label=media_obj.name,
                value=str(media_obj.id),
                description=media_obj.category.name,
            )
            for media_obj in media
        ]

        super().__init__(*args, **kwargs)
        self.user = user

    async def callback(self, interaction: discord.Interaction) -> None:
        media = (
            await Media.objects.select_related('category')
            .only('name', 'description', 'category_id', 'category__name')
            .aget(id=int(self.values[0]))
        )
        modal = self.modal_class(user=self.user, media=media)
        await interaction.response.send_modal(modal)


class MediaSelectToAssessView(discord.ui.View):
    select_class = MediaSelect

    def __init__(self, *args, user: User, media: list[Media], **kwargs):
        super().__init__(*args, **kwargs)
        self.add_item(self.select_class(user=user, media=media))
