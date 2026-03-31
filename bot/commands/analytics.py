from django.contrib.auth import get_user_model
from django.db import models
from django.template.loader import render_to_string

import discord
from discord.app_commands import command, describe

from itertools import groupby

from api.assessment.models import Assessment, Media
from api.llm import openrouter_client, run_create_completion
from bot import views
from bot.cog import BaseCog

User = get_user_model()


class AnalyticsCog(BaseCog):
    message_compare_same_users = (
        'You ask me to compare a soul with itself? Of course... in this cursed world, even reflections feel lonely.'
    )
    message_compare_no_users = 'The archive is incomplete. Some names have long since crumbled into dust...'
    message_compare_no_assessments = (
        'There is nothing... No shared memories, no common echoes of beauty among the ruins.'
    )

    llm_client = openrouter_client
    llm_client_message_compare_default_message = 'Let us witness how souls perceived the ashes of our world...'

    async def compare_check_users(
        self,
        interaction: discord.Interaction,
        *users: discord.User | discord.Member,
    ) -> list[int] | None:
        user_external_ids = {user.id for user in users}
        if len(user_external_ids) != len(users):
            await interaction.edit_original_response(content=self.message_compare_same_users)
            return

        user_ids = User.objects.filter(external_id__in=user_external_ids).values_list('id', flat=True)
        user_ids = [user_id async for user_id in user_ids]
        if len(user_ids) == len(user_external_ids):
            return user_ids

        await interaction.edit_original_response(content=self.message_compare_no_users)

    async def make_comparison(self, interaction: discord.Interaction, groups: dict, template_name: str) -> None:
        view = views.CompareView(groups=groups)
        embed = await view.get_embed()

        context = {'comparison_stats': view.get_comparison_stats(embed)}
        prompt = render_to_string(template_name=template_name, context=context)
        async with self.thinking.start_task(self.thinking.show_thinking_with_loop, interaction=interaction):
            response = await run_create_completion(
                client=self.llm_client,
                prompt=prompt,
                default_message=self.llm_client_message_compare_default_message,
            )

        await interaction.edit_original_response(content=response, embed=embed, view=view)

    @command(description='Compare how two lost souls judged the fading echoes of this dying world.')
    @describe(
        user='The first wandering soul whose judgments you wish to unveil.',
        second_user='Another soul for comparison. Leave empty, and I shall compare them with you, dear traveler...',
    )
    async def compare(
        self,
        interaction: discord.Interaction,
        user: discord.User,
        second_user: discord.User | None = None,
    ) -> None:
        await self.thinking.show_thinking(interaction)
        user_ids = await self.compare_check_users(interaction, user, second_user or interaction.user)
        if not user_ids:
            return

        # retrieve assessments
        shared_media = (
            Assessment.objects.filter(user_id__in=user_ids, media__assessment_status=Media.AssessmentStatus.COMPLETED)
            .values('media_id')
            .alias(shared_count=models.Count('user_id'))
            .filter(shared_count=len(user_ids))
        )

        assessments = (
            Assessment.objects.alias(shared_media=models.Subquery(shared_media))
            .filter(user_id__in=user_ids, media_id__in=models.F('shared_media'))
            .select_related('media', 'user')
            .only('mark', 'media_id', 'media__name', 'user_id', 'user__username')
            .order_by('user__username', 'media_id')
        )
        assessments = [assessment async for assessment in assessments]
        if len(assessments) < len(user_ids) * 2:
            await interaction.edit_original_response(content=self.message_compare_no_assessments)
            return

        # make comparison
        groups = {user: list(assessments) for user, assessments in groupby(assessments, key=lambda x: x.user)}
        await self.make_comparison(interaction, groups, template_name='comparison.html')

    @command(description="Compare a soul's taste with the merciless consensus of the masses.")
    @describe(
        user='Another soul for comparison. Leave empty and I shall weigh your own heart against those distant voices.',
    )
    async def compare_meta(self, interaction: discord.Interaction, user: discord.User | None = None) -> None:
        await self.thinking.show_thinking(interaction)
        user_ids = await self.compare_check_users(interaction, user or interaction.user)
        if not user_ids:
            return

        # retrieve assessments
        assessments = (
            Assessment.objects.filter(
                user_id=user_ids[0],
                media__assessment_status=Media.AssessmentStatus.COMPLETED,
                media__meta_mark__isnull=False,
            )
            .select_related('media', 'user')
            .only('mark', 'media_id', 'media__name', 'media__meta_mark', 'user_id', 'user__username')
            .order_by('user__username', 'media_id')
        )
        assessments = [assessment async for assessment in assessments]
        if len(assessments) < len(user_ids) * 2:
            await interaction.edit_original_response(content=self.message_compare_no_assessments)
            return

        # make comparison
        meta_user = User(id=-1, username='Meta mark')
        groups = {
            assessments[0].user: assessments,
            meta_user: [
                Assessment(id=assessment.id, mark=assessment.media.meta_mark, media=assessment.media, user=meta_user)
                for assessment in assessments
            ],
        }
        await self.make_comparison(interaction, groups, template_name='comparison_meta.html')
