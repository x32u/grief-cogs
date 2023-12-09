

import re
from importlib import reload
from typing import List, Union

import discord
from grief.core import commands
from grief.core.bot import Grief
from grief.core.errors import CogLoadError

from .views import PageSource, PaginatedView

VALID_NAME = r"[\w-]{1,32}"

SLASH_NAME = re.compile(r"^{?(%s)}?$" % VALID_NAME)

ARGUMENT_NAME_DESCRIPTION = re.compile(r"^(%s):(.{1,100})$" % VALID_NAME)


def dev_check(ctx: commands.Context):
    return ctx.bot.get_cog("Dev")


async def menu(ctx: commands.Context, pages: List[Union[str, discord.Embed]]):
    view = PaginatedView(PageSource(pages))
    await view.send_initial_message(ctx)


async def validate_tagscriptengine(bot: Grief, tse_version: str, *, reloaded: bool = False):
    try:
        import TagScriptEngine as tse
    except ImportError as exc:
        raise CogLoadError(
            "The SlashTags cog failed to install TagScriptEngine. Reinstall the cog and restart your "
            "bot. If it continues to fail to load, contact the cog author."
        ) from exc

    commands = [
        "`pip(3) uninstall -y TagScriptEngine`",
        "`pip(3) uninstall -y TagScript`",
        f"`pip(3) install TagScript=={tse_version}`",
    ]
    commands = "\n".join(commands)

    message = (
        "The SlashTags cog attempted to install TagScriptEngine, but the version installed "
        "is outdated. Shut down your bot, then in shell in your venv, run the following "
        f"commands:\n{commands}\nAfter running these commands, restart your bot and reload "
        "SlashTags. If it continues to fail to load, contact the cog author."
    )

    if not hasattr(tse, "VersionInfo"):
        if not reloaded:
            reload(tse)
            await validate_tagscriptengine(bot, tse_version, reloaded=True)
            return

        await bot.send_to_owners(message)
        raise CogLoadError(message)

    if tse.version_info < tse.VersionInfo.from_str(tse_version):
        await bot.send_to_owners(message)
        raise CogLoadError(message)


def chunks(l, n):
    """
    Yield successive n-sized chunks from l.
    https://github.com/flaree/flare-cogs/blob/08b78e33ab814aa4da5422d81a5037ae3df51d4e/commandstats/commandstats.py#L16
    """
    for i in range(0, len(l), n):
        yield l[i : i + n]
