from django import forms
from django.db import close_old_connections
from django.db.models import QuerySet

import discord
from asgiref.sync import sync_to_async

from abc import ABCMeta, abstractmethod

from bot.thinking import ThinkingRegistry, thinking_registry


class BaseModal(discord.ui.Modal, metaclass=ABCMeta):
    thinking: ThinkingRegistry = thinking_registry

    async def interaction_check(self, interaction: discord.Interaction, /) -> bool:
        close_old_connections()
        return await super().interaction_check(interaction)

    async def on_error(self, interaction: discord.Interaction, error: Exception, /) -> None:
        from bot.bot import AssessmentBot

        await interaction.edit_original_response(content=AssessmentBot.error_message, embed=None, view=None)
        await super().on_error(interaction, error)


class BaseFilterModal(BaseModal, title='Search', metaclass=ABCMeta):
    def __init__(self, paginator, **kwargs):
        super().__init__(**kwargs)
        self.paginator = paginator

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await self.thinking.show_thinking(interaction, edit=True)
        items_queryset = await self.filter_items_queryset(self.paginator.items_queryset_base)
        await self.paginator.set_items_queryset(items_queryset)
        await self.paginator.refresh(interaction)

    @abstractmethod
    async def filter_items_queryset(self, items_queryset: QuerySet) -> QuerySet:
        pass


class BaseCreateModal(BaseModal):
    form_class: type[forms.ModelForm]
    form_valid_message = 'Saved. I sealed it carefully in the archives.'

    def get_form(self) -> forms.ModelForm:
        data = {field: getattr(self, field).value for field in self.__modal_children_items__}
        return self.form_class(data=data)

    async def save(self, form: forms.ModelForm):
        await form.instance.asave()
        return form.instance

    async def form_valid(self, form: forms.ModelForm) -> str:
        await self.save(form)
        return self.form_valid_message

    async def form_invalid(self, form: forms.ModelForm) -> str:
        msg = 'Alas... your words are flawed:\n'
        for field, errors in form.errors.items():
            msg = f'{msg}- {field}: {errors[0]}\n'
        return f'{msg}Let the ritual become once more.'

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await self.thinking.show_thinking(interaction, edit=True)
        async with self.thinking.start_task(self.thinking.show_thinking_with_loop, interaction=interaction):
            form = self.get_form()
            if await sync_to_async(form.is_valid)():
                message = await self.form_valid(form)
            else:
                message = await self.form_invalid(form)

        await interaction.edit_original_response(content=message, embed=None, view=None)
