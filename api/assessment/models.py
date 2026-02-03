from django.contrib.auth import get_user_model
from django.core import validators
from django.core.exceptions import ValidationError
from django.db import models

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
    url = models.URLField()
    description = models.TextField(blank=True)
    assessment_status = models.CharField(choices=AssessmentStatus, default=AssessmentStatus.INITIAL)
    assessment_until_dt = models.DateTimeField(blank=True, null=True)
    category = models.ForeignKey(MediaCategory, on_delete=models.PROTECT, related_name='media')

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
