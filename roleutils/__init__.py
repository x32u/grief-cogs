

from grief.core.bot import Grief

from .roleutils import RoleUtils

async def setup(bot: Grief) -> None:
    role_utils = RoleUtils(bot)
    await bot.add_cog(role_utils)
