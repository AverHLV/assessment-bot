from discord import Intents
from discord.ext import commands


class AssessmentBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        intents = Intents.default()
        intents.message_content = True
        kwargs.setdefault('intents', intents)

        super().__init__(*args, **kwargs)


bot = AssessmentBot(command_prefix='!')
