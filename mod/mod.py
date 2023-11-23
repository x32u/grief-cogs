import asyncio
import logging
import re
from abc import ABC
from collections import defaultdict
from typing import Literal
import discord
import logging

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
from .slowmode import Slowmode
from .settings import ModSettings
from grief.core.utils.chat_formatting import box, humanize_list

from AAA3A_utils import Cog, CogsUtils, Settings
from AAA3A_utils.settings import CustomMessageConverter

from grief.core.utils.predicates import MessagePredicate
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
    Slowmode,
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
                log.info(
                    f"AutoPublisher has been disabled in {message.guild} due to missing permissions."
                )
            return
        if "NEWS" not in message.guild.features:
            if await self.config.guild(message.guild).toggle():
                await self.config.guild(message.guild).toggle.set(False)
                log.info(
                    f"AutoPublisher has been disabled in {message.guild} due to News Channel feature is not enabled."
                )
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
    async def nuke_channel(self, ctx: commands.Context, confirmation: bool = False) -> None:
        """Delete all messages from the current channel by duplicating it and then deleting it.
        """
        config = await self.config.guild(ctx.guild).all()
        old_channel = ctx.channel
        channel_position = old_channel.position

        if not confirmation and not ctx.assume_yes:
            embed: discord.Embed = discord.Embed()
            embed.title = _("Nuke")
            embed.description = _(
                "Nuke channel {old_channel.mention} ({old_channel.id})?\n The channel will be deleted and recreated."
            ).format(old_channel=old_channel)
            embed.color = 0x313338
            if not await CogsUtils.ConfirmationAsk(
                ctx, content=f"{ctx.author.mention}", embed=embed
            ):
                await CogsUtils.delete_message(ctx.message)
                return

        reason = _("Nuke requested by {ctx.author} ({ctx.author.id}).").format(ctx=ctx)
        new_channel = await old_channel.clone(reason=reason)
        await old_channel.delete(reason=reason)
        await new_channel.edit(
            position=channel_position,
            reason=reason,
        )
        self.log.info(
            f"{ctx.author} ({ctx.author.id}) deleted all messages in channel {old_channel.name} ({old_channel.id})."
        ),
        await new_channel.send("first")