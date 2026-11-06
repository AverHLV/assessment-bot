from django.test import override_settings

import time
from unittest.mock import AsyncMock, patch
from urllib.parse import parse_qs, urlsplit

from api.mcp.authorization import cookie_name
from api.mcp.models import OAuthNonce
from api.mcp.tests.base import OAuthTestCase
from api.mcp.tokens import load
from api.user.models import User


class CallbackTestCase(OAuthTestCase):
    def setUp(self):
        super().setUp()
        self.client_info = self.register()
        self.state = self.authorize(self.client_info)

    def test__callback__code_and_hashed_nonces(self):
        response, identify = self.callback(self.state)

        self.assertEqual(response.status_code, 302)
        code = parse_qs(urlsplit(response.headers['location']).query)['code'][0]
        payload = load(code, 'code')
        self.assertEqual(payload['subject'], str(self.user.pk))
        self.assertEqual(payload['exp'] - payload['iat'], 600)
        self.assertTrue(self.nonce(OAuthNonce.Purpose.DISCORD_STATE).consumed)
        self.assertFalse(self.nonce(OAuthNonce.Purpose.AUTHORIZATION_CODE).consumed)
        self.assertNotIn(self.state, list(OAuthNonce.objects.values_list('digest', flat=True)))
        self.assertEqual(self.cookies.get(cookie_name(self.state)), None)
        identify.assert_awaited_once()

    def test__callback__errors__unknown_user(self):
        before = User.objects.count()

        response, identify = self.callback(self.state, external_id=999999, queries=2)

        self.assertEqual(response.status_code, 403)
        self.assertIn('use the Discord bot first', response.text)
        self.assertEqual(User.objects.count(), before)
        self.assertFalse(OAuthNonce.objects.filter(purpose=OAuthNonce.Purpose.AUTHORIZATION_CODE).exists())
        identify.assert_awaited_once()

    def test__callback__errors__inactive_user(self):
        User.objects.filter(pk=self.user.pk).update(is_active=False)

        response, _ = self.callback(self.state, queries=2)

        self.assertEqual(response.status_code, 403)
        self.assertFalse(OAuthNonce.objects.filter(purpose=OAuthNonce.Purpose.AUTHORIZATION_CODE).exists())

    def test__callback__errors__cancelled(self):
        response, identify = self.callback(self.state, queries=1, error='access_denied')

        self.assertEqual(response.status_code, 302)
        query = parse_qs(urlsplit(response.headers['location']).query)
        self.assertEqual(query['error'], ['access_denied'])
        self.assertEqual(query['state'], ['original-client-state'])
        self.assertTrue(self.nonce(OAuthNonce.Purpose.DISCORD_STATE).consumed)
        identify.assert_not_awaited()

    def test__callback__errors__missing_invalid_unknown_cookie(self):
        for params in ({}, {'state': 'unknown'}, {'state': 'u' * 43}, {'state': self.state + 'x'}):
            with self.subTest(params=params):
                response = self.request('GET', '/oauth/discord/callback', 0, params=params)

                self.assertEqual(response.status_code, 400)
                self.assertNotIn('location', response.headers)

    def test__callback__errors__missing_cookie(self):
        self.cookies.clear()

        response, identify = self.callback(self.state, queries=0)

        self.assertEqual(response.status_code, 400)
        identify.assert_not_awaited()

    def test__callback__errors__expired_cookie(self):
        with patch('api.mcp.tokens.time.time', return_value=time.time() + 601):
            response, identify = self.callback(self.state, queries=0)

        self.assertEqual(response.status_code, 400)
        identify.assert_not_awaited()

    def test__callback__errors__unknown_nonce(self):
        OAuthNonce.objects.all().delete()

        response, identify = self.callback(self.state, queries=1)

        self.assertEqual(response.status_code, 400)
        identify.assert_not_awaited()

    def test__callback__errors__replayed_state(self):
        original_cookie = self.cookies.get(cookie_name(self.state))
        self.callback(self.state)
        self.cookies.set(cookie_name(self.state), original_cookie, domain='127.0.0.1', path='/oauth/discord/callback')

        response, identify = self.callback(self.state, queries=1)

        self.assertEqual(response.status_code, 400)
        self.assertNotIn('location', response.headers)
        identify.assert_not_awaited()

    def test__callback__errors__discord_unavailable(self):
        mock = AsyncMock(side_effect=ValueError('sentinel-discord-secret'))
        with (
            patch('api.mcp.callback.discord_client.identify', mock),
            patch('api.mcp.callback.logger.exception') as exception_log,
        ):
            response = self.request(
                'GET', '/oauth/discord/callback', 1, params={'state': self.state, 'code': 'sentinel-discord-code'}
            )

        self.assertEqual(response.status_code, 502)
        self.assertNotIn('sentinel', response.text)
        self.assertTrue(self.nonce(OAuthNonce.Purpose.DISCORD_STATE).consumed)
        self.assertFalse(OAuthNonce.objects.filter(purpose=OAuthNonce.Purpose.AUTHORIZATION_CODE).exists())
        exception_log.assert_called_once_with('Discord OAuth exchange failed: sentinel-discord-secret')

    @override_settings(SECRET_KEY='different-key', SECRET_KEY_FALLBACKS=['private-test-signing-key'])
    def test__callback__errors__rotated_key_has_no_fallback(self):
        response, identify = self.callback(self.state, queries=0)

        self.assertEqual(response.status_code, 400)
        identify.assert_not_awaited()
