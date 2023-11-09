import json
from pathlib import Path

from grief.core.bot import Red

from .timeout import Timeout


async def setup(bot: Red) -> None:
    cog = Timeout(bot)
    await bot.add_cog(cog)