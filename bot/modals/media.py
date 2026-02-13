from django import forms
from django.contrib.auth import get_user_model
from django.db.models import QuerySet

import discord

from api.assessment.models import Media, MediaCategory
from bot.forms import MediaForm
from bot.modals.base import BaseCreateModal, BaseFilterModal

MEDIA_NAME_FIELD = Media._meta.get_field('name')
MEDIA_URL_FIELD = Media._meta.get_field('url')
MEDIA_DESCRIPTION_FIELD = Media._meta.get_field('description')

User = get_user_model()


class MediaModal(BaseCreateModal):
    name = discord.ui.TextInput(
        label='Name',
        min_length=1,
        max_length=MEDIA_NAME_FIELD.max_length,
    )
    url = discord.ui.TextInput(
        label='URL',
        placeholder=MEDIA_URL_FIELD.help_text,
        min_length=1,
        max_length=MEDIA_URL_FIELD.max_length,
    )
    description = discord.ui.TextInput(
        required=False,
        label='Description',
        placeholder=MEDIA_DESCRIPTION_FIELD.help_text,
        style=discord.TextStyle.long,
    )

    form_class = MediaForm

    def __init__(self, *args, user: User, media_category: MediaCategory, **kwargs):
        kwargs.setdefault('title', f'Add a future {media_category.name.lower()}')
        super().__init__(*args, **kwargs)

        self.user = user
        self.media_category = media_category

    def get_form(self) -> forms.ModelForm:
        form = super().get_form()
        form.data['category'] = self.media_category.id
        return form

    async def save(self, form: forms.ModelForm) -> Media:
        form.instance.creator_id = self.user.id
        return await super().save(form)


class MediaFilterModal(BaseFilterModal):
    media_name = discord.ui.TextInput(
        label='Media name',
        placeholder='Type a part of a media name.',
        max_length=MEDIA_NAME_FIELD.max_length,
    )

    async def filter_items_queryset(self, items_queryset: QuerySet[Media]) -> QuerySet[Media]:
        return items_queryset.filter(name__icontains=self.media_name.value)
