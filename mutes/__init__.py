from grief.core.bot import Grief
from .mutes import Mutes


async def setup(bot: Grief) -> None:
    cog = Mutes(bot)
    await bot.add_cog(cog)
    cog.create_init_task()
