from django.utils import timezone

import factory

from datetime import timedelta

from api.mcp.models import OAuthClient, OAuthNonce


class OAuthClientFactory(factory.django.DjangoModelFactory):
    client_id = factory.Sequence(lambda n: f'client-{n}')
    metadata = factory.LazyFunction(lambda: {'redirect_uris': ['https://claude.ai/callback']})
    secret_digest = factory.Sequence(lambda n: f'{n:064x}')

    class Meta:
        model = OAuthClient


class OAuthNonceFactory(factory.django.DjangoModelFactory):
    digest = factory.Sequence(lambda n: f'{n:064x}')
    purpose = OAuthNonce.Purpose.AUTHORIZATION_CODE
    expires_at = factory.LazyFunction(lambda: timezone.now() + timedelta(minutes=10))

    class Meta:
        model = OAuthNonce
