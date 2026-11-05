from asgiref.sync import async_to_sync

from unittest.mock import AsyncMock, patch

from api.assessment.models import Media, MediaCategory
from bot.commands.media import MediaCog
from bot.commands.rate import AssessmentCog
from bot.tests.base import CogWithCommandsBaseTestCase
from bot.tests.media_modal_base import MEDIA_NAME, media_modal_payload, submit_media_modal


class AddMediaAssessmentTestCase(CogWithCommandsBaseTestCase):
    cog_class = MediaCog

    def open_modal(self, queries=2):
        with self.assertNumQueries(queries):
            async_to_sync(self.cog.add_future_media.callback)(self.cog, self.interaction)

        self.assert_thinking(self.interaction)
        response = self.interaction.edit_original_response.call_args.kwargs
        self.assertEqual(response['content'], self.cog.message_add_future_media)
        select = response['view'].children[0]
        category = MediaCategory.objects.movie()

        self.interaction.reset_mock()
        with self.assertNumQueries(1), patch('discord.ui.select.selected_values') as values_mock:
            values_mock.get.return_value.get.return_value = [str(category.pk)]
            async_to_sync(select.callback)(self.interaction)

        self.interaction.response.send_modal.assert_awaited_once()
        modal = self.interaction.response.send_modal.call_args.args[0]
        self.assertIs(modal.user, select.user)
        self.assertEqual(modal.user.external_id, self.interaction.user.id)
        return modal

    @patch('api.assessment.models.omdb_client.search', return_value={'imdbRating': '7.5'})
    def test__add_future_media__staff_can_rate_new_media(self, search_mock):
        self.user.is_staff = True
        self.user.save(update_fields=['is_staff'])
        modal = self.open_modal()
        self.assertTrue(modal.move_to_assessment.default)
        self.interaction.reset_mock()

        with self.assertNumQueries(3):
            submit_media_modal(modal, self.interaction, media_modal_payload(modal))

        self.interaction.edit_original_response.assert_awaited_once_with(
            content=modal.form_valid_message, embed=None, view=None
        )
        media = Media.objects.get()
        self.assertEqual(media.assessment_status, Media.AssessmentStatus.IN_PROGRESS)
        self.assertEqual(media.creator_id, self.user.pk)
        self.assertEqual(media.category_id, modal.media_category.pk)
        search_mock.assert_awaited_once_with(title=MEDIA_NAME)

        self.interaction.reset_mock()
        with self.assertNumQueries(1):
            async_to_sync(self.cog.future_media.callback)(self.cog, self.interaction)

        self.interaction.edit_original_response.assert_awaited_once_with(content=self.cog.message_future_media_no_media)

        # The new media can be selected for assessment immediately.
        rate_interaction = AsyncMock()
        rate_interaction.user.id = self.user.external_id
        rate_cog = AssessmentCog(self.bot)
        with self.assertNumQueries(2):
            async_to_sync(rate_cog.rate.callback)(rate_cog, rate_interaction)

        response = rate_interaction.edit_original_response.call_args.kwargs
        self.assertEqual(response['content'], rate_cog.message_rate)
        self.assertEqual([option.value for option in response['view'].children[0].options], [str(media.pk)])

    @patch('api.assessment.models.omdb_client.search', return_value={'imdbRating': '7.5'})
    def test__add_future_media__first_interaction_keeps_future_status(self, search_mock):
        self.user.delete()
        self.interaction.user.name = 'New media author'
        modal = self.open_modal(queries=5)
        self.assertFalse(modal.user.is_staff)
        self.assertIsNone(modal.move_to_assessment)
        self.interaction.reset_mock()

        with self.assertNumQueries(3):
            submit_media_modal(modal, self.interaction, media_modal_payload(modal))

        self.interaction.edit_original_response.assert_awaited_once_with(
            content=modal.form_valid_message, embed=None, view=None
        )
        media = Media.objects.get()
        self.assertEqual(media.assessment_status, Media.AssessmentStatus.INITIAL)
        self.assertEqual(media.creator_id, modal.user.pk)
        search_mock.assert_awaited_once_with(title=MEDIA_NAME)
