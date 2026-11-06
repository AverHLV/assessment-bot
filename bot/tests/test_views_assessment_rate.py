from asgiref.sync import async_to_sync

from unittest.mock import patch

from api.assessment.models import Media
from api.assessment.tests.factories import MediaFactory
from bot.tests.base import CogWithCommandsBaseTestCase
from bot.views.assessment_rate import MediaSelect


class MediaSelectTestCase(CogWithCommandsBaseTestCase):
    select_class = MediaSelect

    def setUp(self):
        super().setUp()
        self.select = self.select_class(user=self.user, media=[])

    @patch('discord.ui.select.selected_values')
    def test__media_select__callback(self, values_mock):
        media = MediaFactory(description='Selected story description')
        values_mock.get.return_value.get.return_value = [str(media.pk)]

        with self.assertNumQueries(1):
            async_to_sync(self.select.callback)(self.interaction)

        self.interaction.response.send_modal.assert_called_once()
        modal = self.interaction.response.send_modal.call_args.args[0]
        self.assertEqual(modal.user.pk, self.user.pk)
        self.assertEqual(modal.media.pk, media.pk)
        self.assertEqual(modal.media.description, 'Selected story description')
        self.assertEqual(modal.media.category.name, media.category.name)
        self.assertIn(media.name, modal.title)
        self.assertEqual(modal.children[-1].text, 'Review')
        values_mock.get.assert_called_once()

    @patch('discord.ui.select.selected_values')
    def test__media_select__errors__missing_media(self, values_mock):
        values_mock.get.return_value.get.return_value = ['-1']

        with self.assertNumQueries(1), self.assertRaises(Media.DoesNotExist):
            async_to_sync(self.select.callback)(self.interaction)

        self.interaction.response.send_modal.assert_not_called()
