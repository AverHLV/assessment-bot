from django import forms
from django.conf import settings
from django.db.models import QuerySet

import discord
from asgiref.sync import sync_to_async

import math
from abc import ABCMeta, abstractmethod


class BasePaginator(discord.ui.View, metaclass=ABCMeta):
    embed_item_value_max_length: int = 1024

    def __init__(self, items_queryset: QuerySet, item_count: int, per_page: int = 10, **kwargs):
        if per_page > settings.BOT_PAGE_SIZE:
            raise ValueError(f'The given page size exceeds the Discord limit: {per_page}')

        super().__init__(**kwargs)

        self.page = self.total_pages = 0
        self.per_page = per_page
        self.items_queryset = items_queryset
        self.set_total_pages(item_count)

    def strip_embed_item_value(self, value: str) -> str:
        if len(value) > self.embed_item_value_max_length:
            value = f'{value[: self.embed_item_value_max_length - 3]}...'
        return value

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

    async def refresh(self, interaction: discord.Interaction) -> None:
        embed = await self.get_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label='<- Prev', style=discord.ButtonStyle.secondary)
    async def previous(self, interaction: discord.Interaction, _button: discord.Button) -> None:
        if self.page <= 0:
            await interaction.response.defer()
            return

        self.page -= 1
        await self.refresh(interaction)

    @discord.ui.button(label='Next ->', style=discord.ButtonStyle.secondary)
    async def next(self, interaction: discord.Interaction, _button: discord.Button) -> None:
        if self.page >= self.total_pages - 1:
            await interaction.response.defer()
            return

        self.page += 1
        await self.refresh(interaction)

    @abstractmethod
    async def add_items(self, embed: discord.Embed, queryset: QuerySet) -> discord.Embed:
        pass


class BaseFilterModal(discord.ui.Modal, title='Search', metaclass=ABCMeta):
    def __init__(self, paginator: 'BaseFilterPaginator', **kwargs):
        super().__init__(**kwargs)
        self.paginator = paginator

    async def on_submit(self, interaction: discord.Interaction) -> None:
        items_queryset = await self.filter_items_queryset(self.paginator.items_queryset)
        await self.paginator.set_items_queryset(items_queryset)
        await self.paginator.refresh(interaction)

    @abstractmethod
    async def filter_items_queryset(self, items_queryset: QuerySet) -> QuerySet:
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
        await self.clear_items_queryset()
        await self.refresh(interaction)


class BaseCreateModal(discord.ui.Modal, metaclass=ABCMeta):
    form_class: type[forms.ModelForm]

    def get_form(self) -> forms.ModelForm:
        data = {field: getattr(self, field).value for field in self.__modal_children_items__}
        return self.form_class(data=data)

    async def save(self, form: forms.ModelForm):
        await form.instance.asave()
        return form.instance

    async def form_invalid(self, form: forms.ModelForm) -> str:
        msg = 'Alas... your words are flawed:\n'
        for field, errors in form.errors.items():
            msg = f'{msg}- {field}: {errors[0]}\n'
        return f'{msg}Let the ritual become once more.'

    async def on_submit(self, interaction: discord.Interaction) -> None:
        form = self.get_form()
        if await sync_to_async(form.is_valid)():
            msg = await self.form_valid(form)
        else:
            msg = await self.form_invalid(form)

        await interaction.response.edit_message(content=msg, embed=None, view=None)

    @abstractmethod
    async def form_valid(self, form: forms.ModelForm) -> str:
        pass
