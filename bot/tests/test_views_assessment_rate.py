from django.contrib.auth import get_user_model
from django.test import TestCase

from asgiref.sync import async_to_sync, sync_to_async

from decimal import Decimal
from unittest.mock import AsyncMock, Mock, patch

from api.assessment.models import Assessment, Media
from api.assessment.tests.factories import MediaFactory
from api.user.tests.factories import UserFactory
from bot.tests.base import LLMClientTestMixin
from bot.views.assessment_rate import AssessmentModal, MediaSelect

User = get_user_model()


class AssessmentModalTestCase(LLMClientTestMixin, TestCase):
    modal_class = AssessmentModal

    def setUp(self):
        super().setUp()

        self.mark = '5.5'
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

    @patch('bot.views.assessment_rate.openrouter_client.create_completion')
    @async_to_sync
    async def test__assessment_modal__on_submit(self, completion_mock):
        user = await sync_to_async(UserFactory.create)()
        media = await sync_to_async(MediaFactory.create)(description='media description')

        completion_mock.return_value = self.response_data
        modal = self.modal_class(user=user, media=media)
        modal.mark._value = self.mark

        await modal.on_submit(self.interaction)

        assessment = await media.assessments.filter(user_id=user.id).afirst()
        self.assertIsNotNone(assessment)
        self.assert_assessment_instance(assessment, user, media, self.mark)

        prompt = self.assert_llm_completion_mock(completion_mock)
        self.assertIn(str(assessment.mark), prompt)
        self.assertIn(media.name, prompt)
        self.assertIn(media.description, prompt)
        self.assertIn(media.category.name, prompt)

        self.interaction.response.edit_message.assert_called_once_with(
            content=self.response_content,
            embed=None,
            view=None,
        )

    @patch('bot.views.assessment_rate.openrouter_client.create_completion')
    @async_to_sync
    async def test__assessment_modal__on_submit__partial(self, completion_mock):
        user = await sync_to_async(UserFactory.create)()
        media = await sync_to_async(MediaFactory.create)()

        completion_mock.return_value = self.response_data
        modal = self.modal_class(user=user, media=media)
        modal.mark._value = self.mark
        modal.partial._value = self.partial

        await modal.on_submit(self.interaction)

        assessment = await media.assessments.filter(user_id=user.id).afirst()
        self.assertIsNotNone(assessment)
        self.assert_assessment_instance(assessment, user, media, self.mark, partial=self.partial)

        prompt = self.assert_llm_completion_mock(completion_mock)
        self.assertIn(assessment.partial, prompt)

        self.interaction.response.edit_message.assert_called_once()

    @patch('bot.views.assessment_rate.openrouter_client.create_completion')
    @async_to_sync
    async def test__assessment_modal__on_submit__errors__validation_error(self, completion_mock):
        user = await sync_to_async(UserFactory.create)()
        media = await sync_to_async(MediaFactory.create)()

        self.mark = '4.3'
        modal = self.modal_class(user=user, media=media)
        modal.mark._value = self.mark

        await modal.on_submit(self.interaction)

        assessment_exists = await media.assessments.filter(user_id=user.id).aexists()
        self.assertFalse(assessment_exists)

        completion_mock.assert_not_called()
        self.interaction.response.edit_message.assert_called_once()
        _, kwargs = self.interaction.response.edit_message.call_args
        msg = kwargs['content']
        self.assertIn('mark', msg)
        self.assertIn('Value must be an integer or end with .5.', msg)


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
        values_mock.get.assert_called_once()
