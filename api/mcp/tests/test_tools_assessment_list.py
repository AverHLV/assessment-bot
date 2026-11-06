from datetime import UTC, datetime, timedelta
from decimal import Decimal

from api.assessment.models import MediaCategory
from api.assessment.tests.factories import AssessmentFactory, MediaFactory
from api.mcp.tests.assessment_base import AssessmentProtocolTestCase, AssessmentToolsTestCase
from api.user.tests.factories import UserFactory


class AssessmentPaginationTestCase(AssessmentProtocolTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        movie = MediaCategory.objects.get(code=MediaCategory.Code.MOVIE)
        start = datetime(2025, 1, 1, tzinfo=UTC)
        cls.assessments = [
            AssessmentFactory(
                user=cls.user,
                media=MediaFactory(
                    creator=cls.user,
                    category=movie,
                    description='Long media description. ' * 100,
                    url='https://example.com/media',
                    meta_mark=Decimal('8.1'),
                ),
                mark=Decimal('7.5'),
                partial='Partial note',
                review='Long review. ' * 70,
                create_dt=start + timedelta(days=index // 7),
            )
            for index in range(61)
        ]
        cls.expected = sorted(cls.assessments, key=lambda row: (row.create_dt, row.pk), reverse=True)
        other = UserFactory()
        AssessmentFactory.create_batch(5, user=other, media__creator=other, media__category=movie)

    def test__list_assessments__stable_pages_and_constant_query_budget(self):
        seen = []
        for page, count in ((1, 30), (2, 30), (3, 1)):
            with self.subTest(page=page):
                result = self.call_tool('list_assessments', {'page': page}, queries=3)

                expected = self.expected[(page - 1) * 30 : page * 30]
                self.assert_page(result, [row.pk for row in expected], total=61, page=page, has_next=page < 3)
                self.assertEqual(len(result['items']), count)
                for item, row in zip(result['items'], expected, strict=True):
                    self.assertEqual(item['mark'], 7.5)
                    self.assertIsInstance(item['mark'], (int, float))
                    self.assertEqual(item['partial'], 'Partial note')
                    self.assert_timestamp(item['create_dt'], row.create_dt)
                    self.assertEqual(item['media']['id'], row.media_id)
                    self.assertEqual(item['media']['name'], row.media.name)
                    self.assertEqual(item['media']['meta_mark'], 8.1)
                    self.assertEqual(
                        item['media']['category'], {'code': row.media.category.code, 'name': row.media.category.name}
                    )
                seen.extend(item['id'] for item in result['items'])

                page_query = self.last_queries[-1]['sql']
                for column in ('review', 'description', 'url'):
                    self.assertNotIn(f'"{column}"', page_query)
                self.assertIn('LIMIT 30', page_query)

        self.assertEqual(seen, [row.pk for row in self.expected])
        repeated = self.call_tool('list_assessments', {'page': 2}, queries=3)
        self.assert_page(repeated, seen[30:60], total=61, page=2, has_next=True)

    def test__list_assessments__beyond_last_page(self):
        result = self.call_tool('list_assessments', {'page': 4}, queries=2)

        self.assert_page(result, [], total=61, page=4)

    def test__list_assessments__extremely_large_page(self):
        page = 10**100

        result = self.call_tool('list_assessments', {'page': page}, queries=2)

        self.assert_page(result, [], total=61, page=page)


class AssessmentEmptyListTestCase(AssessmentProtocolTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        other = UserFactory()
        AssessmentFactory(user=other, media__creator=other)
        MediaFactory(creator=cls.user)

    def test__list_assessments__no_own_assessments(self):
        result = self.call_tool('list_assessments', queries=2)

        self.assert_page(result, [], total=0)


class AssessmentFiltersTestCase(AssessmentToolsTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.dune_book = AssessmentFactory(
            user=cls.user, media=MediaFactory(creator=cls.user, category=cls.book, name='Dune')
        )
        cls.alien = AssessmentFactory(
            user=cls.user, media=MediaFactory(creator=cls.user, category=cls.movie, name='Alien')
        )
        cls.arcane = AssessmentFactory(
            user=cls.user,
            media=MediaFactory(
                creator=cls.user, category=MediaCategory.objects.get(code=MediaCategory.Code.SERIAL), name='Arcane'
            ),
            partial='5 / 9 episodes',
        )
        cls.ordered_ids = [cls.arcane.pk, cls.alien.pk, cls.dune_book.pk, cls.assessment.pk]

    def test__list_assessments__case_insensitive_substring(self):
        result = self.call_tool('list_assessments', {'name': 'UnE'}, queries=3)

        self.assert_page(result, [self.dune_book.pk, self.assessment.pk], total=2)

    def test__list_assessments__category(self):
        result = self.call_tool('list_assessments', {'category': 'movie'}, queries=3)

        self.assert_page(result, [self.alien.pk, self.assessment.pk], total=2)

    def test__list_assessments__combined_filters(self):
        result = self.call_tool('list_assessments', {'name': 'dune', 'category': 'movie'}, queries=3)

        self.assert_page(result, [self.assessment.pk], total=1)

    def test__list_assessments__all_filters_must_match(self):
        result = self.call_tool('list_assessments', {'name': 'dune', 'category': 'movie', 'partial': True}, queries=3)

        self.assert_page(result, [self.assessment.pk], total=1)
        excluded = self.call_tool(
            'list_assessments', {'name': 'dune', 'category': 'movie', 'partial': False}, queries=2
        )
        self.assert_page(excluded, [], total=0)

    def test__list_assessments__partial_true(self):
        result = self.call_tool('list_assessments', {'partial': True}, queries=3)

        self.assert_page(result, [self.arcane.pk, self.assessment.pk], total=2)

    def test__list_assessments__partial_false(self):
        result = self.call_tool('list_assessments', {'partial': False}, queries=3)

        self.assert_page(result, [self.alien.pk, self.dune_book.pk], total=2)

    def test__list_assessments__omitted_filters(self):
        result = self.call_tool('list_assessments', queries=3)

        self.assert_page(result, self.ordered_ids, total=4)

    def test__list_assessments__null_filters(self):
        result = self.call_tool('list_assessments', {'name': None, 'category': None, 'partial': None}, queries=3)

        self.assert_page(result, self.ordered_ids, total=4)

    def test__list_assessments__empty_name(self):
        result = self.call_tool('list_assessments', {'name': ''}, queries=3)

        self.assert_page(result, self.ordered_ids, total=4)

    def test__list_assessments__no_name_matches(self):
        result = self.call_tool('list_assessments', {'name': 'Missing title'}, queries=2)

        self.assert_page(result, [], total=0)

    def test__list_assessments__valid_category_without_matches(self):
        result = self.call_tool('list_assessments', {'category': 'song'}, queries=2)

        self.assert_page(result, [], total=0)

    def test__list_assessments__literal_percent(self):
        row = AssessmentFactory(user=self.user, media__creator=self.user, media__name='100% complete')
        AssessmentFactory(user=self.user, media__creator=self.user, media__name='100 percent complete')

        result = self.call_tool('list_assessments', {'name': '%'}, queries=3)

        self.assert_page(result, [row.pk], total=1)

    def test__list_assessments__literal_underscore(self):
        row = AssessmentFactory(user=self.user, media__creator=self.user, media__name='File_name')
        AssessmentFactory(user=self.user, media__creator=self.user, media__name='FileXname')

        result = self.call_tool('list_assessments', {'name': '_'}, queries=3)

        self.assert_page(result, [row.pk], total=1)

    def test__list_assessments__literal_backslash(self):
        row = AssessmentFactory(user=self.user, media__creator=self.user, media__name=r'Path\name')
        AssessmentFactory(user=self.user, media__creator=self.user, media__name='Pathname')

        result = self.call_tool('list_assessments', {'name': '\\'}, queries=3)

        self.assert_page(result, [row.pk], total=1)

    def test__list_assessments__filter_totals_across_pages(self):
        AssessmentFactory.create_batch(
            30, user=self.user, media__creator=self.user, media__category=self.movie, partial='In progress'
        )

        first = self.call_tool('list_assessments', {'category': 'movie', 'partial': True}, queries=3)
        second = self.call_tool('list_assessments', {'category': 'movie', 'partial': True, 'page': 2}, queries=3)

        self.assertEqual(len(first['items']), 30)
        self.assertEqual(first['total'], 31)
        self.assertIs(first['has_next'], True)
        self.assert_page(second, [self.assessment.pk], total=31, page=2)
