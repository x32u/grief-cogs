import contextlib
import datetime
from typing import List, Literal, Optional, Union

import discord
import humanize
from discord.utils import utcnow
from grief.core import Config, commands, modlog
from grief.core.bot import Red
from grief.core.commands.converter import TimedeltaConverter

from .exceptions import TimeoutException

RequestType = Literal["discord_deleted_user", "owner", "user", "user_strict"]


class Timeout(commands.Cog):
    """
    Manage Timeouts.
    """

    def __init__(self, bot: Red) -> None:
        self.bot = bot
        self.config = Config.get_conf(self, identifier=190, force_registration=True)
        default_guild = {"dm": True, "showmod": False, "role_enabled": False}
        self.config.register_guild(**default_guild)

    def format_help_for_context(self, ctx: commands.Context) -> str:
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}"

    @commands.command(aliases=["tt"])
    @commands.guild_only()
    @commands.cooldown(1, 1, commands.BucketType.user)
    @commands.has_permissions(moderate_members=True)
    async def timeout(self, ctx: commands.Context, member: discord.Member, time: TimedeltaConverter(minimum=datetime.timedelta(minutes=1), maximum=datetime.timedelta(days=28), default_unit="minutes", allowed_units=["minutes", "seconds", "hours", "days"],) = None, *, reason: Optional[str] = None,):
        """
        Timeout users.

        `<member_or_role>` is the username/rolename, ID or mention. If provided a role,
        everyone with that role will be timedout.
        `[time]` is the time to mute for. Time is any valid time length such as `45 minutes`
        or `3 days`. If nothing is provided the timeout will be 60 seconds default.
        `[reason]` is the reason for the timeout. Defaults to `None` if nothing is provided.

        Examples:
        `[p]timeout @member 5m talks too much`
        `[p]timeout @member 10m`

        """
        if not time:
            time = datetime.timedelta(seconds=60)
        timestamp = int(datetime.datetime.timestamp(utcnow() + time))
        if isinstance(member, discord.Member):
            if member.is_timed_out():
                return await ctx.send("This user is already timed out.")
            if not await is_allowed_by_hierarchy(ctx.bot, ctx.author, member):
                return await ctx.send("You cannot timeout this user due to hierarchy.")
            if ctx.channel.permissions_for(member).administrator:
                return await ctx.send("You can't timeout an administrator.")
            await self.timeout_user(ctx, member, time, reason)
            return await ctx.send(
                f"{member.mention} has been timed out till <t:{timestamp}:f>."
            )

    @commands.command(aliases=["utt"])
    @commands.guild_only()
    @commands.cooldown(1, 1, commands.BucketType.user)
    @commands.has_permissions(moderate_members=True)
    async def untimeout(self, ctx: commands.Context, member: discord.Member, *, reason: Optional[str] = None,):
        """
        Untimeout users.
        """
        if isinstance(member, discord.Member):
            if not member.is_timed_out():
                return await ctx.send("This user is not timed out.")
            await self.timeout_user(ctx, member, None, reason)
            return await ctx.send(f"Removed timeout from {member.mention}")

async def is_allowed_by_hierarchy(
    bot: Red, user: discord.Member, member: discord.Member
) -> bool:
    return (
        user.guild.owner_id == user.id
        or user.top_role > member.top_role
        or await bot.is_owner(user)
    )