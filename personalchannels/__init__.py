

from grief.core.bot import Red

from .core import PersonalChannels


async def setup(bot: Red) -> None:
    cog = PersonalChannels(bot)
    await bot.add_cog(cog)
