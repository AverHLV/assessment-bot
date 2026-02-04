import factory.fuzzy

from api.assessment import models
from api.user.tests.factories import UserFactory


class MediaFactory(factory.django.DjangoModelFactory):
    name = factory.Sequence(lambda n: f'name{n}')
    category = factory.Iterator(models.MediaCategory.objects.all())

    class Meta:
        model = models.Media


class AssessmentFactory(factory.django.DjangoModelFactory):
    mark = factory.fuzzy.FuzzyDecimal(low=1, high=10, precision=0)
    media = factory.SubFactory(MediaFactory)
    user = factory.SubFactory(UserFactory)

    class Meta:
        model = models.Assessment
