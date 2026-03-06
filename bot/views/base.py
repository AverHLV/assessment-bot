from django.conf import settings
from django.db.models import QuerySet

import discord

import math
from abc import ABCMeta, abstractmethod

from bot.cog import BaseCog
from bot.modals import BaseFilterModal


class BaseEmbed(discord.ui.View, metaclass=ABCMeta):
    embed_item_value_max_length: int = 1024

    def strip_embed_item_value(self, value: str) -> str:
        if len(value) > self.embed_item_value_max_length:
            value = f'{value[: self.embed_item_value_max_length - 3]}...'
        return value

    async def refresh(self, interaction: discord.Interaction) -> None:
        embed = await self.get_embed()
        await interaction.edit_original_response(content=None, embed=embed, view=self)

    @abstractmethod
    async def get_embed(self) -> discord.Embed:
        pass


class BasePaginator(BaseEmbed, metaclass=ABCMeta):
    def __init__(self, items_queryset: QuerySet, item_count: int, per_page: int = 10, **kwargs):
        if per_page > settings.BOT_PAGE_SIZE:
            raise ValueError(f'The given page size exceeds the Discord limit: {per_page}')

        super().__init__(**kwargs)

        self.page = self.total_pages = 0
        self.per_page = per_page
        self.items_queryset = items_queryset
        self.set_total_pages(item_count)

    def set_total_pages(self, item_count: int) -> None:
        self.total_pages = math.ceil(item_count / self.per_page)

    async def get_embed(self) -> discord.Embed:
        start = self.page * self.per_page
        end = start + self.per_page
        queryset = self.items_queryset.all()[start:end]

        embed = discord.Embed(title='Items')
        embed = await self.add_items(embed, queryset)
        if embed.fields:
            embed.set_footer(text=f'Page {self.page + 1}/{self.total_pages}')
        else:
            embed.add_field(name='No items found', value='')

        return embed

    @discord.ui.button(label='<- Prev', style=discord.ButtonStyle.secondary)
    async def previous(self, interaction: discord.Interaction, _button: discord.Button) -> None:
        if self.page <= 0:
            await interaction.response.defer()
            return

        await BaseCog.show_thinking_placeholder(interaction, edit=True)
        self.page -= 1
        await self.refresh(interaction)

    @discord.ui.button(label='Next ->', style=discord.ButtonStyle.secondary)
    async def next(self, interaction: discord.Interaction, _button: discord.Button) -> None:
        if self.page >= self.total_pages - 1:
            await interaction.response.defer()
            return

        await BaseCog.show_thinking_placeholder(interaction, edit=True)
        self.page += 1
        await self.refresh(interaction)

    @abstractmethod
    async def add_items(self, embed: discord.Embed, queryset: QuerySet) -> discord.Embed:
        pass


class BaseFilterPaginator(BasePaginator, metaclass=ABCMeta):
    modal_class: type[BaseFilterModal]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.items_queryset_base = self.items_queryset.all()

    async def set_items_queryset(self, items_queryset: QuerySet) -> None:
        self.page = 0
        self.items_queryset = items_queryset
        item_count = await self.items_queryset.all().acount()
        self.set_total_pages(item_count)

    async def clear_items_queryset(self) -> None:
        self.page = 0
        self.items_queryset = self.items_queryset_base.all()
        item_count = await self.items_queryset.all().acount()
        self.set_total_pages(item_count)

    @discord.ui.button(label='Search', style=discord.ButtonStyle.primary)
    async def search(self, interaction: discord.Interaction, _button: discord.Button) -> None:
        modal = self.modal_class(paginator=self)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label='Clear', style=discord.ButtonStyle.secondary)
    async def clear(self, interaction: discord.Interaction, _button: discord.Button) -> None:
        await BaseCog.show_thinking_placeholder(interaction, edit=True)
        await self.clear_items_queryset()
        await self.refresh(interaction)
