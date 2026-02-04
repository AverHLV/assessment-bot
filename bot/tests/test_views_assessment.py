from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase

from asgiref.sync import async_to_sync, sync_to_async

from decimal import Decimal
from unittest.mock import AsyncMock, Mock, patch

from api.assessment.models import Assessment, Media
from api.assessment.tests.factories import MediaFactory
from api.user.tests.factories import UserFactory
from bot.views.assessment import AssessmentModal, MediaSelect

User = get_user_model()


class AssessmentModalTestCase(TestCase):
    modal_class = AssessmentModal

    def setUp(self):
        self.mark = '5'
        self.partial = '1 / 5 episodes'
        self.interaction = AsyncMock()

    def assert_assessment_instance(
        self,
        assessment: Assessment,
        user: User,
        media: Media,
        mark: str,
        partial: str = '',
    ) -> None:
        self.assertEqual(assessment.mark, Decimal(mark))
        self.assertEqual(assessment.partial, partial)
        self.assertEqual(assessment.media_id, media.id)
        self.assertEqual(assessment.user_id, user.id)

    async def test__assessment_modal__on_submit(self):
        user = await sync_to_async(UserFactory.create)()
        media = await sync_to_async(MediaFactory.create)()

        modal = self.modal_class(user=user, media_id=media.id)
        modal.mark._value = self.mark

        await modal.on_submit(self.interaction)

        assessment = await media.assessments.filter(user_id=user.id).afirst()
        self.assertIsNotNone(assessment)
        self.assert_assessment_instance(assessment, user, media, self.mark)

        expected_msg = 'So... you have seen it through to the end. Your judgment is carved into the ash.'
        self.interaction.response.send_message.assert_called_once_with(expected_msg, ephemeral=True)

    async def test__assessment_modal__on_submit__partial(self):
        user = await sync_to_async(UserFactory.create)()
        media = await sync_to_async(MediaFactory.create)()

        modal = self.modal_class(user=user, media_id=media.id)
        modal.mark._value = self.mark
        modal.partial._value = self.partial

        await modal.on_submit(self.interaction)

        assessment = await media.assessments.filter(user_id=user.id).afirst()
        self.assertIsNotNone(assessment)
        self.assert_assessment_instance(assessment, user, media, self.mark, partial=self.partial)

        self.interaction.response.send_message.assert_called_once()

    async def test__assessment_modal__on_submit__errors__validation_error(self):
        user = await sync_to_async(UserFactory.create)()
        media = await sync_to_async(MediaFactory.create)()

        self.mark = '4.3'
        modal = self.modal_class(user=user, media_id=media.id)
        modal.mark._value = self.mark

        await modal.on_submit(self.interaction)

        assessment_exists = await media.assessments.filter(user_id=user.id).aexists()
        self.assertFalse(assessment_exists)

        self.interaction.response.send_message.assert_called_once()
        args, _ = self.interaction.response.send_message.call_args
        msg = args[0]
        self.assertIn('mark', msg)
        self.assertIn('Value must be an integer or end with .5.', msg)


class MediaSelectTestCase(SimpleTestCase):
    select_class = MediaSelect

    def setUp(self):
        self.media_id = '1'
        self.user = Mock()
        self.interaction = AsyncMock()
        self.select = self.select_class(user=self.user, media=[])

    @patch('discord.ui.select.selected_values')
    @async_to_sync
    async def test__media_select__callback(self, values_mock):
        values_mock.return_value.get.return_value = [self.media_id]

        await self.select.callback(self.interaction)

        self.interaction.response.send_modal.assert_called_once()
        args, _ = self.interaction.response.send_modal.call_args
        modal = args[0]
        self.assertEqual(modal.user, self.user)
        self.assertEqual(modal.media_id, int(self.media_id))
        values_mock.assert_called_once()
