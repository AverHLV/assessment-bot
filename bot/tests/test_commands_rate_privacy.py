import factory
from asgiref.sync import async_to_sync

from api.assessment.models import Assessment, Media
from api.assessment.tests.factories import AssessmentFactory, MediaFactory
from api.user.tests.factories import UserFactory
from bot.commands.rate import AssessmentCog
from bot.tests.base import CogWithCommandsBaseTestCase


class AssessmentPrivacyTestCase(CogWithCommandsBaseTestCase):
    cog_class = AssessmentCog
    private_review = 'PRIVATE_REVIEW_SENTINEL'

    def test__rates__review_does_not_change_public_output(self):
        media = MediaFactory.create_batch(size=2, assessment_status=Media.AssessmentStatus.COMPLETED)
        users = UserFactory.create_batch(size=2)
        assessments = AssessmentFactory.create_batch(
            size=4,
            media=factory.Iterator((media[0], media[0], media[1], media[1])),
            user=factory.Iterator(users),
            review=self.private_review,
        )

        with self.assertNumQueries(3):
            async_to_sync(self.cog.rates.callback)(self.cog, self.interaction)

        response = self.interaction.edit_original_response.call_args.kwargs
        self.assertEqual(response['content'], self.cog.message_rates)
        fields = response['embed'].fields
        self.assertEqual(len(fields), 2)
        expected_values = {}
        for media_obj, group in zip(media, (assessments[:2], assessments[2:]), strict=True):
            expected_values[f'{media_obj.name}, {media_obj.category.name}'] = ''.join(
                f'{assessment.user.username} - *{assessment.mark:.1f}*\n'
                for assessment in sorted(group, key=lambda item: item.user.username)
            )
        self.assertEqual({field.name: field.value for field in fields}, expected_values)
        with_review = response['embed'].to_dict()
        self.assertNotIn(self.private_review, str(with_review))
        Assessment.objects.filter(pk__in=[assessment.pk for assessment in assessments]).update(review='')
        self.interaction.reset_mock()

        with self.assertNumQueries(3):
            async_to_sync(self.cog.rates.callback)(self.cog, self.interaction)

        without_review = self.interaction.edit_original_response.call_args.kwargs['embed'].to_dict()
        self.assertEqual(with_review, without_review)
