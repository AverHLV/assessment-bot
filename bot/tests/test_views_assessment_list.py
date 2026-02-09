from django.test import TestCase

import factory
from asgiref.sync import sync_to_async

from unittest.mock import AsyncMock

from api.assessment.models import Assessment
from api.assessment.tests.factories import AssessmentFactory
from bot.views.assessment_list import MyAssessmentPaginator


class MyAssessmentPaginatorTestCase(TestCase):
    paginator_class = MyAssessmentPaginator

    def setUp(self):
        self.interaction = AsyncMock()

    def get_paginator(self):
        assessment_queryset = Assessment.objects.none()
        paginator = self.paginator_class(items_queryset=assessment_queryset, item_count=0)
        paginator.get_embed = AsyncMock()
        return paginator

    async def test__my_assessment_paginator__previous(self):
        paginator = self.get_paginator()
        paginator.page = 1

        await paginator.previous.callback(self.interaction)

        self.assertFalse(paginator.page)
        self.interaction.response.edit_message.assert_called_once_with(
            embed=paginator.get_embed.return_value,
            view=paginator,
        )

    async def test__my_assessment_paginator__previous__no_pages(self):
        paginator = self.get_paginator()
        paginator.page = 0

        await paginator.previous.callback(self.interaction)

        self.interaction.response.defer.assert_called_once()

    async def test__my_assessment_paginator__next(self):
        paginator = self.get_paginator()
        old_page = 1
        paginator.page = old_page
        paginator.total_pages = old_page + 2

        await paginator.next.callback(self.interaction)

        self.assertEqual(paginator.page, old_page + 1)
        self.interaction.response.edit_message.assert_called_once_with(
            embed=paginator.get_embed.return_value,
            view=paginator,
        )

    async def test__my_assessment_paginator__next__no_pages(self):
        paginator = self.get_paginator()
        paginator.page = 1

        await paginator.next.callback(self.interaction)

        self.interaction.response.defer.assert_called_once()

    async def test__my_assessment_paginator__search(self):
        paginator = self.get_paginator()

        await paginator.search.callback(self.interaction)

        self.interaction.response.send_modal.assert_called_once()
        args, _ = self.interaction.response.send_modal.call_args
        modal = args[0]
        self.assertIsInstance(modal, self.paginator_class.modal_class)
        self.assertIs(modal.paginator, paginator)

    async def test__my_assessment_paginator__clear(self):
        assessment, _ = await sync_to_async(AssessmentFactory.create_batch)(size=2)

        paginator = self.get_paginator()
        paginator.page = 1
        paginator.total_pages = 5
        paginator.items_queryset_base = Assessment.objects.all()
        paginator.items_queryset = paginator.items_queryset_base.filter(id=assessment.id)

        await paginator.clear.callback(self.interaction)

        self.assertFalse(paginator.page)
        self.assertEqual(paginator.total_pages, 1)
        item_count = await paginator.items_queryset.acount()
        self.assertEqual(item_count, 2)

        self.interaction.response.edit_message.assert_called_once_with(
            embed=paginator.get_embed.return_value,
            view=paginator,
        )

    async def test__my_assessment_paginator__modal__on_submit(self):
        assessment, _ = await sync_to_async(AssessmentFactory.create_batch)(
            size=2,
            media__name=factory.Iterator(('some-media', 'other-media')),
        )

        paginator = self.get_paginator()
        paginator.page = 1
        paginator.total_pages = 5
        paginator.items_queryset = Assessment.objects.all()

        modal = paginator.modal_class(paginator=paginator)
        modal.media_name._value = assessment.media.name[:5].upper()
        await modal.on_submit(self.interaction)

        self.assertFalse(paginator.page)
        self.assertEqual(paginator.total_pages, 1)
        item_count = await paginator.items_queryset.acount()
        self.assertEqual(item_count, 1)
        first_assessment = await paginator.items_queryset.afirst()
        self.assertIsNotNone(first_assessment)
        self.assertEqual(first_assessment.id, assessment.id)

        self.interaction.response.edit_message.assert_called_once_with(
            embed=paginator.get_embed.return_value,
            view=paginator,
        )
