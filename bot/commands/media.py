import discord
from discord.app_commands import checks, command

from api.assessment.models import Media, MediaCategory
from bot import views
from bot.cog import BaseCog


class MediaCog(BaseCog):
    message_future_media = 'A list of stories awaiting their time to be judged - not today.'
    message_future_media_no_media = 'Nothing remains reserved for later. Even tomorrow feels empty.'
    message_add_future_media = 'Every story needs a home before its trial. Choose one.'

    @command(description='These stories are marked for later trials. For now, they rest untouched.')
    async def future_media(self, interaction: discord.Interaction) -> None:
        await self.show_thinking_placeholder(interaction)
        media_queryset = Media.objects.initial()
        media_count = await media_queryset.acount()
        if not media_count:
            await interaction.edit_original_response(content=self.message_future_media_no_media)
            return

        only_fields = 'name', 'url', 'description', 'category_id', 'category__name', 'creator_id', 'creator__username'
        media_queryset = media_queryset.select_related('category', 'creator').only(*only_fields).order_by('-create_dt')

        view = views.FutureMediaPaginator(items_queryset=media_queryset, item_count=media_count)
        await view.refresh(interaction, content=self.message_future_media)

    @command(description='Add a story that will one day face judgment.')
    @checks.cooldown(rate=5, per=60, key=lambda interaction: interaction.user.id)
    async def add_future_media(self, interaction: discord.Interaction) -> None:
        await self.show_thinking_placeholder(interaction)
        user = await self.get_user(interaction)

        media_categories = MediaCategory.objects.order_by('name')
        media_categories = [category async for category in media_categories]

        view = views.MediaCategorySelectView(user=user, media_categories=media_categories)
        await interaction.edit_original_response(content=self.message_add_future_media, view=view)
