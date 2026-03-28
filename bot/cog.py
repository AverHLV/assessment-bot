from django.contrib.auth import get_user_model

import discord
from discord.ext import commands

from bot.thinking import ThinkingRegistry, thinking_registry

User = get_user_model()


class BaseCog(commands.Cog):
    thinking: ThinkingRegistry = thinking_registry

    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    async def get_user(self, interaction: discord.Interaction) -> User:
        return await User.objects.aget_or_create_by_discord(interaction.user)
