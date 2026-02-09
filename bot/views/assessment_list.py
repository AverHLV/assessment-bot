from django.db.models import QuerySet

import discord

from api.assessment.models import Assessment, Media
from bot.views.base import BaseFilterModal, BaseFilterPaginator

MEDIA_NAME_FIELD = Media._meta.get_field('name')


class MyAssessmentFilterModal(BaseFilterModal):
    media_name = discord.ui.TextInput(
        label='Media name',
        placeholder='Type a part of a media name.',
        max_length=MEDIA_NAME_FIELD.max_length,
    )

    async def filter_items_queryset(self, items_queryset: QuerySet) -> QuerySet:
        return items_queryset.filter(media__name__icontains=self.media_name.value)


class MyAssessmentPaginator(BaseFilterPaginator):
    modal_class = MyAssessmentFilterModal

    async def add_items(self, embed: discord.Embed, queryset: QuerySet[Assessment]) -> discord.Embed:
        async for assessment in queryset:
            name = f'{assessment.media.name} - *{assessment.mark}*'
            value = f'{assessment.media.category.name}\n'
            if assessment.partial:
                value = f'{value}{assessment.partial}\n'
            value = f'{value}[Link]({assessment.media.url})\n{assessment.media.description}'
            value = self.strip_embed_item_value(value)

            embed.add_field(name=name, value=value, inline=False)

        return embed
