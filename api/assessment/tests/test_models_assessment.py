from django.test import TestCase

from api.assessment.tests.factories import AssessmentFactory, MediaFactory
from api.user.tests.factories import UserFactory


class AssessmentReviewModelTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.media = MediaFactory(creator=cls.user)

    def test__assessment__default_review_is_persisted_as_empty(self):
        with self.assertNumQueries(1):
            assessment = AssessmentFactory(user=self.user, media=self.media)

        self.assertEqual(assessment.review, '')
        assessment.refresh_from_db()
        self.assertEqual(assessment.review, '')
        self.assertFalse(hasattr(self.media, 'assessment_until_dt'))
