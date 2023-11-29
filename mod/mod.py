import asyncio
import logging
import re
from abc import ABC
from collections import defaultdict
from typing import Literal
import discord
import logging

from copy import copy
from typing import List, Literal, Optional, Union

from grief.core import Config, commands
from grief.core.bot import Red
from grief.core.i18n import Translator, cog_i18n
from grief.core.utils import AsyncIter
from grief.core.utils._internal_utils import send_to_owners_with_prefix_replaced
from grief.core.utils.chat_formatting import inline
from grief.core.utils.views import ConfirmView
from .events import Events
from .kickban import KickBanMixin
from .names import ModInfo
from .settings import ModSettings
from grief.core.utils.chat_formatting import box, humanize_list
from grief.core.utils.mod import get_audit_reason
from datetime import timedelta
from grief.core.utils.chat_formatting import humanize_timedelta

from .converters import ChannelToggle, LockableChannel, LockableRole

from AAA3A_utils import Cog, CogsUtils, Settings
from AAA3A_utils.settings import CustomMessageConverter

from grief.core.utils.predicates import MessagePredicate

from discord.utils import utcnow
from grief.core import Config, commands, modlog
from grief.core.bot import Red
from grief.core.commands.converter import TimedeltaConverter
import datetime
from typing import Any, Dict, Final, List, Literal, Optional

_ = T_ = Translator("Mod", __file__)

__version__ = "1.2.0"


class CompositeMetaClass(type(commands.Cog), type(ABC)):
    """
    This allows the metaclass used for proper type detection to
    coexist with discord.py's metaclass
    """

    pass


@cog_i18n(_)
class Mod(
    ModSettings,
    Events,
    KickBanMixin,
    ModInfo,
    commands.Cog,
    metaclass=CompositeMetaClass,
):
    """Moderation tools."""

    default_global_settings = {
        "version": "",
        "track_all_names": True,
    }

    default_guild_settings = {
        "mention_spam": {"ban": None, "kick": None, "warn": None, "strict": False},
        "delete_repeats": -1,
        "ignored": False,
        "respect_hierarchy": True,
        "delete_delay": -1,
        "reinvite_on_unban": True,
        "current_tempbans": [],
        "dm_on_kickban": True,
        "default_days": 0,
        "default_tempban_duration": 60 * 60 * 24,
        "track_nicknames": True,
    }

    default_channel_settings = {"ignored": False}

    default_member_settings = {"past_nicks": [], "perms_cache": {}, "banned_until": False}

    default_user_settings = {"past_names": []}

    def __init__(self, bot: Red):
        super().__init__()
        self.bot = bot

        self.config = Config.get_conf(self, 4961522000, force_registration=True)
        self.config.register_global(**self.default_global_settings)
        self.config.register_guild(**self.default_guild_settings)
        self.config.register_channel(**self.default_channel_settings)
        self.config.register_member(**self.default_member_settings)
        self.config.register_user(**self.default_user_settings)
        self.cache: dict = {}
        self.tban_expiry_task = asyncio.create_task(self.tempban_expirations_task())
        self.last_case: dict = defaultdict(dict)
        
        default_guild: Dict[str, Union[bool, List[int]]] = {
            "toggle": False,
            "ignored_channels": [],
        }
        self.config.register_guild(**default_guild)

    async def red_delete_data_for_user(
        self,
        *,
        requester: Literal["discord_deleted_user", "owner", "user", "user_strict"],
        user_id: int,
    ):
        if requester != "discord_deleted_user":
            return

        all_members = await self.config.all_members()

        async for guild_id, guild_data in AsyncIter(all_members.items(), steps=100):
            if user_id in guild_data:
                await self.config.member_from_ids(guild_id, user_id).clear()

        await self.config.user_from_id(user_id).clear()

        guild_data = await self.config.all_guilds()

        async for guild_id, guild_data in AsyncIter(guild_data.items(), steps=100):
            if user_id in guild_data["current_tempbans"]:
                async with self.config.guild_from_id(guild_id).current_tempbans() as tbs:
                    try:
                        tbs.remove(user_id)
                    except ValueError:
                        pass
                    # possible with a context switch between here and getting all guilds

    async def cog_load(self) -> None:
        await self._maybe_update_config()

    def cog_unload(self):
        self.tban_expiry_task.cancel()
    
    async def timeout_user(
        self,
        ctx: commands.Context,
        member: discord.Member,
        time: Optional[datetime.timedelta],
        reason: Optional[str] = None,) -> None:
        await member.timeout(time, reason=reason)

    async def _maybe_update_config(self):
        """Maybe update `delete_delay` value set by Config prior to Mod 1.0.0."""
        if not await self.config.version():
            guild_dict = await self.config.all_guilds()
            async for guild_id, info in AsyncIter(guild_dict.items(), steps=25):
                delete_repeats = info.get("delete_repeats", False)
                if delete_repeats:
                    val = 3
                else:
                    val = -1
                await self.config.guild_from_id(guild_id).delete_repeats.set(val)
            await self.config.version.set("1.0.0")  # set version of last update
        if await self.config.version() < "1.1.0":
            message_sent = False
            async for e in AsyncIter((await self.config.all_channels()).values(), steps=25):
                if e["ignored"] is not False:
                    msg = _(
                        "Ignored guilds and channels have been moved. "
                        "Please use {command} to migrate the old settings."
                    ).format(command=inline("[p]moveignoredchannels"))
                    asyncio.create_task(send_to_owners_with_prefix_replaced(self.bot, msg))
                    message_sent = True
                    break
            if message_sent is False:
                async for e in AsyncIter((await self.config.all_guilds()).values(), steps=25):
                    if e["ignored"] is not False:
                        msg = _(
                            "Ignored guilds and channels have been moved. "
                            "Please use {command} to migrate the old settings."
                        ).format(command=inline("[p]moveignoredchannels"))
                        asyncio.create_task(send_to_owners_with_prefix_replaced(self.bot, msg))
                        break
            await self.config.version.set("1.1.0")
        if await self.config.version() < "1.2.0":
            async for e in AsyncIter((await self.config.all_guilds()).values(), steps=25):
                if e["delete_delay"] != -1:
                    msg = _(
                        "Delete delay settings have been moved. "
                        "Please use {command} to migrate the old settings."
                    ).format(command=inline("[p]movedeletedelay"))
                    asyncio.create_task(send_to_owners_with_prefix_replaced(self.bot, msg))
                    break
            await self.config.version.set("1.2.0")
        if await self.config.version() < "1.3.0":
            guild_dict = await self.config.all_guilds()
            async for guild_id in AsyncIter(guild_dict.keys(), steps=25):
                async with self.config.guild_from_id(guild_id).all() as guild_data:
                    current_state = guild_data.pop("ban_mention_spam", False)
                    if current_state is not False:
                        if "mention_spam" not in guild_data:
                            guild_data["mention_spam"] = {}
                        guild_data["mention_spam"]["ban"] = current_state
            await self.config.version.set("1.3.0")

    @commands.Cog.listener()
    async def on_message_without_command(self, message: discord.Message) -> None:
        """Publish message to news channel."""
        if message.guild is None:
            return
        if not await self.config.guild(message.guild).toggle():
            return
        if message.channel.id in (
            await self.config.guild(message.guild).ignored_channels()
        ):
            return
        if await self.bot.cog_disabled_in_guild(self, message.guild):
            return
        if (
            not message.guild.me.guild_permissions.manage_messages
            or not message.guild.me.guild_permissions.view_channel
        ):
            if await self.config.guild(message.guild).toggle():
                await self.config.guild(message.guild).toggle.set(False)
            return
        if "NEWS" not in message.guild.features:
            if await self.config.guild(message.guild).toggle():
                await self.config.guild(message.guild).toggle.set(False)
            return
        if not message.channel.is_news():
            return
        if message.channel.is_news():
            try:
                await asyncio.sleep(0.5)
                await asyncio.wait_for(message.publish(), timeout=60)
            except (
                discord.HTTPException,
                discord.Forbidden,
                asyncio.TimeoutError,
            ) as e:
                log.error(e)

    @commands.command(hidden=True)
    @commands.is_owner()
    async def moveignoredchannels(self, ctx: commands.Context) -> None:
        """Move ignored channels and servers to core"""
        all_guilds = await self.config.all_guilds()
        all_channels = await self.config.all_channels()
        for guild_id, settings in all_guilds.items():
            await self.bot._config.guild_from_id(guild_id).ignored.set(settings["ignored"])
            await self.config.guild_from_id(guild_id).ignored.clear()
        for channel_id, settings in all_channels.items():
            await self.bot._config.channel_from_id(channel_id).ignored.set(settings["ignored"])
            await self.config.channel_from_id(channel_id).clear()
        await ctx.send(_("Ignored channels and guilds restored."))

    @commands.command(hidden=True)
    @commands.is_owner()
    async def movedeletedelay(self, ctx: commands.Context) -> None:
        """
        Move deletedelay settings to core
        """
        all_guilds = await self.config.all_guilds()
        for guild_id, settings in all_guilds.items():
            await self.bot._config.guild_from_id(guild_id).delete_delay.set(
                settings["delete_delay"]
            )
            await self.config.guild_from_id(guild_id).delete_delay.clear()
        await ctx.send(_("Delete delay settings restored."))

    @commands.command()
    @commands.guild_only()
    @commands.cooldown(1, 3, commands.BucketType.guild)
    @commands.has_permissions(administrator=True)
    async def massunban(self, ctx: commands.Context, *, ban_reason: Optional[str] = None):
        """
        Mass unban everyone, or specific people.
        """
        try:
            banlist: List[discord.BanEntry] = [entry async for entry in ctx.guild.bans()]
        except discord.errors.Forbidden:
            msg = _("I need the `Ban Members` permission to fetch the ban list for the guild.")
            await ctx.send(msg)
            return
        except (discord.HTTPException, TypeError):
            await ctx.send("Something went wrong while fetching the ban list!", exc_info=True)
            return

        bancount: int = len(banlist)
        if bancount == 0:
            await ctx.send(_("No users are banned from this server."))
            return

        unban_count: int = 0
        if not ban_reason:
            warning_string = _(
                "Are you sure you want to unban every banned person on this server?\n"
                f"**Please read** `{ctx.prefix}help massunban` **as this action can cause a LOT of modlog messages!**\n"
                "Type `Yes` to confirm, or `No` to cancel."
            )
            await ctx.send(warning_string)
            pred = MessagePredicate.yes_or_no(ctx)
            try:
                await self.bot.wait_for("message", check=pred, timeout=15)
                if pred.result is True:
                    async with ctx.typing():
                        for ban_entry in banlist:
                            await ctx.guild.unban(
                                ban_entry.user,
                                reason=_("Mass Unban requested by {name} ({id})").format(
                                    name=str(ctx.author.display_name), id=ctx.author.id
                                ),
                            )
                            await asyncio.sleep(0.5)
                            unban_count += 1
                else:
                    return await ctx.send(_("Alright, I'm not unbanning everyone."))
            except asyncio.TimeoutError:
                return await ctx.send(
                    _(
                        "Response timed out. Please run this command again if you wish to try again."
                    )
                )
        else:
            async with ctx.typing():
                for ban_entry in banlist:
                    if not ban_entry.reason:
                        continue
                    if ban_reason.lower() in ban_entry.reason.lower():
                        await ctx.guild.unban(
                            ban_entry.user,
                            reason=_("Mass Unban requested by {name} ({id})").format(
                                name=str(ctx.author.display_name), id=ctx.author.id
                            ),
                        )
                        await asyncio.sleep(1)
                        unban_count += 1

        await ctx.send(_("Done. Unbanned {unban_count} users.").format(unban_count=unban_count))

    @commands.group(aliases=["aph", "autopub"])
    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    async def autopublisher(self, ctx: commands.Context) -> None:
        """Manage AutoPublisher setting."""

    @autopublisher.command()
    @commands.bot_has_permissions(manage_messages=True, view_channel=True)
    async def toggle(self, ctx: commands.Context):
        """Toggle AutoPublisher enable or disable.

        - It's disabled by default.
            - Please ensure that the bot has access to `view_channel` in your news channels. it also need `manage_messages` to be able to publish.

        **Note:**
        - This cog requires News Channel. If you don't have it, you can't use this cog.
            - Learn more [here on how to enable](https://support.discord.com/hc/en-us/articles/360047132851-Enabling-Your-Community-Server) community server. (which is a part of news channel feature.)
        """
        if "NEWS" not in ctx.guild.features:
            view = discord.ui.View()
            style = discord.ButtonStyle.gray
            discordinfo = discord.ui.Button(
                style=style,
                label="Learn more here",
                url="https://support.discord.com/hc/en-us/articles/360047132851-Enabling-Your-Community-Server",
                emoji="<:icons_info:880113401207095346>",
            )
            view.add_item(item=discordinfo)
            return await ctx.send(
                f"Your server doesn't have News Channel feature. Please enable it first.",
                view=view,
            )
        await self.config.guild(ctx.guild).toggle.set(
            not await self.config.guild(ctx.guild).toggle()
        )
        toggle = await self.config.guild(ctx.guild).toggle()
        await ctx.send(f"AutoPublisher has been {'enabled' if toggle else 'disabled'}.")

    @autopublisher.command(
        aliases=["ignorechannels"], usage="<add_or_remove> <channels>"
    )
    async def ignore(
        self,
        ctx: commands.Context,
        add_or_remove: Literal["add", "remove"],
        channels: commands.Greedy[discord.TextChannel] = None,
    ) -> None:
        """Add or remove channels for your guild.

        `<add_or_remove>` should be either `add` to add channels or `remove` to remove channels.

        **Example:**
        - `[p]autopublisher ignore add #news`
        - `[p]autopublisher ignore remove #news`

        **Note:**
        - You can add or remove multiple channels at once.
        - You can also use channel ID instead of mentioning the channel.
        """
        if channels is None:
            await ctx.send("`Channels` is a required argument.")
            return

        async with self.config.guild(ctx.guild).ignored_channels() as c:
            for channel in channels:
                if channel.is_news():  # add check for news channel
                    if add_or_remove.lower() == "add":
                        if not channel.id in c:
                            c.append(channel.id)

                    elif add_or_remove.lower() == "remove":
                        if channel.id in c:
                            c.remove(channel.id)

        news_channels = [
            channel for channel in channels if channel.is_news()
        ]  # filter news channels
        ids = len(news_channels)
        embed = discord.Embed(
            title="Success!",
            description=f"{'added' if add_or_remove.lower() == 'add' else 'removed'} {ids} {'channel' if ids == 1 else 'channels'}.",
            color=0xE91E63,
        )
        embed.add_field(
            name=f"{'channel:' if ids == 1 else 'channels:'}",
            value=humanize_list([channel.mention for channel in news_channels]),
        )  # This needs menus to be able to show all channels if there are more than 25 channels.
        await ctx.send(embed=embed)

    @commands.bot_has_permissions(embed_links=True)
    @autopublisher.command(aliases=["view"])
    async def settings(self, ctx: commands.Context) -> None:
        """Show AutoPublisher setting."""
        data = await self.config.guild(ctx.guild).all()
        toggle = data["toggle"]
        channels = data["ignored_channels"]
        ignored_channels: List[str] = []
        for channel in channels:
            channel = ctx.guild.get_channel(channel)
            ignored_channels.append(channel.mention)
        embed = discord.Embed(
            title="AutoPublisher Setting",
            description="""
            **Toggle:** {toggle}
            **Ignored Channels:** {ignored_channels}
            """.format(
                toggle=toggle,
                ignored_channels=humanize_list(ignored_channels)
                if ignored_channels
                else "None",
            ),
            color=await ctx.embed_color(),
        )
        await ctx.send(embed=embed)

    @autopublisher.command()
    async def reset(self, ctx: commands.Context) -> None:
        """Reset AutoPublisher setting."""
        view = ConfirmView(ctx.author, disable_buttons=True)
        view.message = await ctx.send(
            "Are you sure you want to reset AutoPublisher setting?", view=view
        )
        await view.wait()
        if view.result:
            await self.config.guild(ctx.guild).clear()
            await ctx.send("AutoPublisher setting has been reset.")
        else:
            await ctx.send("AutoPublisher setting reset has been cancelled.")

    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    @commands.hybrid_command(name="nuke")
    async def nuke(self, ctx: commands.Context, confirmation: bool = False) -> None:
        """Delete all messages from the current channel by duplicating it and then deleting it."""
        config = await self.config.guild(ctx.guild).all()
        old_channel = ctx.channel
        channel_position = old_channel.position

        if not confirmation and not ctx.assume_yes:
            embed: discord.Embed = discord.Embed()
            embed.title = ("Nuke")
            embed.description = ("Nuke channel {old_channel.mention} ({old_channel.id})?\n The channel will be deleted and recreated.").format(old_channel=old_channel)
            embed.color = 0x313338
            if not await CogsUtils.ConfirmationAsk(ctx, content=f"{ctx.author.mention}", embed=embed):
                await CogsUtils.delete_message(ctx.message)
                return

        reason = _("Nuke requested by {ctx.author} ({ctx.author.id}).").format(ctx=ctx)
        new_channel = await old_channel.clone(reason=reason)
        await old_channel.delete(reason=reason)
        await new_channel.edit(
            position=channel_position,
            reason=reason,
        ),
        await new_channel.send("first")

    @commands.has_permissions(manage_channels=True)
    @commands.group(invoke_without_command=True)
    async def lock(
        self,
        ctx: commands.Context,
        channel: Optional[Union[LockableChannel, discord.VoiceChannel]] = None,
        roles_or_members: commands.Greedy[Union[LockableRole, discord.Member]] = None,
    ):
        """
        Lock a channel.

        Provide a role or member if you would like to lock it for them.
        You can only lock a maximum of 10 things at once.

        **Examples:**
        `[p]lock #general`
        `[p]lock 737958453905063977 @members`
        """
        try:
            await ctx.typing()
        except discord.Forbidden:
            return

        if not channel:
            channel = ctx.channel
        if not roles_or_members:
            roles_or_members = [ctx.guild.default_role]
        else:
            roles_or_members = roles_or_members[:10]
        succeeded = []
        cancelled = []
        failed = []
        reason = get_audit_reason(ctx.author)

        if isinstance(channel, discord.TextChannel):
            for role in roles_or_members:
                current_perms = channel.overwrites_for(role)
                my_perms = channel.overwrites_for(ctx.me)
                if my_perms.send_messages != True:
                    my_perms.update(send_messages=True)
                    await channel.set_permissions(ctx.me, overwrite=my_perms)
                if current_perms.send_messages == False:
                    cancelled.append(inline(role.name))
                else:
                    current_perms.update(send_messages=False)
                    try:
                        await channel.set_permissions(role, overwrite=current_perms, reason=reason)
                        succeeded.append(inline(role.name))
                    except:
                        failed.append(inline(role.name))
        elif isinstance(channel, discord.VoiceChannel):
            for role in roles_or_members:
                current_perms = channel.overwrites_for(role)
                if current_perms.connect == False:
                    cancelled.append(inline(role.name))
                else:
                    current_perms.update(connect=False)
                    try:
                        await channel.set_permissions(role, overwrite=current_perms, reason=reason)
                        succeeded.append(inline(role.name))
                    except:
                        failed.append(inline(role.name))

        msg = ""
        if succeeded:
            msg += f"{channel.mention} has been locked for {humanize_list(succeeded)}.\n"
        if cancelled:
            msg += f"{channel.mention} was already locked for {humanize_list(cancelled)}.\n"
        if failed:
            msg += f"I failed to lock {channel.mention} for {humanize_list(failed)}.\n"
        if msg:
            await ctx.send(msg)

    @commands.has_permissions(manage_channels=True)
    @commands.command()
    async def viewlock(
        self,
        ctx: commands.Context,
        channel: Optional[Union[LockableChannel, discord.VoiceChannel]] = None,
        roles_or_members: commands.Greedy[Union[LockableRole, discord.Member]] = None,
    ):
        """
        Prevent users from viewing a channel.

        Provide a role or member if you would like to lock it for them.
        You can only lock a maximum of 10 things at once.

        **Example:**
        `[p]viewlock #secret-channel`
        `[p]viewlock 7382395026348520 @nubs`
        """
        try:
            await ctx.typing()
        except discord.Forbidden:
            return

        if not channel:
            channel = ctx.channel
        if not roles_or_members:
            roles_or_members = [ctx.guild.default_role]
        else:
            roles_or_members = roles_or_members[:10]
        succeeded = []
        cancelled = []
        failed = []
        reason = get_audit_reason(ctx.author)

        for role in roles_or_members:
            current_perms = channel.overwrites_for(role)
            if current_perms.read_messages == False:
                cancelled.append(inline(role.name))
            else:
                current_perms.update(read_messages=False)
                try:
                    await channel.set_permissions(role, overwrite=current_perms, reason=reason)
                    succeeded.append(inline(role.name))
                except:
                    failed.append(inline(role.name))

        msg = ""
        if succeeded:
            msg += f"{channel.mention} has been viewlocked for {humanize_list(succeeded)}.\n"
        if cancelled:
            msg += f"{channel.mention} was already viewlocked for {humanize_list(cancelled)}.\n"
        if failed:
            msg += f"I failed to viewlock {channel.mention} for {humanize_list(failed)}.\n"
        if msg:
            await ctx.send(msg)

    @lock.command("server")
    async def lock_server(self, ctx: commands.Context, *roles: LockableRole):
        """
        Lock the server.

        Provide a role if you would like to lock it for that role.

        **Example:**
        `[p]lock server @members`
        """
        if not roles:
            roles = [ctx.guild.default_role]
        succeeded = []
        cancelled = []
        failed = []

        for role in roles:
            current_perms = role.permissions
            if ctx.guild.me.top_role <= role:
                failed.append(inline(role.name))
            elif current_perms.send_messages == False:
                cancelled.append(inline(role.name))
            else:
                current_perms.update(send_messages=False)
                try:
                    await role.edit(permissions=current_perms)
                    succeeded.append(inline(role.name))
                except:
                    failed.append(inline(role.name))
        if succeeded:
            await ctx.send(f"The server has locked for {humanize_list(succeeded)}.")
        if cancelled:
            await ctx.send(f"The server was already locked for {humanize_list(cancelled)}.")
        if failed:
            await ctx.send(
                f"I failed to lock the server for {humanize_list(failed)}, probably because I was lower than the roles in heirarchy."
            )

    @commands.is_owner()  # unstable, incomplete
    @lock.command("perms")
    async def lock_perms(
        self,
        ctx: commands.Context,
        channel: Optional[Union[LockableChannel, discord.VoiceChannel]] = None,
        roles_or_members: commands.Greedy[Union[LockableRole, discord.Member]] = None,
        *permissions: str,
    ):
        """Set the given permissions for a role or member to True."""
        if not permissions:
            raise commands.BadArgument

        try:
            await ctx.typing()
        except discord.Forbidden:
            return

        channel = channel or ctx.channel
        roles_or_members = roles_or_members or [ctx.guild.default_role]

        perms = {}
        for perm in permissions:
            perms.update({perm: False})
        for role in roles_or_members:
            overwrite = self.update_overwrite(ctx, channel.overwrites_for(role), perms)
            await channel.set_permissions(role, overwrite=overwrite[0])
        msg = ""
        if overwrite[1]:
            msg += (
                f"The following permissions have been denied for "
                f"{humanize_list([f'`{obj}`' for obj in roles_or_members])} in {channel.mention}:\n"
                f"{humanize_list([f'`{perm}`' for perm in overwrite[1]])}\n"
            )
        if overwrite[2]:
            msg += overwrite[2]
        if overwrite[3]:
            msg += overwrite[3]
        if msg:
            await ctx.send(msg)

    @commands.has_permissions(manage_channels=True)
    @commands.group(invoke_without_command=True)
    async def unlock(
        self,
        ctx: commands.Context,
        channel: Optional[Union[LockableChannel, discord.VoiceChannel]] = None,
        state: Optional[ChannelToggle] = None,
        roles_or_members: commands.Greedy[Union[LockableRole, discord.Member]] = None,
    ):
        """
        Unlock a channel.

        Provide a role or member if you would like to unlock it for them.
        If you would like to override-unlock for something, you can do so by pass `true` as the state argument.
        You can only unlock a maximum of 10 things at once.

        **Examples:**
        `[p]unlock #general`
        `[p]unlock 739562845027353 true`
        """
        try:
            await ctx.typing()
        except discord.Forbidden:
            return

        if not channel:
            channel = ctx.channel
        if roles_or_members:
            roles_or_members = roles_or_members[:10]
        else:
            roles_or_members = [ctx.guild.default_role]
        succeeded = []
        cancelled = []
        failed = []
        reason = get_audit_reason(ctx.author)

        if isinstance(channel, discord.TextChannel):
            for role in roles_or_members:
                current_perms = channel.overwrites_for(role)
                if current_perms.send_messages != False and current_perms.send_messages == state:
                    cancelled.append(inline(role.name))
                else:
                    current_perms.update(send_messages=state)
                    try:
                        await channel.set_permissions(role, overwrite=current_perms, reason=reason)
                        succeeded.append(inline(role.name))
                    except:
                        failed.append(inline(role.name))
        elif isinstance(channel, discord.VoiceChannel):
            for role in roles_or_members:
                current_perms = channel.overwrites_for(role)
                if current_perms.connect in [False, state]:
                    current_perms.update(connect=state)
                    try:
                        await channel.set_permissions(role, overwrite=current_perms, reason=reason)
                        succeeded.append(inline(role.name))
                    except:
                        failed.append(inline(role.name))
                else:
                    cancelled.append(inline(role.name))

        msg = ""
        if succeeded:
            msg += f"{channel.mention} has unlocked for {humanize_list(succeeded)} with state `{'true' if state else 'default'}`.\n"
        if cancelled:
            msg += f"{channel.mention} was already unlocked for {humanize_list(cancelled)} with state `{'true' if state else 'default'}`.\n"
        if failed:
            msg += f"I failed to unlock {channel.mention} for {humanize_list(failed)}.\n"
        if msg:
            await ctx.send(msg)

    @commands.has_permissions(manage_channels=True)
    @commands.group(invoke_without_command=True)
    async def unviewlock(
        self,
        ctx: commands.Context,
        channel: Optional[Union[LockableChannel, discord.VoiceChannel]] = None,
        state: Optional[ChannelToggle] = None,
        roles_or_members: commands.Greedy[Union[LockableRole, discord.Member]] = None,
    ):
        """
        Allow users to view a channel.

        Provide a role or member if you would like to unlock it for them.
        If you would like to override-unlock for something, you can do so by pass `true` as the state argument.
        You can only unlock a maximum of 10 things at once.

        **Example:**
        `[p]unviewlock #hidden-channel true`
        `[p]unviewlock 746284923572835 @boosters`
        """
        try:
            await ctx.typing()
        except discord.Forbidden:
            return

        if not channel:
            channel = ctx.channel
        if not roles_or_members:
            roles_or_members = [ctx.guild.default_role]
        else:
            roles_or_members = roles_or_members[:10]
        succeeded = []
        cancelled = []
        failed = []
        reason = get_audit_reason(ctx.author)

        for role in roles_or_members:
            current_perms = channel.overwrites_for(role)
            if current_perms.read_messages != False and current_perms.read_messages == state:
                cancelled.append(inline(role.name))
            else:
                current_perms.update(read_messages=state)
                try:
                    await channel.set_permissions(role, overwrite=current_perms, reason=reason)
                    succeeded.append(inline(role.name))
                except:
                    failed.append(inline(role.name))

        msg = ""
        if succeeded:
            msg += f"{channel.mention} has unlocked viewing for {humanize_list(succeeded)} with state `{'true' if state else 'default'}`.\n"
        if cancelled:
            msg += f"{channel.mention} was already unviewlocked for {humanize_list(cancelled)} with state `{'true' if state else 'default'}`.\n"
        if failed:
            msg += f"I failed to unlock {channel.mention} for {humanize_list(failed)}.\n"
        if msg:
            await ctx.send(msg)

    @unlock.command("server")
    async def unlock_server(self, ctx: commands.Context, *roles: LockableRole):
        """
        Unlock the server.

        Provide a role if you would like to unlock it for that role.

        **Examples:**
        `[p]unlock server @members`
        """
        if not roles:
            roles = [ctx.guild.default_role]
        succeeded = []
        cancelled = []
        failed = []

        for role in roles:
            current_perms = role.permissions
            if ctx.guild.me.top_role <= role:
                failed.append(inline(role.name))
            elif current_perms.send_messages == True:
                cancelled.append(inline(role.name))
            else:
                current_perms.update(send_messages=True)
                try:
                    await role.edit(permissions=current_perms)
                    succeeded.append(inline(role.name))
                except:
                    failed.append(inline(role.name))

        msg = []
        if succeeded:
            msg.append(f"The server has unlocked for {humanize_list(succeeded)}.")
        if cancelled:
            msg.append(f"The server was already unlocked for {humanize_list(cancelled)}.")
        if failed:
            msg.append(
                f"I failed to unlock the server for {humanize_list(failed)}, probably because I was lower than the roles in heirarchy."
            )
        if msg:
            await ctx.send("\n".join(msg))

    @commands.is_owner()  # unstable, incomplete
    @unlock.command("perms")
    async def unlock_perms(
        self,
        ctx: commands.Context,
        channel: Optional[Union[LockableChannel, discord.VoiceChannel]] = None,
        state: Optional[ChannelToggle] = None,
        roles_or_members: commands.Greedy[Union[LockableRole, discord.Member]] = None,
        *permissions: str,
    ):
        """
        Set the given permissions for a role or member to `True` or `None`, depending on the given state
        """
        if not permissions:
            raise commands.BadArgument

        try:
            await ctx.typing()
        except discord.Forbidden:
            return

        channel = channel or ctx.channel
        roles_or_members = roles_or_members or [ctx.guild.default_role]

        perms = {}
        for perm in permissions:
            perms.update({perm: state})
        for role in roles_or_members:
            overwrite = self.update_overwrite(ctx, channel.overwrites_for(role), perms)
            await channel.set_permissions(role, overwrite=overwrite[0])
        msg = ""
        if overwrite[1]:
            msg += (
                f"The following permissions have been set to `{state}` for "
                f"{humanize_list([f'`{obj}`' for obj in roles_or_members])} in {channel.mention}:\n"
                f"{humanize_list([f'`{perm}`' for perm in overwrite[1]])}"
            )
        if overwrite[2]:
            msg += overwrite[2]
        if overwrite[3]:
            msg += overwrite[3]
        if msg:
            await ctx.send(msg)

    @commands.command()
    @commands.guild_only()
    @commands.bot_can_manage_channel()
    @commands.admin_or_can_manage_channel()
    async def slowmode(
        self,
        ctx,
        *,
        interval: commands.TimedeltaConverter(
            minimum=timedelta(seconds=0), maximum=timedelta(hours=6), default_unit="seconds"
        ) = timedelta(seconds=0),
    ):
        """Changes thread's or text channel's slowmode setting.

        Interval can be anything from 0 seconds to 6 hours.
        Use without parameters to disable.
        """
        seconds = interval.total_seconds()
        await ctx.channel.edit(slowmode_delay=seconds)
        if seconds > 0:
            await ctx.send(
                _("Slowmode interval is now {interval}.").format(
                    interval=humanize_timedelta(timedelta=interval)
                )
            )
        else:
            await ctx.send(_("Slowmode has been disabled."))

    @staticmethod
    def update_overwrite(
        ctx: commands.Context, overwrite: discord.PermissionOverwrite, permissions: dict
    ):
        base_perms = dict(iter(discord.PermissionOverwrite()))
        old_perms = copy(permissions)
        ctx.channel.permissions_for(ctx.author)
        invalid_perms = []
        valid_perms = []
        not_allowed: List[str] = []
        for perm in old_perms:
            if perm in base_perms:
                valid_perms.append(f"`{perm}`")
            else:
                invalid_perms.append(f"`{perm}`")
                del permissions[perm]
        overwrite.update(**permissions)
        if invalid_perms:
            invalid = (
                f"\nThe following permissions were invalid:\n{humanize_list(invalid_perms)}\n"
            )
            possible = humanize_list([f"`{perm}`" for perm in base_perms])
            invalid += f"Possible permissions are:\n{possible}"
        else:
            invalid = ""
        return overwrite, valid_perms, invalid, not_allowed
    

    @commands.command(aliases=["tt"])
    @commands.guild_only()
    @commands.cooldown(1, 3, commands.BucketType.user)
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
                return await ctx.reply(embed = discord.Embed(description=f"> {member.mention} is already timed out.", mention_author=False, color=0x313338))
            if not await is_allowed_by_hierarchy(ctx.bot, ctx.author, member):
                return await ctx.send("You cannot timeout this user due to hierarchy.")
            if ctx.channel.permissions_for(member).administrator:
                return await ctx.send("You can't timeout an administrator.")
            await self.timeout_user(ctx, member, time, reason)
            embed = discord.Embed(description=f"> {member.mention} has been timed out until <t:{timestamp}:f>. ", color=0x313338)
            await ctx.reply(embed=embed, mention_author=False)

    @commands.command(aliases=["utt"])
    @commands.guild_only()
    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands.has_permissions(moderate_members=True)
    async def untimeout(self, ctx: commands.Context, member: discord.Member, *, reason: Optional[str] = None,):
        """
        Untimeout users.
        """
        if isinstance(member, discord.Member):
            await self.timeout_user(ctx, member, None, reason)
            embed = discord.Embed(description=f"> Removed the timeout for {member.mention}.", color=0x313338)
            if not member.is_timed_out():
                embed = discord.Embed(description=f"> {member.mention} is not timed out.", color=0x313338)
            await ctx.reply(embed=embed, mention_author=False)
        
async def is_allowed_by_hierarchy(
    bot: Red, user: discord.Member, member: discord.Member
) -> bool:
    return (
        user.guild.owner_id == user.id
        or user.top_role > member.top_role
        or await bot.is_owner(user)
    )