from grief.core.bot import errors  # isort:skip
import importlib
import sys

try:
    import AAA3A_utils
except ModuleNotFoundError:
    raise errors.CogLoadError(
        "The needed utils to run the cog were not found. Please execute the command `[p]pipinstall git+https://github.com/AAA3A-AAA3A/AAA3A_utils.git`. A restart of the bot isn't necessary."
    )
modules = sorted(
    [module for module in sys.modules if module.split(".")[0] == "AAA3A_utils"], reverse=True
)
for module in modules:
    try:
        importlib.reload(sys.modules[module])
    except ModuleNotFoundError:
        pass
del AAA3A_utils

from grief.core.bot import Red  # isort:skip
import asyncio

from grief.core.utils import get_end_user_data_statement

from .tools import tools

__red_end_user_data_statement__ = get_end_user_data_statement(file=__file__)

old_editrole = None


async def setup_after_ready(bot: Red) -> None:
    await bot.wait_until_red_ready()
    cog = tools(bot)
    global old_editrole
    if old_editrole := bot.get_command("editrole"):
        bot.remove_command(old_editrole.name)
    await bot.add_cog(cog)


async def setup(bot: Red) -> None:
    asyncio.create_task(setup_after_ready(bot))


def teardown(bot: Red) -> None:
    if old_editrole is not None:
        bot.add_command(old_editrole)
