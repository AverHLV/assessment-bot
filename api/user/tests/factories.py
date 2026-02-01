from django.contrib.auth import get_user_model

import factory

User = get_user_model()

DEFAULT_PASSWORD = 'password'


class UserFactory(factory.django.DjangoModelFactory):
    username = factory.Sequence(lambda n: f'username{n}')
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    email = factory.Faker('email')
    password = factory.django.Password(DEFAULT_PASSWORD)

    class Meta:
        model = User
