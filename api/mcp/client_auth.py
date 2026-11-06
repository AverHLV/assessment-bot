from mcp.server.auth.middleware.client_auth import AuthenticationError
from starlette.datastructures import FormData
from starlette.requests import Request

import base64
import binascii
import hmac
import time
from urllib.parse import unquote_plus

from api.mcp.managers import digest
from api.mcp.provider import OAuthProvider
from api.mcp.validation import RegisteredClient


class HashedClientAuthenticator:
    def __init__(self, provider: OAuthProvider) -> None:
        self.provider = provider

    async def authenticate_request(self, request: Request) -> RegisteredClient:
        form = await request.form()
        client_id = form.get('client_id')
        secret = form.get('client_secret')
        method = 'client_secret_post' if secret is not None else 'none'
        header = request.headers.get('Authorization')
        if header:
            try:
                scheme, encoded = header.split(' ', 1)
                if scheme.lower() != 'basic' or secret is not None:
                    raise ValueError
                basic_id, secret = base64.b64decode(encoded, validate=True).decode().split(':', 1)
                basic_id, secret = unquote_plus(basic_id), unquote_plus(secret)
                if client_id is not None and client_id != basic_id:
                    raise ValueError
                client_id, method = basic_id, 'client_secret_basic'
            except (ValueError, binascii.Error, UnicodeError):
                raise AuthenticationError('Invalid client credentials') from None
        if not isinstance(client_id, str) or not client_id or len(client_id) > 128:
            raise AuthenticationError('Invalid client credentials')
        client = await self.provider.get_client(client_id)
        if client is None or client.token_endpoint_auth_method != method:
            raise AuthenticationError('Invalid client credentials')
        if method != 'none' and (
            not isinstance(secret, str)
            or not client.secret_digest
            or not hmac.compare_digest(digest(secret), client.secret_digest)
            or (client.client_secret_expires_at and client.client_secret_expires_at <= time.time())
        ):
            raise AuthenticationError('Invalid client credentials')
        request._form = FormData({**dict(form), 'client_id': client_id})
        return client
