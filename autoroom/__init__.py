"""Package for AutoRoom cog."""
import json
from pathlib import Path

from grief.core.bot import Red

from .autoroom import AutoRoom




async def setup(bot: Red) -> None:
    """Load AutoRoom cog."""
    cog = AutoRoom(bot)
    await cog.initialize()
    await bot.add_cog(cog)
