from grief.core.bot import Red

from .tools import Admin


async def setup(bot: Red) -> None:
    await bot.add_cog(Admin(bot))
