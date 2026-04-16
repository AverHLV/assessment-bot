import factory
from asgiref.sync import async_to_sync, sync_to_async

from unittest.mock import Mock, patch

from api.assessment.models import Assessment, Media
from api.assessment.tests.factories import AssessmentFactory, MediaFactory
from bot.bot import AssessmentBot
from bot.tests.base import PaginatorBaseTestCase
from bot.views.assessment_list import AssessmentPaginator, MyAssessmentPaginator


class AssessmentPaginatorTestCase(PaginatorBaseTestCase):
    paginator_class = AssessmentPaginator

    async def test__assessment_paginator__modal__on_submit(self):
        media, _ = await sync_to_async(MediaFactory.create_batch)(
            size=2,
            name=factory.Iterator(('some-media', 'other-media')),
        )

        paginator = self.get_paginator()
        paginator.items_queryset_base = Media.objects.all()

        modal = paginator.modal_class(paginator=paginator)
        modal.media_name._value = media.name[:5].upper()
        await modal.on_submit(self.interaction)

        self.assert_thinking(self.interaction, edit=True)
        item_count = await paginator.items_queryset.acount()
        self.assertEqual(item_count, 1)
        first_media = await paginator.items_queryset.afirst()
        self.assertIsNotNone(first_media)
        self.assertEqual(first_media.id, media.id)

        self.interaction.response.edit_message.assert_called_once()


class MyAssessmentPaginatorTestCase(PaginatorBaseTestCase):
    paginator_class = MyAssessmentPaginator

    @classmethod
    def setUpTestData(cls):
        cls.assessment, _ = AssessmentFactory.create_batch(
            size=2,
            media__name=factory.Iterator(('some-media', 'other-media')),
        )

    async def test__my_assessment_paginator__previous(self):
        paginator = self.get_paginator()
        paginator.page = 1

        await paginator.previous.callback(self.interaction)

        self.assert_thinking(self.interaction, edit=True)
        self.assertFalse(paginator.page)
        self.interaction.edit_original_response.assert_called_once_with(
            content=None,
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

        self.assert_thinking(self.interaction, edit=True)
        self.assertEqual(paginator.page, old_page + 1)
        self.interaction.edit_original_response.assert_called_once_with(
            content=None,
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
        paginator = self.get_paginator()
        paginator.page = 1
        paginator.total_pages = 5
        paginator.items_queryset_base = Assessment.objects.all()
        paginator.items_queryset = paginator.items_queryset_base.filter(id=self.assessment.id)

        await paginator.clear.callback(self.interaction)

        self.assert_thinking(self.interaction, edit=True)
        self.assertFalse(paginator.page)
        self.assertEqual(paginator.total_pages, 1)
        item_count = await paginator.items_queryset.acount()
        self.assertEqual(item_count, 2)

        self.interaction.edit_original_response.assert_called_once_with(
            content=None,
            embed=paginator.get_embed.return_value,
            view=paginator,
        )

    @patch('bot.views.base.close_old_connections')
    @async_to_sync
    async def test__my_assessment_paginator__interaction_check(self, close_mock):
        paginator = self.get_paginator()

        result = await paginator.interaction_check(self.interaction)

        self.assertTrue(result)
        close_mock.assert_called_once()

    async def test__my_assessment_paginator__on_error(self):
        item = Mock()
        error = ValueError('error')
        paginator = self.get_paginator()

        await paginator.on_error(self.interaction, error, item)

        self.interaction.edit_original_response.assert_called_once_with(
            content=AssessmentBot.error_message,
            embed=None,
            view=None,
        )

    async def test__my_assessment_paginator__modal__on_submit(self):
        paginator = self.get_paginator()
        paginator.page = 1
        paginator.total_pages = 5
        paginator.items_queryset_base = Assessment.objects.all()

        modal = paginator.modal_class(paginator=paginator)
        modal.media_name._value = self.assessment.media.name[:5].upper()
        await modal.on_submit(self.interaction)

        self.assert_thinking(self.interaction, edit=True)
        self.assertFalse(paginator.page)
        self.assertEqual(paginator.total_pages, 1)
        item_count = await paginator.items_queryset.acount()
        self.assertEqual(item_count, 1)
        first_assessment = await paginator.items_queryset.afirst()
        self.assertIsNotNone(first_assessment)
        self.assertEqual(first_assessment.id, self.assessment.id)

        self.interaction.edit_original_response.assert_called_once_with(
            content=None,
            embed=paginator.get_embed.return_value,
            view=paginator,
        )
