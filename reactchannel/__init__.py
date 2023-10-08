"""Package for ReactChannel cog."""
import json
from pathlib import Path

from grief.core.bot import Red

from .reactchannel import ReactChannel

with open(Path(__file__).parent / "info.json") as fp:
    __red_end_user_data_statement__ = json.load(fp)["end_user_data_statement"]


async def setup(bot: Red) -> None:
    """Load ReactChannel cog."""
    cog = ReactChannel(bot)
    await cog.initialize()
    await bot.add_cog(cog)
