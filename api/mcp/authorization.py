from django.conf import settings

from mcp.server.auth.provider import AuthorizationParams, AuthorizeError, construct_redirect_uri
from mcp.shared.auth import OAuthClientInformationFull

from datetime import UTC, datetime
from urllib.parse import urlencode

from api.mcp.context import oauth_request
from api.mcp.managers import digest
from api.mcp.models import OAuthNonce
from api.mcp.tokens import TokenClaims, issue, load
from api.mcp.validation import CALLBACK_PATH, MAX_CONTEXT_SIZE, parsed_url, public_base_url

DISCORD_AUTHORIZE_URL = 'https://discord.com/oauth2/authorize'


def cookie_name(state: str) -> str:
    return f'mcp_oauth_{digest(state)}'


async def begin_authorization(client: OAuthClientInformationFull, params: AuthorizationParams) -> str:
    resource = params.resource if params.resource is not None else f'{public_base_url()}/mcp'
    try:
        parsed_url(resource)
    except ValueError:
        raise AuthorizeError('invalid_target', 'Invalid resource') from None
    claims = params.model_dump(mode='json', exclude={'resource'})
    claims['redirect_uri'] = oauth_request.get()['redirect_uri']
    signed = issue('pending', client_id=client.client_id, **claims, resource=resource)
    if len(signed) > MAX_CONTEXT_SIZE:
        raise AuthorizeError('invalid_request', 'Authorization context is too large')
    payload = load(signed, 'pending')
    state = payload['nonce']
    await OAuthNonce.objects.acreate(
        digest=digest(state),
        purpose=OAuthNonce.Purpose.DISCORD_STATE,
        expires_at=datetime.fromtimestamp(payload['exp'], UTC),
    )
    oauth_request.get()['cookie'] = (cookie_name(state), signed)
    return (
        DISCORD_AUTHORIZE_URL
        + '?'
        + urlencode(
            {
                'client_id': settings.DISCORD_CLIENT_ID,
                'redirect_uri': public_base_url() + CALLBACK_PATH,
                'response_type': 'code',
                'scope': 'identify',
                'state': state,
            }
        )
    )


async def issue_code(pending: TokenClaims, user_id: int) -> str:
    claims = {
        key: pending[key]
        for key in (
            'client_id',
            'redirect_uri',
            'redirect_uri_provided_explicitly',
            'code_challenge',
            'resource',
            'state',
        )
    }
    code = issue('code', **claims, subject=str(user_id))
    payload = load(code, 'code')
    await OAuthNonce.objects.acreate(
        digest=digest(payload['nonce']),
        purpose=OAuthNonce.Purpose.AUTHORIZATION_CODE,
        expires_at=datetime.fromtimestamp(payload['exp'], UTC),
    )
    return construct_redirect_uri(pending['redirect_uri'], code=code, state=pending['state'])
