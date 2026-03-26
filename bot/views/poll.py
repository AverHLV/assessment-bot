from django.contrib.auth import get_user_model
from django.db import transaction

import discord
from asgiref.sync import sync_to_async
from pyrankvote.helpers import ElectionResults

from api.assessment.models import Media, Poll
from bot.cog import BaseCog
from bot.views.base import BaseEmbedView, BaseView

User = get_user_model()


class CandidateSelect(discord.ui.Select):
    def __init__(self, *args, candidates: list[Media], **kwargs):
        kwargs.setdefault('placeholder', 'Choose a candidate to move...')
        candidates = sorted(candidates, key=lambda x: x.name)
        kwargs['options'] = [
            discord.SelectOption(label=candidate.name, value=str(n)) for n, candidate in enumerate(candidates)
        ]

        super().__init__(*args, **kwargs)
        self.candidate_mapping = {n: candidate.id for n, candidate in enumerate(candidates)}

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()

        selected_row = int(self.values[0])
        for row, option in enumerate(self.options):
            option.default = row == selected_row

        await self.view.select_candidate(interaction, candidate_id=self.candidate_mapping[selected_row])


class CandidateSwapButton(discord.ui.Button):
    def __init__(self, *args, is_up: bool, **kwargs):
        kwargs.setdefault('label', '▲' if is_up else '▼')
        kwargs.setdefault('style', discord.ButtonStyle.secondary)

        super().__init__(*args, **kwargs)
        self.is_up = is_up

    async def callback(self, interaction: discord.Interaction) -> None:
        await self.view.swap_item(interaction, self.is_up)


class PollView(BaseEmbedView):
    select_class = CandidateSelect
    swap_button_class = CandidateSwapButton

    message_vote_saved = "Saved! I'll protect your vote, promise."
    message_poll_resolved = "🎉 Ta-da! The poll '{poll_name}' is over! 🎉"

    def __init__(self, *args, user: User, poll: Poll, **kwargs):
        super().__init__(*args, **kwargs)

        self.selected_row = None
        self.user = user
        self.poll = poll
        self.candidates = list(self.poll.candidates.all())

        self.add_item(self.select_class(row=0, candidates=self.candidates))
        self.add_item(self.swap_button_class(row=1, is_up=True))
        self.add_item(self.swap_button_class(row=1, is_up=False))

    async def get_embed(self) -> discord.Embed:
        embed = discord.Embed(title='Candidates')

        for row, candidate in enumerate(self.candidates):
            name = f'{row + 1}. {candidate.name}'
            if self.selected_row == row:
                name = f'-> {name}'
            value = f'[Link]({candidate.url})\n{candidate.description}'
            value = self.strip_embed_item_value(value)

            embed.add_field(name=name, value=value, inline=False)

        return embed

    async def get_result_embed(self, result: ElectionResults) -> discord.Embed:
        embed = discord.Embed(title='The votes danced around and chose a winner!')

        for candidate, number_of_votes, status in result.rounds[-1].candidate_results:
            value = f'votes: {number_of_votes:.0f}\nstatus: {status.lower()}'
            value = self.strip_embed_item_value(value)
            embed.add_field(name=candidate.name, value=value, inline=False)

        return embed

    async def select_candidate(self, interaction: discord.Interaction, candidate_id: int) -> None:
        for row, candidate in enumerate(self.candidates):
            if candidate.id == candidate_id:
                self.selected_row = row
                break

        await self.refresh(interaction)

    async def swap_item(self, interaction: discord.Interaction, is_up: bool) -> None:
        await interaction.response.defer()
        if self.selected_row is None:
            return

        new_row = self.selected_row - 1 if is_up else self.selected_row + 1
        if new_row < 0 or new_row >= len(self.candidates):
            return

        self.candidates[self.selected_row], self.candidates[new_row] = (
            self.candidates[new_row],
            self.candidates[self.selected_row],
        )
        self.selected_row = new_row
        await self.refresh(interaction)

    @transaction.atomic
    def check_resolve(self) -> ElectionResults | None:
        self.poll = Poll.objects.select_for_update().only('name', 'status').get(id=self.poll.id)
        return self.poll.resolve()

    @discord.ui.button(label='Confirm', style=discord.ButtonStyle.primary, row=1)
    async def confirm(self, interaction: discord.Interaction, _button: discord.Button) -> None:
        await BaseCog.show_thinking_placeholder(interaction, edit=True)
        await self.poll.save_vote(self.user, self.candidates)
        await interaction.edit_original_response(content=self.message_vote_saved, embed=None, view=None)

        result = await sync_to_async(self.check_resolve)()
        if not result:
            return

        message = self.message_poll_resolved.format(poll_name=self.poll.name)
        embed = await self.get_result_embed(result)
        await interaction.followup.send(content=message, embed=embed)


class PollSelect(discord.ui.Select):
    poll_view_class = PollView

    def __init__(self, *args, user: User, polls: list[Poll], **kwargs):
        kwargs.setdefault('placeholder', 'Ehehe... which poll shall we peek into?')
        kwargs['options'] = [discord.SelectOption(label=poll.name, value=str(poll.id)) for poll in polls]

        super().__init__(*args, **kwargs)
        self.user = user
        self.poll_mapping = {poll.id: poll for poll in polls}

    async def callback(self, interaction: discord.Interaction) -> None:
        poll = self.poll_mapping[int(self.values[0])]
        view = self.poll_view_class(user=self.user, poll=poll)
        embed = await view.get_embed()
        await interaction.response.edit_message(content=None, embed=embed, view=view)


class PollSelectView(BaseView):
    select_class = PollSelect

    def __init__(self, *args, user: User, polls: list[Poll], **kwargs):
        super().__init__(*args, **kwargs)
        self.add_item(self.select_class(user=user, polls=polls))
