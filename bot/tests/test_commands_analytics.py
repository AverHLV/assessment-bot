import discord
import factory
from asgiref.sync import async_to_sync, sync_to_async

from unittest.mock import Mock, patch

from api.assessment.models import Media
from api.assessment.tests.factories import AssessmentFactory, MediaFactory
from api.user.tests.factories import UserFactory
from bot import commands
from bot.tests.base import CogWithCommandsBaseTestCase


class AnalyticsCogTestCase(CogWithCommandsBaseTestCase):
    cog_class = commands.AnalyticsCog

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.users = [cls.user, UserFactory()]
        cls.media = MediaFactory.create_batch(
            size=2,
            assessment_status=Media.AssessmentStatus.COMPLETED,
        )

    def setUp(self):
        super().setUp()

        self.discord_user = Mock()
        self.discord_user.id = self.users[-1].external_id

    def assert_compare_view_embed(self, embed: discord.Embed, prompt: str) -> None:
        embed_fields = embed.fields
        self.assertEqual(len(embed_fields), 5)
        correlation_field = embed_fields[1]
        self.assertEqual(correlation_field.name, 'Pearson correlation')
        self.assertIn(correlation_field.value, prompt)

        compatibility_field = embed_fields[0]
        self.assertEqual(compatibility_field.name, 'Taste compatibility')
        expected_compatibility = (float(correlation_field.value) + 1) / 2 * 100
        self.assertEqual(float(compatibility_field.value[:-1]), expected_compatibility)
        self.assertIn(compatibility_field.value, prompt)

        shared_media_field = embed_fields[2]
        self.assertEqual(shared_media_field.name, 'Shared media')
        expected_shared_media = f'{len(self.media)} / {len(self.media)}'
        self.assertEqual(shared_media_field.value, expected_shared_media)

        mean_field = embed_fields[3]
        self.assertEqual(mean_field.name, 'Average marks')
        for user in self.users:
            self.assertIn(user.username, mean_field.value)

        disagreement_field = embed_fields[4]
        self.assertEqual(disagreement_field.name, 'Biggest disagreements')
        for media in self.media:
            self.assertIn(media.name, disagreement_field.value)

    @patch('bot.commands.analytics.run_create_completion')
    @async_to_sync
    async def test__analytics_cog__compare(self, completion_mock):
        completion_mock.return_value = 'response content'

        assessments = await sync_to_async(AssessmentFactory.create_batch)(
            size=len(self.media) * len(self.users),
            mark=factory.Iterator(range(len(self.media) * len(self.users))),
            media=factory.Iterator(self.media),
            user=factory.Iterator((self.users[0], self.users[0], self.users[1], self.users[1])),
        )

        await self.cog.compare.callback(self.cog, self.interaction, self.discord_user)

        self.assert_thinking_placeholder(self.interaction)

        completion_mock.assert_called_once()
        _, kwargs = completion_mock.call_args
        prompt = kwargs['prompt']
        for assessment in assessments:
            self.assertIn(str(assessment.mark), prompt)
            self.assertIn(assessment.user.username, prompt)
            self.assertIn(assessment.media.name, prompt)
        self.assertEqual(kwargs['default_message'], self.cog.llm_client_message_compare_default_message)

        self.interaction.edit_original_response.assert_called_once()
        _, kwargs = self.interaction.edit_original_response.call_args
        self.assertEqual(kwargs['content'], completion_mock.return_value)
        view = kwargs['view']
        self.assertIsNotNone(view)
        self.assertListEqual(list(view.groups), self.users)
        expected_groups = [assessments[:2], assessments[2:]]
        self.assertListEqual(list(view.groups.values()), expected_groups)

        self.assert_compare_view_embed(kwargs['embed'], prompt)

    @patch('bot.commands.analytics.run_create_completion')
    @async_to_sync
    async def test__analytics_cog__compare__same_users(self, completion_mock):
        await self.cog.compare.callback(
            self=self.cog,
            interaction=self.interaction,
            user=self.discord_user,
            second_user=self.discord_user,
        )

        self.assert_thinking_placeholder(self.interaction)
        self.interaction.edit_original_response.assert_called_once_with(content=self.cog.message_compare_same_users)
        completion_mock.assert_not_called()

    @patch('bot.commands.analytics.run_create_completion')
    @async_to_sync
    async def test__analytics_cog__compare__user_not_found(self, completion_mock):
        self.discord_user.id = -1

        await self.cog.compare.callback(self.cog, self.interaction, self.discord_user)

        self.assert_thinking_placeholder(self.interaction)
        self.interaction.edit_original_response.assert_called_once_with(content=self.cog.message_compare_no_users)
        completion_mock.assert_not_called()

    @patch('bot.commands.analytics.run_create_completion')
    @async_to_sync
    async def test__analytics_cog__compare__no_shared_media(self, completion_mock):
        await sync_to_async(AssessmentFactory.create)(media=self.media[0], user=self.users[0])

        await self.cog.compare.callback(self.cog, self.interaction, self.discord_user)

        self.assert_thinking_placeholder(self.interaction)
        self.interaction.edit_original_response.assert_called_once_with(content=self.cog.message_compare_no_assessments)
        completion_mock.assert_not_called()
