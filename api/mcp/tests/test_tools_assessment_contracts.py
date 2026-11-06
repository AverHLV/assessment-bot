from types import SimpleNamespace
from unittest.mock import patch

from api.assessment.models import MediaCategory
from api.mcp.tests.assessment_base import (
    DETAIL_KEYS,
    MEDIA_DETAIL_KEYS,
    MEDIA_SUMMARY_KEYS,
    SUMMARY_KEYS,
    AssessmentProtocolTestCase,
)


class AssessmentToolContractsTestCase(AssessmentProtocolTestCase):
    def test__tools__schemas_and_annotations(self):
        response = self.rpc('tools/list')

        self.assertEqual(response.status_code, 200, response.text)
        tools = {tool['name']: tool for tool in response.json()['result']['tools']}
        self.assertEqual(set(tools), {'list_assessments', 'retrieve_assessment', 'update_review'})
        expected_inputs = {
            'list_assessments': ({'page', 'name', 'category', 'partial', 'has_review'}, set()),
            'retrieve_assessment': ({'assessment_id'}, {'assessment_id'}),
            'update_review': ({'assessment_id', 'review'}, {'assessment_id', 'review'}),
        }
        for name, tool in tools.items():
            with self.subTest(tool=name):
                schema = tool['inputSchema']
                fields, required = expected_inputs[name]
                self.assertEqual(schema['type'], 'object')
                self.assertEqual(set(schema['properties']), fields)
                self.assertEqual(set(schema.get('required', [])), required)
                for field in schema['properties'].values():
                    self.assertTrue(field['description'])

                self.assertIn('0–10', tool['description'])
                self.assertIn('half steps', tool['description'])
                self.assertEqual('1000 characters after trimming' in tool['description'], name == 'update_review')
                hints = tool['annotations']
                self.assertIs(hints['readOnlyHint'], name != 'update_review')
                self.assertIs(hints['destructiveHint'], name == 'update_review')
                self.assertIs(hints['idempotentHint'], True)
                self.assertIs(hints['openWorldHint'], False)
                output = tool['outputSchema']
                self.assertEqual(output['type'], 'object')
                self.assertIn('properties', output)

        listing = tools['list_assessments']
        inputs = listing['inputSchema']
        self.assertEqual(inputs['properties']['page']['default'], 1)
        self.assertEqual(inputs['properties']['page']['minimum'], 1)
        self.assertEqual(inputs['properties']['page']['type'], 'integer')
        category_schema = inputs['$defs']['Code']
        self.assertEqual(set(category_schema['enum']), set(MediaCategory.Code.values))
        self.assertIn({'type': 'boolean'}, inputs['properties']['partial']['anyOf'])
        self.assertEqual(inputs['properties']['has_review']['anyOf'], [{'type': 'boolean'}, {'type': 'null'}])
        self.assertIsNone(inputs['properties']['has_review']['default'])
        page = listing['outputSchema']
        self.assertEqual(set(page['properties']), {'items', 'page', 'page_size', 'total', 'has_next'})
        self.assertEqual(page['properties']['page_size']['minimum'], 30)
        self.assertEqual(page['properties']['page_size']['maximum'], 30)
        summary = page['$defs']['AssessmentSummary']
        self.assertEqual(set(summary['properties']), SUMMARY_KEYS)
        self.assertEqual(summary['properties']['media']['$ref'], '#/$defs/MediaSummary')
        media = page['$defs']['MediaSummary']
        self.assertEqual(set(media['properties']), MEDIA_SUMMARY_KEYS)
        self.assertEqual(media['properties']['category']['$ref'], '#/$defs/CategoryDetails')
        self.assertEqual(set(page['$defs']['CategoryDetails']['properties']), {'code', 'name'})
        self.assertEqual(summary['properties']['mark']['type'], 'number')
        self.assertIn({'type': 'null'}, media['properties']['meta_mark']['anyOf'])

        retrieve = tools['retrieve_assessment']
        update = tools['update_review']
        self.assertIn('only when the user asks', update['description'])
        self.assertIn('save, summarize, or record their thoughts', update['description'])
        self.assertIn('first-person voice', update['description'])
        self.assertIn('"I think" instead of "The user thinks"', update['description'])
        self.assertEqual(retrieve['outputSchema'], update['outputSchema'])
        detail = retrieve['outputSchema']
        self.assertEqual(set(detail['properties']), DETAIL_KEYS)
        self.assertEqual(detail['properties']['media']['$ref'], '#/$defs/MediaDetail')
        self.assertEqual(set(detail['$defs']['MediaDetail']['properties']), MEDIA_DETAIL_KEYS)
        self.assertEqual(detail['properties']['create_dt']['format'], 'date-time')
        review = update['inputSchema']['properties']['review']
        self.assertEqual(review['type'], 'string')
        self.assertEqual(review['maxLength'], 1000)
        self.assertIn('trim', review['description'])
        for tool in (retrieve, update):
            identifier = tool['inputSchema']['properties']['assessment_id']
            self.assertEqual(identifier['type'], 'integer')
            self.assertIn('top-level id', identifier['description'])

    def test__tools__errors__hello_removed(self):
        result = self.call_tool('hello', error=True)

        self.assertIn('hello', self.error_text(result))

    def test__tools__errors__missing_verified_subject(self):
        for token in (None, SimpleNamespace(subject=None)):
            for name, arguments in (
                ('list_assessments', {}),
                ('retrieve_assessment', {'assessment_id': 1}),
                ('update_review', {'assessment_id': 1, 'review': 'Review'}),
            ):
                with (
                    self.subTest(token=token, tool=name),
                    patch('api.mcp.tools.assessment.get_access_token', return_value=token),
                ):
                    result = self.call_tool(name, arguments, error=True)

                self.assertIn('Authentication is required', self.error_text(result))
