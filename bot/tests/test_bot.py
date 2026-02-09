from django.test import SimpleTestCase

import discord
from asgiref.sync import async_to_sync

from unittest.mock import AsyncMock, patch

from bot.bot import AssessmentBot, on_command_error


class AssessmentBotTestCase(SimpleTestCase):
    bot_class = AssessmentBot

    def setUp(self):
        self.bot = self.bot_class(command_prefix='!')
        self.interaction = AsyncMock()
        self.error = discord.app_commands.AppCommandError('error')

    @patch('bot.bot.AssessmentBot.tree', new_callable=AsyncMock)
    @async_to_sync
    async def test__assessment_bot__setup_hook(self, tree_mock):
        await self.bot.setup_hook()
        tree_mock.sync.assert_called_once()

    async def test__assessment_bot__on_error(self):
        event_method = self.bot.EventMethod.ON_MESSAGE
        await self.bot.on_error(event_method, self.interaction)
        self.interaction.reply.assert_called_once_with(self.bot.error_message)

    async def test__assessment_bot__on_command_error(self):
        await on_command_error(self.interaction, self.error)
        self.interaction.edit_original_response.assert_called_once_with(
            content=self.bot.error_message,
            embed=None,
            view=None,
        )
