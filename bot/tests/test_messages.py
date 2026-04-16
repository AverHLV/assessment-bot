from django.utils import timezone

from asgiref.sync import async_to_sync, sync_to_async

from datetime import timedelta
from unittest.mock import Mock, patch

from api.assessment.tests.factories import AssessmentFactory
from api.llm.clients import AsyncOpenRouterClient
from bot import messages
from bot.tests.base import CogWithCommandsBaseTestCase, get_async_context_manager_mock, get_async_iterator_mock


class MessageCogTestCase(CogWithCommandsBaseTestCase):
    cog_class = messages.MessageCog

    def setUp(self):
        super().setUp()

        self.message = self.interaction
        self.message.author.id = self.user.external_id
        self.message.author.bot = False
        self.message.mentions = [self.bot.user]
        self.message.content = 'message content'

        self.message_history = []
        current_time = timezone.now()
        message_created_ats = [
            current_time - timedelta(minutes=1),
            current_time - timedelta(hours=1),
            current_time - timedelta(days=1),
        ]
        for n, created_at in enumerate(message_created_ats):
            previous_message = Mock()
            previous_message.author.name = f'Name#{n}'
            previous_message.content = f'Content#{n}'
            previous_message.created_at = created_at
            self.message_history.append(previous_message)

    @patch('bot.messages.run_create_completion')
    @patch('bot.cog.BaseCog.close_old_db_connections')
    @async_to_sync
    async def test__message_cog__on_message(self, close_mock, completion_mock):
        self.message.channel.typing = get_async_context_manager_mock()
        self.message.channel.history = get_async_iterator_mock(self.message_history)
        completion_mock.return_value = 'response content'

        assessment, _ = await sync_to_async(AssessmentFactory.create_batch)(size=2, user=self.user)

        await self.cog.on_message(self.message)

        close_mock.assert_called_once()
        completion_mock.assert_called_once()
        args, _ = completion_mock.call_args
        openrouter_client, prompt = args
        self.assertIsInstance(openrouter_client, AsyncOpenRouterClient)
        self.assertIn(str(assessment.mark), prompt)
        self.assertIn(assessment.media.name, prompt)
        self.assertIn(assessment.media.category.name, prompt)
        self.assertIn(self.user.username, prompt)
        self.assertIn(self.message.content, prompt)
        previous_message = self.message_history[0]
        self.assertIn(previous_message.author.name, prompt)
        self.assertIn(previous_message.content, prompt)
        self.assertNotIn(self.message_history[-1].content, prompt)

        self.message.channel.typing.assert_called_once()
        self.message.channel.history.assert_called_once_with(limit=5, before=self.message)
        self.message.reply.assert_called_once_with(completion_mock.return_value)

    @patch('bot.cog.BaseCog.close_old_db_connections')
    @async_to_sync
    async def test__message_cog__on_message__not_mentioned(self, close_mock):
        self.message.mentions = []

        await self.cog.on_message(self.message)

        close_mock.assert_not_called()
        self.message.channel.typing.assert_not_called()
