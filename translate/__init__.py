

import json
from pathlib import Path

from grief.core.bot import Red

from .translate import Translate

async def setup(bot: Red):
    await bot.add_cog(Translate(bot))