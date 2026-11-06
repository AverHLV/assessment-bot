from django.db import models

from api.mcp.managers import OAuthNonceManager


class OAuthClient(models.Model):
    client_id = models.CharField(max_length=128, primary_key=True)
    metadata = models.JSONField()
    secret_digest = models.CharField(max_length=64, null=True)

    def __str__(self) -> str:
        return self.client_id


class OAuthNonce(models.Model):
    class Purpose(models.TextChoices):
        DISCORD_STATE = 'discord_state'
        AUTHORIZATION_CODE = 'authorization_code'

    digest = models.CharField(max_length=64, primary_key=True)
    purpose = models.CharField(max_length=32, choices=Purpose.choices)
    expires_at = models.DateTimeField()
    consumed = models.BooleanField(default=False)

    objects = OAuthNonceManager()

    def __str__(self) -> str:
        return f'{self.purpose}: {self.digest}'
