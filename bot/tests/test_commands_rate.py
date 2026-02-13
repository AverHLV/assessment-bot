from django.contrib.auth import get_user_model
from django.utils import timezone

import factory
from asgiref.sync import sync_to_async

from datetime import timedelta

from api.assessment.models import Media
from api.assessment.tests.factories import AssessmentFactory, MediaFactory
from bot import commands
from bot.tests.base import CommandBaseTestCase

User = get_user_model()


class RatesTestCase(CommandBaseTestCase):
    async def test__rates(self):
        current_time = timezone.now()
        assessments = await sync_to_async(AssessmentFactory.create_batch)(
            size=2,
            partial=factory.Iterator(('', 'partial')),
            media__create_dt=factory.Iterator((current_time, current_time - timedelta(hours=1))),
            media__assessment_status=Media.AssessmentStatus.COMPLETED,
        )

        await commands.rates.callback(self.interaction)

        self.assert_thinking_placeholder(self.interaction)
        self.interaction.edit_original_response.assert_called_once()
        _, kwargs = self.interaction.edit_original_response.call_args
        expected_message = 'Stories, scorched by opinions. I kept them for you.'
        self.assertEqual(kwargs['content'], expected_message)
        self.assertIsNotNone(kwargs['view'])

        embed = kwargs['embed']
        embed_fields = embed._fields
        self.assertEqual(len(embed_fields), len(assessments))
        for n, field in enumerate(embed_fields):
            assessment = assessments[n]
            self.assertFalse(field['inline'])
            self.assertIn(assessment.media.name, field['name'])
            self.assertIn(assessment.media.category.name, field['name'])
            self.assertIn(assessment.user.username, field['value'])
            self.assertIn(str(assessment.mark), field['value'])
        self.assertIn(assessments[1].partial, embed_fields[1]['value'])

    async def test__rates__no_media(self):
        await commands.rates.callback(self.interaction)

        self.assert_thinking_placeholder(self.interaction)
        expected_message = 'I searched everywhere. Not a single story survived.'
        self.interaction.edit_original_response.assert_called_once_with(content=expected_message)


class MyRatesTestCase(CommandBaseTestCase):
    async def test__my_rates(self):
        current_time = timezone.now()
        media = await sync_to_async(MediaFactory.create_batch)(size=2)
        assessments = await sync_to_async(AssessmentFactory.create_batch)(
            size=len(media),
            create_dt=factory.Iterator((current_time, current_time - timedelta(hours=1))),
            partial=factory.Iterator(('', 'partial')),
            media=factory.Iterator(media),
            user=self.user,
        )

        await commands.my_rates.callback(self.interaction)

        self.assert_thinking_placeholder(self.interaction)
        self.interaction.edit_original_response.assert_called_once()
        _, kwargs = self.interaction.edit_original_response.call_args
        expected_message = 'These are your past verdicts. Heavy, warm, and a little embarrassing, but precious.'
        self.assertEqual(kwargs['content'], expected_message)
        self.assertIsNotNone(kwargs['view'])

        embed = kwargs['embed']
        self.assertTrue(embed._footer)
        embed_fields = embed._fields
        self.assertEqual(len(embed_fields), len(assessments))
        for n, field in enumerate(embed_fields):
            assessment = assessments[n]
            self.assertFalse(field['inline'])
            self.assertIn(assessment.media.name, field['name'])
            self.assertIn(str(assessment.mark), field['name'])
            self.assertIn(assessment.media.category.name, field['value'])
            self.assertIn(assessment.media.url, field['value'])
        self.assertIn(assessments[1].partial, embed_fields[1]['value'])

    async def test__my_rates__no_assessments(self):
        await commands.my_rates.callback(self.interaction)

        self.assert_thinking_placeholder(self.interaction)
        expected_message = 'Only cold ash remains. You have judged nothing... or perhaps I have already forgotten.'
        self.interaction.edit_original_response.assert_called_once_with(content=expected_message)


class RateTestCase(CommandBaseTestCase):
    async def test__rate(self):
        media = await sync_to_async(MediaFactory.create_batch)(
            size=3,
            assessment_status=Media.AssessmentStatus.IN_PROGRESS,
            assessment_until_dt=timezone.now() + timedelta(days=1),
        )
        await sync_to_async(AssessmentFactory.create)(media=media[-1], user=self.user)
        selected_media = media[:-1]

        await commands.rate.callback(self.interaction)

        self.assert_thinking_placeholder(self.interaction)
        self.interaction.edit_original_response.assert_called_once()
        _, kwargs = self.interaction.edit_original_response.call_args
        expected_message = 'Choose a story from the ashes...'
        self.assertEqual(kwargs['content'], expected_message)

        view_elements = kwargs['view']._children
        self.assertEqual(len(view_elements), 1)
        media_select = view_elements[0]
        self.assertEqual(media_select.user.id, self.user.id)
        options = media_select._underlying.options
        self.assertEqual(len(options), len(selected_media))
        for n, option in enumerate(options):
            media_obj = selected_media[n]
            self.assertEqual(option.label, media_obj.name)
            self.assertEqual(option.value, str(media_obj.id))
            self.assertEqual(option.description, media_obj.category.name)

    async def test__rate__no_media(self):
        self.interaction.user.id = 100
        self.interaction.user.name = 'Discord user'

        await commands.rate.callback(self.interaction)

        user = await User.objects.filter(external_id=self.interaction.user.id).afirst()
        self.assertIsNotNone(user)
        self.assertEqual(user.username, self.interaction.user.name)

        self.assert_thinking_placeholder(self.interaction)
        expected_message = 'The ashes are silent... There is nothing left for you to judge.'
        self.interaction.edit_original_response.assert_called_once_with(content=expected_message)
