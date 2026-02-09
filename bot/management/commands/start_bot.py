from django.conf import settings
from django.core.management.base import BaseCommand

import uvloop

import asyncio
import logging

from bot.bot import bot

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    requires_migrations_checks = True
    help = 'Start the Discord bot'

    def handle(self, *args, **options):
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
        asyncio.run(self.handle_async(), debug=settings.DEBUG)

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
        async with bot:
            await bot.start(settings.BOT_TOKEN)
