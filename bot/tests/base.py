from django.contrib.auth import get_user_model
from django.test import TestCase

from asgiref.sync import sync_to_async

from unittest.mock import AsyncMock

from api.llm.clients import AsyncOpenRouterClient
from api.user.tests.factories import UserFactory

User = get_user_model()


class AsyncTestContextManager:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        return


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
        self.assertEqual(message['role'], AsyncOpenRouterClient.OpenRouterRole.USER)
        prompt = message['content']
        self.assertTrue(prompt)
        return prompt


class CommandBaseTestCase(TestCase):
    def setUp(self):
        self.interaction = AsyncMock()

    async def get_auth_user(self) -> User:
        user = await sync_to_async(UserFactory.create)()
        self.interaction.user.id = user.external_id
        return user

    @staticmethod
    def assert_thinking_placeholder(interaction: AsyncMock) -> None:
        expected_message = 'My gears turn, ah - still hot from the past...'
        interaction.response.send_message.assert_called_once_with(expected_message, ephemeral=True)
