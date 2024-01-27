from grief.core.bot import Grief
from .names import Names


async def setup(bot: Grief) -> None:
    await bot.add_cog(Names(bot))