from grief.core import commands, checks, modlog, Config
import discord
from typing import Optional
from datetime import datetime
from discord.ext import tasks
from grief.core.i18n import Translator, cog_i18n
import logging

log = logging.getLogger("red.dav-cogs.nicknamer")


_ = Translator("NickNamer", __file__)


@cog_i18n(_)
class NickNamer(commands.Cog):
    """NickNamer"""

    def format_help_for_context(self, ctx: commands.Context) -> str:
        # Thanks Sinbad! And Trusty in whose cogs I found this.
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}"

    def __init__(self, bot):
        self.bot = bot
        standard = {"frozen": [], "active": [],}
        self.config.register_guild(**standard)
        self.config = Config.get_conf(self, identifier=190420201535, force_registration=True)

    def valid_nickname(self, nickname: str):
        if len(nickname) <= 32:
            return True
        return False

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if before.nick != after.nick:
            settings = await self.config.guild(after.guild).frozen()
            for e in settings:
                if after.id in e:
                    if after.nick != e[1]:
                        try:
                            await after.edit(nick=e[1], reason="Nickname frozen.")
                        except discord.errors.Forbidden:
                            log.info(
                                f"Missing permissions to change {before.nick} ({before.id}) in {before.guild.id}, removing freeze"
                            )
                            async with self.config.guild(after.guild).frozen() as frozen:
                                for e in frozen:
                                    if e[0] == before.id:
                                        frozen.remove(e)

    @commands.command()
    @commands.has_permissions(manage_nicknames=True)
    @checks.bot_has_permissions(manage_nicknames=True)
    async def freezenick(self, ctx, user: discord.Member, nickname: str, *, reason: Optional[str] = "Nickname frozen."):
        """Freeze a users nickname."""
        name_check = await self.config.guild(ctx.guild).frozen()
        for id in name_check:
            if user.id in id:
                return await ctx.send("User is already frozen. Unfreeze them first.")
        valid_nick_check = self.valid_nickname(nickname=nickname)
        if not valid_nick_check:
            return await ctx.send("That nickname is too long. Keep it under 32 characters, please")

        try:
            await user.edit(nick=nickname)
            await ctx.tick()
            async with self.config.guild(ctx.guild).frozen() as frozen:
                frozen.append((user.id, nickname))
        except discord.errors.Forbidden:
            await ctx.send(_("Missing permissions."))

    @commands.has_permissions(manage_nicknames=True)
    @commands.command()
    async def unfreezenick(self, ctx, user: discord.Member):
        """Unfreeze a user's nickname."""
        async with self.config.guild(ctx.guild).frozen() as frozen:
            for e in frozen:
                if user.id in e:
                    frozen.remove(e)
                    await ctx.tick()
    
    @commands.has_permissions(manage_nicknames=True)
    @commands.command()
    async def nickpurge(self, ctx, are_you_sure: Optional[bool]):
        """Remove all nicknames in the server."""
        if are_you_sure:
            for member in ctx.guild.members:
                if member.nick:
                    await member.edit(nick=None, reason="Nickname purge")
            await ctx.send(_("Nicknames purged"))
        else:
            await ctx.send(
                _(
                    "This will remove the nicknames of all members. If you are sure you want to do this run:\n{command}"
                ).format(command=f"``{ctx.clean_prefix}nickpurge yes``")
            )