

import re
from typing import TYPE_CHECKING

from discord.utils import escape_mentions
from grief.core import commands

from .errors import SlashTagException
from .objects import SlashTag
from .utils import SLASH_NAME

PASTEBIN_RE = re.compile(r"(?:https?://(?:www\.)?)?pastebin\.com/(?:raw/)?([a-zA-Z0-9]+)")


class TagSearcher:
    def __init__(self, **search_kwargs):
        self.search_kwargs = search_kwargs

    def get_tag(self, ctx: commands.Context, argument: str):
        cog = ctx.bot.get_cog("SlashTags")
        return cog.get_tag_by_name(ctx.guild, argument, **self.search_kwargs)


class TagName(TagSearcher, commands.Converter):
    def __init__(self, *, check_command: bool = True, check_regex: bool = True, **search_kwargs):
        self.check_command = check_command
        self.check_regex = check_regex
        super().__init__(**search_kwargs)

    async def convert(self, ctx: commands.Converter, argument: str) -> str:
        if len(argument) > 32:
            raise commands.BadArgument("Slash tag names may not exceed 32 characters.")
        if self.check_regex:
            argument = argument.lower()
            match = SLASH_NAME.match(argument)
            if not match:
                raise commands.BadArgument(
                    "Slash tag characters must be alphanumeric or '_' or '-'."
                )
            name = match.group(1)
        else:
            name = argument
        if self.check_command and self.get_tag(ctx, name):
            raise commands.BadArgument(f"A slash tag named `{name}` is already registered.")
        return name


class TagConverter(TagSearcher, commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> SlashTag:
        tag = self.get_tag(ctx, argument)
        if not tag:
            raise commands.BadArgument(f'Slash tag "{escape_mentions(argument)}" not found.')
        return tag


GlobalTagConverter = TagConverter(check_global=True, global_priority=True)
GuildTagConverter = TagConverter(check_global=False, global_priority=False)


class TagScriptConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> str:
        try:
            await ctx.cog.validate_tagscript(ctx, argument)
        except SlashTagException as e:
            raise commands.BadArgument(str(e))
        return argument


class PastebinConverter(TagScriptConverter):
    async def convert(self, ctx: commands.Context, argument: str) -> str:
        match = PASTEBIN_RE.match(argument)
        if not match:
            raise commands.BadArgument(f"`{argument}` is not a valid Pastebin link.")
        paste_id = match.group(1)
        async with ctx.cog.session.get(f"https://pastebin.com/raw/{paste_id}") as resp:
            if resp.status != 200:
                raise commands.BadArgument(f"`{argument}` is not a valid Pastebin link.")
            tagscript = await resp.text()
        return await super().convert(ctx, tagscript)


if TYPE_CHECKING:
    TagConverter = SlashTag
    TagScriptConverter = str
    PastebinConverter = str
