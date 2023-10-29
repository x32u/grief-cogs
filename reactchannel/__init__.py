"""Package for ReactChannel cog."""
import json
from pathlib import Path

from grief.core.bot import Red

from .reactchannel import ReactChannel




async def setup(bot: Red) -> None:
    """Load ReactChannel cog."""
    cog = ReactChannel(bot)
    await cog.initialize()
    await bot.add_cog(cog)
