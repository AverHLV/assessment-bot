from django.utils import timezone

import factory
from asgiref.sync import sync_to_async

from datetime import timedelta

from api.assessment.tests.factories import MediaFactory
from bot import commands
from bot.tests.base import CommandBaseTestCase


class FutureMediaTestCase(CommandBaseTestCase):
    async def test__future_media(self):
        current_time = timezone.now()
        media = await sync_to_async(MediaFactory.create_batch)(
            size=2,
            description='media description',
            create_dt=factory.Iterator((current_time, current_time - timedelta(hours=1))),
        )

        await commands.future_media.callback(self.interaction)

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
            self.assertIn(media_obj.url, field['value'])
            self.assertIn(media_obj.description, field['value'])

    async def test__future_media__no_media(self):
        await commands.future_media.callback(self.interaction)

        self.assert_thinking_placeholder(self.interaction)
        expected_message = 'Nothing remains reserved for later. Even tomorrow feels empty.'
        self.interaction.edit_original_response.assert_called_once_with(content=expected_message)
