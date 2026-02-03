from django.contrib.auth import get_user_model

import discord

from api.assessment.models import Media
from bot import views
from bot.bot import bot

User = get_user_model()


@bot.tree.command(description='Another judgment calls...')
async def rate(interaction: discord.Interaction) -> None:
    user = await User.objects.aget_or_create_by_discord(interaction.user)
    media = (
        Media.objects.for_assessment(user_id=user.id)
        .select_related('category')
        .only('name', 'category_id', 'category__name')[:25]
    )
    media = [media_obj async for media_obj in media]
    if not media:
        msg = 'The ashes are silent... There is nothing left for you to judge.'
        await interaction.response.send_message(msg, ephemeral=True)
        return

    msg = 'Choose a story from the ashes...'
    view = views.MediaSelectToAssessView(user=user, media=media)
    await interaction.response.send_message(msg, view=view, ephemeral=True)
