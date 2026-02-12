import discord

from api.assessment.models import MediaCategory
from bot.modals import MediaModal


class MediaCategorySelect(discord.ui.Select):
    modal_class = MediaModal

    def __init__(self, *args, media_categories: list[MediaCategory], **kwargs):
        kwargs.setdefault('placeholder', 'Pick its resting place among the shelves...')
        kwargs['options'] = [
            discord.SelectOption(label=category.name, value=str(category.id)) for category in media_categories
        ]

        super().__init__(*args, **kwargs)

    async def callback(self, interaction: discord.Interaction) -> None:
        media_category = await MediaCategory.objects.aget(id=int(self.values[0]))
        modal = self.modal_class(media_category=media_category)
        await interaction.response.send_modal(modal)


class MediaCategorySelectView(discord.ui.View):
    select_class = MediaCategorySelect

    def __init__(self, *args, media_categories: list[MediaCategory], **kwargs):
        super().__init__(*args, **kwargs)
        self.add_item(self.select_class(media_categories=media_categories))
