

import json
from pathlib import Path

from grief.core.bot import Red

from .reactlog import ReactLog




async def setup(bot: Red):
    await bot.add_cog(ReactLog(bot))
