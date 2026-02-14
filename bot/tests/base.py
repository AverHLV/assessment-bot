from django.db.models import QuerySet
from django.test import TestCase

from unittest.mock import AsyncMock

from api.assessment.models import Assessment
from api.llm.clients import AsyncOpenRouterClient
from api.user.tests.factories import UserFactory


class AsyncTestContextManager:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        return


class AssertThinkingPlaceholderMixin:
    @staticmethod
    def assert_thinking_placeholder(interaction: AsyncMock, edit: bool = False) -> None:
        expected_message = "Please wait... I'm gently sifting through fading memories."
        if edit:
            interaction.response.edit_message.assert_called_once_with(content=expected_message, embed=None, view=None)
        else:
            interaction.response.send_message.assert_called_once_with(expected_message, ephemeral=True)


class LLMClientTestMixin:
    def setUp(self):
        super().setUp()

        self.response_content = 'response content'
        self.response_data = {
            'choices': [
                {
                    'message': {
                        'content': self.response_content,
                    },
                },
            ],
        }

    def assert_llm_completion_mock(self, mock: AsyncMock) -> str:
        mock.assert_called_once()
        _, kwargs = mock.call_args
        self.assertIn('messages', kwargs)
        message = kwargs['messages'][0]
        self.assertEqual(message['role'], AsyncOpenRouterClient.Role.USER)
        prompt = message['content']
        self.assertTrue(prompt)
        return prompt


class CommandBaseTestCase(AssertThinkingPlaceholderMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()

    def setUp(self):
        self.interaction = AsyncMock()
        self.interaction.user.id = self.user.external_id


class PaginatorBaseTestCase(AssertThinkingPlaceholderMixin, TestCase):
    paginator_class: type
    queryset: QuerySet = Assessment.objects.none()

    def setUp(self):
        self.interaction = AsyncMock()

    def get_paginator(self):
        paginator = self.paginator_class(items_queryset=self.queryset.all(), item_count=0)
        paginator.get_embed = AsyncMock()
        return paginator
