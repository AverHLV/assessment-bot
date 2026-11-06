import base64
import time
from unittest.mock import patch
from urllib.parse import quote

from api.mcp.models import OAuthNonce
from api.mcp.tests.base import BASE_URL, REDIRECT, OAuthTestCase
from api.mcp.tokens import load
from api.user.models import User
from core.asgi import create_application


class TokenTestCase(OAuthTestCase):
    def test__token__code_consumed_once_and_no_token_rows(self):
        client, code = self.code()

        response = self.exchange(client, code)

        self.assertEqual(response.status_code, 200)
        token = response.json()
        self.assertEqual(token['expires_in'], 3600)
        self.assertEqual(load(token['access_token'], 'access')['subject'], str(self.user.pk))
        self.assertEqual(
            load(token['refresh_token'], 'refresh')['exp'] - load(token['refresh_token'], 'refresh')['iat'], 2592000
        )
        self.assertTrue(self.nonce(OAuthNonce.Purpose.AUTHORIZATION_CODE).consumed)
        self.assertEqual(OAuthNonce.objects.count(), 2)
        self.assertEqual(response.headers['cache-control'], 'no-store')

        response = self.exchange(client, code)

        self.assert_oauth_error(response, 'invalid_grant')

    def test__token__errors__wrong_verifier_does_not_consume(self):
        client, code = self.code()

        response = self.exchange(client, code, queries=1, code_verifier='wrong' * 16)

        self.assert_oauth_error(response, 'invalid_grant')
        self.assertFalse(self.nonce(OAuthNonce.Purpose.AUTHORIZATION_CODE).consumed)
        self.assertEqual(self.exchange(client, code).status_code, 200)

    def test__token__errors__wrong_client_redirect_expired_and_unknown(self):
        client, code = self.code()
        other = self.register()
        cases = [
            (other, code, {}),
            (client, code, {'redirect_uri': REDIRECT + 'x'}),
            (client, 'unknown', {}),
        ]
        for owner, grant, params in cases:
            with self.subTest(params=params, owner=owner['client_id']):
                response = self.exchange(owner, grant, queries=1, **params)

                self.assert_oauth_error(response, 'invalid_grant')

        with patch('api.mcp.tokens.time.time', return_value=time.time() + 601):
            response = self.exchange(client, code, queries=1)

        self.assert_oauth_error(response, 'invalid_grant')
        self.assertFalse(self.nonce(OAuthNonce.Purpose.AUTHORIZATION_CODE).consumed)

    def test__token__errors__inactive_or_deleted_owner(self):
        client, code = self.code()
        User.objects.filter(pk=self.user.pk).update(is_active=False)

        response = self.exchange(client, code, queries=2)

        self.assert_oauth_error(response, 'invalid_grant')
        self.assertFalse(self.nonce(OAuthNonce.Purpose.AUTHORIZATION_CODE).consumed)

    def test__token__refresh_reuse_preserves_expiry(self):
        client, token = self.tokens()
        expiry = load(token['refresh_token'], 'refresh')['exp']
        for delta in (1, 3600):
            with self.subTest(delta=delta), patch('api.mcp.tokens.time.time', return_value=time.time() + delta):
                response = self.refresh(client, token['refresh_token'])

                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()['refresh_token'], token['refresh_token'])
                self.assertEqual(load(response.json()['refresh_token'], 'refresh')['exp'], expiry)
                self.assertNotEqual(response.json()['access_token'], token['access_token'])

        with patch('api.mcp.tokens.time.time', return_value=expiry):
            response = self.refresh(client, token['refresh_token'], queries=1)

        self.assert_oauth_error(response, 'invalid_grant')

    def test__token__errors__refresh_owner_gone(self):
        client, token = self.tokens()
        User.objects.filter(pk=self.user.pk).delete()

        response = self.refresh(client, token['refresh_token'])

        self.assert_oauth_error(response, 'invalid_grant')

    def test__token__errors__refresh_owner_inactive(self):
        client, token = self.tokens()
        User.objects.filter(pk=self.user.pk).update(is_active=False)

        response = self.refresh(client, token['refresh_token'])

        self.assert_oauth_error(response, 'invalid_grant')

    def test__token__errors__refresh_wrong_client_scope_and_type(self):
        client, token = self.tokens()
        other = self.register()
        for owner, grant, params, error in (
            (other, token['refresh_token'], {}, 'invalid_grant'),
            (client, token['access_token'], {}, 'invalid_grant'),
            (client, token['refresh_token'], {'scope': 'other'}, 'invalid_scope'),
            (client, 'unknown', {}, 'invalid_grant'),
        ):
            with self.subTest(error=error, grant=grant[:12]):
                response = self.refresh(owner, grant, queries=1, **params)

                self.assert_oauth_error(response, error)

    def test__token__resource_binding(self):
        client, code = self.code(resource='https://other.example/mcp')

        response = self.exchange(client, code, queries=1, resource=BASE_URL + '/mcp')

        self.assert_oauth_error(response, 'invalid_target')
        self.assertFalse(self.nonce(OAuthNonce.Purpose.AUTHORIZATION_CODE).consumed)

        response = self.exchange(client, code)

        self.assertEqual(response.status_code, 200)
        tokens = response.json()
        self.assertEqual(load(tokens['access_token'], 'access')['resource'], 'https://other.example/mcp')
        self.assert_unauthorized(self.mcp(tokens['access_token']))
        response = self.refresh(client, tokens['refresh_token'], queries=1, resource=BASE_URL + '/mcp')
        self.assert_oauth_error(response, 'invalid_target')

    def test__token__confidential_post_and_basic(self):
        for method in ('client_secret_post', 'client_secret_basic'):
            with self.subTest(method=method):
                client, code = self.code(self.register(method))
                kwargs = {'client_secret': client['client_secret']} if method == 'client_secret_post' else {}
                headers = {}
                if method == 'client_secret_basic':
                    credentials = quote(client['client_id'], safe='') + ':' + quote(client['client_secret'], safe='')
                    headers['Authorization'] = 'Basic ' + base64.b64encode(credentials.encode()).decode()
                params = {
                    'grant_type': 'authorization_code',
                    'code': code,
                    'redirect_uri': REDIRECT,
                    'code_verifier': 'v' * 64,
                    **kwargs,
                }
                if method == 'client_secret_post':
                    params['client_id'] = client['client_id']
                response = self.request('POST', '/token', 3, data=params, headers=headers)

                self.assertEqual(response.status_code, 200, response.text)

    def test__token__errors__client_authentication(self):
        client, code = self.code(self.register('client_secret_post'))
        for secret in ('wrong-secret', self.nonce(OAuthNonce.Purpose.AUTHORIZATION_CODE).digest, ''):
            response = self.exchange(client, code, queries=1, client_secret=secret)

            self.assert_oauth_error(response, 'invalid_client', 401)

    def test__token__errors__malformed_request(self):
        for data, queries, error, status in (
            ({}, 0, 'invalid_client', 401),
            ({'client_id': 'unknown'}, 1, 'invalid_client', 401),
            (
                {'client_id': self.register()['client_id'], 'grant_type': 'bad', 'code': 'sentinel-code'},
                1,
                'invalid_request',
                400,
            ),
        ):
            response = self.request('POST', '/token', queries, data=data)

            self.assert_oauth_error(response, error, status)
            self.assertNotIn('sentinel-code', response.text)

    def test__token__separate_workers(self):
        client, code = self.code()
        self.app = create_application()

        response = self.exchange(client, code)

        self.assertEqual(response.status_code, 200)
        self.app = create_application()
        self.assertEqual(self.refresh(client, response.json()['refresh_token']).status_code, 200)
