from django.test import SimpleTestCase, override_settings

from asgiref.sync import async_to_sync
from httpx2 import MockTransport, Response, TimeoutException

from unittest.mock import patch

from api.mcp.clients import DiscordOAuthClient
from api.mcp.tests.base import OAUTH_SETTINGS


@override_settings(**OAUTH_SETTINGS)
class DiscordClientTestCase(SimpleTestCase):
    def setUp(self):
        self.client_test = DiscordOAuthClient()
        self.addCleanup(async_to_sync(self.client_test.close_session))

    def test__discord__form_exchange_and_request_scoped_token(self):
        requests = []

        def respond(request):
            requests.append(request)
            body = {'access_token': 'sentinel-access'} if request.url.path.endswith('/token') else {'id': '1234'}
            return Response(200, json=body)

        self.client_test.session._transport = MockTransport(respond)

        result = async_to_sync(self.client_test.identify)('sentinel-code')

        self.assertEqual(result, 1234)
        self.assertIn(b'code=sentinel-code', requests[0].content)
        self.assertEqual(requests[1].headers['authorization'], 'Bearer sentinel-access')
        self.assertNotIn('Authorization', self.client_test.session.headers)
        self.assertTrue(requests[0].headers['content-type'].startswith('application/x-www-form-urlencoded'))

    def test__discord__errors__http_timeout_and_malformed_responses(self):
        for value in ({}, {'access_token': ''}, TimeoutException('sentinel-timeout')):
            with self.subTest(value=value), patch.object(self.client_test, '_make_request') as request:
                if isinstance(value, Exception):
                    request.side_effect = value
                else:
                    request.return_value = value
                with self.assertRaises((ValueError, TimeoutException)):
                    async_to_sync(self.client_test.identify)('sentinel-code')
