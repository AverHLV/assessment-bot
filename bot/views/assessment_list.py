import discord

from api.assessment.models import Assessment
from bot.views.base import BasePaginator


class MyAssessmentPaginator(BasePaginator):
    def add_items(self, embed: discord.Embed, page_items: list[Assessment]) -> discord.Embed:
        for assessment in page_items:
            name = f'{assessment.media.name} - *{assessment.mark}*'
            value = f'{assessment.media.category.name}\n'
            if assessment.partial:
                value = f'{value}{assessment.partial}\n'
            value = f'{value}[Link]({assessment.media.url})\n{assessment.media.description}'
            value = self.strip_embed_item_value(value)

            embed.add_field(name=name, value=value, inline=False)

        return embed
