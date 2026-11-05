from asgiref.sync import async_to_sync

from decimal import Decimal

from api.assessment.models import Assessment
from api.assessment.tests.factories import MediaFactory
from bot.modals.assessment_rate import AssessmentModal
from bot.tests.base import CogWithCommandsBaseTestCase


class AssessmentReviewBaseTestCase(CogWithCommandsBaseTestCase):
    review_text = 'Great pacing'
    completion_text = 'Rating saved'

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.media = MediaFactory(description='A short description', creator=cls.user)

    def get_modal(self, review=None):
        modal = AssessmentModal(user=self.user, media=self.media)
        modal.mark._value = '8'
        if review is not None:
            modal.review._value = review
        return modal

    def submit(self, modal, queries=1):
        with self.assertNumQueries(queries):
            async_to_sync(modal.on_submit)(self.interaction)

    def assert_saved_review(self, modal, review, completion_mock):
        self.interaction.edit_original_response.assert_called_once_with(
            content=self.completion_text,
            embed=None,
            view=None,
        )
        assessment = Assessment.objects.get()
        self.assertEqual(assessment.mark, Decimal('8'))
        self.assertEqual(assessment.partial, '')
        self.assertEqual(assessment.review, review)
        self.assertEqual(assessment.media_id, self.media.pk)
        self.assertEqual(assessment.user_id, self.user.pk)
        self.assert_thinking(self.interaction, edit=True)
        self.assert_thinking_with_loop(self.interaction)
        completion_mock.assert_awaited_once()
        return assessment

    def set_completion(self, completion_mock):
        completion_mock.return_value = {'choices': [{'message': {'content': self.completion_text}}]}
