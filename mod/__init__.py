from grief.core.bot import Red
from .mod import Mod


async def setup(bot: Red) -> None:
    cog = Mod(bot)
    await bot.add_cog(Mod(bot))
