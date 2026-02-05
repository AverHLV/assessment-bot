from django.contrib.auth import get_user_model
from django.test import TestCase

from asgiref.sync import sync_to_async

from unittest.mock import AsyncMock

from api.user.tests.factories import UserFactory

User = get_user_model()


class CommandBaseTestCase(TestCase):
    def setUp(self):
        self.interaction = AsyncMock()

    async def get_auth_user(self) -> User:
        user = await sync_to_async(UserFactory.create)()
        self.interaction.user.id = user.external_id
        return user

    @staticmethod
    def assert_thinking_placeholder(interaction: AsyncMock) -> None:
        interaction.response.defer.assert_called_once_with(ephemeral=True)
        expected_message = 'My gears turn, ah - still hot from the past...'
        interaction.followup.send.assert_called_once_with(expected_message, ephemeral=True)
