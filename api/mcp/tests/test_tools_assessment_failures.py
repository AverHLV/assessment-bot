from unittest.mock import patch

from api.mcp.schemas.assessment import AssessmentDetail
from api.mcp.tests.assessment_base import NOT_FOUND, AssessmentToolsTestCase
from api.mcp.tests.base import BASE_URL
from api.mcp.tokens import issue, load
from api.user.models import User
from api.user.tests.factories import UserFactory


class AssessmentToolAuthenticationTestCase(AssessmentToolsTestCase):
    def test__tools__errors__missing_token(self):
        self.assert_tools_unauthorized(queries=0, authenticated=False)

    def test__tools__errors__invalid_token(self):
        self.assert_tools_unauthorized(queries=0, token='invalid')

    def test__tools__errors__expired_token(self):
        token = self.access()
        expiration = load(token, 'access')['exp']

        with patch('api.mcp.tokens.time.time', return_value=expiration):
            self.assert_tools_unauthorized(queries=0, token=token)

    def test__tools__errors__inactive_owner(self):
        token = self.access()
        User.objects.filter(pk=self.user.pk).update(is_active=False)

        self.assert_tools_unauthorized(queries=1, token=token)

    def test__tools__errors__deleted_owner(self):
        deleted = UserFactory()
        token = issue('access', client_id='test-client', subject=str(deleted.pk), resource=BASE_URL + '/mcp')
        deleted.delete()

        self.assert_tools_unauthorized(queries=1, token=token)


class AssessmentDatabaseFailureTestCase(AssessmentToolsTestCase):
    def test__list_assessments__errors__database_unavailable_without_retry(self):
        before = self.snapshot()

        with self.fail_assessment_sql('SELECT') as attempts:
            result = self.call_tool('list_assessments', queries=2, error=True)

        self.assertNotIn(NOT_FOUND, self.error_text(result))
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(len(attempts), 1)

    def test__list_assessments__errors__page_read_failure_without_retry(self):
        before = self.snapshot()

        with self.fail_assessment_sql('SELECT', occurrence=2) as attempts:
            result = self.call_tool('list_assessments', queries=3, error=True)

        self.assertNotIn(NOT_FOUND, self.error_text(result))
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(len(attempts), 2)

    def test__retrieve_assessment__errors__database_unavailable_without_retry(self):
        before = self.snapshot()

        with self.fail_assessment_sql('SELECT') as attempts:
            result = self.call_tool('retrieve_assessment', {'assessment_id': self.assessment.pk}, queries=2, error=True)

        self.assertNotIn(NOT_FOUND, self.error_text(result))
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(len(attempts), 1)

    def test__update_review__errors__database_unavailable_without_retry(self):
        before = self.snapshot()

        with self.fail_assessment_sql('UPDATE') as attempts:
            result = self.call_tool(
                'update_review', {'assessment_id': self.assessment.pk, 'review': 'Unsaved'}, queries=5, error=True
            )

        self.assertNotIn(NOT_FOUND, self.error_text(result))
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(len(attempts), 1)

    def test__update_review__errors__detail_read_failure_rolls_back_write(self):
        before = self.snapshot()

        with self.fail_assessment_sql('SELECT') as attempts:
            result = self.call_tool(
                'update_review',
                {'assessment_id': self.assessment.pk, 'review': 'Must roll back'},
                queries=6,
                error=True,
            )

        self.assertNotIn(NOT_FOUND, self.error_text(result))
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(len(attempts), 1)

    def test__update_review__errors__response_validation_failure_rolls_back_write(self):
        before = self.snapshot()

        with patch(
            'api.mcp.tools.assessment.detail_from_row', side_effect=lambda row: AssessmentDetail.model_validate({})
        ) as serialize:
            result = self.call_tool(
                'update_review',
                {'assessment_id': self.assessment.pk, 'review': 'Must roll back'},
                queries=6,
                error=True,
            )

        self.assertNotIn(NOT_FOUND, self.error_text(result))
        self.assertEqual(self.snapshot(), before)
        serialize.assert_called_once()
        self.assertEqual(serialize.call_args.args[0]['review'], 'Must roll back')
