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

        self.assert_thinking_placeholder(self.interaction)
        self.interaction.edit_original_response.assert_called_once()
        _, kwargs = self.interaction.edit_original_response.call_args
        expected_message = 'A list of stories awaiting their time to be judged - not today.'
        self.assertEqual(kwargs['content'], expected_message)
        self.assertIsNotNone(kwargs['view'])

        embed = kwargs['embed']
        embed_fields = embed._fields
        self.assertEqual(len(embed_fields), len(media))
        for n, field in enumerate(embed_fields):
            media_obj = media[n]
            self.assertFalse(field['inline'])
            self.assertIn(media_obj.name, field['name'])
            self.assertIn(media_obj.category.name, field['name'])
            self.assertIn(media_obj.creator.username, field['value'])
            self.assertIn(media_obj.url, field['value'])
            self.assertIn(media_obj.description, field['value'])

    async def test__media_cog__future_media__no_media(self):
        await self.cog.future_media.callback(self.cog, self.interaction)

        self.assert_thinking_placeholder(self.interaction)
        expected_message = 'Nothing remains reserved for later. Even tomorrow feels empty.'
        self.interaction.edit_original_response.assert_called_once_with(content=expected_message)

    async def test__media_cog__add_future_media(self):
        media_categories = MediaCategory.objects.order_by('name')
        media_categories = [category async for category in media_categories]

        await self.cog.add_future_media.callback(self.cog, self.interaction)

        self.assert_thinking_placeholder(self.interaction)
        self.interaction.edit_original_response.assert_called_once()
        _, kwargs = self.interaction.edit_original_response.call_args
        expected_message = 'Every story needs a home before its trial. Choose one.'
        self.assertEqual(kwargs['content'], expected_message)

        view_elements = kwargs['view']._children
        self.assertEqual(len(view_elements), 1)
        media_category_select = view_elements[0]
        self.assertEqual(media_category_select.user.id, self.user.id)
        options = media_category_select._underlying.options
        self.assertEqual(len(options), len(media_categories))
        for n, option in enumerate(options):
            category = media_categories[n]
            self.assertEqual(option.label, category.name)
            self.assertEqual(option.value, str(category.id))
