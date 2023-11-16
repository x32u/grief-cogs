

import json
import re
from pathlib import Path

from grief.core.bot import Red
from grief.core.errors import CogLoadError

from .core import SlashTags
from .http import *  # noqa
from .objects import *  # noqa


async def setup(bot: Red):
    cog = SlashTags(bot)
    await bot.add_cog(cog)
