

import json
from pathlib import Path

from grief.core.bot import Red

from .baron import Baron




async def setup(bot: Red) -> None:
    cog = Baron(bot)
    await bot.add_cog(cog)
