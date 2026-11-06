from django.db import IntegrityError, transaction

import discord
from asgiref.sync import async_to_sync
from httpx2 import TimeoutException

from unittest.mock import patch

from api.assessment.models import Assessment
from api.assessment.tests.factories import AssessmentFactory
from bot.bot import AssessmentBot
from bot.forms import AssessmentForm
from bot.tests.assessment_rate_base import AssessmentReviewBaseTestCase


class AssessmentReviewTestCase(AssessmentReviewBaseTestCase):
    def test__assessment_modal__review_input(self):
        modal = self.get_modal()

        self.assertEqual([item.text for item in modal.children], ['Mark', 'If partial', 'Review'])
        self.assertIs(modal.children[2], modal.review)
        self.assertFalse(modal.review.component.required)
        self.assertEqual(modal.review.component.style, discord.TextStyle.paragraph)
        self.assertEqual(modal.review.component.max_length, 1000)
        self.assertIn('Optional', modal.review.component.placeholder)
        self.assertLessEqual(len(modal.children), 5)
        for item in modal.children:
            self.assertIsInstance(item, discord.ui.Label)
            self.assertLessEqual(len(item.text), 45)
            self.assertLessEqual(len(item.component.placeholder), 100)

        components = modal.to_dict()['components']
        self.assertEqual([item['label'] for item in components], ['Mark', 'If partial', 'Review'])
        self.assertEqual([item['type'] for item in components], [18, 18, 18])
        for item in components:
            self.assertEqual(item['component']['type'], 4)
            self.assertIsNone(item['component']['label'])

    @patch('api.llm.clients.AsyncOpenRouterClient.create_completion')
    def test__assessment_modal__review_saved(self, completion_mock):
        self.set_completion(completion_mock)
        modal = self.get_modal(self.review_text)

        self.submit(modal)

        self.assert_saved_review(modal, 'Great pacing', completion_mock)

    @patch('api.llm.clients.AsyncOpenRouterClient.create_completion')
    def test__assessment_modal__review_omitted(self, completion_mock):
        self.set_completion(completion_mock)
        modal = self.get_modal()

        self.submit(modal)

        self.assert_saved_review(modal, '', completion_mock)

    @patch('api.llm.clients.AsyncOpenRouterClient.create_completion')
    def test__assessment_modal__review_empty(self, completion_mock):
        self.set_completion(completion_mock)
        modal = self.get_modal('')

        self.submit(modal)

        self.assert_saved_review(modal, '', completion_mock)

    @patch('api.llm.clients.AsyncOpenRouterClient.create_completion')
    def test__assessment_modal__review_whitespace(self, completion_mock):
        self.set_completion(completion_mock)
        modal = self.get_modal(' \n\t ')

        self.submit(modal)

        self.assert_saved_review(modal, '', completion_mock)

    @patch('api.llm.clients.AsyncOpenRouterClient.create_completion')
    def test__assessment_modal__review_one_character(self, completion_mock):
        self.set_completion(completion_mock)
        modal = self.get_modal('Я')

        self.submit(modal)

        self.assert_saved_review(modal, 'Я', completion_mock)

    @patch('api.llm.clients.AsyncOpenRouterClient.create_completion')
    def test__assessment_modal__review_maximum_length(self, completion_mock):
        self.set_completion(completion_mock)
        modal = self.get_modal('я' * 1000)

        self.submit(modal)

        self.assert_saved_review(modal, 'я' * 1000, completion_mock)

    @patch('api.llm.clients.AsyncOpenRouterClient.create_completion')
    def test__assessment_modal__review_multiline_markdown_and_cleaning(self, completion_mock):
        self.set_completion(completion_mock)
        modal = self.get_modal('  **Чудово**\nДруга  думка\n> Фінал\t ')

        self.submit(modal)

        self.assert_saved_review(modal, '**Чудово**\nДруга  думка\n> Фінал', completion_mock)

    def test__assessment_form__missing_review_defaults_to_empty(self):
        form = AssessmentForm(data={'mark': '8'})

        with self.assertNumQueries(0):
            valid = form.is_valid()

        self.assertTrue(valid, form.errors)
        self.assertEqual(form.cleaned_data['review'], '')
        self.assertEqual(form.instance.review, '')

    @patch('api.llm.clients.AsyncOpenRouterClient.create_completion')
    def test__assessment_modal__errors__review_too_long(self, completion_mock):
        modal = self.get_modal('я' * 1001)

        self.submit(modal, queries=0)

        response = self.interaction.edit_original_response.call_args.kwargs
        self.assertIn('- review: Ensure this value has at most 1000 characters (it has 1001).', response['content'])
        self.assertFalse(Assessment.objects.exists())
        completion_mock.assert_not_called()
        self.assert_thinking_with_loop(self.interaction)

    @patch('api.llm.clients.AsyncOpenRouterClient.create_completion')
    def test__assessment_modal__errors__partial_too_long(self, completion_mock):
        modal = self.get_modal(self.review_text)
        modal.partial.component._value = 'p' * 301

        self.submit(modal, queries=0)

        self.assertIn('- partial:', self.interaction.edit_original_response.call_args.kwargs['content'])
        self.assertFalse(Assessment.objects.exists())
        completion_mock.assert_not_called()

    @patch('api.llm.clients.AsyncOpenRouterClient.create_completion')
    def test__assessment_modal__errors__invalid_mark_with_review(self, completion_mock):
        modal = self.get_modal(self.review_text)
        modal.mark.component._value = '4.3'

        self.submit(modal, queries=0)

        self.assertIn('- mark:', self.interaction.edit_original_response.call_args.kwargs['content'])
        self.assertFalse(Assessment.objects.exists())
        completion_mock.assert_not_called()

    @patch('api.llm.clients.AsyncOpenRouterClient.create_completion')
    def test__assessment_modal__errors__duplicate_preserves_existing_review(self, completion_mock):
        existing = AssessmentFactory(user=self.user, media=self.media, review='Original review')
        modal = self.get_modal(self.review_text)

        # Isolate the real uniqueness violation so assertions can use the test database after rollback.
        with self.assertRaises(IntegrityError), transaction.atomic(), self.assertNumQueries(1):
            async_to_sync(modal.on_submit)(self.interaction)
        with self.assertNumQueries(0):
            async_to_sync(modal.on_error)(self.interaction, IntegrityError('Duplicate assessment'))

        self.interaction.edit_original_response.assert_called_once_with(
            content=AssessmentBot.error_message,
            embed=None,
            view=None,
        )
        self.assertEqual(Assessment.objects.count(), 1)
        existing.refresh_from_db()
        self.assertEqual(existing.review, 'Original review')
        completion_mock.assert_not_called()

    @patch('api.llm.clients.AsyncOpenRouterClient.create_completion')
    def test__assessment_modal__llm_timeout_keeps_review(self, completion_mock):
        completion_mock.side_effect = TimeoutException('Controlled timeout')
        modal = self.get_modal(self.review_text)

        self.submit(modal)

        self.interaction.edit_original_response.assert_called_once_with(
            content=modal.llm_client_default_message,
            embed=None,
            view=None,
        )
        self.assertEqual(Assessment.objects.get().review, 'Great pacing')
        completion_mock.assert_awaited_once()

    @patch('api.llm.clients.AsyncOpenRouterClient.create_completion')
    def test__assessment_modal__review_hidden_from_prompt(self, completion_mock):
        self.set_completion(completion_mock)
        modal = self.get_modal('PRIVATE_REVIEW_SENTINEL')

        self.submit(modal)

        prompt_with_review = completion_mock.call_args.kwargs['messages'][0]['content']
        self.assertNotIn('PRIVATE_REVIEW_SENTINEL', prompt_with_review)
        self.assertIn(self.media.description, prompt_with_review)
        self.assertEqual(Assessment.objects.get().review, 'PRIVATE_REVIEW_SENTINEL')
        Assessment.objects.all().delete()
        self.interaction.reset_mock()
        completion_mock.reset_mock()
        modal = self.get_modal()

        self.submit(modal)

        prompt_without_review = completion_mock.call_args.kwargs['messages'][0]['content']
        self.assertEqual(prompt_with_review, prompt_without_review)
