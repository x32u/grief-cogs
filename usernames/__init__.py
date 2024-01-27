from grief.core.bot import Grief
from .names import Usernames


async def setup(bot: Grief) -> None:
    await bot.add_cog(Usernames(bot))