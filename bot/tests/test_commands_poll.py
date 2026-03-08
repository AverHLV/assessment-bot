from django.utils import timezone

import factory
from asgiref.sync import sync_to_async

from datetime import timedelta

from api.assessment.tests.factories import MediaFactory, PollFactory, VoteFactory
from api.user.tests.factories import UserFactory
from bot import commands
from bot.tests.base import CogWithCommandsBaseTestCase


class PollCogTestCase(CogWithCommandsBaseTestCase):
    cog_class = commands.PollCog

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.other_user = UserFactory()
        cls.candidates = MediaFactory.create_batch(
            size=2,
            creator=factory.Iterator((cls.user, cls.other_user)),
        )
        cls.poll = PollFactory(candidates=cls.candidates)

    async def test__poll_cog__vote(self):
        other_poll = await sync_to_async(PollFactory)(
            candidates=self.candidates,
            create_dt=timezone.now() - timedelta(hours=1),
        )
        polls = [self.poll, other_poll]
        await sync_to_async(VoteFactory.create_batch)(size=len(polls), poll=factory.Iterator(polls), voter=self.user)

        await self.cog.vote.callback(self.cog, self.interaction)

        self.assert_thinking_placeholder(self.interaction)
        self.interaction.edit_original_response.assert_called_once()
        _, kwargs = self.interaction.edit_original_response.call_args
        self.assertEqual(kwargs['content'], self.cog.message_poll)

        view_elements = kwargs['view']._children
        self.assertEqual(len(view_elements), 1)
        poll_select = view_elements[0]
        self.assertEqual(poll_select.user.id, self.user.id)
        expected_poll_mapping = {poll.id: poll for poll in polls}
        self.assertDictEqual(poll_select.poll_mapping, expected_poll_mapping)
        options = poll_select._underlying.options
        self.assertEqual(len(options), len(polls))
        for n, option in enumerate(options):
            poll = polls[n]
            self.assertEqual(option.label, poll.name)
            self.assertEqual(option.value, str(poll.id))

    async def test__poll_cog__vote__no_invited(self):
        await self.cog.vote.callback(self.cog, self.interaction)

        self.assert_thinking_placeholder(self.interaction)
        self.interaction.edit_original_response.assert_called_once_with(content=self.cog.message_poll_no_polls)

    async def test__poll_cog__vote__already_voted(self):
        await sync_to_async(VoteFactory.create)(poll=self.poll, voter=self.user, ranks=[1])

        await self.cog.vote.callback(self.cog, self.interaction)

        self.assert_thinking_placeholder(self.interaction)
        self.interaction.edit_original_response.assert_called_once()
        _, kwargs = self.interaction.edit_original_response.call_args
        self.assertNotIn('view', kwargs)

    async def test__poll_cog__vote__no_own_candidates(self):
        await sync_to_async(VoteFactory.create)(poll=self.poll, voter=self.user)

        await self.cog.vote.callback(self.cog, self.interaction)

        self.assert_thinking_placeholder(self.interaction)
        self.interaction.edit_original_response.assert_called_once()
        _, kwargs = self.interaction.edit_original_response.call_args
        poll_select = kwargs['view']._children[0]
        actual_poll = poll_select.poll_mapping[self.poll.id]
        actual_candidates = list(actual_poll.candidates.all())
        expected_candidates = [self.candidates[1]]
        self.assertListEqual(actual_candidates, expected_candidates)
