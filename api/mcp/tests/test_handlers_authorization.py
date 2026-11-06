from django.test import override_settings

from urllib.parse import parse_qs, urlencode, urlsplit

from api.mcp.models import OAuthNonce
from api.mcp.tests.base import BASE_URL, CHALLENGE, REDIRECT, OAuthTestCase


class AuthorizationTestCase(OAuthTestCase):
    def setUp(self):
        super().setUp()
        self.client_info = self.register()
        self.params = {
            'client_id': self.client_info['client_id'],
            'redirect_uri': REDIRECT,
            'response_type': 'code',
            'code_challenge': CHALLENGE,
            'code_challenge_method': 'S256',
            'state': 'client-state',
        }

    def test__authorization__browser_cookie(self):
        response = self.request('GET', '/authorize', 2, params=self.params)

        self.assertEqual(response.status_code, 302)
        self.assertIn('HttpOnly', response.headers['set-cookie'])
        self.assertIn('SameSite=lax', response.headers['set-cookie'])
        self.assertEqual(OAuthNonce.objects.count(), 1)
        self.assertFalse(self.nonce(OAuthNonce.Purpose.DISCORD_STATE).consumed)

    def test__authorization__errors__client_and_redirect(self):
        for params in (
            {'client_id': 'unknown'},
            {'redirect_uri': 'https://attacker.example/cb'},
            {'redirect_uri': 'http://localhost:6275/callback?existing=kept'},
            {'redirect_uri': 'http://localhost:6274/callback?existing=changed'},
        ):
            with self.subTest(params=params):
                response = self.request('GET', '/authorize', 1, params={**self.params, **params})

                self.assertEqual(response.status_code, 400)
                self.assertNotIn('location', response.headers)

        self.assertFalse(OAuthNonce.objects.exists())

    def test__authorization__errors__pkce_response_scope(self):
        for params, error in (
            ({'code_challenge_method': None}, 'invalid_request'),
            ({'code_challenge_method': 'plain'}, 'invalid_request'),
            ({'code_challenge': 'bad'}, 'invalid_request'),
            ({'response_type': 'token'}, 'unsupported_response_type'),
            ({'scope': 'unsupported'}, 'invalid_scope'),
        ):
            with self.subTest(params=params):
                query = {key: value for key, value in {**self.params, **params}.items() if value is not None}
                response = self.request('GET', '/authorize', 1, params=query)

                self.assertEqual(response.status_code, 302)
                destination = urlsplit(response.headers['location'])
                self.assertEqual(destination.netloc, 'localhost:6274')
                self.assertEqual(parse_qs(destination.query)['error'], [error])
                self.assertEqual(parse_qs(destination.query)['state'], ['client-state'])

        self.assertFalse(OAuthNonce.objects.exists())

    def test__authorization__errors__missing_client(self):
        response = self.request('GET', '/authorize', 0, params={'state': 'client-state'})

        self.assertEqual(response.status_code, 400)
        self.assertNotIn('location', response.headers)

    def test__authorization__errors__duplicate_parameters_redirect_with_state(self):
        for method in ('GET', 'POST'):
            for key in ('scope', 'response_type', 'code_challenge', 'code_challenge_method', 'resource'):
                with self.subTest(method=method, parameter=key):
                    params = [*self.params.items(), (key, 'first'), (key, 'second')]
                    kwargs = (
                        {'params': params}
                        if method == 'GET'
                        else {
                            'content': urlencode(params),
                            'headers': {'Content-Type': 'application/x-www-form-urlencoded'},
                        }
                    )

                    response = self.request(method, '/authorize', 1, **kwargs)

                    self.assertEqual(response.status_code, 302)
                    destination = urlsplit(response.headers['location'])
                    self.assertEqual(destination._replace(query=''), urlsplit(REDIRECT)._replace(query=''))
                    self.assertEqual(
                        parse_qs(destination.query),
                        {'existing': ['kept'], 'error': ['invalid_request'], 'state': ['client-state']},
                    )
                    self.assertNotIn('set-cookie', response.headers)

        self.assertFalse(OAuthNonce.objects.exists())

    def test__authorization__errors__ambiguous_client_redirect_or_state(self):
        for method in ('GET', 'POST'):
            for key in ('client_id', 'redirect_uri', 'state'):
                for value in (self.params[key], 'different'):
                    with self.subTest(method=method, parameter=key, value=value):
                        params = [*self.params.items(), (key, value), ('scope', 'first'), ('scope', 'second')]
                        kwargs = (
                            {'params': params}
                            if method == 'GET'
                            else {
                                'content': urlencode(params),
                                'headers': {'Content-Type': 'application/x-www-form-urlencoded'},
                            }
                        )

                        response = self.request(method, '/authorize', 0, **kwargs)

                        self.assert_oauth_error(response, 'invalid_request')
                        self.assertNotIn('location', response.headers)

        self.assertFalse(OAuthNonce.objects.exists())

    def test__authorization__errors__duplicates_do_not_bypass_client_or_redirect_validation(self):
        for invalid in ({'client_id': 'unknown'}, {'redirect_uri': 'https://attacker.example/cb'}):
            with self.subTest(invalid=invalid):
                params = [*{**self.params, **invalid}.items(), ('scope', 'first'), ('scope', 'second')]

                response = self.request('GET', '/authorize', 1, params=params)

                self.assert_oauth_error(response, 'invalid_request')
                self.assertNotIn('location', response.headers)

        self.assertFalse(OAuthNonce.objects.exists())

    @override_settings(MCP_REDIRECT_URI_HOSTS=['claude.ai'])
    def test__authorization__errors__allowlist_changed(self):
        response = self.request('GET', '/authorize', 1, params=self.params)

        self.assertEqual(response.status_code, 400)
        self.assertNotIn('location', response.headers)

    def test__authorization__errors__oversized_context(self):
        response = self.request('GET', '/authorize', 1, params={**self.params, 'state': 's' * 4000})

        self.assertEqual(response.status_code, 302)
        self.assertIn('error=invalid_request', response.headers['location'])
        self.assertFalse(OAuthNonce.objects.exists())

    def test__authorization__parallel_browser_flows(self):
        first = self.authorize(self.client_info)
        second = self.authorize(self.client_info)

        self.assertNotEqual(first, second)
        self.assertEqual(len(self.cookies), 2)
        for state in (first, second):
            response, _ = self.callback(state)
            self.assertEqual(response.status_code, 302)

    def test__authorization__post_and_omitted_redirect(self):
        params = {key: value for key, value in self.params.items() if key != 'redirect_uri'}
        response = self.request('POST', '/authorize', 2, data=params)

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers['location'].startswith('https://discord.com/'))

    @override_settings(PUBLIC_BASE_URL=BASE_URL.replace('http:', 'https:'))
    def test__authorization__secure_cookie_on_https(self):
        response = self.request('GET', '/authorize', 2, params=self.params)

        self.assertEqual(response.status_code, 302)
        self.assertIn('Secure', response.headers['set-cookie'])
