from api.mcp.tests.assessment_base import AssessmentToolsTestCase


class AssessmentArgumentValidationTestCase(AssessmentToolsTestCase):
    def test__list_assessments__errors__nonpositive_page(self):
        for page in (0, -1):
            with self.subTest(page=page):
                self.assert_invalid('list_assessments', {'page': page}, 'page')

    def test__list_assessments__errors__page_type(self):
        for page in (1.5, True, None, 'not a page', [], {}):
            with self.subTest(page=page):
                self.assert_invalid('list_assessments', {'page': page}, 'page')

    def test__list_assessments__errors__unknown_category(self):
        for category in ('podcast', 'MOVIE'):
            with self.subTest(category=category):
                self.assert_invalid('list_assessments', {'category': category}, 'category')

    def test__list_assessments__errors__category_type(self):
        for category in (1, True, [], {}):
            with self.subTest(category=category):
                self.assert_invalid('list_assessments', {'category': category}, 'category')

    def test__list_assessments__errors__name_type(self):
        for name in (1, True, [], {}):
            with self.subTest(name=name):
                self.assert_invalid('list_assessments', {'name': name}, 'name')

    def test__list_assessments__errors__partial_type(self):
        for partial in (0, 1, 1.5, 'not a flag', [], {}):
            with self.subTest(partial=partial):
                self.assert_invalid('list_assessments', {'partial': partial}, 'partial')

    def test__retrieve_assessment__errors__identifier_type(self):
        for identifier in (1.5, True, None, 'not an id', [], {}):
            with self.subTest(assessment_id=identifier):
                self.assert_invalid('retrieve_assessment', {'assessment_id': identifier}, 'assessment_id')

    def test__retrieve_assessment__errors__missing_identifier(self):
        self.assert_invalid('retrieve_assessment', {}, 'assessment_id')

    def test__retrieve_assessment__errors__media_id_cannot_replace_identifier(self):
        self.assert_invalid('retrieve_assessment', {'media_id': self.media.pk}, 'assessment_id')

    def test__update_review__errors__identifier_type(self):
        for identifier in (1.5, True, None, 'not an id', [], {}):
            with self.subTest(assessment_id=identifier):
                self.assert_invalid(
                    'update_review', {'assessment_id': identifier, 'review': 'Valid review'}, 'assessment_id'
                )

    def test__update_review__errors__missing_identifier(self):
        self.assert_invalid('update_review', {'review': 'Valid review'}, 'assessment_id')

    def test__update_review__errors__media_id_cannot_replace_identifier(self):
        self.assert_invalid('update_review', {'media_id': self.media.pk, 'review': 'Valid review'}, 'assessment_id')

    def test__update_review__errors__missing_review(self):
        self.assert_invalid('update_review', {'assessment_id': self.assessment.pk}, 'review')

    def test__update_review__errors__missing_all_arguments(self):
        self.assert_invalid('update_review', {}, 'assessment_id')

    def test__update_review__errors__review_type(self):
        for review in (1, True, None, [], {}):
            with self.subTest(review=review):
                self.assert_invalid('update_review', {'assessment_id': self.assessment.pk, 'review': review}, 'review')

    def test__update_review__errors__1001_characters(self):
        before = self.snapshot()

        result = self.call_tool(
            'update_review', {'assessment_id': self.assessment.pk, 'review': 'Я' * 1001}, error=True
        )

        self.assertIn('review', self.error_text(result))
        self.assertIn('1000', self.error_text(result))
        self.assertEqual(self.snapshot(), before)

    def test__update_review__errors__oversized_after_trimming(self):
        self.assert_invalid(
            'update_review', {'assessment_id': self.assessment.pk, 'review': ' \t' + 'x' * 1001 + '\n '}, '1000'
        )

    def test__update_review__trims_before_measuring_whitespace_only_review(self):
        before = self.snapshot()

        result = self.call_tool('update_review', {'assessment_id': self.assessment.pk, 'review': ' ' * 1001}, queries=5)

        self.assert_review_change(result, '', before)
