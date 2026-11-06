from django.db import OperationalError, connection
from django.utils.dateparse import parse_datetime

from asgiref.sync import async_to_sync
from httpx2 import ASGITransport, AsyncClient

import json
from contextlib import contextmanager
from decimal import Decimal
from unittest.mock import patch

from api.assessment.models import Assessment, Media, MediaCategory
from api.assessment.tests.factories import AssessmentFactory, MediaFactory
from api.mcp.tests.base import BASE_URL, OAuthTestCase
from api.user.tests.factories import UserFactory
from core.asgi import create_application

NOT_FOUND = 'No assessment found for the authenticated user.'
SUMMARY_KEYS = {'id', 'media', 'mark', 'partial', 'create_dt'}
MEDIA_SUMMARY_KEYS = {'id', 'name', 'category', 'meta_mark'}
DETAIL_KEYS = SUMMARY_KEYS | {'review'}
MEDIA_DETAIL_KEYS = MEDIA_SUMMARY_KEYS | {'url', 'description', 'assessment_status', 'create_dt'}


class AssessmentProtocolTestCase(OAuthTestCase):
    def setUp(self):
        super().setUp()
        external = patch('core.clients.AsyncHTTPBaseClient._make_request', side_effect=AssertionError('External I/O'))
        self.external_request = external.start()
        self.addCleanup(external.stop)
        self.addCleanup(self.external_request.assert_not_called)

    def rpc(self, method, params=None, queries=1, token=None, authenticated=True):
        # MCP's session manager permits only one lifespan per instance, even in stateless mode.
        app = create_application()
        headers = {'Accept': 'application/json, text/event-stream', 'MCP-Protocol-Version': '2025-06-18'}
        if authenticated:
            headers['Authorization'] = f'Bearer {token or self.access()}'

        async def send():
            async with (
                app.router.lifespan_context(app),
                AsyncClient(transport=ASGITransport(app), base_url=BASE_URL) as client,
            ):
                return await client.post(
                    '/mcp',
                    headers=headers,
                    json={'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params or {}},
                )

        with self.assertNumQueries(queries) as captured:
            response = async_to_sync(send)()

        self.last_queries = captured.captured_queries
        return response

    def call_tool(self, name, arguments=None, queries=1, error=False):
        response = self.rpc('tools/call', {'name': name, 'arguments': arguments or {}}, queries=queries)

        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertNotIn('error', body, body)
        result = body['result']
        self.assertEqual(result.get('isError', False), error, result)
        self.assertTrue(result['content'], result)
        self.assertTrue(all(item['type'] == 'text' for item in result['content']))
        if error:
            self.assertTrue(self.error_text(result).strip())
            return result

        self.assertIn('structuredContent', result)
        self.assertEqual(json.loads(result['content'][0]['text']), result['structuredContent'])
        return result['structuredContent']

    @staticmethod
    def error_text(result):
        return '\n'.join(item['text'] for item in result['content'])

    def assert_page(self, result, ids, total, page=1, has_next=False):
        self.assertEqual(set(result), {'items', 'page', 'page_size', 'total', 'has_next'})
        self.assertEqual([item['id'] for item in result['items']], ids)
        self.assertEqual(result['page'], page)
        self.assertEqual(result['page_size'], 30)
        self.assertEqual(result['total'], total)
        self.assertIs(result['has_next'], has_next)
        for item in result['items']:
            self.assertEqual(set(item), SUMMARY_KEYS)
            self.assertEqual(set(item['media']), MEDIA_SUMMARY_KEYS)
            self.assertEqual(set(item['media']['category']), {'code', 'name'})

    def assert_timestamp(self, value, expected):
        self.assertIsInstance(value, str)
        parsed = parse_datetime(value)
        self.assertIsNotNone(parsed)
        self.assertIsNotNone(parsed.utcoffset())
        self.assertEqual(parsed, expected)


class AssessmentToolsTestCase(AssessmentProtocolTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.other_user = UserFactory()
        cls.movie = MediaCategory.objects.get(code=MediaCategory.Code.MOVIE)
        cls.book = MediaCategory.objects.get(code=MediaCategory.Code.BOOK)
        cls.media = MediaFactory(
            creator=cls.user,
            category=cls.movie,
            name='Dune',
            url='https://example.com/dune',
            description='A long description. ' * 100,
            meta_mark=Decimal('8.1'),
            assessment_status=Media.AssessmentStatus.COMPLETED,
        )
        cls.assessment = AssessmentFactory(
            pk=1000000,
            user=cls.user,
            media=cls.media,
            mark=Decimal('7.5'),
            partial='5 / 9 episodes',
            review='Old review',
        )
        cls.foreign = AssessmentFactory(user=cls.other_user, media=cls.media, review='Private review')
        cls.foreign_only = AssessmentFactory(
            user=cls.other_user,
            media=MediaFactory(creator=cls.other_user, category=cls.book),
            review='Another private review',
        )

    @staticmethod
    def snapshot():
        return {
            'assessments': list(Assessment.objects.order_by('pk').values()),
            'media': list(Media.objects.order_by('pk').values()),
            'categories': list(MediaCategory.objects.order_by('pk').values()),
        }

    def assert_detail(self, result, assessment=None, media=None, review=None):
        assessment = assessment or self.assessment
        media = media or self.media
        self.assertEqual(set(result), DETAIL_KEYS)
        self.assertEqual(set(result['media']), MEDIA_DETAIL_KEYS)
        self.assertEqual(result['id'], assessment.pk)
        self.assertIsInstance(result['id'], int)
        self.assertEqual(result['mark'], float(assessment.mark))
        self.assertIsInstance(result['mark'], (int, float))
        self.assertEqual(result['partial'], assessment.partial)
        self.assertEqual(result['review'], assessment.review if review is None else review)
        self.assert_timestamp(result['create_dt'], assessment.create_dt)
        detail = result['media']
        self.assertEqual(detail['id'], media.pk)
        self.assertEqual(detail['name'], media.name)
        self.assertEqual(detail['category'], {'code': media.category.code, 'name': media.category.name})
        if media.meta_mark is None:
            self.assertIsNone(detail['meta_mark'])
        else:
            self.assertIsInstance(detail['meta_mark'], (int, float))
            self.assertEqual(detail['meta_mark'], float(media.meta_mark))
        self.assertEqual(detail['url'], media.url)
        self.assertEqual(detail['description'], media.description)
        self.assertEqual(detail['assessment_status'], media.assessment_status)
        self.assert_timestamp(detail['create_dt'], media.create_dt)

    def assert_review_change(self, result, review, before):
        self.assert_detail(result, review=review)
        for row in before['assessments']:
            if row['id'] == self.assessment.pk:
                row['review'] = review

        self.assertEqual(self.snapshot(), before)

    def assert_invalid(self, tool, arguments, field):
        before = self.snapshot()

        result = self.call_tool(tool, arguments, error=True)

        self.assertIn(field, self.error_text(result))
        self.assertEqual(self.snapshot(), before)

    @contextmanager
    def fail_assessment_sql(self, statement, occurrence=1):
        attempts = []

        def fail(execute, sql, params, many, context):
            if sql.startswith(statement) and '"assessment_assessment"' in sql:
                attempts.append(sql)
                if len(attempts) >= occurrence:
                    raise OperationalError('Controlled database failure')
            return execute(sql, params, many, context)

        with connection.execute_wrapper(fail):
            yield attempts

    def assert_tools_unauthorized(self, queries, **credentials):
        before = self.snapshot()
        for tool, arguments in (
            ('list_assessments', {}),
            ('retrieve_assessment', {'assessment_id': self.assessment.pk}),
            ('update_review', {'assessment_id': self.assessment.pk, 'review': 'Unauthorized review'}),
        ):
            with self.subTest(tool=tool):
                response = self.rpc(
                    'tools/call', {'name': tool, 'arguments': arguments}, queries=queries, **credentials
                )

                self.assert_unauthorized(response)
                self.assertEqual(self.snapshot(), before)
