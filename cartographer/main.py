import asyncio
import logging
import typing as t
from datetime import datetime

import discord
from discord.ext import tasks
from grief.core import Config, commands
from grief.core.bot import Grief
from grief.core.i18n import Translator, cog_i18n
from grief.core.utils.chat_formatting import humanize_number

from .common.models import DB
from .common.views import BackupMenu

log = logging.getLogger("red.vrt.cartographer")
_ = Translator("Cartographer", __file__)
RequestType = t.Literal["discord_deleted_user", "owner", "user", "user_strict"]


# redgettext -D main.py common/formatting.py common/models.py common/views.py --command-docstring


@cog_i18n(_)
class Cartographer(commands.Cog):
    """
    Backup & Restore tools for Discord servers.

    This cog can backup & restore the following:
    - Categories (permissions/order)
    - Text channels (permissions/order)
    - Voice channels (permissions/order)
    - Forum channels  (permissions/order)[Not forum posts]
    - Roles (permissions and what members they're assigned to)

    **Caveats**
    Note the following
    - If there are multiple roles, channels, categories, or forums with the same name, only 1 of each will be restored.
     - This is because object IDs cannot be restored so the bot relies on the name of the object.
    - When restoring, some roles may not be fully restored (such as order) if they were higher than the bot's role.
    """

    def __init__(self, bot: Grief):
        super().__init__()
        self.bot = bot
        self.config = Config.get_conf(self, 117, force_registration=True)
        self.config.register_global(db={})

        self.db: DB = DB()
        self.saving = False

    async def cog_load(self) -> None:
        asyncio.create_task(self.initialize())

    async def cog_unload(self) -> None:
        self.auto_backup.cancel()

    async def initialize(self) -> None:
        await self.bot.wait_until_red_ready()
        data = await self.config.db()
        self.db = await asyncio.to_thread(DB.model_validate, data)
        log.info("Config loaded")
        self.auto_backup.start()

    async def save(self) -> None:
        if self.saving:
            return
        try:
            self.saving = True
            dump = await asyncio.to_thread(self.db.model_dump, mode="json")
            await self.config.db.set(dump)
        except Exception as e:
            log.exception("Failed to save config", exc_info=e)
        finally:
            self.saving = False

    @tasks.loop(minutes=1)
    async def auto_backup(self):
        if not self.db.allow_auto_backups:
            return
        now = datetime.now().astimezone()
        save = False
        for guild_id, settings in self.db.configs.items():
            if not settings.auto_backup_interval_hours:
                continue
            if guild_id in self.db.ignored_guilds:
                continue
            if self.db.allowed_guilds and guild_id not in self.db.allowed_guilds:
                continue
            guild = self.bot.get_guild(guild_id)
            if not guild:
                settings.backups.clear()
                continue
            delta_hours = (now.timestamp() - settings.last_backup.timestamp()) / 3600
            if delta_hours > settings.auto_backup_interval_hours:
                await settings.backup(guild)
                save = True
            self.db.cleanup(guild)

        if save:
            await self.save()

    @commands.command(name="backupmenu")
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(administrator=True)
    @commands.guild_only()
    async def backup_menu(self, ctx: commands.Context):
        """Open the Backup/Restore menu"""
        if ctx.guild.id in self.db.ignored_guilds:
            txt = _("This server is in the ingored list!")
            return await ctx.send(txt)
        if self.db.allowed_guilds and ctx.guild.id not in self.db.allowed_guilds:
            txt = _("This server is not in the allowed list!")
            return await ctx.send(txt)

        view = BackupMenu(ctx, self.db)
        try:
            await view.start()
            await view.wait()
        finally:
            await self.save()

    @commands.group(name="backupset")
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def backup_base(self, ctx: commands.Context):
        """Backup & Restore Tools"""

    @backup_base.command(name="backup")
    async def backup_server(self, ctx: commands.Context):
        """Create a backup of this server"""
        if ctx.guild.id in self.db.ignored_guilds:
            txt = _("This server is in the ingored list!")
            return await ctx.send(txt)
        if self.db.allowed_guilds and ctx.guild.id not in self.db.allowed_guilds:
            txt = _("This server is not in the allowed list!")
            return await ctx.send(txt)

        async with ctx.typing():
            conf = self.db.get_conf(ctx.guild)
            await conf.backup(ctx.guild)
            await ctx.send(_("A backup has been created!"))
            await self.save()

    @backup_base.command(name="restorelatest")
    @commands.bot_has_permissions(administrator=True)
    async def restore_server_latest(self, ctx: commands.Context, delete_existing: bool = False):
        """
        Restore the latest backup for this server

        **Arguments**
        - delete_existing: if True, deletes existing channels/roles that aren't part of the backup.
        """
        if ctx.guild.id in self.db.ignored_guilds:
            txt = _("This server is in the ingored list!")
            return await ctx.send(txt)
        if self.db.allowed_guilds and ctx.guild.id not in self.db.allowed_guilds:
            txt = _("This server is not in the allowed list!")
            return await ctx.send(txt)

        async with ctx.typing():
            conf = self.db.get_conf(ctx.guild)
            if not conf.backups:
                txt = _("There are no backups for this guild!")
                return await ctx.send(txt)
            await conf.backups[-1].restore(ctx.guild, ctx.channel, delete_existing)
            await ctx.send(_("Server restore is complete!"))

    @backup_base.command(name="view")
    @commands.is_owner()
    async def view_settings(self, ctx: commands.Context):
        """View current global settings"""
        backups = sum([len(i.backups) for i in self.db.configs.values()])
        ignored = ", ".join([str(i) for i in self.db.ignored_guilds]) if self.db.ignored_guilds else _("None Set")
        allowed = ", ".join([str(i) for i in self.db.allowed_guilds]) if self.db.allowed_guilds else _("None Set")
        txt = _(
            "### Global Settings\n"
            "- Global backups: {}\n"
            "- Max backups per server: {}\n"
            "- Allow auto-backups: {}\n"
            "- Ignored servers: {}\n"
            "- Allowed servers: {}\n"
        ).format(
            humanize_number(backups),
            self.db.max_backups_per_guild,
            self.db.allow_auto_backups,
            ignored,
            allowed,
        )
        await ctx.send(txt)

    @backup_base.command(name="autobackups")
    @commands.is_owner()
    async def toggle_auto_backups(self, ctx: commands.Context):
        """Enable/Disable allowing auto backups"""
        if self.db.allow_auto_backups:
            self.db.allow_auto_backups = False
            txt = _("Auto backups have been **Disabled**")
        else:
            self.db.allow_auto_backups = True
            txt = _("Auto backups have been **Enabled**")
        await ctx.send(txt)
        await self.save()

    @backup_base.command(name="maxbackups")
    @commands.is_owner()
    async def set_max_backups(self, ctx: commands.Context, max_backups: int):
        """Set the max amount of backups a server can have"""
        self.db.max_backups_per_guild = max_backups
        if max_backups == 0:
            txt = _("Max backups set to 0, Cartographer has been **Disabled**")
        else:
            txt = _("Max backup count has been set")
        await ctx.send(txt)
        await self.save()

    @backup_base.command(name="ignore")
    @commands.is_owner()
    async def ignore_list(self, ctx: commands.Context, guild: discord.Guild):
        """Add/Remove a server from the ignore list"""
        if guild.id in self.db.ignored_guilds:
            self.db.ignored_guilds.remove(guild.id)
            txt = _("Server removed from the ignore list")
        else:
            self.db.ignored_guilds.append(guild.id)
            txt = _("Server added to the ignore list")
        await ctx.send(txt)
        await self.save()

    @backup_base.command(name="allow")
    @commands.is_owner()
    async def allow_list(self, ctx: commands.Context, guild: discord.Guild):
        """Add/Remove a server from the allow list"""
        if guild.id in self.db.allowed_guilds:
            self.db.allowed_guilds.remove(guild.id)
            txt = _("Server removed from the allow list")
        else:
            self.db.allowed_guilds.append(guild.id)
            txt = _("Server added to the allow list")
        await ctx.send(txt)
        await self.save()
