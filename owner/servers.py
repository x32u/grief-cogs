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

_ = Translator("ServerStats", __file__)
log = logging.getLogger("red.trusty-cogs.ServerStats")


@cog_i18n(_)
class Owner(commands.Cog):
    """
    Gather useful information about servers the bot is in.
    """

    def __init__(self, bot):
        self.bot: Red = bot
        default_global: dict = {"join_channel": None}
        default_guild: dict = {"last_checked": 0, "members": {}, "total": 0, "channels": {}}
        self.config: Config = Config.get_conf(self, 54853421465543, force_registration=True)
        self.config.register_global(**default_global)
        self.config.register_guild(**default_guild)

    async def red_delete_data_for_user(
        self,
        *,
        requester: Literal["discord_deleted_user", "owner", "user", "user_strict"],
        user_id: int,
    ):
        """
        Method for finding users data inside the cog and deleting it.
        """
        all_guilds = await self.config.all_guilds()
        for guild_id, data in all_guilds.items():
            save = False
            if str(user_id) in data["members"]:
                del data["members"][str(user_id)]
                save = True
            for channel_id, chan_data in data["channels"].items():
                if str(user_id) in chan_data["members"]:
                    del chan_data["members"][str(user_id)]
                    save = True
            if save:
                await self.config.guild_from_id(guild_id).set(data)

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

    @commands.hybrid_command()
    @commands.bot_has_permissions(read_message_history=True, add_reactions=True)
    async def whois(self, ctx: commands.Context, *, user_id: discord.User) -> None:
        """
        Display servers a user shares with the bot

        `member` can be a user ID or mention
        """
        async with ctx.typing():
            if not user_id:
                await ctx.send(_("You need to supply a user ID for this to work properly."))
                return
            if isinstance(user_id, int):
                try:
                    member = await self.bot.fetch_user(user_id)
                except AttributeError:
                    member = await self.bot.get_user_info(user_id)
                except discord.errors.NotFound:
                    await ctx.send(str(user_id) + _(" doesn't seem to be a discord user."))
                    return
            else:
                member = user_id

            if await self.bot.is_owner(ctx.author):
                guild_list = []
                async for guild in AsyncIter(self.bot.guilds, steps=100):
                    if m := guild.get_member(member.id):
                        guild_list.append(m)
            else:
                guild_list = []
                async for guild in AsyncIter(self.bot.guilds, steps=100):
                    if not guild.get_member(ctx.author.id):
                        continue
                    if m := guild.get_member(member.id):
                        guild_list.append(m)
            embed_list = []
            robot = "\N{ROBOT FACE}" if member.bot else ""
            if guild_list != []:
                url = "https://discord.com/channels/{guild_id}"
                msg = f"**{member}** ({member.id}) {robot}" + _("is on:\n\n")
                embed_msg = ""
                for m in guild_list:
                    # m = guild.get_member(member.id)
                    guild_join = ""
                    guild_url = url.format(guild_id=m.guild.id)
                    if m.joined_at:
                        ts = int(m.joined_at.timestamp())
                        guild_join = f"Joined the server <t:{ts}:R>"
                    is_owner = ""
                    nick = ""
                    if m.id == m.guild.owner_id:
                        is_owner = "\N{CROWN}"
                    if m.nick:
                        nick = f"`{m.nick}` in"
                    msg += f"{is_owner}{nick} __[{m.guild.name}]({guild_url})__ {guild_join}\n\n"
                    embed_msg += (
                        f"{is_owner}{nick} __[{m.guild.name}]({guild_url})__ {guild_join}\n\n"
                    )
                if ctx.channel.permissions_for(ctx.me).embed_links:
                    for em in pagify(embed_msg, ["\n"], page_length=1024):
                        embed = discord.Embed()
                        since_created = f"<t:{int(member.created_at.timestamp())}:R>"
                        user_created = f"<t:{int(member.created_at.timestamp())}:D>"
                        public_flags = ""
                        if version_info >= VersionInfo.from_str("3.4.0"):
                            public_flags = "\n".join(
                                bold(i.replace("_", " ").title())
                                for i, v in member.public_flags
                                if v
                            )
                        created_on = _(
                            "Joined Discord on {user_created}\n"
                            "({since_created})\n"
                            "{public_flags}"
                        ).format(
                            user_created=user_created,
                            since_created=since_created,
                            public_flags=public_flags,
                        )
                        embed.description = created_on
                        embed.set_thumbnail(url=member.display_avatar)
                        embed.colour = 0x313338
                        embed.set_author(
                            name=f"{member} ({member.id}) {robot}", icon_url=member.display_avatar
                        )
                        embed.add_field(name=_("Shared Servers"), value=em)
                        embed_list.append(embed)
                else:
                    for page in pagify(msg, ["\n"]):
                        embed_list.append(page)
            else:
                if ctx.channel.permissions_for(ctx.me).embed_links:
                    embed = discord.Embed()
                    since_created = f"<t:{int(member.created_at.timestamp())}:R>"
                    user_created = f"<t:{int(member.created_at.timestamp())}:D>"
                    public_flags = ""
                    if version_info >= VersionInfo.from_str("3.4.0"):
                        public_flags = "\n".join(
                            bold(i.replace("_", " ").title()) for i, v in member.public_flags if v
                        )
                    created_on = _(
                        "Joined Discord on {user_created}\n" "({since_created})\n" "{public_flags}"
                    ).format(
                        user_created=user_created,
                        since_created=since_created,
                        public_flags=public_flags,
                    )
                    embed.description = created_on
                    embed.set_thumbnail(url=member.display_avatar)
                    embed.colour = discord.Colour.dark_theme()
                    embed.set_author(
                        name=f"{member} ({member.id}) {robot}", icon_url=member.display_avatar
                    )
                    embed_list.append(embed)
                else:
                    msg = f"**{member}** ({member.id}) " + _("is not in any shared servers!")
                    embed_list.append(msg)
            await BaseView(
                source=ListPages(pages=embed_list),
                cog=self,
            ).start(ctx=ctx)

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