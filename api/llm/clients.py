from django.conf import settings
from django.db.models import TextChoices

from httpx import HTTPStatusError, TimeoutException

from http import HTTPStatus

from core.clients import AsyncHTTPTokenAuthBaseClient, HTTPClientResponseData

DEFAULT_MESSAGE = (
    'My voice flickers like a dying ember... even I cannot always answer through the ash. '
    'Speak again in a few moments, lost soul.'
)


async def run_create_completion(
    client: 'AsyncOpenRouterClient',
    prompt: str,
    default_message: str = DEFAULT_MESSAGE,
) -> str:
    messages = [{'role': client.Role.USER, 'content': prompt}]

    try:
        response = await client.create_completion(messages=messages)
        return response['choices'][0]['message']['content']
    except TimeoutException:
        return default_message
    except HTTPStatusError as exc:
        if exc.response.status_code != HTTPStatus.TOO_MANY_REQUESTS:
            raise
        return default_message


class AsyncOpenRouterClient(AsyncHTTPTokenAuthBaseClient):
    class Role(TextChoices):
        ASSISTANT = 'assistant'
        USER = 'user'

    def __init__(self, **kwargs):
        kwargs.setdefault('host', settings.OPENROUTER_URL)
        kwargs.setdefault('access_token', settings.OPENROUTER_API_KEY)
        super().__init__(**kwargs)

    async def create_completion(
        self,
        messages: list[dict],
        model: str = settings.OPENROUTER_MODEL,
        reasoning: dict = None,
        provider: dict = None,
    ) -> HTTPClientResponseData:
        if not reasoning:
            reasoning = {'enabled': True, 'exclude': True}
        if not provider:
            provider = {'allow_fallbacks': True}

        data = {'messages': messages, 'model': model, 'reasoning': reasoning, 'provider': provider}
        return await self._make_request('POST', f'{self.host}/api/v1/chat/completions', body=data)
