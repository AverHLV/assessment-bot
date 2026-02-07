from django.conf import settings
from django.test import SimpleTestCase

from asgiref.sync import async_to_sync

from unittest.mock import patch

from api.llm.clients import AsyncOpenRouterClient


class AsyncOpenRouterClientTestCase(SimpleTestCase):
    test_client_class = AsyncOpenRouterClient

    def setUp(self):
        self.test_client = self.test_client_class()

    @patch('core.clients.AsyncHTTPBaseClient._make_request')
    @async_to_sync
    async def test__async_openrouter_client__create_completion(self, request_mock):
        messages = [{'field': 'value'}]

        response = await self.test_client.create_completion(messages=messages)

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
