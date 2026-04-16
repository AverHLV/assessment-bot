from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.utils import timezone

import discord

from datetime import timedelta

from api.llm import openrouter_client, run_create_completion
from bot.cog import BaseCog

User = get_user_model()


class MessageCog(BaseCog):
    llm_client = openrouter_client

    async def get_user(self, interaction: discord.Message) -> User:
        return await User.objects.aget_or_create_by_discord(interaction.author)

    @BaseCog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or self.bot.user not in message.mentions:
            return

        self.close_old_db_connections()
        async with message.channel.typing():
            user = await self.get_user(message)
            only_fields = 'mark', 'partial', 'media_id', 'media__name', 'media__category_id', 'media__category__name'
            assessments = (
                user.assessments.select_related('media', 'media__category')
                .only(*only_fields)
                .order_by('-create_dt')[:10]
            )

            message_from = timezone.now() - timedelta(hours=3)
            message_history = message.channel.history(limit=5, before=message)
            message_history = [
                {'author': previous_message.author.name, 'message': previous_message.content}
                async for previous_message in message_history
                if previous_message.created_at > message_from
            ]

            context = {
                'user': user,
                'assessments': [assessment async for assessment in assessments],
                'message': message.content,
                'message_history': message_history,
            }
            prompt = render_to_string(template_name='message.html', context=context)
            response = await run_create_completion(self.llm_client, prompt)

        await message.reply(response)
