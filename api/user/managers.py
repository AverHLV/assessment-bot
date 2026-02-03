from django.contrib.auth.models import UserManager as BaseUserManager

import discord


class UserManager(BaseUserManager):
    async def aget_or_create_by_discord(self, discord_user: discord.User):
        defaults = {'username': discord_user.name}
        user, _ = await self.get_queryset().aget_or_create(defaults=defaults, external_id=discord_user.id)
        return user
