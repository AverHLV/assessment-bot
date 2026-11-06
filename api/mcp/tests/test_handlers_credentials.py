import base64

from api.mcp.managers import digest
from api.mcp.tests.base import OAuthTestCase


class ClientCredentialsTestCase(OAuthTestCase):
    def test__client_auth__errors__basic_conflicting_credentials(self):
        client, code = self.code(self.register('client_secret_basic'))
        basic = base64.b64encode(f'{client["client_id"]}:{client["client_secret"]}'.encode()).decode()
        for params, header, count in (
            ({'client_id': 'different'}, f'Basic {basic}', 0),
            ({'client_secret': 'duplicate'}, f'Basic {basic}', 0),
            ({}, 'Basic invalid-base64', 0),
            ({}, 'Bearer token', 0),
            ({}, 'Basic ' + base64.b64encode(f'{client["client_id"]}:wrong'.encode()).decode(), 1),
        ):
            with self.subTest(params=params, header=header[:12]):
                response = self.request(
                    'POST',
                    '/token',
                    count,
                    data={
                        'grant_type': 'authorization_code',
                        'code': code,
                        **params,
                    },
                    headers={'Authorization': header},
                )

                self.assert_oauth_error(response, 'invalid_client', 401)

    def test__client_auth__errors__digest_is_not_a_secret(self):
        client, code = self.code(self.register('client_secret_post'))

        response = self.exchange(client, code, queries=1, client_secret=digest(client['client_secret']))

        self.assert_oauth_error(response, 'invalid_client', 401)

    def test__client_auth__errors__public_client_cannot_send_secret(self):
        client, code = self.code()

        response = self.exchange(client, code, queries=1, client_secret='unexpected-secret')

        self.assert_oauth_error(response, 'invalid_client', 401)
