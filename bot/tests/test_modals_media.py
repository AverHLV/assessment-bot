from django.contrib.auth import get_user_model

from asgiref.sync import sync_to_async

from unittest.mock import AsyncMock

from api.assessment.models import Media, MediaCategory
from api.assessment.tests.factories import MediaFactory
from api.user.tests.factories import UserFactory
from bot.tests.base import CogBaseTestCase
from bot.views.media import MediaModal

User = get_user_model()


class MediaModalTestCase(CogBaseTestCase):
    modal_class = MediaModal

    @classmethod
    def setUpTestData(cls):
        cls.category = MediaCategory.objects.first()
        cls.user = UserFactory()

    def setUp(self):
        super().setUp()

        self.name = 'media name'
        self.url = 'https://media.com/media/'
        self.description = 'media description'
        self.interaction = AsyncMock()

    def assert_media_instance(
        self,
        media: Media,
        creator: User,
        name: str,
        url: str,
        category: MediaCategory,
        description: str = '',
    ) -> None:
        self.assertEqual(media.name, name)
        self.assertEqual(media.url, url)
        self.assertEqual(media.description, description)
        self.assertEqual(media.category_id, category.id)
        self.assertEqual(media.creator_id, creator.id)

    async def test__media_modal__on_submit(self):
        modal = self.modal_class(user=self.user, media_category=self.category)
        modal.name._value = self.name
        modal.url._value = self.url

        await modal.on_submit(self.interaction)

        self.assert_thinking_placeholder(self.interaction, edit=True)
        media = await Media.objects.afirst()
        self.assertIsNotNone(media)
        self.assert_media_instance(media, self.user, self.name, self.url, self.category)

        self.interaction.edit_original_response.assert_called_once_with(
            content=modal.form_valid_message,
            embed=None,
            view=None,
        )

    async def test__media_modal__on_submit__description(self):
        modal = self.modal_class(user=self.user, media_category=self.category)
        modal.name._value = self.name
        modal.url._value = self.url
        modal.description._value = self.description

        await modal.on_submit(self.interaction)

        self.assert_thinking_placeholder(self.interaction, edit=True)
        media = await Media.objects.afirst()
        self.assertIsNotNone(media)
        self.assert_media_instance(media, self.user, self.name, self.url, self.category, description=self.description)

        self.interaction.edit_original_response.assert_called_once_with(
            content=modal.form_valid_message,
            embed=None,
            view=None,
        )

    async def test__media_modal__on_submit__errors__validation_error(self):
        await sync_to_async(MediaFactory.create)(name=self.name, category=self.category)

        modal = self.modal_class(user=self.user, media_category=self.category)
        modal.name._value = self.name
        modal.url._value = self.url

        await modal.on_submit(self.interaction)

        self.assert_thinking_placeholder(self.interaction, edit=True)
        media_count = await Media.objects.acount()
        self.assertEqual(media_count, 1)

        self.interaction.edit_original_response.assert_called_once()
        _, kwargs = self.interaction.edit_original_response.call_args
        expected_error = 'Media with this Name and Category already exists.'
        self.assertIn(expected_error, kwargs['content'])
