from django.contrib.auth import get_user_model
from django.contrib.postgres.fields import ArrayField
from django.core import validators
from django.core.exceptions import ValidationError
from django.db import models

import pyrankvote
from pyrankvote.helpers import ElectionResults

from decimal import Decimal

from api.assessment import managers
from core.models import Directory, TimeStamped

User = get_user_model()


def validate_half_step(value: Decimal) -> None:
    if (value * Decimal('2')) % Decimal('1'):
        raise ValidationError('Value must be an integer or end with .5.')


class MediaCategory(Directory):
    class Code(models.TextChoices):
        MOVIE = 'movie'
        SERIAL = 'serial'
        ANIME = 'anime'
        GAME = 'game'
        BOOK = 'book'
        SONG = 'song'
        VIDEO = 'video'

    code = models.CharField(max_length=100, unique=True, choices=Code)


class Media(TimeStamped):
    class AssessmentStatus(models.TextChoices):
        INITIAL = 'initial'
        IN_PROGRESS = 'in_progress'
        COMPLETED = 'completed'

    name = models.CharField(max_length=300, db_index=True)
    url = models.URLField(help_text='URL that describes the media, such as an IMDb page.')
    description = models.TextField(blank=True, help_text='Description for quick media memorization.')
    assessment_status = models.CharField(choices=AssessmentStatus, default=AssessmentStatus.INITIAL)
    assessment_until_dt = models.DateTimeField(blank=True, null=True)

    category = models.ForeignKey(MediaCategory, on_delete=models.PROTECT, related_name='media')
    creator = models.ForeignKey(User, on_delete=models.PROTECT, related_name='media')

    objects = managers.MediaQuerySet.as_manager()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['name', 'category'], name='uq_media_name_currency'),
        ]

    def __str__(self):
        return f'{type(self).__name__} {self.id}: {self.name}'


class Assessment(models.Model):
    mark = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        validators=[
            validators.MinValueValidator(Decimal('1')),
            validators.MaxValueValidator(Decimal('10')),
            validate_half_step,
        ],
        help_text='Your mark, from 1 to 10 in half steps.',
    )
    partial = models.CharField(
        max_length=300,
        blank=True,
        help_text='Indicates that the media has been partially reviewed, for example, 5 / 10 episodes of an anime.',
    )
    create_dt = models.DateTimeField(auto_now_add=True)

    media = models.ForeignKey(Media, on_delete=models.PROTECT, related_name='assessments')
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name='assessments')

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['media', 'user'], name='uq_assessment_media_user'),
        ]

    def __str__(self):
        return f'{type(self).__name__} {self.user_id}: {self.media_id}'


class Poll(TimeStamped):
    class Status(models.TextChoices):
        INITIAL = 'initial'
        COMPLETED = 'completed'

    name = models.CharField(max_length=300)
    status = models.CharField(choices=Status, default=Status.INITIAL)

    winner = models.ForeignKey(Media, on_delete=models.PROTECT, related_name='winning_polls', blank=True, null=True)
    candidates = models.ManyToManyField(Media, related_name='polls')
    voters = models.ManyToManyField(
        User,
        related_name='polls',
        through='assessment.Vote',
        through_fields=('poll', 'voter'),
    )

    objects = managers.PollQuerySet.as_manager()

    def __str__(self):
        return f'{type(self).__name__} {self.id}: {self.name}'

    @property
    def is_completed(self) -> bool:
        return self.status == self.Status.COMPLETED

    def complete(self, winner_id: int, save: bool = True) -> None:
        self.winner_id = winner_id
        self.status = self.Status.COMPLETED
        if save:
            self.save(update_fields=['status', 'winner_id', 'update_dt'])

    def resolve(self, save: bool = True) -> ElectionResults | None:
        if self.is_completed or self.votes.filter(ranks__len=0).exists():
            return

        candidate_mapping = {
            candidate.id: pyrankvote.Candidate(candidate.name) for candidate in self.candidates.only('name').all()
        }
        ballots = [
            pyrankvote.Ballot(
                ranked_candidates=[candidate_mapping[candidate_id] for candidate_id in vote.ranks],
            )
            for vote in self.votes.all()
        ]
        result = pyrankvote.instant_runoff_voting(candidates=list(candidate_mapping.values()), ballots=ballots)

        winner = result.get_winners()[0]
        for candidate_id, candidate in candidate_mapping.items():
            if candidate.name == winner.name:
                self.complete(candidate_id, save=save)
                break

        return result

    async def save_vote(self, user: User, candidates: list[Media]) -> None:
        ranks = [candidate.id for candidate in candidates]
        await self.votes.filter(voter_id=user.id).aupdate(ranks=ranks)


class Vote(models.Model):
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE, related_name='votes')
    voter = models.ForeignKey(User, on_delete=models.PROTECT, related_name='votes')
    ranks = ArrayField(models.BigIntegerField(), blank=True, default=list)

    def __str__(self):
        return f'{type(self).__name__} {self.poll_id}: {self.voter_id}'
