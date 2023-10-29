import json
from pathlib import Path

from grief.core.bot import Red

from .customhelp import CustomHelp


async def setup(bot: Red) -> None:
    cog = CustomHelp(bot)
    await bot.add_cog(cog)
