from django.core.asgi import get_asgi_application

from starlette.applications import Starlette
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django_application = get_asgi_application()

# Django must be initialized before importing the OAuth models.
from django.conf import settings  # noqa: E402

from api.mcp import discord_client  # noqa: E402
from api.mcp.routes import auth_routes  # noqa: E402
from api.mcp.server import create_server  # noqa: E402


def create_application() -> Starlette:
    server, provider, mcp_endpoint = create_server()

    @asynccontextmanager
    async def lifespan(app: Starlette) -> AsyncIterator[None]:
        try:
            async with server.session_manager.run():
                yield
        finally:
            await discord_client.close_session()

    return Starlette(
        lifespan=lifespan,
        routes=[
            *auth_routes(provider),
            Route('/mcp', mcp_endpoint, methods=['GET', 'POST', 'DELETE', 'OPTIONS']),
            Mount('/static', StaticFiles(directory=settings.STATIC_ROOT, check_dir=False)),
            Mount('/', django_application),
        ],
    )


application = create_application()
