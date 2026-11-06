from django.utils import timezone

import factory
from asgiref.sync import async_to_sync

from datetime import timedelta
from unittest.mock import Mock

from api.assessment.tests.factories import AssessmentFactory
from bot.bot import AssessmentBot
from bot.tests.assessment_list_base import MyRatesBaseTestCase


class MyRatesReviewPaginationTestCase(MyRatesBaseTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        now = timezone.now()
        cls.assessments = AssessmentFactory.create_batch(
            size=12,
            user=cls.user,
            create_dt=factory.Iterator([now - timedelta(minutes=n) for n in range(12)]),
            review=factory.Sequence(lambda n: f'Private review {n}'),
            media__name=factory.Sequence(lambda n: f'Story {n:02d}'),
        )
        AssessmentFactory(review='Hidden foreign review', media__name=cls.assessments[0].media.name + ' foreign')

    def open_paginator(self):
        response = self.open_my_rates()
        self.paginator = response['view']
        self.assertEqual(len(response['embed'].fields), 10)
        self.assertEqual(response['embed'].footer.text, 'Page 1/2')
        self.assert_review_field(response['embed'].fields[0], self.assessments[0], self.assessments[0].review)
        self.interaction.reset_mock()

    def test__my_rates__next_page_with_reviews(self):
        self.open_paginator()
        with self.assertNumQueries(1):
            self.click_paginator_button(self.paginator.next)

        response = self.interaction.edit_original_response.call_args.kwargs
        self.assertEqual(response['embed'].footer.text, 'Page 2/2')
        self.assertEqual(len(response['embed'].fields), 2)
        self.assert_review_field(response['embed'].fields[0], self.assessments[10], self.assessments[10].review)

    def test__my_rates__previous_page_with_reviews(self):
        self.open_paginator()
        self.paginator.page = 1

        with self.assertNumQueries(1):
            self.click_paginator_button(self.paginator.previous)

        response = self.interaction.edit_original_response.call_args.kwargs
        self.assertEqual(response['embed'].footer.text, 'Page 1/2')
        self.assert_review_field(response['embed'].fields[0], self.assessments[0], self.assessments[0].review)

    def test__my_rates__page_boundaries(self):
        self.open_paginator()
        with self.assertNumQueries(0):
            self.click_paginator_button(self.paginator.previous)
        self.interaction.response.defer.assert_awaited_once()
        self.interaction.reset_mock()
        self.paginator.page = 1

        with self.assertNumQueries(0):
            self.click_paginator_button(self.paginator.next)

        self.interaction.response.defer.assert_awaited_once()
        self.interaction.edit_original_response.assert_not_called()

    def test__my_rates__search_opens_modal(self):
        self.open_paginator()
        with self.assertNumQueries(0):
            self.click_paginator_button(self.paginator.search)

        modal = self.interaction.response.send_modal.call_args.args[0]
        self.assertIs(modal.paginator, self.paginator)
        self.assertEqual(
            modal.to_dict()['components'],
            [
                {
                    'type': 18,
                    'label': 'Media name',
                    'component': {
                        'type': 4,
                        'style': 1,
                        'label': None,
                        'custom_id': modal.media_name.component.custom_id,
                        'required': True,
                        'placeholder': 'Type a part of a media name.',
                        'max_length': self.assessments[0].media._meta.get_field('name').max_length,
                    },
                },
            ],
        )

    def test__my_rates__search_preserves_ownership_and_review_projection(self):
        self.open_paginator()
        modal = self.paginator.modal_class(paginator=self.paginator)
        modal._refresh(
            self.interaction,
            [
                {
                    'type': 18,
                    'component': {
                        'type': 4,
                        'custom_id': modal.media_name.component.custom_id,
                        'value': self.assessments[0].media.name.upper(),
                    },
                },
            ],
            {},
        )
        self.paginator.page = 1

        with self.assertNumQueries(2):
            async_to_sync(modal.on_submit)(self.interaction)

        response = self.interaction.edit_original_response.call_args.kwargs
        self.assertEqual(len(response['embed'].fields), 1)
        self.assertEqual(response['embed'].footer.text, 'Page 1/1')
        self.assert_review_field(response['embed'].fields[0], self.assessments[0], self.assessments[0].review)

    def test__my_rates__search_no_results(self):
        self.open_paginator()
        modal = self.paginator.modal_class(paginator=self.paginator)
        modal.media_name.component._value = 'Missing story'

        with self.assertNumQueries(2):
            async_to_sync(modal.on_submit)(self.interaction)

        field = self.interaction.edit_original_response.call_args.kwargs['embed'].fields[0]
        self.assertEqual(field.name, 'No items found')
        self.assertEqual(field.value, '')
        self.assertEqual(self.paginator.total_pages, 0)

    def test__my_rates__clear_restores_reviews_and_ownership(self):
        self.open_paginator()
        self.paginator.items_queryset = self.paginator.items_queryset.filter(pk=self.assessments[0].pk)
        self.paginator.page = 1

        with self.assertNumQueries(2):
            self.click_paginator_button(self.paginator.clear)

        response = self.interaction.edit_original_response.call_args.kwargs
        self.assertEqual(response['embed'].footer.text, 'Page 1/2')
        self.assertEqual(len(response['embed'].fields), 10)
        self.assert_review_field(response['embed'].fields[0], self.assessments[0], self.assessments[0].review)
        self.assertNotIn('Hidden foreign review', str(response['embed'].to_dict()))

    def test__my_rates__errors__callback(self):
        self.open_paginator()
        with self.assertNumQueries(0):
            async_to_sync(self.paginator.on_error)(self.interaction, ValueError('Controlled error'), Mock())

        self.interaction.edit_original_response.assert_called_once_with(
            content=AssessmentBot.error_message,
            embed=None,
            view=None,
        )

    def test__my_rates__errors__search_modal(self):
        self.open_paginator()
        modal = self.paginator.modal_class(paginator=self.paginator)

        with self.assertNumQueries(0):
            async_to_sync(modal.on_error)(self.interaction, ValueError('Controlled error'))

        self.interaction.edit_original_response.assert_called_once_with(
            content=AssessmentBot.error_message,
            embed=None,
            view=None,
        )
