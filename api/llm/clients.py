from django.conf import settings
from django.db.models import TextChoices

from core.clients import AsyncHTTPTokenAuthBaseClient, HTTPClientResponseData


class AsyncOpenRouterClient(AsyncHTTPTokenAuthBaseClient):
    class Role(TextChoices):
        ASSISTANT = 'assistant'
        USER = 'user'

    DEFAULT_TIMEOUT = 8
    DEFAULT_MAX_RETRIES = 0

    def __init__(self, **kwargs):
        kwargs.setdefault('host', settings.OPENROUTER_URL)
        kwargs.setdefault('access_token', settings.OPENROUTER_API_KEY)
        super().__init__(**kwargs)

    async def create_completion(
        self,
        messages: list[dict],
        model: str = settings.OPENROUTER_MODEL,
        reasoning: dict = None,
    ) -> HTTPClientResponseData:
        if not reasoning:
            reasoning = {'enabled': True, 'exclude': True}

        data = {'messages': messages, 'model': model, 'reasoning': reasoning}
        return await self._make_request('POST', f'{self.host}/api/v1/chat/completions', body=data)
