from django.db import connection

from decimal import Decimal
from unittest.mock import patch

from api.assessment.models import Assessment
from api.mcp.tests.assessment_base import NOT_FOUND, AssessmentToolsTestCase


class AssessmentReviewTestCase(AssessmentToolsTestCase):
    def test__update_review__creates_review_on_existing_assessment(self):
        Assessment.objects.filter(pk=self.assessment.pk).update(review='')
        before = self.snapshot()

        with patch('api.llm.openrouter_client.create_completion') as completion:
            result = self.call_tool(
                'update_review', {'assessment_id': self.assessment.pk, 'review': '  Great pacing.  '}, queries=5
            )

        self.assert_review_change(result, 'Great pacing.', before)
        retrieved = self.call_tool('retrieve_assessment', {'assessment_id': self.assessment.pk}, queries=2)
        self.assertEqual(result, retrieved)
        completion.assert_not_called()

    def test__update_review__replaces_review_without_other_changes(self):
        before = self.snapshot()

        result = self.call_tool(
            'update_review', {'assessment_id': self.assessment.pk, 'review': '\n  Replacement review.\t '}, queries=5
        )

        self.assert_review_change(result, 'Replacement review.', before)

    def test__update_review__clears_whitespace_only_review(self):
        before = self.snapshot()

        result = self.call_tool(
            'update_review', {'assessment_id': self.assessment.pk, 'review': ' \t\n\u2003 '}, queries=5
        )

        self.assert_review_change(result, '', before)

    def test__update_review__clears_empty_review(self):
        before = self.snapshot()

        result = self.call_tool('update_review', {'assessment_id': self.assessment.pk, 'review': ''}, queries=5)

        self.assert_review_change(result, '', before)

    def test__update_review__accepts_exactly_1000_characters_after_trimming(self):
        review = 'Я' * 1000
        before = self.snapshot()

        result = self.call_tool(
            'update_review', {'assessment_id': self.assessment.pk, 'review': ' \n' + review + '\t '}, queries=5
        )

        self.assert_review_change(result, review, before)
        self.assertEqual(len(result['review']), 1000)

    def test__update_review__idempotent(self):
        arguments = {'assessment_id': self.assessment.pk, 'review': '  Identical review.  '}
        before = self.snapshot()

        first = self.call_tool('update_review', arguments, queries=5)
        second = self.call_tool('update_review', arguments, queries=5)

        self.assertEqual(first, second)
        self.assert_review_change(second, 'Identical review.', before)

    def test__update_review__follows_listed_assessment_id(self):
        before = self.snapshot()
        listed = self.call_tool('list_assessments', queries=3)
        item = listed['items'][0]
        self.assertNotEqual(item['id'], item['media']['id'])
        retrieved = self.call_tool('retrieve_assessment', {'assessment_id': item['id']}, queries=2)

        updated = self.call_tool('update_review', {'assessment_id': item['id'], 'review': 'My review.'}, queries=5)

        self.assert_review_change(updated, 'My review.', before)
        self.assertEqual(updated['id'], item['id'])
        self.assertEqual(updated['media'], retrieved['media'])
        retrieved['review'] = 'My review.'
        self.assertEqual(updated, retrieved)

    def test__update_review__preserves_other_fields_changed_at_write_boundary(self):
        before = self.snapshot()
        interleaved = False

        def change_mark_and_partial(execute, sql, params, many, context):
            nonlocal interleaved
            if sql.startswith('UPDATE "assessment_assessment"') and not interleaved:
                # Another writer's completed change occurs immediately before the review write.
                interleaved = True
                Assessment.objects.filter(pk=self.assessment.pk).update(mark=Decimal('9.0'), partial='Finished later')
            return execute(sql, params, many, context)

        # The sixth query is the controlled writer's UPDATE; the tool still has its five-query budget.
        with connection.execute_wrapper(change_mark_and_partial):
            result = self.call_tool(
                'update_review', {'assessment_id': self.assessment.pk, 'review': 'Current review.'}, queries=6
            )

        self.assertEqual(result['mark'], 9.0)
        self.assertEqual(result['partial'], 'Finished later')
        self.assertEqual(result['review'], 'Current review.')
        for row in before['assessments']:
            if row['id'] == self.assessment.pk:
                row.update(mark=Decimal('9.0'), partial='Finished later', review='Current review.')

        self.assertEqual(self.snapshot(), before)
        self.assertTrue(interleaved)
        retrieved = self.call_tool('retrieve_assessment', {'assessment_id': self.assessment.pk}, queries=2)
        self.assertEqual(result, retrieved)


class AssessmentReviewOwnershipTestCase(AssessmentToolsTestCase):
    def test__update_review__errors__foreign_and_missing_ids_are_indistinguishable(self):
        before = self.snapshot()
        errors = []
        for identifier in (self.foreign.pk, self.foreign_only.pk, -1):
            with self.subTest(assessment_id=identifier):
                result = self.call_tool(
                    'update_review',
                    {'assessment_id': identifier, 'review': 'Unauthorized change'},
                    queries=5,
                    error=True,
                )

                text = self.error_text(result)
                self.assertIn(NOT_FOUND, text)
                errors.append(text)
                self.assertEqual(self.snapshot(), before)

        self.assertEqual(len(set(errors)), 1)

    def test__update_review__errors__deleted_after_listing(self):
        listed = self.call_tool('list_assessments', queries=3)
        identifier = listed['items'][0]['id']
        Assessment.objects.filter(pk=identifier).delete()
        before = self.snapshot()

        result = self.call_tool(
            'update_review', {'assessment_id': identifier, 'review': 'Too late'}, queries=5, error=True
        )

        self.assertIn(NOT_FOUND, self.error_text(result))
        self.assertEqual(self.snapshot(), before)

    def test__update_review__errors__media_id_is_not_an_assessment_key(self):
        before = self.snapshot()
        self.assertNotEqual(self.assessment.pk, self.media.pk)

        result = self.call_tool(
            'update_review', {'assessment_id': self.media.pk, 'review': 'Wrong key'}, queries=5, error=True
        )

        self.assertIn(NOT_FOUND, self.error_text(result))
        self.assertEqual(self.snapshot(), before)

    def test__tools__caller_fields_cannot_redirect_owner_or_change_marks(self):
        before = self.snapshot()
        injected = {
            'user_id': self.other_user.pk,
            'user': self.other_user.pk,
            'subject': str(self.other_user.pk),
            'media_id': self.foreign_only.media_id,
            'mark': 1.0,
            'partial': 'Injected note',
            'page_size': 1000,
        }
        # The SDK ignores undeclared fields. Assert that they cannot change ownership or writable fields.
        listing = self.call_tool('list_assessments', {**injected, 'partial': True}, queries=3)
        self.assert_page(listing, [self.assessment.pk], total=1)
        retrieved = self.call_tool('retrieve_assessment', {**injected, 'assessment_id': self.assessment.pk}, queries=2)
        self.assert_detail(retrieved)

        result = self.call_tool(
            'update_review', {**injected, 'assessment_id': self.assessment.pk, 'review': 'Allowed review'}, queries=5
        )

        self.assert_review_change(result, 'Allowed review', before)
        foreign = self.call_tool(
            'update_review', {**injected, 'assessment_id': self.foreign.pk, 'review': 'Rejected'}, queries=5, error=True
        )
        self.assertIn(NOT_FOUND, self.error_text(foreign))
        self.assertEqual(self.snapshot(), before)
