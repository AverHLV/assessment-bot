from django import forms
from django.contrib.auth import get_user_model

import discord

from api.assessment.models import Assessment, Media
from bot.forms import AssessmentForm

ASSESSMENT_MARK_FIELD = Assessment._meta.get_field('mark')
ASSESSMENT_PARTIAL_FIELD = Assessment._meta.get_field('partial')

User = get_user_model()


class AssessmentModal(discord.ui.Modal, title='Inscribe Your Judgment'):
    mark = discord.ui.TextInput(
        label='Mark',
        placeholder=ASSESSMENT_MARK_FIELD.help_text,
        min_length=1,
        max_length=3,
    )

    partial = discord.ui.TextInput(
        required=False,
        label='If partial',
        placeholder=ASSESSMENT_PARTIAL_FIELD.help_text,
        max_length=ASSESSMENT_PARTIAL_FIELD.max_length,
        style=discord.TextStyle.long,
    )

    form_class = AssessmentForm

    def __init__(self, *args, user: User, media_id: int, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.media_id = media_id

    def validate(self) -> forms.ModelForm:
        form = self.form_class(data={'mark': self.mark.value, 'partial': self.partial.value})
        form.is_valid()
        return form

    async def create_assessment(self, form: forms.ModelForm) -> None:
        await Assessment.objects.acreate(
            mark=form.cleaned_data['mark'],
            partial=form.cleaned_data['partial'],
            media_id=self.media_id,
            user_id=self.user.id,
        )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        form = self.validate()
        if form.is_valid():
            await self.create_assessment(form)
            # TODO: Provide response messages by LLM
            if form.cleaned_data['partial']:
                msg = 'Hehe... even broken stories leave scars. I have written yours down.'
            else:
                msg = 'So... you have seen it through to the end. Your judgment is carved into the ash.'

        else:
            msg = 'Alas... your words are flawed:\n'
            for field, errors in form.errors.items():
                msg = f'{msg}- {field}: {errors[0]}\n'
            msg = f'{msg}Let the judgment become once more.'

        await interaction.response.send_message(msg, ephemeral=True)


class MediaSelect(discord.ui.Select):
    modal_class = AssessmentModal

    def __init__(self, *args, user: User, media: list[Media], **kwargs):
        kwargs.setdefault('placeholder', 'Pick a story... I`ll watch with you.')
        kwargs['options'] = [
            discord.SelectOption(
                label=media_obj.name,
                value=str(media_obj.id),
                description=media_obj.category.name,
            )
            for media_obj in media
        ]

        super().__init__(*args, **kwargs)
        self.user = user

    async def callback(self, interaction: discord.Interaction) -> None:
        modal = self.modal_class(user=self.user, media_id=int(self.values[0]))
        await interaction.response.send_modal(modal)


class MediaSelectToAssessView(discord.ui.View):
    select_class = MediaSelect

    def __init__(self, *args, user: User, media: list[Media], **kwargs):
        super().__init__(*args, **kwargs)
        self.add_item(self.select_class(user=user, media=media))
