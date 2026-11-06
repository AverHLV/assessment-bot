from django.conf import settings

from mcp.shared.auth import InvalidRedirectUriError, InvalidScopeError, OAuthClientInformationFull
from pydantic import AnyUrl

from urllib.parse import SplitResult, urlsplit

LOOPBACK_HOSTS = {'localhost', '127.0.0.1', '::1'}
AUTH_METHODS = ['none', 'client_secret_post', 'client_secret_basic']
CALLBACK_PATH = '/oauth/discord/callback'
MAX_CONTEXT_SIZE = 3600


def parsed_url(value: str) -> SplitResult:
    if not isinstance(value, str) or not value or any(char.isspace() or ord(char) < 32 for char in value):
        raise ValueError('Invalid URL')
    url = urlsplit(value)
    if not url.hostname or url.username is not None or url.password is not None or '#' in value or '\\' in value:
        raise ValueError('Invalid URL')
    if url.port == 0:
        raise ValueError('Invalid port')
    if url.scheme not in {'http', 'https'}:
        raise ValueError('Invalid scheme')
    return url


def redirect_allowed(value: str) -> bool:
    try:
        url = parsed_url(value)
        allowed = {host.strip().lower().strip('[]') for host in settings.MCP_REDIRECT_URI_HOSTS}
        return url.hostname.lower() in allowed and (url.scheme == 'https' or url.hostname.lower() in LOOPBACK_HOSTS)
    except ValueError:
        return False


def public_base_url() -> str:
    value = settings.PUBLIC_BASE_URL.rstrip('/')
    url = parsed_url(value)
    if url.path or url.query or (url.scheme != 'https' and not (settings.DEBUG and url.hostname in LOOPBACK_HOSTS)):
        raise ValueError('Invalid public base URL')
    return value


def configuration_ready() -> bool:
    try:
        public_base_url()
        return bool(
            settings.DISCORD_CLIENT_ID
            and settings.DISCORD_CLIENT_SECRET
            and settings.DISCORD_CLIENT_SECRET not in {'secret', 'key', 'placeholder'}
        )
    except ValueError:
        return False


class RegisteredClient(OAuthClientInformationFull):
    secret_digest: str | None = None
    raw_redirect_uris: list[str] = []

    def validate_redirect_uri(self, redirect_uri: AnyUrl | None) -> AnyUrl:
        selected = super().validate_redirect_uri(redirect_uri)
        if not redirect_allowed(str(selected)):
            raise InvalidRedirectUriError('Redirect URI is not allowed')
        return selected

    def validate_scope(self, requested_scope: str | None) -> list[str]:
        if requested_scope and requested_scope.strip():
            raise InvalidScopeError('Scopes are not supported')
        return []
