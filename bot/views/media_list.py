from django.db.models import QuerySet

import discord

from api.assessment.models import Media
from bot.modals import MediaFilterModal
from bot.views.base import BaseFilterPaginator


class FutureMediaPaginator(BaseFilterPaginator):
    modal_class = MediaFilterModal

    async def add_items(self, embed: discord.Embed, queryset: QuerySet[Media]) -> discord.Embed:
        async for media in queryset:
            name = f'{media.name}, {media.category.name}'
            value = f'Added by *{media.creator.username}*\n[Link]({media.url})\n{media.description}'
            value = self.strip_embed_item_value(value)

            embed.add_field(name=name, value=value, inline=False)

        return embed
