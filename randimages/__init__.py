from grief.core.bot import Grief
from .randimages import RandImages

__red_end_user_data_statement__ = (
    "This cog does not persistently store data or metadata about users."
)


async def setup(bot: Grief):
    cog = RandImages(bot)
    await bot.add_cog(cog)
