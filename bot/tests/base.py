from django.db.models import QuerySet
from django.test import TestCase

from unittest.mock import AsyncMock, Mock

from api.assessment.models import Assessment
from api.user.tests.factories import UserFactory
from bot.cog import BaseCog
from bot.views.base import BasePaginator


class AsyncTestContextManager:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        return


def get_async_context_manager_mock() -> Mock:
    manager_mock = AsyncMock(spec=AsyncTestContextManager())
    return Mock(return_value=manager_mock)


def get_async_iterator_mock(values: list) -> Mock:
    content_mock = AsyncMock()
    content_mock.__aiter__ = Mock(return_value=content_mock)
    content_mock.__anext__.side_effect = *values, StopAsyncIteration
    return Mock(return_value=content_mock)


class CogBaseTestCase(TestCase):
    cog_class: type[BaseCog] = BaseCog

    def setUp(self):
        self.interaction = AsyncMock()
        self.bot = AsyncMock()
        self.cog = self.cog_class(self.bot)

    def assert_thinking_placeholder(self, interaction: AsyncMock, edit: bool = False) -> None:
        if edit:
            interaction.response.edit_message.assert_called_once_with(
                content=self.cog.message_thinking_placeholder,
                embed=None,
                view=None,
            )
        else:
            interaction.response.send_message.assert_called_once_with(
                content=self.cog.message_thinking_placeholder,
                ephemeral=True,
            )


class CogWithCommandsBaseTestCase(CogBaseTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()

    def setUp(self):
        super().setUp()
        self.interaction.user.id = self.user.external_id


class PaginatorBaseTestCase(CogBaseTestCase):
    paginator_class: type[BasePaginator]
    queryset: QuerySet = Assessment.objects.none()

    def get_paginator(self) -> BasePaginator:
        paginator = self.paginator_class(items_queryset=self.queryset.all(), item_count=0)
        paginator.get_embed = AsyncMock()
        return paginator
