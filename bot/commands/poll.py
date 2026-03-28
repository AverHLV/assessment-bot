from django.db import models

import discord
from discord.app_commands import command

from api.assessment.models import Media, Poll, Vote
from bot import views
from bot.cog import BaseCog


class PollCog(BaseCog):
    message_poll = 'These are the trials prepared for the future. Choose one, and cast your fragile vote.'
    message_poll_no_polls = 'Silence. There is no future to cast.'

    @command(description='Step into a poll and whisper your judgment of what is yet to come.')
    async def vote(self, interaction: discord.Interaction) -> None:
        await self.thinking.show_thinking(interaction)
        user = await self.get_user(interaction)

        media_base = Media.objects.initial().exclude(creator_id=user.id)
        media = media_base.only('name', 'url', 'description').order_by('?')
        candidate_exists = media_base.filter(polls__id=models.OuterRef('id')).values('id')

        voter_exists = Vote.objects.filter(voter_id=user.id, poll_id=models.OuterRef('id')).values('id')
        vote_exists = voter_exists.filter(ranks__len__gt=0)

        polls = (
            Poll.objects.alias(
                candidate_exists=models.Exists(candidate_exists),
                voter_exists=models.Exists(voter_exists),
                vote_exists=models.Exists(vote_exists),
            )
            .initial(candidate_exists=True, voter_exists=True, vote_exists=False)
            .prefetch_related(models.Prefetch(lookup='candidates', queryset=media))
            .only('name')
            .order_by('-create_dt')
        )
        polls = [poll async for poll in polls]
        if not polls:
            await interaction.edit_original_response(content=self.message_poll_no_polls)
            return

        view = views.PollSelectView(user=user, polls=polls)
        await interaction.edit_original_response(content=self.message_poll, view=view)
