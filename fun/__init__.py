from grief.core.bot import Red

from .fun import Fun


async def setup(bot: Red) -> None:
    await bot.add_cog(Fun(bot))
