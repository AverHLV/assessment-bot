from asgiref.sync import async_to_sync

from bot.commands.rate import AssessmentCog
from bot.tests.base import CogWithCommandsBaseTestCase


class MyRatesBaseTestCase(CogWithCommandsBaseTestCase):
    cog_class = AssessmentCog

    def open_my_rates(self, queries=3):
        with self.assertNumQueries(queries):
            async_to_sync(self.cog.my_rates.callback)(self.cog, self.interaction)

        response = self.interaction.edit_original_response.call_args.kwargs
        self.assertEqual(response['content'], self.cog.message_my_rates)
        return response

    def assert_review_field(self, field, assessment, expected_review):
        media = assessment.media
        self.assertEqual(field.name, f'{media.name} - *{assessment.mark:.1f}*')
        self.assertFalse(field.inline)
        self.assertEqual(
            field.value, f'{media.category.name}\n[Link]({media.url})\n{media.description}\n{expected_review}'
        )
        self.assertLessEqual(len(field.value), 1024)
