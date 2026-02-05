import factory.fuzzy

from api.assessment import models
from api.user.tests.factories import UserFactory
from core.utils_tests import pause_date_auto_fields


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

    @classmethod
    @pause_date_auto_fields(fields=['create_dt'])
    def _create(cls, *args, **kwargs):
        return super()._create(*args, **kwargs)
