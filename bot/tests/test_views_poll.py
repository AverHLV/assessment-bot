from django.db import models
from django.test import TestCase

from asgiref.sync import async_to_sync, sync_to_async

from unittest.mock import AsyncMock, Mock, patch

from api.assessment.tests.factories import MediaFactory, PollFactory, VoteFactory
from api.user.tests.factories import UserFactory
from bot.tests.base import AssertThinkingPlaceholderMixin
from bot.views.poll import PollSelect, PollView


class PollViewTestCase(AssertThinkingPlaceholderMixin, TestCase):
    view_class = PollView

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.candidates = MediaFactory.create_batch(size=2, description='media description', creator=cls.user)
        cls.poll = PollFactory(candidates=cls.candidates)

    def setUp(self):
        self.interaction = AsyncMock()
        # prevent an async operation on view init
        models.prefetch_related_objects([self.poll], 'candidates')

    def get_view(self) -> view_class:
        return self.view_class(user=self.user, poll=self.poll)

    async def test__poll_view__get_embed(self):
        view = self.get_view()
        view.selected_row = 0

        embed = await view.get_embed()

        embed_fields = embed._fields
        self.assertEqual(len(embed_fields), len(self.candidates))
        for n, field in enumerate(embed_fields):
            candidate = self.candidates[n]
            self.assertFalse(field['inline'])
            self.assertIn(str(n + 1), field['name'])
            self.assertIn(candidate.name, field['name'])
            if n == view.selected_row:
                self.assertIn('->', field['name'])
            self.assertIn(candidate.url, field['value'])
            self.assertIn(candidate.description, field['value'])

    async def test__poll_view__get_result_embed(self):
        result_mock, round_mock = Mock(), Mock()
        election_status = 'Status'
        round_mock.candidate_results = [(candidate, n, election_status) for n, candidate in enumerate(self.candidates)]
        result_mock.rounds = [round_mock]
        view = self.get_view()

        embed = await view.get_result_embed(result_mock)

        embed_fields = embed._fields
        self.assertEqual(len(embed_fields), len(round_mock.candidate_results))
        for n, field in enumerate(embed_fields):
            candidate, number_of_votes, status = round_mock.candidate_results[n]
            self.assertFalse(field['inline'])
            self.assertEqual(field['name'], candidate.name)
            self.assertIn(str(number_of_votes), field['value'])
            self.assertIn(election_status.lower(), field['value'])

    async def test__poll_view__select_candidate(self):
        view = self.get_view()
        view.get_embed = AsyncMock()
        candidate = self.candidates[-1]
        candidate_id = candidate.id
        expected_row = self.candidates.index(candidate)

        await view.select_candidate(self.interaction, candidate_id)

        self.assertEqual(view.selected_row, expected_row)
        self.interaction.edit_original_response.assert_called_once_with(
            content=None,
            embed=view.get_embed.return_value,
            view=view,
        )

    async def test__poll_view__swap_item(self):
        view = self.get_view()
        view.get_embed = AsyncMock()
        old_selected_row = 0
        view.selected_row = old_selected_row
        selected_candidate = self.candidates[view.selected_row]
        other_candidate = self.candidates[view.selected_row + 1]

        await view.swap_item(self.interaction, is_up=False)

        expected_selected_row = old_selected_row + 1
        self.assertEqual(view.selected_row, expected_selected_row)
        self.assertEqual(view.candidates.index(selected_candidate), expected_selected_row)
        self.assertEqual(view.candidates.index(other_candidate), old_selected_row)
        self.interaction.edit_original_response.assert_called_once_with(
            content=None,
            embed=view.get_embed.return_value,
            view=view,
        )

    async def test__poll_view__swap_item__no_selected_row(self):
        view = self.get_view()
        await view.swap_item(self.interaction, is_up=False)
        self.interaction.response.defer.assert_called_once()

    async def test__poll_view__swap_item__no_new_row(self):
        view = self.get_view()
        view.selected_row = 0

        await view.swap_item(self.interaction, is_up=True)

        self.interaction.response.defer.assert_called_once()

    @patch('api.assessment.models.Poll.resolve')
    @async_to_sync
    async def test__poll_view__confirm(self, resolve_mock):
        resolve_mock.return_value = 'resolved'
        vote = await sync_to_async(VoteFactory.create)(poll=self.poll, voter=self.user)

        view = self.get_view()
        view.get_result_embed = AsyncMock()

        await view.confirm.callback(self.interaction)

        await vote.arefresh_from_db(fields=['ranks'])
        expected_ranks = [candidate.id for candidate in self.candidates]
        self.assertListEqual(vote.ranks, expected_ranks)

        self.assert_thinking_placeholder(self.interaction, edit=True)
        expected_message = "Saved! I'll protect your vote, promise."
        self.interaction.edit_original_response.assert_called_once_with(content=expected_message, embed=None, view=None)
        expected_message = f"🎉 Ta-da! The poll '{self.poll.name}' is over! 🎉"
        self.interaction.followup.send.assert_called_once_with(
            content=expected_message,
            embed=view.get_result_embed.return_value,
        )

        view.get_result_embed.assert_called_once_with(resolve_mock.return_value)
        resolve_mock.assert_called_once()

    async def test__poll_view__swap_button__callback(self):
        view = self.get_view()
        view.swap_item = AsyncMock()
        swap_button = view._children[2]

        await swap_button.callback(self.interaction)

        view.swap_item.assert_called_once_with(self.interaction, swap_button.is_up)

    @patch('discord.ui.select.selected_values')
    @async_to_sync
    async def test__poll_view__select__callback(self, values_mock):
        view = self.get_view()
        view.select_candidate = AsyncMock()
        candidate_select = view._children[1]
        selected_option_index = 0
        selected_option = candidate_select._underlying.options[selected_option_index]
        expected_candidate_id = candidate_select.candidate_mapping[selected_option_index]

        values_mock.get.return_value.get.return_value = [selected_option.value]

        await candidate_select.callback(self.interaction)

        self.interaction.response.defer.assert_called_once()
        self.assertTrue(selected_option.default)
        values_mock.get.assert_called_once()
        view.select_candidate.assert_called_once_with(self.interaction, candidate_id=expected_candidate_id)


class PollSelectTestCase(TestCase):
    select_class = PollSelect

    def setUp(self):
        self.user = Mock()
        self.interaction = AsyncMock()

        self.candidates = MediaFactory.create_batch(size=2)
        self.poll = PollFactory(candidates=self.candidates)
        models.prefetch_related_objects([self.poll], 'candidates')

        self.select = self.select_class(user=self.user, polls=[self.poll])

    @patch('bot.views.poll.PollView.get_embed', new_callable=AsyncMock)
    @patch('discord.ui.select.selected_values')
    @async_to_sync
    async def test__poll_select__callback(self, values_mock, embed_mock):
        values_mock.get.return_value.get.return_value = [str(self.poll.id)]

        await self.select.callback(self.interaction)

        self.interaction.response.edit_message.assert_called_once()
        _, kwargs = self.interaction.response.edit_message.call_args
        self.assertIsNone(kwargs['content'])
        self.assertIs(kwargs['embed'], embed_mock.return_value)
        view = kwargs['view']
        self.assertIsNone(view.selected_row)
        self.assertEqual(view.user, self.user)
        self.assertEqual(view.poll.id, self.poll.id)
        self.assertListEqual(view.candidates, self.candidates)
        view_elements = view._children
        self.assertEqual(len(view_elements), 4)

        candidate_select = view_elements[1]
        self.assertEqual(candidate_select.row, 0)
        sorted_candidates = sorted(self.candidates, key=lambda x: x.name)
        expected_candidate_mapping = {n: candidate.id for n, candidate in enumerate(sorted_candidates)}
        self.assertDictEqual(candidate_select.candidate_mapping, expected_candidate_mapping)
        options = candidate_select._underlying.options
        self.assertEqual(len(options), len(sorted_candidates))
        for n, option in enumerate(options):
            self.assertEqual(option.label, sorted_candidates[n].name)
            self.assertEqual(option.value, str(n))

        expected_row = 1
        confirm_button = view_elements[0]
        self.assertEqual(confirm_button.row, expected_row)
        up_button, down_button = view_elements[2:]
        self.assertTrue(up_button.is_up)
        self.assertEqual(up_button.row, expected_row)
        self.assertFalse(down_button.is_up)
        self.assertEqual(down_button.row, expected_row)

        values_mock.get.assert_called_once()
        embed_mock.assert_called_once()
