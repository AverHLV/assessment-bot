from django.test import override_settings

import json

from api.mcp.managers import digest
from api.mcp.models import OAuthClient
from api.mcp.tests.base import OAuthTestCase


class RegistrationTestCase(OAuthTestCase):
    def test__registration__public_and_confidential(self):
        for method in ('none', 'client_secret_post', 'client_secret_basic'):
            with self.subTest(method=method):
                client = self.register(method)

                stored = OAuthClient.objects.get(pk=client['client_id'])
                self.assertNotIn('client_secret', stored.metadata)
                if method == 'none':
                    self.assertIsNone(stored.secret_digest)
                else:
                    self.assertEqual(stored.secret_digest, digest(client['client_secret']))
                    self.assertNotIn(client['client_secret'], json.dumps(stored.metadata))

        self.assertEqual(OAuthClient.objects.count(), 3)

    def test__registration__errors__redirect_policy(self):
        invalid = [
            'https://attacker.example/callback',
            'http://claude.ai/callback',
            'https://sub.claude.ai/callback',
            'https://claude.ai.attacker.example/callback',
            'https://user:pass@claude.ai/callback',
            'https://claude.ai/callback#fragment',
            'ftp://claude.ai/callback',
            'https://claude.ai:99999/callback',
            'https://claude.ai:bad/callback',
            'not a url',
            '',
            None,
            7,
        ]
        for redirect in invalid:
            with self.subTest(redirect=redirect):
                response = self.request('POST', '/register', 0, json={'redirect_uris': [redirect]})

                self.assert_oauth_error(response, 'invalid_redirect_uri')

        self.assertFalse(OAuthClient.objects.exists())

    def test__registration__https_paths_queries_and_ipv6(self):
        for uri in ('https://CLAUDE.ai/any/path?q=1', 'http://[::1]:6274/callback', 'https://chatgpt.com/cb?a=2'):
            with self.subTest(uri=uri):
                self.register(redirect=uri)

    @override_settings(MCP_REDIRECT_URI_HOSTS=['claude.ai'])
    def test__registration__errors__loopback_not_allowlisted(self):
        response = self.request('POST', '/register', 0, json={'redirect_uris': ['http://localhost:6274/cb']})

        self.assert_oauth_error(response, 'invalid_redirect_uri')

    def test__registration__errors__metadata(self):
        cases = [
            {'token_endpoint_auth_method': 'private_key_jwt'},
            {'grant_types': ['authorization_code', 'other']},
            {'grant_types': ['refresh_token']},
            {'response_types': ['code', 'token']},
            {'scope': 'unsupported'},
        ]
        for params in cases:
            with self.subTest(params=params):
                response = self.request(
                    'POST',
                    '/register',
                    0,
                    json={
                        'redirect_uris': ['https://claude.ai/callback'],
                        **params,
                    },
                )

                self.assert_oauth_error(response, 'invalid_client_metadata')

    def test__registration__errors__malformed_body(self):
        for body in ('{', '[]', '{"client_secret":"sentinel-secret","redirect_uris":null}'):
            with self.subTest(body=body):
                response = self.request('POST', '/register', 0, content=body)

                self.assertEqual(response.status_code, 400)
                self.assertNotIn('sentinel-secret', response.text)
