from api.assessment.models import Assessment, Media
from api.mcp.tests.assessment_base import NOT_FOUND, AssessmentToolsTestCase
from api.mcp.tests.base import BASE_URL
from api.mcp.tokens import issue


class AssessmentRetrieveTestCase(AssessmentToolsTestCase):
    def test__retrieve_assessment__full_detail(self):
        before = self.snapshot()

        result = self.call_tool('retrieve_assessment', {'assessment_id': self.assessment.pk}, queries=2)

        self.assert_detail(result)
        self.assertEqual(self.snapshot(), before)

    def test__retrieve_assessment__explicit_null_and_empty_values(self):
        Media.objects.filter(pk=self.media.pk).update(meta_mark=None, url='', description='')
        Assessment.objects.filter(pk=self.assessment.pk).update(partial='', review='')
        self.media.refresh_from_db()
        self.assessment.refresh_from_db()

        result = self.call_tool('retrieve_assessment', {'assessment_id': self.assessment.pk}, queries=2)

        self.assert_detail(result)
        self.assertIsNone(result['media']['meta_mark'])
        self.assertEqual(result['partial'], '')
        self.assertEqual(result['review'], '')
        self.assertEqual(result['media']['url'], '')
        self.assertEqual(result['media']['description'], '')
        listed = self.call_tool('list_assessments', queries=3)
        self.assertIsNone(listed['items'][0]['media']['meta_mark'])
        self.assertEqual(listed['items'][0]['partial'], '')

    def test__retrieve_assessment__errors__foreign_and_missing_ids_are_indistinguishable(self):
        before = self.snapshot()
        errors = []
        for identifier in (self.foreign.pk, self.foreign_only.pk, -1):
            with self.subTest(assessment_id=identifier):
                result = self.call_tool('retrieve_assessment', {'assessment_id': identifier}, queries=2, error=True)

                text = self.error_text(result)
                self.assertIn(NOT_FOUND, text)
                errors.append(text)

        self.assertEqual(len(set(errors)), 1)
        self.assertEqual(self.snapshot(), before)

    def test__retrieve_assessment__errors__deleted_after_listing(self):
        listed = self.call_tool('list_assessments', queries=3)
        identifier = listed['items'][0]['id']
        Assessment.objects.filter(pk=identifier).delete()
        before = self.snapshot()

        result = self.call_tool('retrieve_assessment', {'assessment_id': identifier}, queries=2, error=True)

        self.assertIn(NOT_FOUND, self.error_text(result))
        self.assertEqual(self.snapshot(), before)

    def test__retrieve_assessment__errors__media_id_is_not_an_assessment_key(self):
        self.assertNotEqual(self.assessment.pk, self.media.pk)

        result = self.call_tool('retrieve_assessment', {'assessment_id': self.media.pk}, queries=2, error=True)

        self.assertIn(NOT_FOUND, self.error_text(result))

    def test__tools__owner_is_token_subject(self):
        other_token = issue(
            'access',
            client_id='other-client',
            subject=str(self.other_user.pk),
            resource=BASE_URL + '/mcp',
        )
        listed = self.rpc('tools/call', {'name': 'list_assessments', 'arguments': {}}, queries=3, token=other_token)

        self.assertEqual(listed.status_code, 200, listed.text)
        ids = [row['id'] for row in listed.json()['result']['structuredContent']['items']]
        self.assertEqual(ids, [self.foreign_only.pk, self.foreign.pk])
        self.assertNotIn(self.assessment.pk, ids)
