from django.contrib.auth import get_user_model
from django.utils import timezone

import factory
from asgiref.sync import sync_to_async

from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from api.assessment.models import Media
from api.assessment.tests.factories import AssessmentFactory, MediaFactory
from bot import commands
from bot.tests.base import CogWithCommandsBaseTestCase

User = get_user_model()


class AssessmentCogTestCase(CogWithCommandsBaseTestCase):
    cog_class = commands.AssessmentCog

    async def test__assessment_cog__rates(self):
        current_time = timezone.now()
        assessments = await sync_to_async(AssessmentFactory.create_batch)(
            size=2,
            partial=factory.Iterator(('', 'partial')),
            media__create_dt=factory.Iterator((current_time, current_time - timedelta(hours=1))),
            media__assessment_status=Media.AssessmentStatus.COMPLETED,
            media__meta_mark=factory.Iterator((Decimal('5.7'), None)),
        )

        await self.cog.rates.callback(self.cog, self.interaction)

        self.assert_thinking(self.interaction)
        self.interaction.edit_original_response.assert_called_once()
        _, kwargs = self.interaction.edit_original_response.call_args
        self.assertEqual(kwargs['content'], self.cog.message_rates)
        self.assertIsNotNone(kwargs['view'])

        embed_fields = kwargs['embed'].fields
        self.assertEqual(len(embed_fields), len(assessments))
        for n, field in enumerate(embed_fields):
            assessment = assessments[n]
            self.assertFalse(field.inline)
            self.assertIn(assessment.media.name, field.name)
            self.assertIn(assessment.media.category.name, field.name)
            self.assertIn(assessment.user.username, field.value)
            self.assertIn(str(assessment.mark), field.value)
        self.assertIn(str(assessments[0].media.meta_mark), embed_fields[0].value)
        self.assertIn(assessments[1].partial, embed_fields[1].value)

    async def test__assessment_cog__rates__no_media(self):
        await self.cog.rates.callback(self.cog, self.interaction)

        self.assert_thinking(self.interaction)
        self.interaction.edit_original_response.assert_called_once_with(content=self.cog.message_rates_no_assessments)

    async def test__assessment_cog__my_rates(self):
        current_time = timezone.now()
        media = await sync_to_async(MediaFactory.create_batch)(
            size=2,
            meta_mark=factory.Iterator((Decimal('5.7'), None)),
        )
        assessments = await sync_to_async(AssessmentFactory.create_batch)(
            size=len(media),
            create_dt=factory.Iterator((current_time, current_time - timedelta(hours=1))),
            partial=factory.Iterator(('', 'partial')),
            media=factory.Iterator(media),
            user=self.user,
        )

        await self.cog.my_rates.callback(self.cog, self.interaction)

        self.assert_thinking(self.interaction)
        self.interaction.edit_original_response.assert_called_once()
        _, kwargs = self.interaction.edit_original_response.call_args
        self.assertEqual(kwargs['content'], self.cog.message_my_rates)
        self.assertIsNotNone(kwargs['view'])

        embed = kwargs['embed']
        self.assertTrue(embed.footer)
        embed_fields = embed.fields
        self.assertEqual(len(embed_fields), len(assessments))
        for n, field in enumerate(embed_fields):
            assessment = assessments[n]
            self.assertFalse(field.inline)
            self.assertIn(assessment.media.name, field.name)
            self.assertIn(str(assessment.mark), field.name)
            self.assertIn(assessment.media.category.name, field.value)
            self.assertIn(assessment.media.url, field.value)
        self.assertIn(str(assessments[0].media.meta_mark), embed_fields[0].value)
        self.assertIn(assessments[1].partial, embed_fields[1].value)

    async def test__assessment_cog__my_rates__no_assessments(self):
        await self.cog.my_rates.callback(self.cog, self.interaction)

        self.assert_thinking(self.interaction)
        self.interaction.edit_original_response.assert_called_once_with(
            content=self.cog.message_my_rates_no_assessments,
        )

    async def test__assessment_cog__rate(self):
        media = await sync_to_async(MediaFactory.create_batch)(
            size=3,
            assessment_status=Media.AssessmentStatus.IN_PROGRESS,
            assessment_until_dt=timezone.now() + timedelta(days=1),
        )
        await sync_to_async(AssessmentFactory.create)(media=media[-1], user=self.user)
        selected_media = media[:-1]

        await self.cog.rate.callback(self.cog, self.interaction)

        self.assert_thinking(self.interaction)
        self.interaction.edit_original_response.assert_called_once()
        _, kwargs = self.interaction.edit_original_response.call_args
        self.assertEqual(kwargs['content'], self.cog.message_rate)

        view_elements = kwargs['view'].children
        self.assertEqual(len(view_elements), 1)
        media_select = view_elements[0]
        self.assertEqual(media_select.user.id, self.user.id)
        self.assertEqual(len(media_select.options), len(selected_media))
        for n, option in enumerate(media_select.options):
            media_obj = selected_media[n]
            self.assertEqual(option.label, media_obj.name)
            self.assertEqual(option.value, str(media_obj.id))
            self.assertEqual(option.description, media_obj.category.name)

    async def test__assessment_cog__rate__no_media(self):
        self.interaction.user.id = 100
        self.interaction.user.name = 'Discord user'

        await self.cog.rate.callback(self.cog, self.interaction)

        user = await User.objects.filter(external_id=self.interaction.user.id).afirst()
        self.assertIsNotNone(user)
        self.assertEqual(user.username, self.interaction.user.name)

        self.assert_thinking(self.interaction)
        self.interaction.edit_original_response.assert_called_once_with(content=self.cog.message_rate_no_media)

    @patch('bot.cog.close_old_connections')
    def test__assessment_cog__interaction_check(self, close_mock):
        result = self.cog.interaction_check(self.interaction)
        self.assertTrue(result)
        close_mock.assert_called_once()
