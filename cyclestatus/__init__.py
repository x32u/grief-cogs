import json
import pathlib

from grief.core.bot import Red

from .cycle_status import CycleStatus


async def setup(bot: Red):
    await bot.add_cog(CycleStatus(bot))
