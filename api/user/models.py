from django.contrib.auth.models import AbstractUser
from django.db import models

from api.user import managers


class User(AbstractUser):
    external_id = models.BigIntegerField(unique=True)

    objects = managers.UserManager()
