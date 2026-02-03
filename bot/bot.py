import discord
from discord.ext import commands

import logging

logger = logging.getLogger(__name__)


class AssessmentBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        intents = discord.Intents.default()
        intents.message_content = True
        kwargs.setdefault('intents', intents)

        super().__init__(*args, **kwargs)

    async def setup_hook(self) -> None:
        await self.tree.sync()


bot = AssessmentBot(command_prefix='!')


@bot.tree.error
async def on_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError) -> None:
    logger.exception(error)

    msg = 'The ritual failed. My master will have twisted the threads of fate. Try again... if he allows it.'
    if interaction.response.is_done():
        await interaction.followup.send(msg, ephemeral=True)
    else:
        await interaction.response.send_message(msg, ephemeral=True)
