from grief.core.bot import Grief
from .usernames import Usernames


async def setup(bot: Grief) -> None:
    await bot.add_cog(Usernames(bot))