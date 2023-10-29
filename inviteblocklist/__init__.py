import json
from pathlib import Path

from grief.core.bot import Red

from .inviteblocklist import InviteBlocklist




async def setup(bot: Red):
    cog = InviteBlocklist(bot)
    await bot.add_cog(cog)
