from django.conf import settings

from api.mcp.validation import CALLBACK_PATH, public_base_url
from core.clients import AsyncHTTPBaseClient


class DiscordOAuthClient(AsyncHTTPBaseClient):
    def __init__(self) -> None:
        super().__init__(host='https://discord.com/api')

    async def identify(self, code: str) -> int:
        token = await self._make_request(
            'POST',
            f'{self.host}/oauth2/token',
            data={
                'client_id': settings.DISCORD_CLIENT_ID,
                'client_secret': settings.DISCORD_CLIENT_SECRET,
                'grant_type': 'authorization_code',
                'code': code,
                'redirect_uri': public_base_url() + CALLBACK_PATH,
            },
            follow_redirects=False,
        )
        if not isinstance(token, dict) or not isinstance(token.get('access_token'), str) or not token['access_token']:
            raise ValueError('Invalid Discord token response')
        user = await self._make_request(
            'GET',
            f'{self.host}/users/@me',
            headers={'Authorization': f'Bearer {token["access_token"]}'},
            follow_redirects=False,
        )
        if not isinstance(user, dict) or not isinstance(user.get('id'), str) or not user['id'].isascii():
            raise ValueError('Invalid Discord identity response')
        external_id = int(user['id'])
        if not 0 < external_id < 2**63:
            raise ValueError('Invalid Discord identity')
        return external_id
