from mcp.server.auth.provider import (
    AccessToken,
    AuthorizationCode,
    AuthorizationParams,
    OAuthAuthorizationServerProvider,
    RefreshToken,
    RegistrationError,
    TokenError,
)
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken

import logging
import re

from api.mcp.authorization import begin_authorization
from api.mcp.context import oauth_request
from api.mcp.managers import digest
from api.mcp.models import OAuthClient, OAuthNonce
from api.mcp.tokens import TokenClaims, TokenPurpose, issue, load
from api.mcp.validation import AUTH_METHODS, RegisteredClient, configuration_ready, public_base_url, redirect_allowed
from api.user.models import User

logger = logging.getLogger(__name__)


class RequestAccessToken(AccessToken):
    username: str


class OAuthProvider(OAuthAuthorizationServerProvider[AuthorizationCode, RefreshToken, RequestAccessToken]):
    async def get_client(self, client_id: str) -> RegisteredClient | None:
        cache = oauth_request.get()['clients']
        if client_id not in cache:
            stored = await OAuthClient.objects.filter(client_id=client_id).afirst()
            cache[client_id] = (
                RegisteredClient(
                    client_id=stored.client_id,
                    **stored.metadata,
                    secret_digest=stored.secret_digest,
                    raw_redirect_uris=stored.metadata['redirect_uris'],
                )
                if stored
                else None
            )
        return cache[client_id]

    async def register_client(self, client_info: OAuthClientInformationFull) -> None:
        redirects = oauth_request.get()['redirects']
        if not redirects or not all(redirect_allowed(uri) for uri in redirects):
            logger.info('OAuth registration refused: redirect host policy')
            raise RegistrationError('invalid_redirect_uri', 'Redirect URI is not allowed')
        if (
            client_info.token_endpoint_auth_method not in AUTH_METHODS
            or not set(client_info.grant_types) <= {'authorization_code', 'refresh_token'}
            or client_info.response_types != ['code']
        ):
            raise RegistrationError('invalid_client_metadata', 'Unsupported client metadata')
        metadata = client_info.model_dump(mode='json', exclude={'client_secret', 'client_id'}, exclude_none=True)
        metadata['redirect_uris'] = redirects
        await OAuthClient.objects.acreate(
            client_id=client_info.client_id,
            metadata=metadata,
            secret_digest=digest(client_info.client_secret) if client_info.client_secret else None,
        )

    async def authorize(self, client: OAuthClientInformationFull, params: AuthorizationParams) -> str:
        return await begin_authorization(client, params)

    def bound_grant(
        self, credential: str, purpose: TokenPurpose, client: OAuthClientInformationFull
    ) -> TokenClaims | None:
        payload = load(credential, purpose)
        if payload is None or payload['client_id'] != client.client_id:
            return None
        resource = oauth_request.get().get('resource')
        if resource is not None and resource != payload['resource']:
            oauth_request.get()['grant_error'] = 'invalid_target'
            return None
        return payload

    async def load_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: str
    ) -> AuthorizationCode | None:
        payload = self.bound_grant(authorization_code, 'code', client)
        if payload is None:
            return None
        # Retain raw redirect equality rather than AnyUrl's normalization.
        expected = payload['redirect_uri'] if payload['redirect_uri_provided_explicitly'] else None
        if oauth_request.get().get('redirect_uri') != expected:
            return None
        if not re.fullmatch(r'[A-Za-z0-9._~-]{43,128}', oauth_request.get().get('code_verifier', '')):
            return None
        return AuthorizationCode(
            code=authorization_code,
            expires_at=payload['exp'],
            **{
                key: payload[key]
                for key in (
                    'client_id',
                    'scopes',
                    'code_challenge',
                    'redirect_uri',
                    'redirect_uri_provided_explicitly',
                    'resource',
                    'subject',
                )
            },
        )

    async def exchange_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: AuthorizationCode
    ) -> OAuthToken:
        payload = load(authorization_code.code, 'code')
        if payload is None:
            raise TokenError('invalid_grant', 'Invalid authorization code')
        await self.require_user(payload['subject'])
        if not await OAuthNonce.objects.consume(payload['nonce'], OAuthNonce.Purpose.AUTHORIZATION_CODE):
            logger.info('OAuth grant refused: authorization code already used or unknown')
            raise TokenError('invalid_grant', 'Invalid authorization code')
        return self.issue_tokens(payload)

    async def load_refresh_token(self, client: OAuthClientInformationFull, refresh_token: str) -> RefreshToken | None:
        payload = self.bound_grant(refresh_token, 'refresh', client)
        if payload is None:
            return None
        return RefreshToken(
            token=refresh_token,
            client_id=client.client_id,
            scopes=[],
            expires_at=payload['exp'],
            subject=payload['subject'],
            resource=payload['resource'],
        )

    async def exchange_refresh_token(
        self, client: OAuthClientInformationFull, refresh_token: RefreshToken, scopes: list[str]
    ) -> OAuthToken:
        payload = load(refresh_token.token, 'refresh')
        if payload is None or scopes:
            raise TokenError('invalid_grant', 'Invalid refresh token')
        await self.require_user(payload['subject'])
        return self.issue_tokens(payload, refresh_token.token)

    @staticmethod
    async def require_user(subject: str) -> User:
        user = await User.objects.filter(pk=subject, is_active=True).only('id', 'username').afirst()
        if user is None:
            logger.info('OAuth grant refused: user is missing or inactive')
            raise TokenError('invalid_grant', 'User is unavailable')
        return user

    @staticmethod
    def issue_tokens(payload: TokenClaims, refresh_token: str | None = None) -> OAuthToken:
        claims = {key: payload[key] for key in ('client_id', 'subject', 'resource')}
        return OAuthToken(
            access_token=issue('access', **claims),
            token_type='Bearer',
            expires_in=3600,
            refresh_token=refresh_token or issue('refresh', **claims),
        )

    async def verify_token(self, token: str) -> RequestAccessToken | None:
        if not configuration_ready():
            return None
        payload = load(token, 'access')
        if payload is None or payload['resource'] != f'{public_base_url()}/mcp':
            return None
        user = await User.objects.filter(pk=payload['subject'], is_active=True).only('id', 'username').afirst()
        if user is None:
            return None
        return RequestAccessToken(
            token=token,
            client_id=payload['client_id'],
            subject=payload['subject'],
            scopes=[],
            expires_at=payload['exp'],
            resource=payload['resource'],
            claims={'iss': payload['iss']},
            username=user.username,
        )

    async def load_access_token(self, token: str) -> RequestAccessToken | None:
        return await self.verify_token(token)
