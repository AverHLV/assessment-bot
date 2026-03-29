from django.conf import settings
from django.db.models import TextChoices

from api.assessment import errors
from core.clients import AsyncHTTPBaseClient, HTTPClientResponseData, HTTPClientResponseType


class AsyncOMDbClient(AsyncHTTPBaseClient):
    class ResultType(TextChoices):
        MOVIE = 'movie'
        SERIES = 'series'
        EPISODE = 'episode'

    class ErrorMessage(TextChoices):
        NOT_FOUND = 'Movie not found!'

    def __init__(self, api_key: str = settings.OMDB_API_KEY, **kwargs):
        kwargs.setdefault('host', settings.OMDB_URL)
        super().__init__(**kwargs)
        self.api_key = api_key

    def _get_api_key(self) -> dict:
        return {'apikey': self.api_key}

    async def _make_request(self, *args, **kwargs) -> HTTPClientResponseData:
        response = await super()._make_request(*args, **kwargs)
        response_type = kwargs.get('response_type', HTTPClientResponseType.JSON)
        if response_type != HTTPClientResponseType.JSON:
            return response

        error = response.get('Error')
        if error:
            raise errors.OMDbError(error)

        return response

    async def search(
        self,
        imdb_id: str = None,
        title: str = None,
        type_: ResultType = None,
        year: int = None,
    ) -> HTTPClientResponseData:
        if not (imdb_id or title):
            raise ValueError('At least one field is required: imdb_id, title')

        params = self._remove_none(i=imdb_id, t=title, type=type_, y=year)
        params.update(self._get_api_key())
        return await self._make_request('GET', self.host, params=params)
