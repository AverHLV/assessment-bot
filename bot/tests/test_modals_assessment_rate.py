from django.contrib.auth import get_user_model

from asgiref.sync import async_to_sync

from decimal import Decimal
from unittest.mock import patch

from api.assessment.models import Assessment, Media
from api.assessment.tests.factories import MediaFactory
from api.user.tests.factories import UserFactory
from bot.bot import AssessmentBot
from bot.tests.base import CogBaseTestCase
from bot.views.assessment_rate import AssessmentModal

User = get_user_model()


class AssessmentModalTestCase(CogBaseTestCase):
    modal_class = AssessmentModal

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.media = MediaFactory(description='media description', creator=cls.user)

    def setUp(self):
        super().setUp()

        self.mark = '5.5'
        self.partial = '1 / 5 episodes'
        self.completion_response = 'response content'

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

    @patch('bot.modals.assessment_rate.run_create_completion')
    @async_to_sync
    async def test__assessment_modal__on_submit(self, completion_mock):
        completion_mock.return_value = self.completion_response
        modal = self.modal_class(user=self.user, media=self.media)
        modal.mark._value = self.mark

        await modal.on_submit(self.interaction)

        self.assert_thinking(self.interaction, edit=True)
        self.assert_thinking_with_loop(self.interaction)
        assessment = await self.media.assessments.filter(user_id=self.user.id).afirst()
        self.assertIsNotNone(assessment)
        self.assert_assessment_instance(assessment, self.user, self.media, self.mark)

        completion_mock.assert_called_once()
        args, kwargs = completion_mock.call_args
        prompt = args[1]
        self.assertIn(str(assessment.mark), prompt)
        self.assertIn(self.media.name, prompt)
        self.assertIn(self.media.description, prompt)
        self.assertIn(self.media.category.name, prompt)
        self.assertEqual(kwargs['default_message'], modal.llm_client_default_message)

        self.interaction.edit_original_response.assert_called_once_with(
            content=completion_mock.return_value,
            embed=None,
            view=None,
        )

    @patch('bot.modals.assessment_rate.run_create_completion')
    @async_to_sync
    async def test__assessment_modal__on_submit__partial(self, completion_mock):
        completion_mock.return_value = self.completion_response
        modal = self.modal_class(user=self.user, media=self.media)
        modal.mark._value = self.mark
        modal.partial._value = self.partial

        await modal.on_submit(self.interaction)

        self.assert_thinking(self.interaction, edit=True)
        self.assert_thinking_with_loop(self.interaction)
        assessment = await self.media.assessments.filter(user_id=self.user.id).afirst()
        self.assertIsNotNone(assessment)
        self.assert_assessment_instance(assessment, self.user, self.media, self.mark, partial=self.partial)

        completion_mock.assert_called_once()
        args, _ = completion_mock.call_args
        self.assertIn(assessment.partial, args[1])

        self.interaction.edit_original_response.assert_called_once()

    @patch('bot.modals.assessment_rate.run_create_completion')
    @async_to_sync
    async def test__assessment_modal__on_submit__errors__validation_error(self, completion_mock):
        self.mark = '4.3'
        modal = self.modal_class(user=self.user, media=self.media)
        modal.mark._value = self.mark

        await modal.on_submit(self.interaction)

        self.assert_thinking(self.interaction, edit=True)
        self.assert_thinking_with_loop(self.interaction)
        assessment_exists = await self.media.assessments.filter(user_id=self.user.id).aexists()
        self.assertFalse(assessment_exists)

        completion_mock.assert_not_called()
        self.interaction.edit_original_response.assert_called_once()
        _, kwargs = self.interaction.edit_original_response.call_args
        msg = kwargs['content']
        self.assertIn('mark', msg)
        expected_error = 'Value must be an integer or end with .5.'
        self.assertIn(expected_error, msg)

    async def test__assessment_modal__on_error(self):
        error = ValueError('error')
        modal = self.modal_class(user=self.user, media=self.media)

        await modal.on_error(self.interaction, error)

        self.interaction.edit_original_response.assert_called_once_with(
            content=AssessmentBot.error_message,
            embed=None,
            view=None,
        )
