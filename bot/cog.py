from django.contrib.auth import get_user_model
from django.db import close_old_connections

import discord
from discord.ext import commands

from bot.thinking import ThinkingRegistry, thinking_registry

User = get_user_model()


class BaseCog(commands.Cog):
    thinking: ThinkingRegistry = thinking_registry

    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    def interaction_check(self, interaction: discord.Interaction, /) -> bool:
        self.close_old_db_connections()
        return super().interaction_check(interaction)

    @staticmethod
    def close_old_db_connections() -> None:
        close_old_connections()

    async def get_user(self, interaction: discord.Interaction) -> User:
        return await User.objects.aget_or_create_by_discord(interaction.user)
