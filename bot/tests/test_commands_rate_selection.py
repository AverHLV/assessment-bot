from django.test import override_settings
from django.utils import timezone

from asgiref.sync import async_to_sync

from datetime import UTC, datetime
from unittest.mock import patch

from api.assessment.models import Media
from api.assessment.tests.factories import AssessmentFactory, MediaFactory
from bot.commands.rate import AssessmentCog
from bot.tests.base import CogWithCommandsBaseTestCase


class RateSelectionTestCase(CogWithCommandsBaseTestCase):
    cog_class = AssessmentCog

    def run_rate(self, queries=2):
        with self.assertNumQueries(queries):
            async_to_sync(self.cog.rate.callback)(self.cog, self.interaction)

    def test__rate__open_media_sorted_without_clock_restriction(self):
        media_b = MediaFactory(name='B', assessment_status=Media.AssessmentStatus.IN_PROGRESS)
        media_a = MediaFactory(name='A', assessment_status=Media.AssessmentStatus.IN_PROGRESS)
        AssessmentFactory(media=media_a)

        for year in (2000, 2100):
            with self.subTest(year=year), patch.object(timezone, 'now', return_value=datetime(year, 1, 1, tzinfo=UTC)):
                self.interaction.reset_mock()
                self.run_rate()

                self.assert_thinking(self.interaction)
                response = self.interaction.edit_original_response.call_args.kwargs
                self.assertEqual(response['content'], self.cog.message_rate)
                select = response['view'].children[0]
                self.assertEqual(select.user.pk, self.user.pk)
                self.assertEqual([option.value for option in select.options], [str(media_a.pk), str(media_b.pk)])
                self.assertEqual([option.label for option in select.options], ['A', 'B'])
                self.assertEqual(select.options[0].description, media_a.category.name)

        self.assertEqual(set(Media.objects.values_list('assessment_status', flat=True)), {'in_progress'})

    def test__rate__closed_and_already_rated_media_excluded(self):
        MediaFactory(assessment_status=Media.AssessmentStatus.INITIAL)
        MediaFactory(assessment_status=Media.AssessmentStatus.COMPLETED)
        AssessmentFactory(user=self.user, media__assessment_status=Media.AssessmentStatus.IN_PROGRESS)

        self.run_rate()

        self.interaction.edit_original_response.assert_called_once_with(content=self.cog.message_rate_no_media)

    @override_settings(BOT_PAGE_SIZE=2)
    def test__rate__page_limit(self):
        for name in ('C', 'B', 'A'):
            MediaFactory(name=name, assessment_status=Media.AssessmentStatus.IN_PROGRESS)

        self.run_rate()

        response = self.interaction.edit_original_response.call_args.kwargs
        self.assertEqual([option.label for option in response['view'].children[0].options], ['A', 'B'])

    def test__rate__first_interaction(self):
        self.user.delete()
        self.interaction.user.name = 'New rater'
        media = MediaFactory(assessment_status=Media.AssessmentStatus.IN_PROGRESS)

        self.run_rate(queries=5)

        response = self.interaction.edit_original_response.call_args.kwargs
        select = response['view'].children[0]
        self.assertEqual(select.options[0].value, str(media.pk))
        self.assertEqual(select.user.external_id, self.interaction.user.id)
        self.assertEqual(select.user.username, 'New rater')
        select.user.refresh_from_db()
        self.assertEqual(select.user.username, 'New rater')

    def test__rate__empty_first_interaction(self):
        self.user.delete()
        self.interaction.user.name = 'New rater'

        self.run_rate(queries=5)

        self.interaction.edit_original_response.assert_called_once_with(content=self.cog.message_rate_no_media)
