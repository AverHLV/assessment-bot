from django.contrib.auth import get_user_model

import discord

from api.assessment.models import Media
from bot.modals import AssessmentModal
from bot.views.base import BaseView

User = get_user_model()


class MediaSelect(discord.ui.Select):
    modal_class = AssessmentModal

    def __init__(self, *args, user: User, media: list[Media], **kwargs):
        kwargs.setdefault('placeholder', 'Pick a story... I`ll watch with you.')
        kwargs['options'] = [
            discord.SelectOption(
                label=media_obj.name,
                value=str(media_obj.id),
                description=media_obj.category.name,
            )
            for media_obj in media
        ]

        super().__init__(*args, **kwargs)
        self.user = user

    async def callback(self, interaction: discord.Interaction) -> None:
        media = (
            await Media.objects.select_related('category')
            .only('name', 'description', 'category_id', 'category__name')
            .aget(id=int(self.values[0]))
        )
        modal = self.modal_class(user=self.user, media=media)
        await interaction.response.send_modal(modal)


class MediaSelectToAssessView(BaseView):
    select_class = MediaSelect

    def __init__(self, *args, user: User, media: list[Media], **kwargs):
        super().__init__(*args, **kwargs)
        self.add_item(self.select_class(user=user, media=media))
