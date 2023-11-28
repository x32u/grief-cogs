from grief.core import commands, checks, modlog, Config
import discord
from typing import Optional
from datetime import datetime
from discord.ext import tasks
from grief.core.i18n import Translator, cog_i18n
import logging

log = logging.getLogger("grief.nicknamer")


_ = Translator("NickNamer", __file__)


@cog_i18n(_)
class NickNamer(commands.Cog):
    """Commands to manage a users nickname."""

    async def red_delete_data_for_user(self, *, requester, user_id):
        if requester == "user":
            return
        elif requester == "user_strict":
            data = await self.config.all_guilds()
            for guild_id in data:
                async with self.config.guild_from_id(guild_id).active() as active:
                    for e in active:
                        if e[0] == user_id:
                            active.remove(e)
        elif requester == "owner" or requester == "discord_deleted_user":
            data = await self.config.all_guilds()
            for guild_id in data:
                async with self.config.guild_from_id(guild_id).active() as active:
                    for e in active:
                        if e[0] == user_id:
                            active.remove(e)
                async with self.config.guild_from_id(guild_id).frozen() as frozen:
                    for e in frozen:
                        if e[0] == user_id:
                            frozen.remove(e)

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=190420201535, force_registration=True)
        standard = {
            "nick": "CHANGEME",
            "dm": False,
            "frozen": [],
            "active": [],
        }
        self.config.register_guild(**standard)
        self._rename_tempnicknames.start()

    def cog_unload(self):
        self._rename_tempnicknames.cancel()

    async def initialize(self):
        await self.register_casetypes()

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

    @tasks.loop(minutes=10)
    async def _rename_tempnicknames(self):
        for guild in self.bot.guilds:
            async with self.config.guild(guild).all() as settings:
                if not settings["active"]:
                    continue
                else:
                    for e in settings["active"]:
                        expiry_time = datetime.utcfromtimestamp(e[2])
                        if datetime.utcnow() > expiry_time:
                            if guild.get_member(e[0]):
                                await guild.get_member(e[0]).edit(
                                    nick=e[1], reason=_("Temporary nickname expired.")
                                )
                            settings["active"].remove(e)
                            if settings["dm"]:
                                try:
                                    await guild.get_member(e[0]).send(
                                        _(
                                            "Your nickname in ``{guildname}`` has been reset to your original nickname."
                                        ).format(guildname=guild.name)
                                    )
                                except:
                                    pass

    @checks.mod()
    @commands.command()
    @checks.bot_has_permissions(manage_nicknames=True)
    async def nick(self, ctx, user: discord.Member, *, reason: Optional[str]):
        """Forcibly change a user's nickname to a predefined string."""
        if not reason:
            reason = _("Nickname force-changed")
        try:
            await user.edit(nick=await self.config.guild(ctx.guild).nick())
            await ctx.tick()
        except discord.errors.Forbidden:
            await ctx.send(
                _("Missing permissions.")
            )  # can remove this as the check is made on invoke with the decorator

    @checks.mod()
    @commands.command()
    @checks.bot_has_permissions(manage_nicknames=True)
    async def freezenick(
        self,
        ctx,
        user: discord.Member,
        nickname: str,
        *,
        reason: Optional[str] = "Nickname frozen.",
    ):
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

    @checks.mod()
    @commands.command()
    async def unfreezenick(self, ctx, user: discord.Member):
        """Unfreeze a user's nickname."""
        async with self.config.guild(ctx.guild).frozen() as frozen:
            for e in frozen:
                if user.id in e:
                    frozen.remove(e)
                    await ctx.tick()

    @checks.mod()
    @commands.command()
    @checks.bot_has_permissions(manage_nicknames=True)
    async def tempnick(
        self,
        ctx,
        user: discord.Member,
        duration: commands.TimedeltaConverter,
        nickname: str,
        *,
        reason: Optional[str] = "User has been temporarily renamed.",
    ):
        """Temporarily rename a user.\n**IMPORTANT**: For better performance, temporary nicknames are checked in a 10 minute intervall."""
        valid_nick_check = self.valid_nickname(nickname=nickname)
        if not valid_nick_check:
            return await ctx.send(
                "That nickname is too long. Keep it under 32 characters, please."
            )
        try:
            oldnick = user.nick
            await user.edit(nick=nickname)
            await ctx.tick()
            change_end = datetime.utcnow() + duration
            async with self.config.guild(ctx.guild).active() as active:
                active.append((user.id, oldnick, change_end.timestamp()))
                pass
        except discord.errors.Forbidden:
            await ctx.send(_("Missing permissions."))