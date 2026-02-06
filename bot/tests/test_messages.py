from django.contrib.auth import get_user_model

from asgiref.sync import async_to_sync, sync_to_async

from unittest.mock import AsyncMock, Mock, patch

from api.assessment.tests.factories import AssessmentFactory
from api.llm.clients import AsyncOpenRouterClient
from bot import messages
from bot.bot import bot
from bot.tests.base import CommandBaseTestCase

User = get_user_model()


class AsyncTestContextManager:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        return


class MessagesTestCase(CommandBaseTestCase):
    def setUp(self):
        super().setUp()

        self.message = self.interaction
        self.message.author.bot = False
        self.message.mentions = [bot.user]
        self.message.content = 'message content'

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

    async def get_auth_user(self) -> User:
        user = await super().get_auth_user()
        self.message.author.id = user.external_id
        return user

    @patch('bot.messages.openrouter_client.create_completion')
    @async_to_sync
    async def test__on_message(self, completion_mock):
        typing_manager_mock = AsyncMock(spec=AsyncTestContextManager())
        self.message.channel.typing = Mock(return_value=typing_manager_mock)
        completion_mock.return_value = self.response_data

        user = await self.get_auth_user()
        assessment, _ = await sync_to_async(AssessmentFactory.create_batch)(size=2, user=user)

        await messages.on_message(self.message)

        completion_mock.assert_called_once()
        _, kwargs = completion_mock.call_args
        message = kwargs['messages'][0]
        self.assertEqual(message['role'], AsyncOpenRouterClient.OpenRouterRole.USER)
        prompt = message['content']
        self.assertIn(user.username, prompt)
        self.assertIn(str(assessment.mark), prompt)
        self.assertIn(assessment.media.name, prompt)
        self.assertIn(assessment.media.category.name, prompt)
        self.assertIn(self.message.content, prompt)

        self.message.channel.typing.assert_called_once()
        self.message.reply.assert_called_once_with(self.response_content)

    async def test__on_message__not_mentioned(self):
        self.message.mentions = []
        await messages.on_message(self.message)
        self.message.channel.typing.assert_not_called()
