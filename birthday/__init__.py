import contextlib
import importlib
import json
from pathlib import Path

from grief.core import VersionInfo
from grief.core.bot import Red

from . import vexutils
from .birthday import Birthday

async def setup(bot: Red) -> None:
    cog = Birthday(bot)
    await bot.add_cog(cog)
