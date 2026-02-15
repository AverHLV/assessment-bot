from django.utils import timezone

import factory
from asgiref.sync import sync_to_async

from datetime import timedelta

from api.assessment.tests.factories import MediaFactory, PollFactory, VoteFactory
from api.user.tests.factories import UserFactory
from bot import commands
from bot.tests.base import CommandBaseTestCase


class VoteTestCase(CommandBaseTestCase):
    async def test__vote(self):
        current_time = timezone.now()
        polls = await sync_to_async(PollFactory.create_batch)(
            size=2,
            create_dt=factory.Iterator((current_time, current_time - timedelta(hours=1))),
        )

        await commands.vote.callback(self.interaction)

        self.assert_thinking_placeholder(self.interaction)
        self.interaction.edit_original_response.assert_called_once()
        _, kwargs = self.interaction.edit_original_response.call_args
        expected_message = 'These are the trials prepared for the future. Choose one, and cast your fragile vote.'
        self.assertEqual(kwargs['content'], expected_message)

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

    async def test__vote__no_polls(self):
        await commands.vote.callback(self.interaction)

        self.assert_thinking_placeholder(self.interaction)
        expected_message = 'Silence. There is no future to cast.'
        self.interaction.edit_original_response.assert_called_once_with(content=expected_message)

    async def test__vote__already_voted(self):
        poll = await sync_to_async(PollFactory.create)()
        await sync_to_async(VoteFactory.create)(poll=poll, voter=self.user, ranks=[1])

        await commands.vote.callback(self.interaction)

        self.assert_thinking_placeholder(self.interaction)
        self.interaction.edit_original_response.assert_called_once()
        _, kwargs = self.interaction.edit_original_response.call_args
        self.assertNotIn('view', kwargs)

    async def test__vote__no_own_candidates(self):
        other_user = await sync_to_async(UserFactory.create)()
        candidates = await sync_to_async(MediaFactory.create_batch)(
            size=2,
            creator=factory.Iterator((other_user, self.user)),
        )
        poll = await sync_to_async(PollFactory.create)(candidates=candidates)

        await commands.vote.callback(self.interaction)

        self.assert_thinking_placeholder(self.interaction)
        self.interaction.edit_original_response.assert_called_once()
        _, kwargs = self.interaction.edit_original_response.call_args
        poll_select = kwargs['view']._children[0]
        actual_poll = poll_select.poll_mapping[poll.id]
        actual_candidates = list(actual_poll.candidates.all())
        self.assertListEqual(actual_candidates, [candidates[0]])
