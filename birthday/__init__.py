import contextlib
import importlib
import json
from pathlib import Path

from grief.core import VersionInfo
from grief.core.bot import Red

from . import vexutils
from .birthday import Birthday
from .vexutils.meta import out_of_date_check

async def setup(bot: Red) -> None:
    cog = Birthday(bot)
    await out_of_date_check("birthday", cog.__version__)
    await bot.add_cog(cog)
