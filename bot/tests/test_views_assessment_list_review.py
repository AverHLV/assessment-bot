from asgiref.sync import async_to_sync

from decimal import Decimal

from api.assessment.models import Assessment
from api.assessment.tests.factories import AssessmentFactory
from bot.tests.assessment_list_base import MyRatesBaseTestCase


class MyRatesReviewTestCase(MyRatesBaseTestCase):
    def test__my_rates__short_review_after_existing_content(self):
        assessment = AssessmentFactory(
            user=self.user,
            mark=8,
            partial='2 / 3 episodes',
            review='Great pacing',
            media__url='https://example.com/story',
            media__description='Story description',
            media__meta_mark=Decimal('7.5'),
        )
        AssessmentFactory(review='Another user private review')

        response = self.open_my_rates()

        fields = response['embed'].fields
        self.assertEqual(len(fields), 1)
        self.assertEqual(fields[0].name, f'{assessment.media.name} - *8.0*')
        self.assertEqual(
            fields[0].value,
            (
                f'{assessment.media.category.name}\n2 / 3 episodes\nMeta mark - *7.5*\n'
                '[Link](https://example.com/story)\nStory description\nGreat pacing'
            ),
        )
        self.assertEqual(Assessment.objects.get(pk=assessment.pk).review, 'Great pacing')

    def test__my_rates__review_299_characters(self):
        assessment = AssessmentFactory(user=self.user, review='r' * 299)

        response = self.open_my_rates()

        self.assert_review_field(response['embed'].fields[0], assessment, 'r' * 299)

    def test__my_rates__review_300_characters(self):
        assessment = AssessmentFactory(user=self.user, review='r' * 300)

        response = self.open_my_rates()

        self.assert_review_field(response['embed'].fields[0], assessment, 'r' * 300)

    def test__my_rates__review_301_characters(self):
        assessment = AssessmentFactory(user=self.user, review='r' * 297 + 'TAIL')

        response = self.open_my_rates()

        self.assert_review_field(response['embed'].fields[0], assessment, 'r' * 297 + '...')
        self.assertEqual(Assessment.objects.get(pk=assessment.pk).review, 'r' * 297 + 'TAIL')

    def test__my_rates__review_1000_characters(self):
        assessment = AssessmentFactory(user=self.user, review='я' * 1000)

        response = self.open_my_rates()

        self.assert_review_field(response['embed'].fields[0], assessment, 'я' * 297 + '...')
        self.assertEqual(len(Assessment.objects.get(pk=assessment.pk).review), 1000)

    def test__my_rates__empty_review_preserves_entry(self):
        assessment = AssessmentFactory(user=self.user, review='', media__description='Description')

        response = self.open_my_rates()

        self.assertEqual(
            response['embed'].fields[0].value,
            (f'{assessment.media.category.name}\n[Link]({assessment.media.url})\nDescription'),
        )

    def test__my_rates__review_markdown_and_linebreaks(self):
        assessment = AssessmentFactory(user=self.user, review='**Чудово**\n> Другий рядок')

        response = self.open_my_rates()

        self.assert_review_field(response['embed'].fields[0], assessment, '**Чудово**\n> Другий рядок')

    def test__my_rates__long_description_hides_review(self):
        assessment = AssessmentFactory(user=self.user, review='PRIVATE_TAIL', media__description='d' * 1100)

        response = self.open_my_rates()

        field = response['embed'].fields[0]
        prefix = f'{assessment.media.category.name}\n[Link]({assessment.media.url})\n'
        self.assertEqual(field.value, prefix + 'd' * (1021 - len(prefix)) + '...')
        self.assertEqual(len(field.value), 1024)
        self.assertNotIn('PRIVATE_TAIL', field.value)

    def test__my_rates__combined_value_exactly_1024_characters(self):
        assessment = AssessmentFactory(user=self.user, review='r' * 300, media__description='')
        prefix = f'{assessment.media.category.name}\n[Link]({assessment.media.url})\n'
        description = 'd' * (1024 - len(prefix) - 301)
        type(assessment.media).objects.filter(pk=assessment.media_id).update(description=description)

        response = self.open_my_rates()

        self.assertEqual(response['embed'].fields[0].value, prefix + description + '\n' + 'r' * 300)
        self.assertEqual(len(response['embed'].fields[0].value), 1024)

    def test__my_rates__combined_value_over_limit_truncates_review(self):
        assessment = AssessmentFactory(user=self.user, review='r' * 300, media__description='')
        prefix = f'{assessment.media.category.name}\n[Link]({assessment.media.url})\n'
        description = 'd' * (1025 - len(prefix) - 301)
        type(assessment.media).objects.filter(pk=assessment.media_id).update(description=description)

        response = self.open_my_rates()

        self.assertEqual(response['embed'].fields[0].value, prefix + description + '\n' + 'r' * 296 + '...')
        self.assertEqual(len(response['embed'].fields[0].value), 1024)

    def test__my_rates__empty(self):
        AssessmentFactory(review='Another user private review')

        with self.assertNumQueries(2):
            async_to_sync(self.cog.my_rates.callback)(self.cog, self.interaction)

        self.interaction.edit_original_response.assert_called_once_with(
            content=self.cog.message_my_rates_no_assessments
        )

    def test__my_rates__first_interaction_empty(self):
        self.user.delete()
        self.interaction.user.name = 'New rater'

        with self.assertNumQueries(5):
            async_to_sync(self.cog.my_rates.callback)(self.cog, self.interaction)

        self.interaction.edit_original_response.assert_called_once_with(
            content=self.cog.message_my_rates_no_assessments
        )
