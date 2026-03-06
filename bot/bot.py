from django.db.models import TextChoices

import discord
from discord.ext.commands import Bot

import logging
from collections.abc import Callable

from bot import commands, messages

logger = logging.getLogger(__name__)


class AssessmentBot(Bot):
    class EventMethod(TextChoices):
        ON_MESSAGE = 'on_message'

    error_message = 'The ritual failed. My master will have twisted the threads of fate. Try again... if he allows it.'
    error_cooldown_message = 'Ah, slow down. Even an automaton needs a breath. Try again in {retry:.0f} seconds.'

    async def setup_hook(self) -> None:
        await self.tree.sync()

    async def on_error(self, event_method: str, *args, **kwargs) -> None:
        if event_method == self.EventMethod.ON_MESSAGE:
            message = args[0]
            await message.reply(self.error_message)

        await super().on_error(event_method, *args, **kwargs)


async def on_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError) -> None:
    match type(error):
        case discord.app_commands.CommandOnCooldown:
            msg = AssessmentBot.error_cooldown_message.format(retry=error.retry_after)
            await interaction.response.send_message(msg, ephemeral=True)
        case _:
            logger.exception(error)
            await interaction.edit_original_response(content=AssessmentBot.error_message, embed=None, view=None)


async def get_assessment_bot(
    command_prefix: str = '!',
    command_error_handler: Callable = on_command_error,
) -> AssessmentBot:
    intents = discord.Intents.default()
    intents.message_content = True

    bot = AssessmentBot(command_prefix=command_prefix, intents=intents)
    bot.tree.error(command_error_handler)

    await bot.add_cog(messages.MessageCog(bot))
    for cog in commands.cogs:
        await bot.add_cog(cog(bot))

    return bot
