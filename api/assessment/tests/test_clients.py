from django.conf import settings
from django.test import SimpleTestCase

from asgiref.sync import async_to_sync

from unittest.mock import patch

from api.assessment import errors
from api.assessment.clients import AsyncOMDbClient


class AsyncOMDbClientTestCase(SimpleTestCase):
    client_test_class = AsyncOMDbClient

    def setUp(self):
        self.title = 'movie title'
        self.response_data = {'field': 'value'}
        self.client_test = self.client_test_class()

    @patch('core.clients.AsyncHTTPBaseClient._make_request')
    @async_to_sync
    async def test__async_omdb_client__search(self, request_mock):
        request_mock.return_value = self.response_data

        response = await self.client_test.search(title=self.title)

        self.assertIs(response, request_mock.return_value)
        request_mock.assert_called_once()
        args, kwargs = request_mock.call_args
        method, url = args
        self.assertEqual(method, 'GET')
        self.assertEqual(url, settings.OMDB_URL)

        self.assertIn('params', kwargs)
        params = kwargs['params']
        self.assertEqual(params['t'], self.title)
        self.assertEqual(params['apikey'], self.client_test.api_key)

    @patch('core.clients.AsyncHTTPBaseClient._make_request')
    @async_to_sync
    async def test__async_omdb_client__search__errors__one_field_required(self, request_mock):
        with self.assertRaises(ValueError) as manager:
            await self.client_test.search(year=2000)

        self.assertEqual(str(manager.exception), 'At least one field is required: imdb_id, title')
        request_mock.assert_not_called()

    @patch('core.clients.AsyncHTTPBaseClient._make_request')
    @async_to_sync
    async def test__async_omdb_client__search__errors__response_error(self, request_mock):
        request_mock.return_value = {'Error': 'API error'}

        with self.assertRaises(errors.OMDbError) as manager:
            await self.client_test.search(title=self.title)

        self.assertEqual(manager.exception.error, request_mock.return_value['Error'])
        request_mock.assert_called_once()
