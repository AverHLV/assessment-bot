from django.db.models import QuerySet

import discord

from api.assessment.models import Assessment, Media
from bot.views.base import BaseFilterPaginator
from bot.views.media_list import MediaFilterModal


class AssessmentPaginator(BaseFilterPaginator):
    modal_class = MediaFilterModal

    async def add_items(self, embed: discord.Embed, queryset: QuerySet[Media]) -> discord.Embed:
        async for media in queryset:
            name = f'{media.name}, {media.category.name}'
            value = ''
            for assessment in media.assessments.all():
                value = f'{value}{assessment.user.username} - *{assessment.mark}*'
                if assessment.partial:
                    value = f'{value}, ({assessment.partial})'
                value = f'{value}\n'
            value = self.strip_embed_item_value(value)

            embed.add_field(name=name, value=value, inline=False)

        return embed


class MyAssessmentFilterModal(MediaFilterModal):
    async def filter_items_queryset(self, items_queryset: QuerySet[Assessment]) -> QuerySet[Assessment]:
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
