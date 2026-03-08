from django.conf import settings
from django.core.management.base import BaseCommand

import httpx

import logging
from contextlib import suppress

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    requires_migrations_checks = False
    requires_system_checks = ()
    help = 'Wake up the Discord bot with an HTTP request'

    def handle(self, *args, **options):
        logger.info('Performing wake-up request...')
        with suppress(httpx.HTTPError):
            httpx.get(f'{settings.EXTERNAL_URL}/liveness/', timeout=10)
        logger.info('Wake-up request performed successfully')
