from .nicknamer import NickNamer
from pathlib import Path
import json




async def setup(bot):
    cog = NickNamer(bot)
    await cog.initialize()
    await bot.add_cog(cog)
