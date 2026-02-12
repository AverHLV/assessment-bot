from django import forms

import discord

from api.assessment.models import Media, MediaCategory
from bot.forms import MediaForm
from bot.modals.base import BaseCreateModal

MEDIA_NAME_FIELD = Media._meta.get_field('name')
MEDIA_URL_FIELD = Media._meta.get_field('url')
MEDIA_DESCRIPTION_FIELD = Media._meta.get_field('description')


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

    def __init__(self, *args, media_category: MediaCategory, **kwargs):
        kwargs.setdefault('title', f'Add a future {media_category.name.lower()}')
        super().__init__(*args, **kwargs)

        self.media_category = media_category

    def get_form(self) -> forms.ModelForm:
        form = super().get_form()
        form.data['category'] = self.media_category.id
        return form
