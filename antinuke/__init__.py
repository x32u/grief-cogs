import asyncio

from grief.core import VersionInfo, version_info

from .antinuke import AntiNuke

async def setup(bot):
    cog = AntiNuke(bot)
    if version_info >= VersionInfo.from_str("3.5.0"):
        await bot.add_cog(cog)
    else:
        bot.add_cog(cog)
    asyncio.create_task(cog.initialize())
