from mcp.server.auth.handlers.metadata import MetadataHandler
from mcp.server.auth.routes import build_metadata, cors_middleware, create_protected_resource_routes
from mcp.server.auth.settings import ClientRegistrationOptions, RevocationOptions
from mcp.server.transport_security import RequestBodyLimitMiddleware
from pydantic import AnyHttpUrl, TypeAdapter, UrlConstraints
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Route, request_response
from starlette.types import ASGIApp

from collections.abc import Awaitable, Callable
from typing import Annotated

from api.mcp.callback import discord_callback
from api.mcp.context import oauth_request
from api.mcp.handlers import OAuthHandlers, oauth_error
from api.mcp.provider import OAuthProvider
from api.mcp.validation import AUTH_METHODS, CALLBACK_PATH, configuration_ready, public_base_url

MAX_OAUTH_BODY_SIZE = 16384
type OAuthHandler = Callable[[Request], Awaitable[Response]]


def guarded(handler: OAuthHandler) -> OAuthHandler:
    async def handle(request: Request) -> Response:
        context = oauth_request.set({'clients': {}})
        try:
            if not configuration_ready():
                return oauth_error('server_error', 503)
            if len(request.scope.get('query_string', b'')) > MAX_OAUTH_BODY_SIZE:
                return oauth_error()
            return await handler(request)
        finally:
            oauth_request.reset(context)

    return handle


def oauth_route(path: str, handler: OAuthHandler, methods: list[str], cors: bool = False) -> Route:
    endpoint: ASGIApp = RequestBodyLimitMiddleware(request_response(guarded(handler)), MAX_OAUTH_BODY_SIZE)
    if cors:
        endpoint = CORSMiddleware(
            endpoint,
            allow_origins=['*'],
            allow_methods=methods,
            allow_headers=['Authorization', 'Content-Type', 'MCP-Protocol-Version'],
        )
        methods = [*methods, 'OPTIONS']
    return Route(path, endpoint, methods=methods)


def auth_routes(provider: OAuthProvider) -> list[Route]:
    options = ClientRegistrationOptions(enabled=True, valid_scopes=[], default_scopes=[])
    handlers = OAuthHandlers(provider, options)
    routes = [
        oauth_route('/register', handlers.register, ['POST'], cors=True),
        oauth_route('/authorize', handlers.authorize, ['GET', 'POST']),
        oauth_route('/token', handlers.token, ['POST'], cors=True),
        oauth_route(CALLBACK_PATH, discord_callback, ['GET']),
    ]
    try:
        base = public_base_url()
    except ValueError:

        async def unavailable(request: Request) -> Response:
            return oauth_error('server_error', 503)

        for path in ('/.well-known/oauth-authorization-server', '/.well-known/oauth-protected-resource/mcp'):
            routes.append(oauth_route(path, unavailable, ['GET'], cors=True))
        return routes
    issuer = TypeAdapter(Annotated[AnyHttpUrl, UrlConstraints(preserve_empty_path=True)]).validate_python(base)
    metadata = build_metadata(issuer, None, options, RevocationOptions(enabled=False))
    metadata.token_endpoint_auth_methods_supported = AUTH_METHODS
    metadata.client_id_metadata_document_supported = False
    routes.insert(
        0,
        Route(
            '/.well-known/oauth-authorization-server',
            cors_middleware(guarded(MetadataHandler(metadata).handle), ['GET', 'OPTIONS']),
            methods=['GET', 'OPTIONS'],
        ),
    )
    routes[1:1] = create_protected_resource_routes(AnyHttpUrl(base + '/mcp'), [issuer], scopes_supported=[])
    return routes
