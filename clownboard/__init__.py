import json
from pathlib import Path

from .clownboard import Clownboard




async def setup(bot):
    cog = Clownboard(bot)
    await bot.add_cog(cog)
