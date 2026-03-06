from django.test import SimpleTestCase

import discord
from asgiref.sync import async_to_sync

from unittest.mock import AsyncMock, patch

from bot.bot import AssessmentBot, get_assessment_bot, on_command_error


class AssessmentBotTestCase(SimpleTestCase):
    def setUp(self):
        self.interaction = AsyncMock()
        self.error = discord.app_commands.AppCommandError('error')

    @staticmethod
    async def get_bot() -> AssessmentBot:
        return await get_assessment_bot()

    @patch('bot.bot.AssessmentBot.tree')
    @async_to_sync
    async def test__assessment_bot__setup_hook(self, tree_mock):
        tree_mock.sync = AsyncMock()
        bot = await self.get_bot()

        await bot.setup_hook()

        tree_mock.sync.assert_called_once()

    async def test__assessment_bot__on_error(self):
        bot = await self.get_bot()
        event_method = bot.EventMethod.ON_MESSAGE

        await bot.on_error(event_method, self.interaction)

        self.interaction.reply.assert_called_once_with(bot.error_message)

    async def test__assessment_bot__on_command_error(self):
        bot = await self.get_bot()
        await on_command_error(self.interaction, self.error)
        self.interaction.edit_original_response.assert_called_once_with(
            content=bot.error_message,
            embed=None,
            view=None,
        )

    async def test__assessment_bot__on_command_error__cooldown(self):
        bot = await self.get_bot()
        self.error = discord.app_commands.CommandOnCooldown(cooldown=AsyncMock(), retry_after=5)

        await on_command_error(self.interaction, self.error)

        expected_message = bot.error_cooldown_message.format(retry=self.error.retry_after)
        self.interaction.response.send_message.assert_called_once_with(expected_message, ephemeral=True)
