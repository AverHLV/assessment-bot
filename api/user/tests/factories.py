from django.contrib.auth import get_user_model

import factory

User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    username = factory.Sequence(lambda n: f'username{n}')
    external_id = factory.Sequence(lambda n: n)

    class Meta:
        model = User

    @classmethod
    def _setup_next_sequence(cls) -> int:
        return 1
