from grief.core.bot import Grief

from .dashboard import Dashboard


async def setup(bot: Grief):
    cog = Dashboard(bot)
    await bot.add_cog(cog)
    await cog.initialize()
