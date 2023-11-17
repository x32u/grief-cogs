import asyncio
import logging
import importlib.util

from .say import Say

from typing import TYPE_CHECKING
from discord import app_commands
from grief.core.errors import CogLoadError

if TYPE_CHECKING:
    from grief.core.bot import Red

log = logging.getLogger("grief.say")


async def setup(bot: "Red"):
    await bot.add_cog(Say)