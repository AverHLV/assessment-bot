from django.test import override_settings

from asgiref.sync import async_to_sync
from httpx2 import ASGITransport, AsyncClient

import time
from unittest.mock import patch

from api.mcp.tests.base import BASE_URL, OAuthTestCase
from api.mcp.tokens import issue, load
from api.user.models import User


class AuthenticationTestCase(OAuthTestCase):
    def test__mcp__errors__missing_and_invalid_tokens(self):
        for token in (
            None,
            'invalid',
            self.access() + 'tampered',
            issue(
                'refresh',
                client_id='test-client',
                subject=str(self.user.pk),
                resource=BASE_URL + '/mcp',
            ),
        ):
            with self.subTest(token=token and token[:12]):
                self.assert_unauthorized(self.mcp(token))

    def test__mcp__errors__expired_token(self):
        token = self.access()
        with patch('api.mcp.tokens.time.time', return_value=time.time() + 3600):
            self.assert_unauthorized(self.mcp(token))

    def test__mcp__errors__inactive_or_deleted_owner(self):
        token = self.access()
        User.objects.filter(pk=self.user.pk).update(is_active=False)
        self.assert_unauthorized(self.mcp(token, queries=1))
        User.objects.filter(pk=self.user.pk).delete()
        self.assert_unauthorized(self.mcp(token, queries=1))

    def test__mcp__errors__wrong_resource_or_issuer(self):
        token = issue('access', client_id='test-client', subject=str(self.user.pk), resource=BASE_URL + '/mcp/')
        self.assert_unauthorized(self.mcp(token))
        with override_settings(PUBLIC_BASE_URL='https://other.example'):
            token = self.access()
        self.assert_unauthorized(self.mcp(token))

    def test__mcp__accepted_initialization_with_refreshed_token(self):
        owner, original = self.tokens()

        refreshed = self.refresh(owner, original['refresh_token'])

        self.assertEqual(refreshed.status_code, 200, refreshed.text)
        token = refreshed.json()['access_token']
        self.assertNotEqual(token, original['access_token'])
        claims = load(token, 'access')
        self.assertIsNotNone(claims)
        self.assertEqual(claims['client_id'], owner['client_id'])
        self.assertEqual(claims['subject'], str(self.user.pk))
        self.assertEqual(claims['resource'], BASE_URL + '/mcp')

        async def initialize():
            async with (
                self.app.router.lifespan_context(self.app),
                AsyncClient(transport=ASGITransport(self.app), base_url=BASE_URL) as client,
            ):
                return await client.post(
                    '/mcp',
                    headers={
                        'Authorization': f'Bearer {token}',
                        'Accept': 'application/json, text/event-stream',
                    },
                    json={
                        'jsonrpc': '2.0',
                        'id': 1,
                        'method': 'initialize',
                        'params': {
                            'protocolVersion': '2025-06-18',
                            'capabilities': {},
                            'clientInfo': {'name': 'isolated-auth-test', 'version': '1'},
                        },
                    },
                )

        with self.assertNumQueries(1):
            response = async_to_sync(initialize)()

        self.assertEqual(response.status_code, 200, response.text)
        self.assertIn('serverInfo', response.json()['result'])

    def test__mcp__cors_preflight_and_unauthorized(self):
        response = self.request(
            'OPTIONS',
            '/mcp',
            0,
            headers={
                'Origin': 'http://localhost:6274',
                'Access-Control-Request-Method': 'POST',
                'Access-Control-Request-Headers': 'Authorization,Content-Type,MCP-Protocol-Version,Mcp-Session-Id,Last-Event-ID',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['access-control-allow-origin'], '*')
        response = self.mcp(Origin='http://localhost:6274')
        self.assert_unauthorized(response)
        self.assertEqual(response.headers['access-control-allow-origin'], '*')
        self.assertIn('WWW-Authenticate', response.headers['access-control-expose-headers'])
