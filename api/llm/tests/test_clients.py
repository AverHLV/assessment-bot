from django.conf import settings
from django.test import SimpleTestCase

from asgiref.sync import async_to_sync
from httpx import TimeoutException

from http import HTTPStatus
from unittest.mock import patch

from api.llm.clients import DEFAULT_MESSAGE, AsyncOpenRouterClient, run_create_completion
from core.utils_tests import get_httpx_test_response


class AsyncOpenRouterClientTestCase(SimpleTestCase):
    client_test_class = AsyncOpenRouterClient

    def setUp(self):
        self.prompt = 'prompt'
        self.client_test = self.client_test_class()

    @patch('core.clients.AsyncHTTPBaseClient._make_request')
    @async_to_sync
    async def test__async_openrouter_client__create_completion(self, request_mock):
        messages = [{'field': 'value'}]

        response = await self.client_test.create_completion(messages=messages)

        self.assertIs(response, request_mock.return_value)
        request_mock.assert_called_once()
        args, kwargs = request_mock.call_args
        method, url = args
        self.assertEqual(method, 'POST')
        self.assertTrue(url.startswith(settings.OPENROUTER_URL))
        self.assertTrue(url.endswith('completions'))

        self.assertIn('body', kwargs)
        body = kwargs['body']
        self.assertEqual(body['messages'], messages)
        self.assertEqual(body['model'], settings.OPENROUTER_MODEL)
        expected_reasoning = {'enabled': True, 'exclude': True}
        self.assertDictEqual(body['reasoning'], expected_reasoning)
        expected_provider = {'allow_fallbacks': True}
        self.assertDictEqual(body['provider'], expected_provider)

    @patch('api.llm.clients.AsyncOpenRouterClient.create_completion')
    @async_to_sync
    async def test__run_create_completion(self, completion_mock):
        response_content = 'response content'
        completion_mock.return_value = {
            'choices': [
                {
                    'message': {
                        'content': response_content,
                    },
                },
            ],
        }

        response = await run_create_completion(self.client_test, self.prompt)

        self.assertEqual(response, response_content)

        completion_mock.assert_called_once()
        _, kwargs = completion_mock.call_args
        self.assertIn('messages', kwargs)
        message = kwargs['messages'][0]
        self.assertEqual(message['role'], self.client_test.Role.USER)
        self.assertEqual(message['content'], self.prompt)

    @patch('api.llm.clients.AsyncOpenRouterClient.create_completion')
    @async_to_sync
    async def test__run_create_completion__timeout(self, completion_mock):
        completion_mock.side_effect = TimeoutException(message='timeout')

        response = await run_create_completion(self.client_test, self.prompt)

        self.assertEqual(response, DEFAULT_MESSAGE)
        completion_mock.assert_called_once()

    @patch('api.llm.clients.AsyncOpenRouterClient.create_completion')
    @async_to_sync
    async def test__run_create_completion__too_many_requests(self, completion_mock):
        httpx_response = get_httpx_test_response(status_code=HTTPStatus.TOO_MANY_REQUESTS)
        completion_mock.side_effect = lambda *_args, **_kwargs: httpx_response.raise_for_status()

        response = await run_create_completion(self.client_test, self.prompt)

        self.assertEqual(response, DEFAULT_MESSAGE)
        completion_mock.assert_called_once()
