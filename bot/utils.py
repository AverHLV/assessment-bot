import discord


async def show_thinking_placeholder(interaction: discord.Interaction, edit: bool = False) -> None:
    msg = "Please wait... I'm gently sifting through fading memories."
    if edit:
        await interaction.response.edit_message(content=msg, embed=None, view=None)
    else:
        await interaction.response.send_message(msg, ephemeral=True)
