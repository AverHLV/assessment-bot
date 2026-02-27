from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.utils import timezone

import discord

from datetime import timedelta

from api.llm import openrouter_client
from bot.bot import bot

User = get_user_model()


@bot.event
async def on_message(message: discord.Message) -> None:
    if message.author.bot or bot.user not in message.mentions:
        return

    async with message.channel.typing():
        user = await User.objects.aget_or_create_by_discord(message.author)
        only_fields = 'mark', 'partial', 'media_id', 'media__name', 'media__category_id', 'media__category__name'
        assessments = (
            user.assessments.select_related('media', 'media__category').only(*only_fields).order_by('-create_dt')[:10]
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

        messages = [{'role': openrouter_client.Role.USER, 'content': prompt}]
        response = await openrouter_client.create_completion(messages=messages)
        response = response['choices'][0]['message']['content']

    await message.reply(response)
