from django.test import TestCase

import factory
from pyrankvote.helpers import ElectionResults

from api.assessment.models import Poll
from api.assessment.tests.factories import MediaFactory, PollFactory, VoteFactory
from api.user.tests.factories import UserFactory


class PollTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.voters = UserFactory.create_batch(size=2)
        cls.candidates = MediaFactory.create_batch(size=len(cls.voters), creator=factory.Iterator(cls.voters))

    def test__poll_resolve(self):
        poll = PollFactory(winner=None, candidates=self.candidates)
        VoteFactory.create_batch(
            size=len(self.voters),
            poll=poll,
            voter=factory.Iterator(self.voters),
            ranks=factory.Iterator(
                (
                    [self.candidates[0].id],
                    [self.candidates[1].id, self.candidates[0].id],
                )
            ),
        )

        with self.assertNumQueries(4):
            result = poll.resolve()

        self.assertIsInstance(result, ElectionResults)
        expected_winner = self.candidates[0]
        winner = result.get_winners()[0]
        self.assertEqual(winner.name, expected_winner.name)
        poll.refresh_from_db(fields=['status', 'winner_id'])
        self.assertEqual(poll.status, Poll.Status.COMPLETED)
        self.assertEqual(poll.winner_id, expected_winner.id)

    def test__poll_resolve__already_completed(self):
        poll = PollFactory(status=Poll.Status.COMPLETED, winner=None, candidates=self.candidates)
        VoteFactory.create_batch(size=len(self.voters), poll=poll, voter=factory.Iterator(self.voters))

        with self.assertNumQueries(0):
            result = poll.resolve()

        self.assertIsNone(result)
        poll.refresh_from_db(fields=['winner_id'])
        self.assertIsNone(poll.winner_id)

    def test__poll_resolve__not_finished(self):
        poll = PollFactory(winner=None, candidates=self.candidates)
        VoteFactory.create_batch(
            size=len(self.voters),
            poll=poll,
            voter=factory.Iterator(self.voters),
            ranks=factory.Iterator(
                (
                    [self.candidates[0].id],
                    [],
                )
            ),
        )

        with self.assertNumQueries(1):
            result = poll.resolve()

        self.assertIsNone(result)
        poll.refresh_from_db(fields=['status', 'winner_id'])
        self.assertEqual(poll.status, Poll.Status.INITIAL)
        self.assertIsNone(poll.winner_id)
