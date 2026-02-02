from django.conf import settings
from django.core.management import call_command
from django.test import TestCase, override_settings

from asgiref.sync import async_to_sync

from unittest.mock import AsyncMock, patch

from bot.management.commands.start_bot import Command as AssessmentBotCommand


class ExitFromCommand(BaseException):
    """Exception for exiting command loop."""

    pass


class AssessmentBotTestCase(TestCase):
    def test__assessment_bot__command(self):
        with patch.object(AssessmentBotCommand, 'handle_async', new_callable=AsyncMock) as mock:
            call_command('start_bot')
        mock.assert_called_once()

    @patch('bot.management.commands.start_bot.bot', new_callable=AsyncMock)
    @async_to_sync
    async def test__assessment_bot(self, bot_mock):
        bot_mock.start.side_effect = ExitFromCommand

        with self.assertRaises(ExitFromCommand):
            await AssessmentBotCommand().handle_async()

        bot_mock.start.assert_called_once_with(settings.BOT_TOKEN)

    @patch('asyncio.sleep', new_callable=AsyncMock)
    @patch('bot.management.commands.start_bot.bot', new_callable=AsyncMock)
    @async_to_sync
    async def test__assessment_bot__restart(self, bot_mock, sleep_mock):
        bot_mock.start.side_effect = ValueError('error'), ExitFromCommand

        with self.assertRaises(ExitFromCommand):
            await AssessmentBotCommand().handle_async()

        self.assertEqual(bot_mock.start.call_count, 2)
        sleep_mock.assert_called_once()

    @patch('asyncio.sleep', new_callable=AsyncMock)
    @patch('bot.management.commands.start_bot.bot', new_callable=AsyncMock)
    @async_to_sync
    async def test__assessment_bot__idle(self, bot_mock, sleep_mock):
        sleep_mock.side_effect = ExitFromCommand

        with (
            override_settings(FEATURE_BOT_IDLE=True),
            self.assertRaises(ExitFromCommand),
        ):
            await AssessmentBotCommand().handle_async()

        sleep_mock.assert_called_once()
        bot_mock.start.assert_not_called()
