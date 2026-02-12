from django.test import TestCase

from asgiref.sync import async_to_sync, sync_to_async

from unittest.mock import AsyncMock, Mock, patch

from api.assessment.tests.factories import MediaFactory
from bot.views.assessment_rate import MediaSelect


class MediaSelectTestCase(TestCase):
    select_class = MediaSelect

    def setUp(self):
        self.user = Mock()
        self.interaction = AsyncMock()
        self.select = self.select_class(user=self.user, media=[])

    @patch('discord.ui.select.selected_values')
    @async_to_sync
    async def test__media_select__callback(self, values_mock):
        media = await sync_to_async(MediaFactory.create)()
        values_mock.get.return_value.get.return_value = [str(media.id)]

        await self.select.callback(self.interaction)

        self.interaction.response.send_modal.assert_called_once()
        args, _ = self.interaction.response.send_modal.call_args
        modal = args[0]
        self.assertEqual(modal.user, self.user)
        self.assertEqual(modal.media.id, media.id)
        self.assertIn(media.name, modal.title)
        values_mock.get.assert_called_once()
