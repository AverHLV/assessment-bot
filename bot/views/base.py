from django.conf import settings
from django.db.models import QuerySet

import discord

import math
from abc import ABCMeta, abstractmethod


class BasePaginator(discord.ui.View, metaclass=ABCMeta):
    embed_item_value_max_length: int = 1024

    def __init__(self, items_queryset: QuerySet, item_count: int, per_page: int = 10, **kwargs):
        if per_page > settings.BOT_PAGE_SIZE:
            raise ValueError(f'The given page size exceeds the Discord limit: {per_page}')

        super().__init__(**kwargs)

        self.page = 0
        self.per_page = per_page
        self.total_pages = math.ceil(item_count / per_page)
        self.items_queryset = items_queryset

    async def get_embed(self) -> discord.Embed:
        start = self.page * self.per_page
        end = start + self.per_page
        queryset = self.items_queryset.all()[start:end]

        embed = discord.Embed(title='Items')
        embed = await self.add_items(embed, queryset)
        embed.set_footer(text=f'Page {self.page + 1}/{self.total_pages}')
        return embed

    def strip_embed_item_value(self, value: str) -> str:
        if len(value) > self.embed_item_value_max_length:
            value = f'{value[: self.embed_item_value_max_length - 3]}...'
        return value

    @discord.ui.button(label='<- Prev', style=discord.ButtonStyle.secondary)
    async def previous(self, interaction: discord.Interaction, _button: discord.Button) -> None:
        if self.page <= 0:
            await interaction.response.defer()
            return

        self.page -= 1
        embed = await self.get_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label='Next ->', style=discord.ButtonStyle.secondary)
    async def next(self, interaction: discord.Interaction, _button: discord.Button) -> None:
        if self.page >= self.total_pages - 1:
            await interaction.response.defer()
            return

        self.page += 1
        embed = await self.get_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @abstractmethod
    async def add_items(self, embed: discord.Embed, queryset: QuerySet) -> discord.Embed:
        pass
