import logging
import re
import discord

from rapidfuzz import process

from typing import Union, Dict, Optional
from datetime import timedelta

from grief.core import commands, i18n

from unidecode import unidecode

from typing import Union, Dict
from datetime import timedelta

from discord.ext.commands.converter import Converter


class ChannelToggle(commands.Converter):
    async def convert(self, ctx: commands.Context, arg: str) -> Union[bool, None]:
        arg = arg.lower()
        if arg not in ["true", "default", "neutral"]:
            raise commands.BadArgument(
                f"`{arg} is not a valid channel state. You use provide `true` or `default`."
            )
        if arg in ["neutral", "default"]:
            ret = None
        elif arg == "true":
            ret = True
        return ret


class LockableChannel(commands.TextChannelConverter):
    async def convert(self, ctx: commands.Context, arg: str) -> Optional[discord.TextChannel]:
        channel = await super().convert(ctx, arg)
        if not ctx.channel.permissions_for(ctx.me).manage_roles:
            raise commands.BadArgument(
                f"I do not have permission to edit permissions in {channel.mention}."
            )
        if not await ctx.bot.is_owner(ctx.author):
            author_perms = channel.permissions_for(ctx.author)
            if not author_perms.read_messages:
                raise commands.BadArgument(
                    f"You do not have permission to view or edit {channel.mention}."
                )
        return channel


# original converter from https://github.com/TrustyJAID/Trusty-cogs/blob/master/serverstats/converters.py#L19
class FuzzyRole(commands.RoleConverter):
    """
    This will accept role ID's, mentions, and perform a fuzzy search for
    roles within the guild and return a list of role objects
    matching partial names
    Guidance code on how to do this from:
    https://github.com/Rapptz/discord.py/blob/rewrite/discord/ext/commands/converter.py#L85
    https://github.com/Cog-Creators/Red-DiscordBot/blob/V3/develop/redbot/cogs/mod/mod.py#L24
    """

    def __init__(self, response: bool = True):
        self.response = response
        super().__init__()

    async def convert(self, ctx: commands.Context, argument: str) -> discord.Role:
        try:
            basic_role = await super().convert(ctx, argument)
        except commands.BadArgument:
            pass
        else:
            return basic_role
        guild = ctx.guild
        result = [
            (r[2], r[1])
            for r in process.extract(
                argument,
                {r: unidecode(r.name) for r in guild.roles},
                limit=None,
                score_cutoff=75,
            )
        ]
        if not result:
            raise commands.BadArgument(f'Role "{argument}" not found.' if self.response else None)

        sorted_result = sorted(result, key=lambda r: r[1], reverse=True)
        return sorted_result[0][0]


class LockableRole(FuzzyRole):
    async def convert(self, ctx: commands.Context, argument: str) -> discord.Role:
        role = await super().convert(ctx, argument)
        if not await ctx.bot.is_owner(ctx.author) and role >= ctx.author.top_role:
            raise commands.BadArgument(
                f"You do not have permission to edit **{role}**'s permissions."
            )
        return role

# the following regex is slightly modified from Red
# it's changed to be slightly more strict on matching with finditer
# this is to prevent "empty" matches when parsing the full reason
# This is also designed more to allow time interval at the beginning or the end of the mute
# to account for those times when you think of adding time *after* already typing out the reason
# https://github.com/Cog-Creators/Red-DiscordBot/blob/V3/develop/redbot/core/commands/converter.py#L55
TIME_RE_STRING = r"|".join(
    [
        r"((?P<weeks>\d+?)\s?(weeks?|w))",
        r"((?P<days>\d+?)\s?(days?|d))",
        r"((?P<hours>\d+?)\s?(hours?|hrs|hr?))",
        r"((?P<minutes>\d+?)\s?(minutes?|mins?|m(?!o)))",  # prevent matching "months"
        r"((?P<seconds>\d+?)\s?(seconds?|secs?|s))",
    ]
)
TIME_RE = re.compile(TIME_RE_STRING, re.I)
TIME_SPLIT = re.compile(r"t(?:ime)?=")

_ = i18n.Translator("Mutes", __file__)


class MuteTime(Converter):
    """
    This will parse my defined multi response pattern and provide usable formats
    to be used in multiple responses
    """

    async def convert(
        self, ctx: commands.Context, argument: str
    ) -> Dict[str, Union[timedelta, str, None]]:
        time_split = TIME_SPLIT.split(argument)
        result: Dict[str, Union[timedelta, str, None]] = {}
        if time_split:
            maybe_time = time_split[-1]
        else:
            maybe_time = argument

        time_data = {}
        for time in TIME_RE.finditer(maybe_time):
            argument = argument.replace(time[0], "")
            for k, v in time.groupdict().items():
                if v:
                    time_data[k] = int(v)
        if time_data:
            try:
                result["duration"] = timedelta(**time_data)
            except OverflowError:
                raise commands.BadArgument(
                    _("The time provided is too long; use a more reasonable time.")
                )
        result["reason"] = argument.strip()
        return result
