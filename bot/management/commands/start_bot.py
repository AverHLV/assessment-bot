from django.conf import settings
from django.core.management.base import BaseCommand

import uvloop

import asyncio
import logging

from bot.bot import get_assessment_bot

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    requires_migrations_checks = True
    help = 'Start the Discord bot'

    def handle(self, *args, **options):
        asyncio.run(self.handle_async(), debug=settings.DEBUG, loop_factory=uvloop.new_event_loop)

    async def handle_async(self, delay: int = 10) -> None:
        logger.info('Starting the bot...')
        while True:
            try:
                await self.coroutine()
            except Exception as ex:
                logger.exception(f'{type(ex).__name__} error occurred, restart in {delay} seconds')
                await asyncio.sleep(delay)

    @staticmethod
    async def coroutine() -> None:
        async with await get_assessment_bot() as bot:
            await bot.start(settings.BOT_TOKEN)
