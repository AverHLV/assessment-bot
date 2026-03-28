from django.utils import timezone

import factory
from asgiref.sync import sync_to_async

from datetime import timedelta

from api.assessment.models import MediaCategory
from api.assessment.tests.factories import MediaFactory
from bot import commands
from bot.tests.base import CogWithCommandsBaseTestCase


class MediaCogTestCase(CogWithCommandsBaseTestCase):
    cog_class = commands.MediaCog

    async def test__media_cog__future_media(self):
        current_time = timezone.now()
        media = await sync_to_async(MediaFactory.create_batch)(
            size=2,
            description='media description',
            create_dt=factory.Iterator((current_time, current_time - timedelta(hours=1))),
        )

        await self.cog.future_media.callback(self.cog, self.interaction)

        self.assert_thinking(self.interaction)
        self.interaction.edit_original_response.assert_called_once()
        _, kwargs = self.interaction.edit_original_response.call_args
        self.assertEqual(kwargs['content'], self.cog.message_future_media)
        self.assertIsNotNone(kwargs['view'])

        embed_fields = kwargs['embed'].fields
        self.assertEqual(len(embed_fields), len(media))
        for n, field in enumerate(embed_fields):
            media_obj = media[n]
            self.assertFalse(field.inline)
            self.assertIn(media_obj.name, field.name)
            self.assertIn(media_obj.category.name, field.name)
            self.assertIn(media_obj.creator.username, field.value)
            self.assertIn(media_obj.url, field.value)
            self.assertIn(media_obj.description, field.value)

    async def test__media_cog__future_media__no_media(self):
        await self.cog.future_media.callback(self.cog, self.interaction)

        self.assert_thinking(self.interaction)
        self.interaction.edit_original_response.assert_called_once_with(content=self.cog.message_future_media_no_media)

    async def test__media_cog__add_future_media(self):
        media_categories = MediaCategory.objects.order_by('name')
        media_categories = [category async for category in media_categories]

        await self.cog.add_future_media.callback(self.cog, self.interaction)

        self.assert_thinking(self.interaction)
        self.interaction.edit_original_response.assert_called_once()
        _, kwargs = self.interaction.edit_original_response.call_args
        self.assertEqual(kwargs['content'], self.cog.message_add_future_media)

        view_elements = kwargs['view'].children
        self.assertEqual(len(view_elements), 1)
        media_category_select = view_elements[0]
        self.assertEqual(media_category_select.user.id, self.user.id)
        self.assertEqual(len(media_category_select.options), len(media_categories))
        for n, option in enumerate(media_category_select.options):
            category = media_categories[n]
            self.assertEqual(option.label, category.name)
            self.assertEqual(option.value, str(category.id))
