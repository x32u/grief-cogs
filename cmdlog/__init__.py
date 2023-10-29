import contextlib
import importlib
import json
from pathlib import Path

from grief.core import VersionInfo
from grief.core.bot import Red

from . import vexutils
from .cmdlog import CmdLog
from .vexutils.meta import out_of_date_check




async def setup(bot: Red):
    cog = CmdLog(bot)
    await bot.add_cog(cog)
