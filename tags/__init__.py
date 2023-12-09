

import json
import re
from pathlib import Path

from grief.core.bot import Grief
from grief.core.errors import CogLoadError

from .core import Tags
from .utils import validate_tagscriptengine

VERSION_RE = re.compile(r"TagScript==(\d\.\d\.\d)")


async def setup(bot: Grief) -> None:
    tags = Tags(bot)
    await bot.add_cog(tags)
