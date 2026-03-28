from django.conf import settings
from django.db import models

import discord
from discord.app_commands import command

from api.assessment.models import Assessment, Media
from bot import views
from bot.cog import BaseCog


class AssessmentCog(BaseCog):
    message_rates = 'Stories, scorched by opinions. I kept them for you.'
    message_rates_no_assessments = 'I searched everywhere. Not a single story survived.'
    message_my_rates = 'These are your past verdicts. Heavy, warm, and a little embarrassing, but precious.'
    message_my_rates_no_assessments = (
        'Only cold ash remains. You have judged nothing... or perhaps I have already forgotten.'
    )
    message_rate = 'Choose a story from the ashes...'
    message_rate_no_media = 'The ashes are silent... There is nothing left for you to judge.'

    @command(description='Witness how this world was judged by many hands.')
    async def rates(self, interaction: discord.Interaction) -> None:
        await self.thinking.show_thinking(interaction)
        media_queryset = Media.objects.completed()
        media_count = await media_queryset.acount()
        if not media_count:
            await interaction.edit_original_response(content=self.message_rates_no_assessments)
            return

        assessments_only_fields = 'mark', 'partial', 'user_id', 'user__username'
        assessments = (
            Assessment.objects.select_related('user').only(*assessments_only_fields).order_by('user__username')
        )

        media_queryset = (
            media_queryset.select_related('category')
            .prefetch_related(models.Prefetch(lookup='assessments', queryset=assessments))
            .only('name', 'category_id', 'category__name')
            .order_by('-create_dt')
        )

        view = views.AssessmentPaginator(items_queryset=media_queryset, item_count=media_count)
        await view.refresh(interaction, content=self.message_rates)

    @command(description='The echoes of your past judgments rise again.')
    async def my_rates(self, interaction: discord.Interaction) -> None:
        await self.thinking.show_thinking(interaction)
        user = await self.get_user(interaction)
        assessment_queryset = user.assessments.all()
        assessment_count = await assessment_queryset.acount()
        if not assessment_count:
            await interaction.edit_original_response(content=self.message_my_rates_no_assessments)
            return

        only_fields = (
            'mark',
            'partial',
            'media_id',
            'media__name',
            'media__url',
            'media__description',
            'media__category_id',
            'media__category__name',
        )
        assessment_queryset = (
            assessment_queryset.select_related('media', 'media__category').only(*only_fields).order_by('-create_dt')
        )

        view = views.MyAssessmentPaginator(items_queryset=assessment_queryset, item_count=assessment_count)
        await view.refresh(interaction, content=self.message_my_rates)

    @command(description='Another judgment calls...')
    async def rate(self, interaction: discord.Interaction) -> None:
        await self.thinking.show_thinking(interaction)
        user = await self.get_user(interaction)
        media = (
            Media.objects.for_assessment(user_id=user.id)
            .select_related('category')
            .only('name', 'category_id', 'category__name')[: settings.BOT_PAGE_SIZE]
        )
        media = [media_obj async for media_obj in media]
        if not media:
            await interaction.edit_original_response(content=self.message_rate_no_media)
            return

        view = views.MediaSelectToAssessView(user=user, media=media)
        await interaction.edit_original_response(content=self.message_rate, view=view)
