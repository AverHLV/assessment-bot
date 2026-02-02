import logging

from bot.bot import bot

logger = logging.getLogger(__name__)


@bot.event
async def on_ready() -> None:
    logger.info(f'Logged in as {bot.user.name}')
