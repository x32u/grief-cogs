from grief.core.bot import Red
from .mod import Mod
from .mutes import Mutes


async def setup(bot: Red) -> None:
    cog = Mod(bot)
    await bot.add_cog(Mod(bot))
    cog.create_init_task()
