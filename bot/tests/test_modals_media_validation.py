from asgiref.sync import async_to_sync

from unittest.mock import patch

from api.assessment import omdb_client
from api.assessment.errors import OMDbError
from api.assessment.models import Media, MediaCategory
from api.assessment.tests.factories import MediaFactory
from bot.bot import AssessmentBot
from bot.tests.media_modal_base import MediaModalBaseTestCase, media_modal_payload


class MediaModalValidationTestCase(MediaModalBaseTestCase):
    def test__media_modal__errors__duplicate_name_in_category(self):
        existing = MediaFactory(name=self.name, category=self.category, creator=self.regular_user)
        modal = self.get_modal()

        self.submit(modal, queries=2)

        self.assert_invalid('Media with this Name and Category already exists.', count=1)
        existing.refresh_from_db()
        self.assertEqual(existing.assessment_status, Media.AssessmentStatus.INITIAL)
        self.assertEqual(existing.creator_id, self.regular_user.pk)

    def test__media_modal__errors__empty_name(self):
        modal = self.get_modal()

        self.submit(modal, name='', queries=1)

        self.assert_invalid('name: This field is required.')

    def test__media_modal__errors__long_name(self):
        modal = self.get_modal()
        max_length = Media._meta.get_field('name').max_length

        self.submit(modal, name='a' * (max_length + 1), queries=1)

        self.assert_invalid(f'Ensure this value has at most {max_length} characters')

    def test__media_modal__errors__invalid_url(self):
        modal = self.get_modal()

        self.submit(modal, url='not a URL', queries=2)

        self.assert_invalid('url: Enter a valid URL.')

    def test__media_modal__errors__deleted_category(self):
        modal = self.get_modal()
        MediaCategory.objects.filter(pk=self.category.pk).delete()

        self.submit(modal, queries=1)

        self.assert_invalid('category: Select a valid choice.')

    def test__media_modal__meta_mark_not_found(self):
        modal = self.get_modal()
        self.search_mock.side_effect = OMDbError(omdb_client.ErrorMessage.NOT_FOUND)

        self.submit(modal)

        self.assert_saved(modal, Media.AssessmentStatus.IN_PROGRESS, meta_mark=None)
        self.search_mock.assert_awaited_once_with(title=self.name)

    def test__media_modal__errors__meta_mark_provider(self):
        modal = self.get_modal()
        self.search_mock.side_effect = OMDbError('Provider unavailable')
        components = media_modal_payload(modal)

        with self.assertNumQueries(2), patch('discord.ui.Modal.on_error') as error_mock:
            async_to_sync(modal._scheduled_task)(self.interaction, components, {})

        self.interaction.edit_original_response.assert_called_once_with(
            content=AssessmentBot.error_message, embed=None, view=None
        )
        self.assertFalse(Media.objects.exists())
        self.search_mock.assert_awaited_once_with(title=self.name)
        error_mock.assert_awaited_once()
