from grief.core import errors  # isort:skip
import importlib
import sys
import AAA3A_utils

from grief.core.bot import Red  # isort:skip
from grief.core.utils import get_end_user_data_statement

from .clearchannel import ClearChannel

__red_end_user_data_statement__ = get_end_user_data_statement(file=__file__)


async def setup(bot: Red) -> None:
    cog = ClearChannel(bot)
    await bot.add_cog(cog)
