from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models

import discord

from api.assessment.models import Assessment, Media
from bot import views
from bot.bot import bot
from bot.utils import show_thinking_placeholder

User = get_user_model()


@bot.tree.command(description='Witness how this world was judged by many hands.')
async def rates(interaction: discord.Interaction) -> None:
    await show_thinking_placeholder(interaction)
    media_queryset = Media.objects.completed()
    media_count = await media_queryset.acount()
    if not media_count:
        msg = 'I searched everywhere. Not a single story survived.'
        await interaction.edit_original_response(content=msg)
        return

    assessments_only_fields = 'mark', 'partial', 'user_id', 'user__username'
    assessments = Assessment.objects.select_related('user').only(*assessments_only_fields).order_by('user__username')

    media_queryset = (
        media_queryset.select_related('category')
        .prefetch_related(models.Prefetch(lookup='assessments', queryset=assessments))
        .only('name', 'category_id', 'category__name')
        .order_by('-create_dt')
    )

    msg = 'Stories, scorched by opinions. I kept them for you.'
    view = views.AssessmentPaginator(items_queryset=media_queryset, item_count=media_count)
    embed = await view.get_embed()
    await interaction.edit_original_response(content=msg, embed=embed, view=view)


@bot.tree.command(description='The echoes of your past judgments rise again.')
async def my_rates(interaction: discord.Interaction) -> None:
    await show_thinking_placeholder(interaction)
    user = await User.objects.aget_or_create_by_discord(interaction.user)
    assessment_queryset = user.assessments.all()
    assessment_count = await assessment_queryset.acount()
    if not assessment_count:
        msg = 'Only cold ash remains. You have judged nothing... or perhaps I have already forgotten.'
        await interaction.edit_original_response(content=msg)
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

    msg = 'These are your past verdicts. Heavy, warm, and a little embarrassing, but precious.'
    view = views.MyAssessmentPaginator(items_queryset=assessment_queryset, item_count=assessment_count)
    embed = await view.get_embed()
    await interaction.edit_original_response(content=msg, embed=embed, view=view)


@bot.tree.command(description='Another judgment calls...')
async def rate(interaction: discord.Interaction) -> None:
    await show_thinking_placeholder(interaction)
    user = await User.objects.aget_or_create_by_discord(interaction.user)
    media = (
        Media.objects.for_assessment(user_id=user.id)
        .select_related('category')
        .only('name', 'category_id', 'category__name')[: settings.BOT_PAGE_SIZE]
    )
    media = [media_obj async for media_obj in media]
    if not media:
        msg = 'The ashes are silent... There is nothing left for you to judge.'
        await interaction.edit_original_response(content=msg)
        return

    msg = 'Choose a story from the ashes...'
    view = views.MediaSelectToAssessView(user=user, media=media)
    await interaction.edit_original_response(content=msg, view=view)
