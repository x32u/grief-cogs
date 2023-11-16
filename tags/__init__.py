

import json
import re
from pathlib import Path

from grief.core.bot import Red
from grief.core.errors import CogLoadError

from .core import Tags
from .utils import validate_tagscriptengine

VERSION_RE = re.compile(r"TagScript==(\d\.\d\.\d)")


async def setup(bot: Red) -> None:
    await validate_tagscriptengine(bot)

    tags = Tags(bot)
    await bot.add_cog(tags)
