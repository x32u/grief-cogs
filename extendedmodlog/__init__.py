import json
from pathlib import Path

from .extendedmodlog import ExtendedModLog




async def setup(bot):
    cog = ExtendedModLog(bot)
    await cog.initialize()
    await bot.add_cog(cog)
