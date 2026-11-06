from django.conf import settings

from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.settings import AuthSettings
from mcp.server.mcpserver import MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from starlette.middleware.cors import CORSMiddleware

from typing import cast
from urllib.parse import urlsplit

from api.mcp.provider import OAuthProvider, RequestAccessToken
from api.mcp.validation import public_base_url


def create_server() -> tuple[MCPServer, OAuthProvider, CORSMiddleware]:
    provider = OAuthProvider()
    try:
        base = public_base_url()
    except ValueError:
        # A syntactically valid SDK configuration; verification still fails closed.
        base = 'https://unconfigured.invalid'
    server = MCPServer(
        'Assessment bot',
        token_verifier=provider,
        auth=AuthSettings(
            issuer_url=base,
            resource_server_url=base + '/mcp',
            validate_token_resource=True,
            required_scopes=[],
        ),
    )

    @server.tool()
    async def hello() -> str:
        """Greet the authenticated Discord bot user."""

        token = cast(RequestAccessToken, get_access_token())
        return f'Hello, {token.username}!'

    hosts = [urlsplit(base).netloc]
    origins = [
        base,
        *[
            f'https://{host}'
            for host in settings.MCP_REDIRECT_URI_HOSTS
            if host
            not in {
                'localhost',
                '127.0.0.1',
                '::1',
                '[::1]',
            }
        ],
    ]
    if settings.DEBUG:
        hosts += ['localhost:*', '127.0.0.1:*', '[::1]:*']
        port = settings.MCP_INSPECTOR_PORT
        origins += [f'http://{host}:{port}' for host in ('localhost', '127.0.0.1', '[::1]')]
    app = server.streamable_http_app(
        streamable_http_path='/mcp',
        stateless_http=True,
        json_response=True,
        transport_security=TransportSecuritySettings(allowed_hosts=hosts, allowed_origins=origins),
    )
    cors = CORSMiddleware(
        app,
        allow_origins=['*'],
        allow_methods=['GET', 'POST', 'DELETE', 'OPTIONS'],
        allow_headers=['Authorization', 'Content-Type', 'MCP-Protocol-Version', 'Mcp-Session-Id', 'Last-Event-ID'],
        expose_headers=['WWW-Authenticate', 'Mcp-Session-Id', 'MCP-Protocol-Version'],
    )

    return server, provider, cors
