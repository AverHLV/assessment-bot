from django.contrib.auth import get_user_model

import discord
from discord.ext import commands

User = get_user_model()


class BaseCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    @classmethod
    async def show_thinking_placeholder(cls, interaction: discord.Interaction, edit: bool = False) -> None:
        msg = "Please wait... I'm gently sifting through fading memories."
        if edit:
            await interaction.response.edit_message(content=msg, embed=None, view=None)
        else:
            await interaction.response.send_message(msg, ephemeral=True)

    async def get_user(self, interaction: discord.Interaction) -> User:
        return await User.objects.aget_or_create_by_discord(interaction.user)
