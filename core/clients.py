from httpx import AsyncClient, AsyncHTTPTransport, Response

import json
import logging
import time
from enum import StrEnum

HTTPClientResponseData = None | str | list | dict | tuple[bytes, str] | Response

logger = logging.getLogger(__name__)


class HTTPClientResponseType(StrEnum):
    TEXT = 'text'
    JSON = 'json'
    FILE = 'file'
    RESPONSE_ORIGINAL = 'response_original'


class AsyncHTTPBaseClient:
    DEFAULT_TIMEOUT = 10
    DEFAULT_MAX_RETRIES = 2
    _LOG_MAX_BODY_LENGTH = 300

    def __init__(self, host: str, timeout: int = None, max_retries: int = None, proxy: str = None, **kwargs):
        self.host = host.rstrip('/')
        self.timeout = timeout or self.DEFAULT_TIMEOUT

        max_retries = self.DEFAULT_MAX_RETRIES if max_retries is None else max_retries
        transport = AsyncHTTPTransport(retries=max_retries, **kwargs)
        if proxy:
            proxy = proxy.rstrip('/')
        self.session = AsyncClient(timeout=self.timeout, transport=transport, proxy=proxy)

    def __str__(self):
        return f'{type(self)}(host={self.host})'

    async def close_session(self) -> None:
        await self.session.aclose()

    async def _make_request(
        self,
        method: str,
        url: str,
        params: dict = None,
        data: dict = None,
        body: dict = None,
        headers: dict = None,
        cookies: dict = None,
        files: dict | tuple = None,
        response_type: HTTPClientResponseType = HTTPClientResponseType.JSON,
        **kwargs,
    ) -> HTTPClientResponseData:
        """
        Make an HTTP request.

        :param method: request method
        :param url: request URL
        :param params: URL query parameters
        :param data: form data
        :param body: payload data for JSON format
        :param headers: additional headers for this request
        :param cookies: additional cookies for this request
        :param files: files data in dict or tuple format (field name, file-like object, content-type, etc.)
        :param response_type: how to treat response data
        :param kwargs: additional request parameters for extra cases
        """

        self._log_request(method, url, params, data, body)
        start_time = time.time()
        response = await self.session.request(
            method=method,
            url=url,
            params=params,
            data=data,
            json=body,
            headers=headers,
            cookies=cookies,
            files=files,
            **kwargs,
        )
        try:
            log_response_data = self._get_response_data(response, HTTPClientResponseType.TEXT)
        except UnicodeError:
            log_response_data = None
        self._log_response(response, url, log_response_data, start_time)

        response.raise_for_status()
        return self._get_response_data(response, response_type)

    def _log_request(self, method: str, url: str, params: dict | None, data: dict | None, body: dict | None) -> None:
        body = body or data
        if body:
            body = json.dumps(body)
            body = body if len(body) < self._LOG_MAX_BODY_LENGTH else f'{body[: self._LOG_MAX_BODY_LENGTH]}...'

        request_fields = {
            'method': method,
            'url': url,
            'query': json.dumps(params) if params else None,
            'body': body if body else None,
        }
        logger.info('External request started', extra={'fields': {'request': request_fields}})

    def _log_response(self, response: Response, url: str, response_data: str | None, start_time: float) -> None:
        if response_data and len(response_data) >= self._LOG_MAX_BODY_LENGTH:
            response_data = f'{response_data[: self._LOG_MAX_BODY_LENGTH]}...'

        response_fields = {
            'status_code': response.status_code,
            'url': url,
            'body': response_data,
            'duration': (time.time() - start_time) * 1000,
        }
        logger.info('External response received', extra={'fields': {'response': response_fields}})

    @staticmethod
    def _remove_none(**data) -> dict:
        return {key: value for key, value in data.items() if value is not None}

    @staticmethod
    def _get_response_data(response: Response, response_type: HTTPClientResponseType) -> HTTPClientResponseData:
        if response_type == HTTPClientResponseType.RESPONSE_ORIGINAL:
            return response

        if not response.content:
            return None

        match response_type:
            case HTTPClientResponseType.TEXT:
                return response.text

            case HTTPClientResponseType.FILE:
                content_type = response.headers.get('Content-Type', 'application/octet-stream')
                return response.content, content_type

            case _:
                return response.json()


class AsyncHTTPTokenAuthBaseClient(AsyncHTTPBaseClient):
    keyword = 'Bearer'

    def __init__(self, access_token: str, **kwargs):
        super().__init__(**kwargs)
        self.session.headers['Authorization'] = f'{self.keyword} {access_token}'
