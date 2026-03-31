from django.contrib.auth import get_user_model

import discord
import numpy as np

from api.assessment.models import Assessment, Media
from bot.views.base import BaseEmbedView

User = get_user_model()


class CompareView(BaseEmbedView):
    def __init__(self, *args, groups: dict[User, list[Assessment]], **kwargs):
        super().__init__(*args, **kwargs)
        self.groups = groups

    async def get_embed(self) -> discord.Embed:
        embed = discord.Embed(title=f'Comparison: {" vs ".join(user.username for user in self.groups)}')
        vectors = [np.array([float(assessment.mark) for assessment in group]) for group in self.groups.values()]

        correlation = np.corrcoef(*vectors)[0, 1]
        compatibility = (correlation + 1) / 2 * 100
        embed.add_field(name='Taste compatibility', value=f'{compatibility:.2f}%', inline=False)
        embed.add_field(name='Pearson correlation', value=f'{correlation:.2f}', inline=False)

        media_count = await Media.objects.completed().acount()
        embed.add_field(name='Shared media', value=f'{len(vectors[0])} / {media_count}', inline=False)

        mean_value = ''
        for n, user in enumerate(self.groups):
            mean_value = f'{mean_value}{user.username} - *{np.mean(vectors[n]):.2f}*\n'
        embed.add_field(name='Average marks', value=mean_value, inline=False)

        disagreement_value = ''
        disagreement = np.abs(vectors[0] - vectors[1])
        disagreement_indices = np.argsort(disagreement)[::-1][:5]
        first_group = next(iter(self.groups.values()))
        for n, index in enumerate(disagreement_indices, start=1):
            marks = ' vs '.join(str(group[index].mark) for group in self.groups.values())
            disagreement_value = f'{disagreement_value}{n}. {first_group[index].media.name} - *{marks}*\n'
        embed.add_field(name='Biggest disagreements', value=disagreement_value, inline=False)

        return embed

    @staticmethod
    def get_comparison_stats(embed: discord.Embed) -> str:
        comparison_stats = f'{embed.title}\n'
        for field in embed.fields:
            comparison_stats = f'{comparison_stats}{field.name}\n{field.value}\n'
        return comparison_stats
