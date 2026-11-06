from django.core.signals import request_finished, request_started
from django.db import close_old_connections
from django.test import TestCase, override_settings

from asgiref.sync import async_to_sync
from httpx2 import ASGITransport, AsyncClient, Cookies

import base64
import hashlib
from unittest.mock import AsyncMock, patch
from urllib.parse import parse_qs, urlsplit

from api.mcp.models import OAuthNonce
from api.mcp.tokens import issue
from api.user.tests.factories import UserFactory
from core.asgi import create_application

BASE_URL = 'http://127.0.0.1:8000'
REDIRECT = 'http://localhost:6274/callback?existing=kept'
VERIFIER = 'v' * 64
CHALLENGE = base64.urlsafe_b64encode(hashlib.sha256(VERIFIER.encode()).digest()).decode().rstrip('=')
OAUTH_SETTINGS = {
    'PUBLIC_BASE_URL': BASE_URL,
    'DEBUG': True,
    'DISCORD_CLIENT_ID': 'discord-test-client',
    'DISCORD_CLIENT_SECRET': 'discord-test-secret',
    'SECRET_KEY': 'private-test-signing-key',
    'MCP_REDIRECT_URI_HOSTS': ['claude.ai', 'claude.com', 'chatgpt.com', 'grok.com', 'localhost', '127.0.0.1', '::1'],
}


@override_settings(**OAUTH_SETTINGS)
class OAuthTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()

    def setUp(self):
        self.app = create_application()
        self.cookies = Cookies()

    def request(self, method, path, queries, **kwargs):
        async def send():
            async with AsyncClient(
                transport=ASGITransport(self.app), base_url=BASE_URL, cookies=self.cookies
            ) as client:
                response = await client.request(method, path, **kwargs)
                self.cookies = client.cookies
                return response

        # Match Django's test client: ASGI request cleanup must not close TestCase's transaction.
        request_started.disconnect(close_old_connections)
        request_finished.disconnect(close_old_connections)
        try:
            with self.assertNumQueries(queries):
                return async_to_sync(send)()
        finally:
            request_started.connect(close_old_connections)
            request_finished.connect(close_old_connections)

    def register(self, method='none', redirect=REDIRECT):
        response = self.request(
            'POST',
            '/register',
            1,
            json={
                'redirect_uris': [redirect],
                'token_endpoint_auth_method': method,
                'grant_types': ['authorization_code', 'refresh_token'],
                'response_types': ['code'],
            },
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def authorize(self, client, **params):
        response = self.request(
            'GET',
            '/authorize',
            2,
            params={
                'client_id': client['client_id'],
                'redirect_uri': REDIRECT,
                'response_type': 'code',
                'code_challenge': CHALLENGE,
                'code_challenge_method': 'S256',
                'state': 'original-client-state',
                **params,
            },
        )
        self.assertEqual(response.status_code, 302, response.text)
        location = urlsplit(response.headers['location'])
        self.assertEqual(location.netloc, 'discord.com')
        query = parse_qs(location.query)
        self.assertEqual(query['scope'], ['identify'])
        self.assertEqual(query['redirect_uri'], [BASE_URL + '/oauth/discord/callback'])
        return query['state'][0]

    def callback(self, state, external_id=None, queries=3, **params):
        identify = AsyncMock(return_value=external_id if external_id is not None else self.user.external_id)
        with patch('api.mcp.callback.discord_client.identify', identify):
            response = self.request(
                'GET',
                '/oauth/discord/callback',
                queries,
                params={'state': state, 'code': 'discord-code-sentinel', **params},
            )
        return response, identify

    def code(self, client=None, **params):
        client = client or self.register()
        state = self.authorize(client, **params)
        response, identify = self.callback(state)
        self.assertEqual(response.status_code, 302, response.text)
        query = parse_qs(urlsplit(response.headers['location']).query)
        self.assertEqual(query['state'], ['original-client-state'])
        self.assertEqual(query['existing'], ['kept'])
        identify.assert_awaited_once_with('discord-code-sentinel')
        return client, query['code'][0]

    def exchange(self, client, code, queries=3, **params):
        return self.request(
            'POST',
            '/token',
            queries,
            data={
                'client_id': client['client_id'],
                'grant_type': 'authorization_code',
                'code': code,
                'redirect_uri': REDIRECT,
                'code_verifier': VERIFIER,
                **params,
            },
        )

    def tokens(self):
        client, code = self.code()
        response = self.exchange(client, code)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['expires_in'], 3600)
        return client, response.json()

    def refresh(self, client, token, queries=2, **params):
        return self.request(
            'POST',
            '/token',
            queries,
            data={
                'client_id': client['client_id'],
                'grant_type': 'refresh_token',
                'refresh_token': token,
                **params,
            },
        )

    def mcp(self, token=None, queries=0, **headers):
        if token:
            headers['Authorization'] = f'Bearer {token}'
        # Authentication precedes protocol handling; no hello listing or invocation.
        return self.request('POST', '/mcp', queries, json={}, headers=headers)

    def assert_oauth_error(self, response, error, status=400):
        self.assertEqual(response.status_code, status, response.text)
        self.assertEqual(response.json()['error'], error)

    def assert_unauthorized(self, response):
        self.assertEqual(response.status_code, 401, response.text)
        self.assertIn('Bearer', response.headers['www-authenticate'])
        self.assertIn(BASE_URL + '/.well-known/oauth-protected-resource/mcp', response.headers['www-authenticate'])

    def nonce(self, purpose):
        return OAuthNonce.objects.get(purpose=purpose)

    def access(self, **claims):
        return issue('access', client_id='test-client', subject=str(self.user.pk), resource=BASE_URL + '/mcp', **claims)
