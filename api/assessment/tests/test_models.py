from django.test import TestCase

import factory
from asgiref.sync import async_to_sync, sync_to_async
from pyrankvote.helpers import ElectionResults

from decimal import Decimal
from unittest.mock import patch

from api.assessment import errors
from api.assessment.clients import AsyncOMDbClient
from api.assessment.models import MediaCategory, Poll
from api.assessment.tests.factories import MediaFactory, PollFactory, VoteFactory
from api.user.tests.factories import UserFactory


class MediaTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.movie_category = MediaCategory.objects.movie()
        cls.game_category = MediaCategory.objects.game()

    def setUp(self):
        self.name = 'media name'
        self.response_data = {'imdbRating': '5.7543'}

    @patch('api.assessment.models.omdb_client.search')
    @async_to_sync
    async def test__media_populate_meta_mark(self, search_mock):
        search_mock.return_value = self.response_data
        media = await sync_to_async(MediaFactory.create)(name=self.name, category=self.movie_category)

        await media.populate_meta_mark()

        await media.arefresh_from_db(fields=['meta_mark'])
        expected_meta_mark = round(Decimal(self.response_data['imdbRating']), 1)
        self.assertEqual(media.meta_mark, expected_meta_mark)
        search_mock.assert_called_once_with(title=self.name)

    @patch('api.assessment.models.omdb_client.search')
    @async_to_sync
    async def test__media_populate_meta_mark__unsupported_category(self, search_mock):
        media = await sync_to_async(MediaFactory.create)(name=self.name, category=self.game_category)

        await media.populate_meta_mark()

        await media.arefresh_from_db(fields=['meta_mark'])
        self.assertIsNone(media.meta_mark)
        search_mock.assert_not_called()

    @patch('api.assessment.models.omdb_client.search')
    @async_to_sync
    async def test__media_populate_meta_mark__not_found(self, search_mock):
        search_mock.side_effect = errors.OMDbError(error=AsyncOMDbClient.ErrorMessage.NOT_FOUND)
        media = await sync_to_async(MediaFactory.create)(name=self.name, category=self.movie_category)

        await media.populate_meta_mark()

        await media.arefresh_from_db(fields=['meta_mark'])
        self.assertIsNone(media.meta_mark)
        search_mock.assert_called_once()


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
