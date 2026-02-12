from django.db.models import QuerySet

import discord

from api.assessment.models import Media
from bot.views.base import BaseFilterModal, BaseFilterPaginator

MEDIA_NAME_FIELD = Media._meta.get_field('name')


class MediaFilterModal(BaseFilterModal):
    media_name = discord.ui.TextInput(
        label='Media name',
        placeholder='Type a part of a media name.',
        max_length=MEDIA_NAME_FIELD.max_length,
    )

    async def filter_items_queryset(self, items_queryset: QuerySet[Media]) -> QuerySet[Media]:
        return items_queryset.filter(name__icontains=self.media_name.value)


class FutureMediaPaginator(BaseFilterPaginator):
    modal_class = MediaFilterModal

    async def add_items(self, embed: discord.Embed, queryset: QuerySet[Media]) -> discord.Embed:
        async for media in queryset:
            name = f'{media.name}, {media.category.name}'
            value = f'[Link]({media.url})\n{media.description}'
            value = self.strip_embed_item_value(value)

            embed.add_field(name=name, value=value, inline=False)

        return embed
