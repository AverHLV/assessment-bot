from mcp.server.auth.provider import construct_redirect_uri
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse, Response

import logging
import re

from api.mcp import discord_client
from api.mcp.authorization import cookie_name, issue_code
from api.mcp.models import OAuthNonce
from api.mcp.tokens import TokenClaims, load
from api.mcp.validation import CALLBACK_PATH, MAX_CONTEXT_SIZE
from api.user.models import User

logger = logging.getLogger(__name__)


def error_page(message: str, status_code: int = 400) -> HTMLResponse:
    # Messages are fixed application text, never provider responses or request values.
    return HTMLResponse(
        f'<!doctype html><title>Connection failed</title><p>{message}</p>',
        status_code=status_code,
        headers={'Cache-Control': 'no-store', 'Referrer-Policy': 'no-referrer'},
    )


async def discord_callback(request: Request) -> Response:
    state = request.query_params.get('state', '')
    if not re.fullmatch(r'[A-Za-z0-9_-]{43}', state):
        return error_page('Invalid or expired Discord sign-in. Please start again.')
    name = cookie_name(state)
    cookie = request.cookies.get(name, '')
    pending = load(cookie, 'pending') if len(cookie) <= MAX_CONTEXT_SIZE else None
    response = error_page('Invalid or expired Discord sign-in. Please start again.')
    if (
        pending is not None
        and pending['nonce'] == state
        and await OAuthNonce.objects.consume(state, OAuthNonce.Purpose.DISCORD_STATE)
    ):
        response = await complete_callback(request, pending)
    response.delete_cookie(name, path=CALLBACK_PATH)
    return response


async def complete_callback(request: Request, pending: TokenClaims) -> Response:
    if request.query_params.get('error') == 'access_denied':
        return RedirectResponse(
            construct_redirect_uri(
                pending['redirect_uri'],
                error='access_denied',
                state=pending['state'],
            ),
            status_code=302,
            headers={'Cache-Control': 'no-store', 'Referrer-Policy': 'no-referrer'},
        )
    code = request.query_params.get('code')
    if not code or len(code) > MAX_CONTEXT_SIZE or request.query_params.get('error'):
        return error_page('Discord sign-in failed. Please start again.')
    try:
        external_id = await discord_client.identify(code)
    except Exception as exc:
        logger.exception(f'Discord OAuth exchange failed: {exc}')
        return error_page('Discord is unavailable or sign-in failed. Please start again.', 502)
    user = await User.objects.filter(external_id=external_id, is_active=True).only('id', 'username').afirst()
    if user is None:
        logger.info(
            'OAuth sign-in refused: use the Discord bot first', extra={'fields': {'client_id': pending['client_id']}}
        )
        return error_page('Please use the Discord bot first, then try connecting again.', 403)
    return RedirectResponse(
        await issue_code(pending, user.pk),
        status_code=302,
        headers={'Cache-Control': 'no-store', 'Referrer-Policy': 'no-referrer'},
    )
