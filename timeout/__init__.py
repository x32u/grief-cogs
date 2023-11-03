import json
from pathlib import Path

from grief.core.bot import Red

from .timeout import Timeout


async def setup(bot: Red) -> None:
    cog = Timeout(bot)
    await cog.pre_load()
    await bot.add_cog(cog)