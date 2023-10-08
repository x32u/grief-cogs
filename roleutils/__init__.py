
import json
from pathlib import Path

from grief.core.bot import Red

from .roleutils import RoleUtils

with open(Path(__file__).parent / "info.json") as fp:
    __red_end_user_data_statement__ = json.load(fp)["end_user_data_statement"]


async def setup(bot: Red) -> None:
    role_utils = RoleUtils(bot)
    await bot.add_cog(role_utils)
