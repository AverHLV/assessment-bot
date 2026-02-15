import factory.fuzzy

from api.assessment import models
from api.user.tests.factories import UserFactory
from core.utils_tests import pause_date_auto_fields


class MediaFactory(factory.django.DjangoModelFactory):
    name = factory.Sequence(lambda n: f'name{n}')
    category = factory.Iterator(models.MediaCategory.objects.all())
    creator = factory.SubFactory(UserFactory)

    class Meta:
        model = models.Media

    @classmethod
    @pause_date_auto_fields(fields=['create_dt'])
    def _create(cls, *args, **kwargs):
        return super()._create(*args, **kwargs)


class AssessmentFactory(factory.django.DjangoModelFactory):
    mark = factory.fuzzy.FuzzyDecimal(low=1, high=10, precision=0)
    media = factory.SubFactory(MediaFactory)
    user = factory.SubFactory(UserFactory)

    class Meta:
        model = models.Assessment

    @classmethod
    @pause_date_auto_fields(fields=['create_dt'])
    def _create(cls, *args, **kwargs):
        return super()._create(*args, **kwargs)


class PollFactory(factory.django.DjangoModelFactory):
    name = factory.fuzzy.FuzzyText(length=10)
    winner = factory.SubFactory(MediaFactory)

    class Meta:
        model = models.Poll

    @classmethod
    @pause_date_auto_fields(fields=['create_dt'])
    def _create(cls, *args, **kwargs):
        return super()._create(*args, **kwargs)

    @factory.post_generation
    def candidates(self, _create: bool, extracted: list, **_kwargs) -> None:
        if extracted:
            self.candidates.add(*extracted)


class VoteFactory(factory.django.DjangoModelFactory):
    poll = factory.SubFactory(PollFactory)
    voter = factory.SubFactory(UserFactory)

    class Meta:
        model = models.Vote
