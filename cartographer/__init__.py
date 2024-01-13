from grief.core.bot import Grief

from .main import Cartographer


async def setup(bot: Grief):
    await bot.add_cog(Cartographer(bot))
