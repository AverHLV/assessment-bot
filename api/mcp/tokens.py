from django.conf import settings
from django.core import signing

import secrets
import time
from typing import Any, Literal

from api.mcp.validation import parsed_url, public_base_url

type TokenPurpose = Literal['pending', 'code', 'access', 'refresh']
type TokenClaims = dict[str, Any]

LIFETIMES: dict[TokenPurpose, int] = {'pending': 600, 'code': 600, 'access': 3600, 'refresh': 2592000}
MAX_CREDENTIAL_SIZE = 8192


def signer(purpose: TokenPurpose) -> signing.TimestampSigner:
    return signing.TimestampSigner(key=settings.SECRET_KEY, salt=f'mcp.oauth.{purpose}.v1', fallback_keys=[])


def issue(purpose: TokenPurpose, **claims: Any) -> str:
    now = int(time.time())
    payload = {
        **claims,
        'purpose': purpose,
        'version': 1,
        'iss': public_base_url(),
        'iat': now,
        'exp': now + LIFETIMES[purpose],
        'nonce': secrets.token_urlsafe(32),
        'scopes': [],
    }
    return signer(purpose).sign_object(payload)


def load(value: str, purpose: TokenPurpose) -> TokenClaims | None:
    if not isinstance(value, str) or len(value) > MAX_CREDENTIAL_SIZE:
        return None
    try:
        payload = signer(purpose).unsign_object(value, max_age=LIFETIMES[purpose])
        now = time.time()
        if (
            not isinstance(payload, dict)
            or payload.get('purpose') != purpose
            or payload.get('version') != 1
            or payload.get('iss') != public_base_url()
            or type(payload.get('iat')) is not int
            or type(payload.get('exp')) is not int
            or not payload['iat'] <= now < payload['exp']
            or payload['exp'] - payload['iat'] != LIFETIMES[purpose]
            or payload.get('scopes') != []
            or not all(isinstance(payload.get(key), str) and payload[key] for key in ('nonce', 'client_id', 'resource'))
        ):
            return None
        parsed_url(payload['resource'])
        if purpose != 'pending':
            subject = payload.get('subject')
            if (
                not isinstance(subject, str)
                or not subject.isascii()
                or not subject.isdecimal()
                or not 0 < int(subject) < 2**63
            ):
                return None
        if purpose in {'pending', 'code'}:
            parsed_url(payload['redirect_uri'])
            if (
                type(payload.get('redirect_uri_provided_explicitly')) is not bool
                or not isinstance(payload.get('code_challenge'), str)
                or not isinstance(payload.get('state'), str | type(None))
            ):
                return None
        return payload
    except (signing.BadSignature, ValueError, TypeError, KeyError, UnicodeError):
        return None
