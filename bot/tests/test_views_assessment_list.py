from django.test import TestCase

from unittest.mock import AsyncMock

from api.assessment.models import Assessment
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
