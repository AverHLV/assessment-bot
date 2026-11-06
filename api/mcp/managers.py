from django.db import models
from django.utils import timezone

import hashlib


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


class OAuthNonceManager(models.Manager):
    async def consume(self, nonce: str, purpose: str) -> bool:
        return bool(
            await self.filter(
                digest=digest(nonce), purpose=purpose, consumed=False, expires_at__gt=timezone.now()
            ).aupdate(consumed=True)
        )
