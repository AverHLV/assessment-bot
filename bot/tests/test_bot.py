from django.test import SimpleTestCase

import discord
from asgiref.sync import async_to_sync

from unittest.mock import AsyncMock, Mock, patch

from bot.bot import AssessmentBot, on_command_error


class AssessmentBotTestCase(SimpleTestCase):
    bot_class = AssessmentBot

    def setUp(self):
        self.bot = self.bot_class(command_prefix='!')
        self.interaction = AsyncMock()
        self.error = discord.app_commands.AppCommandError('error')
        self.on_error_msg = (
            'The ritual failed. My master will have twisted the threads of fate. Try again... if he allows it.'
        )

    @patch('bot.bot.AssessmentBot.tree', new_callable=AsyncMock)
    @async_to_sync
    async def test__assessment_bot__setup_hook(self, tree_mock):
        await self.bot.setup_hook()
        tree_mock.sync.assert_called_once()

    async def test__assessment_bot__on_command_error__response_is_done(self):
        self.interaction.response.is_done = Mock(return_value=True)
        await on_command_error(self.interaction, self.error)

        self.interaction.response.is_done.assert_called_once()
        self.interaction.followup.send.assert_called_once_with(self.on_error_msg, ephemeral=True)

    async def test__assessment_bot__on_command_error__response_is_not_done(self):
        self.interaction.response.is_done = Mock(return_value=False)
        await on_command_error(self.interaction, self.error)

        self.interaction.response.is_done.assert_called_once()
        self.interaction.response.send_message.assert_called_once_with(self.on_error_msg, ephemeral=True)
