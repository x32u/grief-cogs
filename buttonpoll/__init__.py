import contextlib
import importlib
import json
from pathlib import Path

import discord
from grief.core import VersionInfo
from grief.core.bot import Red
from grief.core.errors import CogLoadError

from . import vexutils
from .buttonpoll import ButtonPoll
from .vexutils.meta import out_of_date_check




async def setup(bot: Red):
    cog = ButtonPoll(bot)
    await bot.add_cog(cog)
