from django.conf import settings
from django.core.management import call_command
from django.test import TestCase

from asgiref.sync import async_to_sync

from unittest.mock import AsyncMock, patch

from bot.management.commands.start_bot import Command as StartBotCommand


class ExitFromCommand(BaseException):
    """Exception for exiting command loop."""

    pass


class StartBotTestCase(TestCase):
    command = StartBotCommand

    @patch('bot.management.commands.start_bot.get_assessment_bot', new_callable=AsyncMock)
    @async_to_sync
    async def test__start_bot(self, bot_mock):
        bot_mock.return_value.__aenter__.return_value.start.side_effect = ExitFromCommand

        with self.assertRaises(ExitFromCommand):
            await self.command().handle_async()

        bot_mock.return_value.__aenter__.return_value.start.assert_called_once_with(settings.BOT_TOKEN)

    @patch('asyncio.sleep', new_callable=AsyncMock)
    @patch('bot.management.commands.start_bot.get_assessment_bot', new_callable=AsyncMock)
    @async_to_sync
    async def test__start_bot__restart(self, bot_mock, sleep_mock):
        bot_mock.return_value.__aenter__.return_value.start.side_effect = ValueError('error'), ExitFromCommand

        with self.assertRaises(ExitFromCommand):
            await self.command().handle_async()

        self.assertEqual(bot_mock.return_value.__aenter__.return_value.start.call_count, 2)
        sleep_mock.assert_called_once()

    def test__start_bot__command(self):
        with patch.object(self.command, 'handle_async', new_callable=AsyncMock) as mock:
            call_command('start_bot')
        mock.assert_called_once()
