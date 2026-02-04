from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from asgiref.sync import sync_to_async

from datetime import timedelta
from unittest.mock import AsyncMock

from api.assessment.models import Media
from api.assessment.tests.factories import AssessmentFactory, MediaFactory
from api.user.tests.factories import UserFactory
from bot import commands

User = get_user_model()


class RateTestCase(TestCase):
    def setUp(self):
        self.interaction = AsyncMock()

    async def test__rate(self):
        user = await sync_to_async(UserFactory.create)()
        media = await sync_to_async(MediaFactory.create_batch)(
            size=3,
            assessment_status=Media.AssessmentStatus.IN_PROGRESS,
            assessment_until_dt=timezone.now() + timedelta(days=1),
        )
        await sync_to_async(AssessmentFactory.create)(media=media[-1], user=user)

        selected_media = media[:-1]
        self.interaction.user.id = user.external_id

        await commands.rate.callback(self.interaction)

        self.interaction.response.send_message.assert_called_once()
        args, kwargs = self.interaction.response.send_message.call_args
        self.assertEqual(args[0], 'Choose a story from the ashes...')
        self.assertTrue(kwargs['ephemeral'])

        view_elements = kwargs['view']._children
        self.assertEqual(len(view_elements), 1)
        media_select = view_elements[0]
        self.assertEqual(media_select.user.id, user.id)
        options = media_select._underlying.options
        self.assertEqual(len(options), len(selected_media))
        for n, option in enumerate(options):
            media_obj = selected_media[n]
            self.assertEqual(option.label, media_obj.name)
            self.assertEqual(option.value, str(media_obj.id))
            self.assertEqual(option.description, media_obj.category.name)

    async def test__rate__no_media(self):
        self.interaction.user.id = 100
        self.interaction.user.name = 'Discord user'

        await commands.rate.callback(self.interaction)

        user = await User.objects.filter(external_id=self.interaction.user.id).afirst()
        self.assertIsNotNone(user)
        self.assertEqual(user.username, self.interaction.user.name)

        expected_message = 'The ashes are silent... There is nothing left for you to judge.'
        self.interaction.response.send_message.assert_called_once_with(expected_message, ephemeral=True)
