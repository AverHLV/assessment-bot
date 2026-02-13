from asgiref.sync import async_to_sync, sync_to_async

from unittest.mock import AsyncMock, Mock, patch

from api.assessment.tests.factories import AssessmentFactory
from bot import messages
from bot.bot import bot
from bot.tests.base import AsyncTestContextManager, CommandBaseTestCase, LLMClientTestMixin


class MessagesTestCase(LLMClientTestMixin, CommandBaseTestCase):
    def setUp(self):
        super().setUp()

        self.message = self.interaction
        self.message.author.id = self.user.external_id
        self.message.author.bot = False
        self.message.mentions = [bot.user]
        self.message.content = 'message content'

    @patch('bot.messages.openrouter_client.create_completion')
    @async_to_sync
    async def test__on_message(self, completion_mock):
        typing_manager_mock = AsyncMock(spec=AsyncTestContextManager())
        self.message.channel.typing = Mock(return_value=typing_manager_mock)
        completion_mock.return_value = self.response_data

        assessment, _ = await sync_to_async(AssessmentFactory.create_batch)(size=2, user=self.user)

        await messages.on_message(self.message)

        prompt = self.assert_llm_completion_mock(completion_mock)
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
