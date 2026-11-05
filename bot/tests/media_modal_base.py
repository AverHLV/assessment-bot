from asgiref.sync import async_to_sync

from decimal import Decimal
from unittest.mock import patch

from api.assessment.models import Media, MediaCategory
from api.user.tests.factories import UserFactory
from bot.modals.media import MediaModal
from bot.tests.base import CogBaseTestCase

MEDIA_NAME = 'A new story'
MEDIA_URL = 'https://example.com/media'
MEDIA_DESCRIPTION = 'A description'


def get_media_modal(user, category):
    async def create():
        return MediaModal(user=user, media_category=category)

    return async_to_sync(create)()


def media_modal_payload(modal, *, checked=None, name=MEDIA_NAME, url=MEDIA_URL):
    values = (name, url, MEDIA_DESCRIPTION)
    components = [
        {'type': 1, 'components': [{'type': 4, 'custom_id': field.custom_id, 'value': value}]}
        for field, value in zip((modal.name, modal.url, modal.description), values, strict=True)
    ]
    if modal.move_to_assessment is not None:
        components.append(
            {
                'type': 18,
                'component': {
                    'type': modal.move_to_assessment.type.value,
                    'custom_id': modal.move_to_assessment.custom_id,
                    'value': modal.move_to_assessment.default if checked is None else checked,
                },
            }
        )
    return components


def submit_media_modal(modal, interaction, components):
    async def submit():
        modal._refresh(interaction, components, {})
        await modal.on_submit(interaction)

    async_to_sync(submit)()


class MediaModalBaseTestCase(CogBaseTestCase):
    name = MEDIA_NAME
    url = MEDIA_URL
    description = MEDIA_DESCRIPTION
    rating = '7.5'

    @classmethod
    def setUpTestData(cls):
        cls.category = MediaCategory.objects.movie()
        cls.user = UserFactory(is_staff=True)
        cls.regular_user = UserFactory(is_staff=False)

    def setUp(self):
        super().setUp()
        search_patch = patch('api.assessment.models.omdb_client.search', return_value={'imdbRating': self.rating})
        self.search_mock = search_patch.start()
        self.addCleanup(search_patch.stop)

    def get_modal(self, user=None, category=None):
        with self.assertNumQueries(0):
            return get_media_modal(user or self.user, category or self.category)

    def submit(self, modal, *, queries=3, **kwargs):
        components = media_modal_payload(modal, **kwargs)
        with self.assertNumQueries(queries):
            submit_media_modal(modal, self.interaction, components)

    def assert_saved(self, modal, status, *, meta_mark=Decimal('7.5')):
        self.assert_thinking(self.interaction, edit=True)
        self.interaction.edit_original_response.assert_called_once_with(
            content=modal.form_valid_message, embed=None, view=None
        )

        media = Media.objects.get()
        self.assertEqual(media.assessment_status, status)
        self.assertEqual(media.name, self.name)
        self.assertEqual(media.url, self.url)
        self.assertEqual(media.description, self.description)
        self.assertEqual(media.category_id, modal.media_category.pk)
        self.assertEqual(media.creator_id, modal.user.pk)
        self.assertEqual(media.meta_mark, meta_mark)
        return media

    def assert_invalid(self, message, *, count=0):
        self.assert_thinking(self.interaction, edit=True)
        self.interaction.edit_original_response.assert_called_once()
        response = self.interaction.edit_original_response.call_args.kwargs
        self.assertIn(message, response['content'])
        self.assertIsNone(response['embed'])
        self.assertIsNone(response['view'])

        self.assertEqual(Media.objects.count(), count)
        self.search_mock.assert_not_awaited()
