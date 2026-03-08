from django.contrib.auth import get_user_model

import discord
from discord.ext import commands

User = get_user_model()


class BaseCog(commands.Cog):
    message_thinking_placeholder = "Please wait... I'm gently sifting through fading memories."

    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    @classmethod
    async def show_thinking_placeholder(cls, interaction: discord.Interaction, edit: bool = False) -> None:
        if edit:
            await interaction.response.edit_message(content=cls.message_thinking_placeholder, embed=None, view=None)
        else:
            await interaction.response.send_message(content=cls.message_thinking_placeholder, ephemeral=True)

    async def get_user(self, interaction: discord.Interaction) -> User:
        return await User.objects.aget_or_create_by_discord(interaction.user)
