from django.contrib.auth import get_user_model
from django.test import TestCase

from asgiref.sync import async_to_sync

from decimal import Decimal
from unittest.mock import AsyncMock, patch

from api.assessment.models import Assessment, Media
from api.assessment.tests.factories import MediaFactory
from api.user.tests.factories import UserFactory
from bot.tests.base import AssertThinkingPlaceholderMixin, LLMClientTestMixin
from bot.views.assessment_rate import AssessmentModal

User = get_user_model()


class AssessmentModalTestCase(AssertThinkingPlaceholderMixin, LLMClientTestMixin, TestCase):
    modal_class = AssessmentModal

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.media = MediaFactory(description='media description', creator=cls.user)

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

    @patch('bot.modals.assessment_rate.openrouter_client.create_completion')
    @async_to_sync
    async def test__assessment_modal__on_submit(self, completion_mock):
        completion_mock.return_value = self.response_data
        modal = self.modal_class(user=self.user, media=self.media)
        modal.mark._value = self.mark

        await modal.on_submit(self.interaction)

        self.assert_thinking_placeholder(self.interaction, edit=True)
        assessment = await self.media.assessments.filter(user_id=self.user.id).afirst()
        self.assertIsNotNone(assessment)
        self.assert_assessment_instance(assessment, self.user, self.media, self.mark)

        prompt = self.assert_llm_completion_mock(completion_mock)
        self.assertIn(str(assessment.mark), prompt)
        self.assertIn(self.media.name, prompt)
        self.assertIn(self.media.description, prompt)
        self.assertIn(self.media.category.name, prompt)

        self.interaction.edit_original_response.assert_called_once_with(
            content=self.response_content,
            embed=None,
            view=None,
        )

    @patch('bot.modals.assessment_rate.openrouter_client.create_completion')
    @async_to_sync
    async def test__assessment_modal__on_submit__partial(self, completion_mock):
        completion_mock.return_value = self.response_data
        modal = self.modal_class(user=self.user, media=self.media)
        modal.mark._value = self.mark
        modal.partial._value = self.partial

        await modal.on_submit(self.interaction)

        self.assert_thinking_placeholder(self.interaction, edit=True)
        assessment = await self.media.assessments.filter(user_id=self.user.id).afirst()
        self.assertIsNotNone(assessment)
        self.assert_assessment_instance(assessment, self.user, self.media, self.mark, partial=self.partial)

        prompt = self.assert_llm_completion_mock(completion_mock)
        self.assertIn(assessment.partial, prompt)

        self.interaction.edit_original_response.assert_called_once()

    @patch('bot.modals.assessment_rate.openrouter_client.create_completion')
    @async_to_sync
    async def test__assessment_modal__on_submit__errors__validation_error(self, completion_mock):
        self.mark = '4.3'
        modal = self.modal_class(user=self.user, media=self.media)
        modal.mark._value = self.mark

        await modal.on_submit(self.interaction)

        self.assert_thinking_placeholder(self.interaction, edit=True)
        assessment_exists = await self.media.assessments.filter(user_id=self.user.id).aexists()
        self.assertFalse(assessment_exists)

        completion_mock.assert_not_called()
        self.interaction.edit_original_response.assert_called_once()
        _, kwargs = self.interaction.edit_original_response.call_args
        msg = kwargs['content']
        self.assertIn('mark', msg)
        expected_error = 'Value must be an integer or end with .5.'
        self.assertIn(expected_error, msg)
