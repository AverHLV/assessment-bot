import discord


async def show_thinking_placeholder(interaction: discord.Interaction) -> None:
    msg = 'My gears turn, ah - still hot from the past...'
    await interaction.response.send_message(msg, ephemeral=True)
