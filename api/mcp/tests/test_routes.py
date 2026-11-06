from django.conf import settings
from django.test import override_settings
from django.urls import reverse

from pathlib import Path
from tempfile import TemporaryDirectory

from api.mcp.tests.base import BASE_URL, OAuthTestCase
from core.asgi import create_application


class RuntimeTestCase(OAuthTestCase):
    def test__metadata__issuer_endpoints_and_pkce(self):
        response = self.request('GET', '/.well-known/oauth-authorization-server', 0)

        self.assertEqual(response.status_code, 200)
        metadata = response.json()
        self.assertEqual(metadata['issuer'], BASE_URL)
        self.assertEqual(metadata['authorization_endpoint'], BASE_URL + '/authorize')
        self.assertEqual(metadata['token_endpoint'], BASE_URL + '/token')
        self.assertEqual(metadata['registration_endpoint'], BASE_URL + '/register')
        self.assertEqual(metadata['grant_types_supported'], ['authorization_code', 'refresh_token'])
        self.assertEqual(metadata['response_types_supported'], ['code'])
        self.assertEqual(metadata['code_challenge_methods_supported'], ['S256'])
        self.assertFalse(metadata.get('client_id_metadata_document_supported'))
        self.assertNotIn('revocation_endpoint', metadata)
        resource = self.request('GET', '/.well-known/oauth-protected-resource/mcp', 0).json()
        self.assertEqual(resource['resource'], BASE_URL + '/mcp')
        self.assertEqual(resource['authorization_servers'], [BASE_URL])

    def test__oauth__cors_for_browser_endpoints(self):
        for path, method in (('/register', 'POST'), ('/token', 'POST')):
            response = self.request(
                'OPTIONS',
                path,
                0,
                headers={
                    'Origin': 'http://localhost:6274',
                    'Access-Control-Request-Method': method,
                    'Access-Control-Request-Headers': 'Authorization,Content-Type',
                },
            )

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers['access-control-allow-origin'], '*')

    def test__oauth__errors__missing_configuration(self):
        for changes in (
            {'PUBLIC_BASE_URL': ''},
            {'DISCORD_CLIENT_SECRET': ''},
            {'PUBLIC_BASE_URL': 'http://public.example'},
        ):
            with self.subTest(changes=changes), override_settings(**changes):
                self.app = create_application()
                for path in ('/authorize', '/oauth/discord/callback'):
                    response = self.request('GET', path, 0)
                    self.assert_oauth_error(response, 'server_error', 503)
                for path in ('/register', '/token'):
                    response = self.request('POST', path, 0, json={})
                    self.assert_oauth_error(response, 'server_error', 503)

    def test__runtime__django_health_and_admin(self):
        for path, count in (('/liveness', 0), ('/readiness', 1), (reverse('admin:login'), 0)):
            response = self.request('GET', path, count)

            self.assertEqual(response.status_code, 200)
            self.assertNotIn('access-control-allow-origin', response.headers)

    def test__runtime__static_files(self):
        with TemporaryDirectory() as directory, override_settings(STATIC_ROOT=directory):
            Path(directory, 'asset.css').write_text('body { color: blue; }')
            self.app = create_application()

            response = self.request('GET', '/static/asset.css', 0)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, 'body { color: blue; }')
        self.assertNotIn('whitenoise', str(settings.STORAGES))

    def test__oauth__errors__oversized_body(self):
        response = self.request(
            'POST', '/register', 0, content='x' * 16385, headers={'Origin': 'http://localhost:6274'}
        )

        self.assertEqual(response.status_code, 413)
        self.assertEqual(response.headers['access-control-allow-origin'], '*')
