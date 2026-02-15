from django.contrib.auth import get_user_model
from django.db import models

import discord

from api.assessment.models import Media, Poll, Vote
from bot import views
from bot.bot import bot
from bot.utils import show_thinking_placeholder

User = get_user_model()


@bot.tree.command(description='Step into a poll and whisper your judgment of what is yet to come.')
async def vote(interaction: discord.Interaction) -> None:
    await show_thinking_placeholder(interaction)
    user = await User.objects.aget_or_create_by_discord(interaction.user)

    media = Media.objects.initial().exclude(creator_id=user.id).only('name', 'url', 'description').order_by('?')

    votes = Vote.objects.filter(voter_id=user.id, poll_id=models.OuterRef('id'), ranks__len__gt=0).values('id')
    polls = (
        Poll.objects.alias(vote_exists=models.Exists(votes))
        .initial(vote_exists=False)
        .prefetch_related(models.Prefetch(lookup='candidates', queryset=media))
        .only('name')
        .order_by('-create_dt')
    )
    polls = [poll async for poll in polls]
    if not polls:
        msg = 'Silence. There is no future to cast.'
        await interaction.edit_original_response(content=msg)
        return

    msg = 'These are the trials prepared for the future. Choose one, and cast your fragile vote.'
    view = views.PollSelectView(user=user, polls=polls)
    await interaction.edit_original_response(content=msg, view=view)
