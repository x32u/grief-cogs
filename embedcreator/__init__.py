from .embedcreator import EmbedCreator

from grief.core.bot import Grief
from grief.core.utils import get_end_user_data_statement

__red_end_user_data_statement__ = get_end_user_data_statement(__file__)


async def setup(bot: Grief):
    await bot.add_cog(EmbedCreator(bot))
