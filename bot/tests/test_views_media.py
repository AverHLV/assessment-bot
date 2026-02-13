from django.test import TestCase

from asgiref.sync import async_to_sync

from unittest.mock import AsyncMock, Mock, patch

from api.assessment.models import MediaCategory
from bot.views.media import MediaCategorySelect


class MediaCategorySelectTestCase(TestCase):
    select_class = MediaCategorySelect

    def setUp(self):
        self.user = Mock()
        self.interaction = AsyncMock()
        self.select = self.select_class(user=self.user, media_categories=[])

    @patch('discord.ui.select.selected_values')
    @async_to_sync
    async def test__media_category_select__callback(self, values_mock):
        category = await MediaCategory.objects.afirst()
        values_mock.get.return_value.get.return_value = [str(category.id)]

        await self.select.callback(self.interaction)

        self.interaction.response.send_modal.assert_called_once()
        args, _ = self.interaction.response.send_modal.call_args
        modal = args[0]
        self.assertEqual(modal.user, self.user)
        self.assertEqual(modal.media_category.id, category.id)
        self.assertIn(category.name.lower(), modal.title)
        values_mock.get.assert_called_once()
