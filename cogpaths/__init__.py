from .cogpaths import CogPaths

from grief.core.bot import Red
from grief.core.utils import get_end_user_data_statement

__red_end_user_data_statement__ = get_end_user_data_statement(__file__)


async def setup(bot: Red):
    await bot.add_cog(CogPaths(bot))
