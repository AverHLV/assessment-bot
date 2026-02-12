from django.db.models import TextChoices

import discord
from discord.ext import commands

import logging

logger = logging.getLogger(__name__)


class AssessmentBot(commands.Bot):
    class EventMethod(TextChoices):
        ON_MESSAGE = 'on_message'

    error_message = 'The ritual failed. My master will have twisted the threads of fate. Try again... if he allows it.'
    error_cooldown_message = 'Ah, slow down. Even an automaton needs a breath. Try again in {retry:.0f} seconds.'

    def __init__(self, *args, **kwargs):
        intents = discord.Intents.default()
        intents.message_content = True
        kwargs.setdefault('intents', intents)

        super().__init__(*args, **kwargs)

    async def setup_hook(self) -> None:
        await self.tree.sync()

    async def on_error(self, event_method: str, *args, **kwargs) -> None:
        if event_method == self.EventMethod.ON_MESSAGE:
            message = args[0]
            await message.reply(self.error_message)

        await super().on_error(event_method, *args, **kwargs)


bot = AssessmentBot(command_prefix='!')


@bot.tree.error
async def on_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError) -> None:
    match type(error):
        case discord.app_commands.CommandOnCooldown:
            msg = AssessmentBot.error_cooldown_message.format(retry=error.retry_after)
            await interaction.response.send_message(msg, ephemeral=True)
        case _:
            logger.exception(error)
            await interaction.edit_original_response(content=AssessmentBot.error_message, embed=None, view=None)
