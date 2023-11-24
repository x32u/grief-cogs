import discord
import asyncio
import concurrent
import logging
import time
import re
import discord
import speedtest
import random
import colorama
import os
import pathlib
import datetime
from grief.core import checks, commands, data_manager
from grief.core.i18n import Translator, cog_i18n
from grief.core.commands.context import Context
from grief.core.bot import Red
from grief.core import Config, commands
from grief.core.utils.chat_formatting import humanize_list
from discord.utils import get
### FROM SERVERSTATS
import asyncio
import logging
from copy import copy
from datetime import datetime, timedelta, timezone
from io import BytesIO
from typing import Dict, List, Literal, Optional, Tuple, Union, cast

import aiohttp
import discord
from grief import VersionInfo, version_info
from grief.core import Config, checks, commands
from grief.core.bot import Red
from grief.core.i18n import Translator, cog_i18n
from grief.core.utils import AsyncIter
from grief.core.utils.chat_formatting import (
    bold,
    box,
    escape,
    humanize_list,
    humanize_number,
    humanize_timedelta,
    pagify,
)
from grief.core.utils.menus import start_adding_reactions
from grief.core.utils.predicates import MessagePredicate, ReactionPredicate

from .converters import GuildConverter, MultiGuildConverter, PermissionConverter
from .menus import BaseView, GuildPages, ListPages

_ = Translator("Owner", __file__)
log = logging.getLogger("grief.owner")

@cog_i18n(_)
class Owner(commands.Cog):
    """
    Gather useful information about servers the bot is in.
    """

    def __init__(self, bot):
        self.bot = bot
        self.saveFolder = data_manager.cog_data_path(cog_instance=self)
        default_global: dict = {"join_channel": None}
        default_guild: dict = {"last_checked": 0, "members": {}, "total": 0, "channels": {}}
        self.config: Config = Config.get_conf(self, 54853421465543, force_registration=True)
        self.config.register_global(**default_global)
        self.config.register_guild(**default_guild)

    @commands.command()
    @commands.is_owner()
    async def dm(self, ctx, user: discord.User, *, message: str):
        """
        Dm raw text to a user.
        """
        destination = get(self.bot.get_all_members(), id=user.id)
        if not destination:
            return await ctx.send(
                "Invalid ID or user not found. You can only send messages to people I share a server with.",
            )
        await destination.send(message)
        await ctx.tick()

    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.group(invoke_without_command=True)
    async def ping(self, ctx):
        """View bot latency."""
        start = time.monotonic()
        ref = ctx.message.to_reference(fail_if_not_exists=False)
        message = await ctx.send("Pinging...", reference=ref)
        end = time.monotonic()
        totalPing = round((end - start) * 1000, 2)
        e = discord.Embed(
            title="Pinging..", description=f"{'Overall Latency':<16}:{totalPing}ms"
        )
        await asyncio.sleep(0.25)
        try:
            await message.edit(content=None, embed=e)
        except discord.NotFound:
            return

        botPing = round(self.bot.latency * 1000, 2)
        e.description = e.description + f"\n{'Discord WS':<16}:{botPing}ms"
        await asyncio.sleep(0.25)

        averagePing = (botPing + totalPing) / 2
        if averagePing >= 1000:
            color = discord.Colour.dark_theme()
        elif averagePing >= 200:
            color = discord.Colour.dark_theme()
        else:
            color = discord.Colour.dark_theme()

        e.color = color

        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        loop = asyncio.get_event_loop()
        try:
            s = speedtest.Speedtest(secure=True)
            await loop.run_in_executor(executor, s.get_servers)
            await loop.run_in_executor(executor, s.get_best_server)
        except Exception as exc:
            host_latency = "`Failed`"
        else:
            result = s.results.dict()
            host_latency = round(result["ping"], 2)
            host_latency = f"{host_latency}ms"

        e.title = "Pong!"
        e.description = e.description + f"\n{'Host Latency':<16}:{host_latency}"
        await asyncio.sleep(0.25)
        try:
            await message.edit(embed=e)
        except discord.NotFound:
            return
        
    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        """Build and send a message containing serverinfo when the bot joins a new server"""
        channel_id = await self.config.join_channel()
        if channel_id is None:
            return
        channel = self.bot.get_channel(channel_id)
        passed = f"<t:{int(guild.created_at.timestamp())}:R>"

        created_at = _(
            "{bot} has joined a server.\n "
            "That's **{num}** servers now.\n"
            "That's a total of **{users}** users .\n"
            "Server created on **{since}**. "
            "That's over **{passed}**."
        ).format(
            bot=channel.guild.me.mention,
            num=humanize_number(len(self.bot.guilds)),
            users=humanize_number(len(self.bot.users)),
            since=f"<t:{int(guild.created_at.timestamp())}:D>",
            passed=passed,
        )
        try:
            em = await self.guild_embed(guild)
            em.description = created_at
            await channel.send(embed=em)
        except Exception:
            log.error(f"Error creating guild embed for new guild ID {guild.id}", exc_info=True)

    async def guild_embed(self, guild: discord.Guild) -> discord.Embed:
        """
        Builds the guild embed information used throughout the cog
        """

        def _size(num):
            for unit in ["B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB"]:
                if abs(num) < 1024.0:
                    return "{0:.1f}{1}".format(num, unit)
                num /= 1024.0
            return "{0:.1f}{1}".format(num, "YB")

        def _bitsize(num):
            for unit in ["B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB"]:
                if abs(num) < 1000.0:
                    return "{0:.1f}{1}".format(num, unit)
                num /= 1000.0
            return "{0:.1f}{1}".format(num, "YB")

        created_at = _("Created on {date}. That's over {num}!").format(
            date=bold(f"<t:{int(guild.created_at.timestamp())}:D>"),
            num=bold(f"<t:{int(guild.created_at.timestamp())}:R>"),
        )
        total_users = humanize_number(guild.member_count)
        try:
            joined_at = guild.me.joined_at
        except AttributeError:
            joined_at = datetime.now(timezone.utc)
        bot_joined = f"<t:{int(joined_at.timestamp())}:D>"
        since_joined = f"<t:{int(joined_at.timestamp())}:R>"
        joined_on = _(
            "**{bot_name}** joined this server on **{bot_join}**.\n"
            "That's over **{since_join}**!"
        ).format(bot_name=self.bot.user.mention, bot_join=bot_joined, since_join=since_joined)

        shard = (
            _("\nShard ID: **{shard_id}/{shard_count}**").format(
                shard_id=humanize_number(guild.shard_id + 1),
                shard_count=humanize_number(self.bot.shard_count),
            )
            if self.bot.shard_count > 1
            else ""
        )
        colour = 0x313338

        online_stats = {
            _("Humans: "): lambda x: not x.bot,
            _(" • Bots: "): lambda x: x.bot,
            "\N{LARGE GREEN CIRCLE}": lambda x: x.status is discord.Status.online,
            "\N{LARGE ORANGE CIRCLE}": lambda x: x.status is discord.Status.idle,
            "\N{LARGE RED CIRCLE}": lambda x: x.status is discord.Status.do_not_disturb,
            "\N{MEDIUM WHITE CIRCLE}": lambda x: x.status is discord.Status.offline,
            "\N{LARGE PURPLE CIRCLE}": lambda x: (
                x.activity is not None and x.activity.type is discord.ActivityType.streaming
            ),
        }
        member_msg = _("Total Users: {}\n").format(bold(total_users))
        count = 1
        for emoji, value in online_stats.items():
            try:
                num = len([m for m in guild.members if value(m)])
            except Exception as error:
                print(error)
                continue
            else:
                member_msg += f"{emoji} {bold(humanize_number(num))} " + (
                    "\n" if count % 2 == 0 else ""
                )
            count += 1

        text_channels = len(guild.text_channels)
        nsfw_channels = len([c for c in guild.text_channels if c.is_nsfw()])
        voice_channels = len(guild.voice_channels)
        verif = {
            "none": _("0 - None"),
            "low": _("1 - Low"),
            "medium": _("2 - Medium"),
            "high": _("3 - High"),
            "extreme": _("4 - Extreme"),
            "highest": _("4 - Highest"),
        }

        features = {
            "ANIMATED_ICON": _("Animated Icon"),
            "BANNER": _("Banner Image"),
            "COMMERCE": _("Commerce"),
            "COMMUNITY": _("Community"),
            "DISCOVERABLE": _("Server Discovery"),
            "FEATURABLE": _("Featurable"),
            "INVITE_SPLASH": _("Splash Invite"),
            "MEMBER_LIST_DISABLED": _("Member list disabled"),
            "MEMBER_VERIFICATION_GATE_ENABLED": _("Membership Screening enabled"),
            "MORE_EMOJI": _("More Emojis"),
            "NEWS": _("News Channels"),
            "PARTNERED": _("Partnered"),
            "PREVIEW_ENABLED": _("Preview enabled"),
            "PUBLIC_DISABLED": _("Public disabled"),
            "VANITY_URL": _("Vanity URL"),
            "VERIFIED": _("Verified"),
            "VIP_REGIONS": _("VIP Voice Servers"),
            "WELCOME_SCREEN_ENABLED": _("Welcome Screen enabled"),
        }
        guild_features_list = [
            f"✅ {name}" for feature, name in features.items() if feature in guild.features
        ]

        em = discord.Embed(
            description=(f"{guild.description}\n\n" if guild.description else "")
            + f"{created_at}\n{joined_on}",
            colour= 0x313338,
        )
        author_icon = None
        if "VERIFIED" in guild.features:
            author_icon = "https://cdn.discordapp.com/emojis/457879292152381443.png"
        if "PARTNERED" in guild.features:
            author_icon = "https://cdn.discordapp.com/emojis/508929941610430464.png"
        guild_icon = "https://cdn.discordapp.com/embed/avatars/1.png"
        if guild.icon:
            guild_icon = guild.icon.url
        em.set_author(
            name=guild.name,
            icon_url=author_icon,
            url=guild_icon,
        )
        em.set_thumbnail(
            url=guild.icon.url if guild.icon else "https://cdn.discordapp.com/embed/avatars/1.png"
        )
        em.add_field(name=_("Members:"), value=member_msg)
        em.add_field(
            name=_("Channels:"),
            value=_(
                "\N{SPEECH BALLOON} Text: {text}\n{nsfw}"
                "\N{SPEAKER WITH THREE SOUND WAVES} Voice: {voice}"
            ).format(
                text=bold(humanize_number(text_channels)),
                nsfw=_("\N{NO ONE UNDER EIGHTEEN SYMBOL} Nsfw: {}\n").format(
                    bold(humanize_number(nsfw_channels))
                )
                if nsfw_channels
                else "",
                voice=bold(humanize_number(voice_channels)),
            ),
        )
        owner = guild.owner if guild.owner else await self.bot.get_or_fetch_user(guild.owner_id)
        em.add_field(
            name=_("Utility:"),
            value=_(
                "Owner: {owner_mention}\n{owner}\nVerif. level: {verif}\nServer ID: {id}{shard}"
            ).format(
                owner_mention=bold(str(owner.mention)),
                owner=bold(str(owner)),
                verif=bold(verif[str(guild.verification_level)]),
                id=bold(str(guild.id)),
                shard=shard,
            ),
            inline=False,
        )
        em.add_field(
            name=_("Misc:"),
            value=_(
                "AFK channel: {afk_chan}\nAFK timeout: {afk_timeout}\nCustom emojis: {emojis}\nRoles: {roles}"
            ).format(
                afk_chan=bold(str(guild.afk_channel)) if guild.afk_channel else bold(_("Not set")),
                afk_timeout=bold(humanize_timedelta(seconds=guild.afk_timeout)),
                emojis=bold(humanize_number(len(guild.emojis))),
                roles=bold(humanize_number(len(guild.roles))),
            ),
            inline=False,
        )
        if guild_features_list:
            em.add_field(name=_("Server features:"), value="\n".join(guild_features_list))
        if guild.premium_tier != 0:
            nitro_boost = _(
                "Tier {boostlevel} with {nitroboosters} boosters\n"
                "File size limit: {filelimit}\n"
                "Emoji limit: {emojis_limit}\n"
                "VCs max bitrate: {bitrate}"
            ).format(
                boostlevel=bold(str(guild.premium_tier)),
                nitroboosters=bold(humanize_number(guild.premium_subscription_count)),
                filelimit=bold(_size(guild.filesize_limit)),
                emojis_limit=bold(str(guild.emoji_limit)),
                bitrate=bold(_bitsize(guild.bitrate_limit)),
            )
            em.add_field(name=_("Nitro Boost:"), value=nitro_boost)
        if guild.splash:
            em.set_image(url=guild.splash.url)
        return em

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild) -> None:
        """Build and send a message containing serverinfo when the bot leaves a server"""
        channel_id = await self.config.join_channel()
        if channel_id is None:
            return
        channel = self.bot.get_channel(channel_id)
        passed = f"<t:{int(guild.created_at.timestamp())}:R>"
        created_at = _(
            "{bot} has left a server!\n "
            "That's **{num}** servers now!\n"
            "That's a total of **{users}** users !\n"
            "Server created on **{since}**. "
            "That's over **{passed}**!"
        ).format(
            bot=channel.guild.me.mention,
            num=humanize_number(len(self.bot.guilds)),
            users=humanize_number(len(self.bot.users)),
            since=f"<t:{int(guild.created_at.timestamp())}:D>",
            passed=passed,
        )
        try:
            em = await self.guild_embed(guild)
            em.description = created_at
            await channel.send(embed=em)
        except Exception:
            log.error(f"Error creating guild embed for old guild ID {guild.id}", exc_info=True)

    @commands.command()
    @checks.is_owner()
    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def setguildjoin(
        self, ctx: commands.Context, channel: discord.TextChannel = None
    ) -> None:
        """
        Set a channel to see new servers the bot is joining
        """
        if channel is None:
            channel = ctx.message.channel
        await self.config.join_channel.set(channel.id)
        msg = _("Posting new servers and left servers in ") + channel.mention
        await ctx.send(msg)

    @commands.command()
    @checks.is_owner()
    async def removeguildjoin(self, ctx: commands.Context) -> None:
        """
        Stop bots join/leave server messages
        """
        await self.config.join_channel.clear()
        await ctx.send(_("No longer posting joined or left servers."))

    @staticmethod
    async def confirm_leave_guild(ctx: commands.Context, guild) -> None:
        await ctx.send(
            _("Are you sure you want me to leave {guild}? (reply yes or no)").format(
                guild=guild.name
            )
        )
        pred = MessagePredicate.yes_or_no(ctx)
        await ctx.bot.wait_for("message", check=pred)
        if pred.result is True:
            try:
                await ctx.send(_("Leaving {guild}.").format(guild=guild.name))
                await guild.leave()
            except Exception:
                log.error(
                    _("I couldn't leave {guild} ({g_id}).").format(
                        guild=guild.name, g_id=guild.id
                    ),
                    exc_info=True,
                )
                await ctx.send(_("I couldn't leave {guild}.").format(guild=guild.name))
        else:
            await ctx.send(_("Okay, not leaving {guild}.").format(guild=guild.name))

    @staticmethod
    async def get_guild_invite(
        guild: discord.Guild, max_age: int = 86400
    ) -> Optional[discord.Invite]:
        """Handles the reinvite logic for getting an invite
        to send the newly unbanned user
        :returns: :class:`Invite`

        https://github.com/Cog-Creators/Red-DiscordBot/blob/V3/develop/redbot/cogs/mod/mod.py#L771
        """
        my_perms: discord.Permissions = guild.me.guild_permissions
        if my_perms.manage_guild or my_perms.administrator:
            if "VANITY_URL" in guild.features:
                # guild has a vanity url so use it as the one to send
                try:
                    return await guild.vanity_invite()
                except discord.errors.Forbidden:
                    invites = []
            invites = await guild.invites()
        else:
            invites = []
        for inv in invites:  # Loop through the invites for the guild
            if not (inv.max_uses or inv.max_age or inv.temporary):
                # Invite is for the guild's default channel,
                # has unlimited uses, doesn't expire, and
                # doesn't grant temporary membership
                # (i.e. they won't be kicked on disconnect)
                return inv
        else:  # No existing invite found that is valid
            channels_and_perms = zip(
                guild.text_channels,
                map(lambda x: x.permissions_for(guild.me), guild.text_channels),
            )
            channel = next(
                (channel for channel, perms in channels_and_perms if perms.create_instant_invite),
                None,
            )
            if channel is None:
                return
            try:
                # Create invite that expires after max_age
                return await channel.create_invite(max_age=max_age)
            except discord.HTTPException:
                return

    @commands.is_owner()
    @commands.hybrid_command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.bot_has_permissions(read_message_history=True, add_reactions=True, embed_links=True)
    async def getguild(self, ctx: commands.Context, *, guild: GuildConverter = None) -> None:
        """
        Display info about servers the bot is on

        `guild_name` can be either the server ID or partial name
        """
        async with ctx.typing():
            if not ctx.guild and not await ctx.bot.is_owner(ctx.author):
                return await ctx.send(_("This command is not available in DM."))
            guilds = [ctx.guild]
            page = 0
            if await ctx.bot.is_owner(ctx.author):
                if ctx.guild:
                    page = ctx.bot.guilds.index(ctx.guild)
                guilds = ctx.bot.guilds
                if guild:
                    page = ctx.bot.guilds.index(guild)

        await BaseView(
            source=GuildPages(guilds=guilds),
            cog=self,
            page_start=page,
            ctx=ctx,
        ).start(ctx=ctx)

    @commands.is_owner()
    @commands.hybrid_command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.bot_has_permissions(read_message_history=True, add_reactions=True, embed_links=True)
    async def getguilds(self, ctx: commands.Context, *, guilds: MultiGuildConverter) -> None:
        """
        Display info about multiple servers

        `guild_name` can be either the server ID or partial name
        """
        async with ctx.typing():
            page = 0
            if not guilds:
                guilds = ctx.bot.guilds
                page = ctx.bot.guilds.index(ctx.guild)
        await BaseView(
            source=GuildPages(guilds=guilds),
            cog=self,
            page_start=page,
        ).start(ctx=ctx)