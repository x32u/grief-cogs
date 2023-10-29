import json
from pathlib import Path

from .notsobot import NotSoBot




async def setup(bot):
    cog = NotSoBot(bot)
    await bot.add_cog(cog)
