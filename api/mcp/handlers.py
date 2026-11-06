from mcp.server.auth.handlers.authorize import AuthorizationHandler
from mcp.server.auth.handlers.register import RegistrationHandler
from mcp.server.auth.handlers.token import TokenErrorResponse, TokenHandler
from mcp.server.auth.provider import construct_redirect_uri
from mcp.server.auth.settings import ClientRegistrationOptions
from mcp.shared.auth import OAuthToken
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse, Response

import json
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from api.mcp.client_auth import HashedClientAuthenticator
from api.mcp.context import oauth_request
from api.mcp.provider import OAuthProvider
from api.mcp.validation import CALLBACK_PATH, public_base_url, redirect_allowed


def oauth_error(error: str = 'invalid_request', status_code: int = 400) -> JSONResponse:
    return JSONResponse(
        {'error': error, 'error_description': 'OAuth request was rejected.'},
        status_code=status_code,
        headers={'Cache-Control': 'no-store', 'Pragma': 'no-cache'},
    )


def sanitize_error(response: Response) -> Response:
    if response.status_code >= 400:
        try:
            error = json.loads(response.body).get('error', 'invalid_request')
        except (ValueError, AttributeError):
            error = 'server_error'
        return oauth_error(error, response.status_code)
    if response.status_code == 302:
        url = urlsplit(response.headers['location'])
        params = parse_qsl(url.query, keep_blank_values=True)
        if any(key == 'error' for key, _ in params):
            params = [
                (key, 'OAuth request was rejected.' if key == 'error_description' else value) for key, value in params
            ]
            response.headers['location'] = urlunsplit(url._replace(query=urlencode(params)))
    return response


class OAuthHandlers:
    def __init__(self, provider: OAuthProvider, options: ClientRegistrationOptions) -> None:
        self.provider = provider
        self.authorization = AuthorizationHandler(provider)
        self.registration = RegistrationHandler(provider, options)
        self.tokens = SafeTokenHandler(provider, HashedClientAuthenticator(provider))

    async def register(self, request: Request) -> Response:
        try:
            body = json.loads(await request.body())
        except (ValueError, UnicodeError):
            return oauth_error('invalid_client_metadata')
        if not isinstance(body, dict):
            return oauth_error('invalid_client_metadata')
        redirects = body.get('redirect_uris')
        if not isinstance(redirects, list) or not redirects or not all(redirect_allowed(uri) for uri in redirects):
            return oauth_error('invalid_redirect_uri')
        oauth_request.get()['redirects'] = redirects
        return sanitize_error(await self.registration.handle(request))

    async def authorize(self, request: Request) -> Response:
        params = request.query_params if request.method == 'GET' else await request.form()
        if any(len(params.getlist(key)) > 1 for key in ('client_id', 'redirect_uri', 'state')):
            return oauth_error()
        client_id = params.get('client_id')
        if not isinstance(client_id, str) or not client_id or len(client_id) > 128:
            return oauth_error()
        client = await self.provider.get_client(client_id)
        if client is None:
            return oauth_error()
        redirect = params.get('redirect_uri')
        if redirect is None and len(client.raw_redirect_uris) == 1:
            redirect = client.raw_redirect_uris[0]
        if redirect not in client.raw_redirect_uris or not redirect_allowed(redirect):
            return oauth_error()
        oauth_request.get()['redirect_uri'] = redirect
        challenge = params.get('code_challenge', '')
        if (
            any(len(params.getlist(key)) != 1 for key in params)
            or params.get('code_challenge_method') != 'S256'
            or not re.fullmatch(r'[A-Za-z0-9_-]{43}', challenge)
        ):
            return RedirectResponse(
                construct_redirect_uri(
                    redirect,
                    error='invalid_request',
                    state=params.get('state'),
                ),
                status_code=302,
                headers={'Cache-Control': 'no-store'},
            )
        response = sanitize_error(await self.authorization.handle(request))
        if cookie := oauth_request.get().get('cookie'):
            response.set_cookie(
                cookie[0],
                cookie[1],
                max_age=600,
                path=CALLBACK_PATH,
                httponly=True,
                secure=public_base_url().startswith('https:'),
                samesite='lax',
            )
        return response

    async def token(self, request: Request) -> Response:
        form = await request.form()
        if any(len(form.getlist(key)) != 1 for key in form):
            return oauth_error()
        oauth_request.get().update(
            resource=form.get('resource'),
            redirect_uri=form.get('redirect_uri'),
            code_verifier=form.get('code_verifier', ''),
        )
        return sanitize_error(await self.tokens.handle(request))


class SafeTokenHandler(TokenHandler):
    def response(self, obj: OAuthToken | TokenErrorResponse) -> Response:
        if isinstance(obj, TokenErrorResponse):
            obj.error = oauth_request.get().get('grant_error', obj.error)
            obj.error_description = 'OAuth grant was rejected.'
        return super().response(obj)
