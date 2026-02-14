from django.contrib.auth import get_user_model

import discord
from discord.app_commands import checks

from api.assessment.models import Media, MediaCategory
from bot import views
from bot.bot import bot
from bot.utils import show_thinking_placeholder

User = get_user_model()


@bot.tree.command(description='These stories are marked for later trials. For now, they rest untouched.')
async def future_media(interaction: discord.Interaction) -> None:
    await show_thinking_placeholder(interaction)
    media_queryset = Media.objects.initial()
    media_count = await media_queryset.acount()
    if not media_count:
        msg = 'Nothing remains reserved for later. Even tomorrow feels empty.'
        await interaction.edit_original_response(content=msg)
        return

    only_fields = 'name', 'url', 'description', 'category_id', 'category__name', 'creator_id', 'creator__username'
    media_queryset = media_queryset.select_related('category', 'creator').only(*only_fields).order_by('-create_dt')

    msg = 'A list of stories awaiting their time to be judged - not today.'
    view = views.FutureMediaPaginator(items_queryset=media_queryset, item_count=media_count)
    embed = await view.get_embed()
    await interaction.edit_original_response(content=msg, embed=embed, view=view)


@bot.tree.command(description='Add a story that will one day face judgment.')
@checks.cooldown(rate=5, per=60, key=lambda interaction: interaction.user.id)
async def add_future_media(interaction: discord.Interaction) -> None:
    await show_thinking_placeholder(interaction)
    user = await User.objects.aget_or_create_by_discord(interaction.user)

    media_categories = MediaCategory.objects.order_by('name')
    media_categories = [category async for category in media_categories]

    msg = 'Every story needs a home before its trial. Choose one.'
    view = views.MediaCategorySelectView(user=user, media_categories=media_categories)
    await interaction.edit_original_response(content=msg, view=view)
