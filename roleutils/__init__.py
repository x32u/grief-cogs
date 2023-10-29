
import json
from pathlib import Path

from grief.core.bot import Red

from .roleutils import RoleUtils




async def setup(bot: Red) -> None:
    role_utils = RoleUtils(bot)
    await bot.add_cog(role_utils)
