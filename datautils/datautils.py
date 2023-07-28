from asyncio import TimeoutError as AsyncTimeoutError
from textwrap import shorten
from types import SimpleNamespace
from typing import Optional, Union

import discord
import tabulate
from fixcogsutils.dpy_future import TimestampStyle, get_markdown_timestamp
from fixcogsutils.formatting import bool_emojify
from redbot.core import commands
from redbot.core.i18n import cog_i18n
from redbot.core.utils import chat_formatting as chat
from redbot.core.utils.predicates import ReactionPredicate
from redbot.core.utils.chat_formatting import (
    bold,
    escape,
    italics,
    humanize_number,
    humanize_timedelta,
)

from .common_variables import CHANNEL_TYPE_EMOJIS, GUILD_FEATURES, KNOWN_CHANNEL_TYPES
from .embeds import emoji_embed
from .menus import ActivityPager, BaseMenu, ChannelsMenu, ChannelsPager, EmojiPager, PagePager
from .utils import _


@cog_i18n(_)
class DataUtils(commands.Cog):

    # noinspection PyMissingConstructor
    def __init__(self, bot):
        self.bot = bot

    async def red_delete_data_for_user(self, **kwargs):
        return

    @commands.command(aliases=["activity"])
    @commands.guild_only()
    @commands.mod_or_permissions(embed_links=True)
    async def status(self, ctx, *, member: discord.Member = None):
        """List user's activities"""
        if member is None:
            member = ctx.message.author
        if not (activities := member.activities):
            await ctx.send(chat.info(_("Right now this user is doing nothing")))
            return
        await BaseMenu(ActivityPager(activities)).start(ctx)
        
    @commands.command()
    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    @commands.bot_has_permissions(embed_links=True)
    async def invites(self, ctx: commands.Context, *, server: commands.GuildConverter = None):
        """Get invites from server by id"""
        if server is None or not await self.bot.is_owner(ctx.author):
            server = ctx.guild
        if not server.me.guild_permissions.manage_guild:
            await ctx.send(
                _('I need permission "Manage Server" to access list of invites on server')
            )
            return
        invites = await server.invites()
        if invites:
            inviteslist = "\n".join(f"{x} ({x.channel.name})" for x in invites)
            await BaseMenu(PagePager(list(chat.pagify(inviteslist)))).start(ctx)
        else:
            await ctx.send(_("There is no invites for this server"))
            
    @commands.command(aliases=["channellist", "listchannels"])
    @commands.guild_only()
    @commands.admin_or_permissions(manage_channels=True)
    @commands.bot_has_permissions(embed_links=True)
    async def channels(self, ctx, *, server: commands.GuildConverter = None):
        """Get all channels on server"""
        # TODO: Use dpy menus for that
        if server is None or not await self.bot.is_owner(ctx.author):
            server = ctx.guild
        channels = {
            channel_type: ChannelsPager(getattr(server, type_data[0]))
            for channel_type, type_data in KNOWN_CHANNEL_TYPES.items()
        }
        await ChannelsMenu(channels, "category", len(server.channels)).start(ctx)

    @commands.command(aliases=["roleinfo"])
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def rinfo(self, ctx, *, role: discord.Role):
        """Get info about role"""
        em = discord.Embed(
            title=chat.escape(role.name, formatting=True),
            color= 0x313338,
        )
        em.add_field(name=_("ID"), value=role.id)
        em.add_field(
            name=_("Permissions"),
            value="[{0}](https://cogs.fixator10.ru/permissions-calculator/?v={0})".format(
                role.permissions.value
            ),
        )
        em.add_field(
            name=_("Exists since"),
            value=get_markdown_timestamp(role.created_at, TimestampStyle.datetime_long),
        )
        em.add_field(name=_("Color"), value=role.colour)
        em.add_field(name=_("Members"), value=str(len(role.members)))
        em.add_field(name=_("Position"), value=role.position)
        em.add_field(name=_("Managed"), value=bool_emojify(role.managed))
        em.add_field(name=_("Managed by bot"), value=bool_emojify(role.is_bot_managed()))
        em.add_field(name=_("Managed by boosts"), value=bool_emojify(role.is_premium_subscriber()))
        em.add_field(name=_("Managed by integration"), value=bool_emojify(role.is_integration()))
        em.add_field(name=_("Hoist"), value=bool_emojify(role.hoist))
        em.add_field(name=_("Mentionable"), value=bool_emojify(role.mentionable))
        em.add_field(name=_("Mention"), value=role.mention + "\n`" + role.mention + "`")
        em.set_thumbnail(
            url=f"https://xenforo.com/community/rgba.php?r={role.colour.r}&g={role.color.g}&b={role.color.b}&a=255"
        )
        await ctx.send(embed=em)

    @commands.command(aliases=["cperms"])
    @commands.guild_only()
    @commands.admin_or_permissions(administrator=True)
    async def chanperms(
        self,
        ctx,
        member: Optional[discord.Member],
        *,
        channel: Union[
            discord.TextChannel,
            discord.VoiceChannel,
            discord.StageChannel,
            discord.CategoryChannel,
        ] = None,
    ):
        """Check user's permission for current or provided channel"""
        if not member:
            member = ctx.author
        if not channel:
            channel = ctx.channel
        perms = channel.permissions_for(member)
        await ctx.send(
            "{}\n{}".format(
                chat.inline(str(perms.value)),
                chat.box(
                    chat.format_perms_list(perms) if perms.value else _("No permissions"),
                    lang="py",
                ),
            )
        )


    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def serverinfo(self, ctx, details: bool = True):
        """
        Show server information.

        `details`: Shows more information when set to `True`.
        Default to False.
        """
        guild = ctx.guild
        created_at = _("Created on {date_and_time}. That's {relative_time}!").format(
            date_and_time=discord.utils.format_dt(guild.created_at),
            relative_time=discord.utils.format_dt(guild.created_at, "R"),
        )
        online = humanize_number(
            len([m.status for m in guild.members if m.status != discord.Status.offline])
        )
        total_users = guild.member_count and humanize_number(guild.member_count)
        text_channels = humanize_number(len(guild.text_channels))
        voice_channels = humanize_number(len(guild.voice_channels))
        stage_channels = humanize_number(len(guild.stage_channels))
        if not details:
            data = discord.Embed(description=created_at, colour=await ctx.embed_colour())
            data.add_field(
                name=_("Users online"),
                value=f"{online}/{total_users}" if total_users else _("Not available"),
            )
            data.add_field(name=_("Text Channels"), value=text_channels)
            data.add_field(name=_("Voice Channels"), value=voice_channels)
            data.add_field(name=_("Roles"), value=humanize_number(len(guild.roles)))
            data.add_field(name=_("Owner"), value=str(guild.owner))
            data.set_footer(
                text=_("Server ID: ")
                + str(guild.id)
                + _("  •  Use {command} for more info on the server.").format(
                    command=f"{ctx.clean_prefix}serverinfo 1"
                )
            )
            if guild.icon:
                data.set_author(name=guild.name, url=guild.icon)
                data.set_thumbnail(url=guild.icon)
            else:
                data.set_author(name=guild.name)
        else:

            def _size(num: int):
                for unit in ["B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB"]:
                    if abs(num) < 1024.0:
                        return "{0:.1f}{1}".format(num, unit)
                    num /= 1024.0
                return "{0:.1f}{1}".format(num, "YB")

            def _bitsize(num: int):
                for unit in ["B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB"]:
                    if abs(num) < 1000.0:
                        return "{0:.1f}{1}".format(num, unit)
                    num /= 1000.0
                return "{0:.1f}{1}".format(num, "YB")

            shard_info = (
                _("\nShard ID: **{shard_id}/{shard_count}**").format(
                    shard_id=humanize_number(guild.shard_id + 1),
                    shard_count=humanize_number(ctx.bot.shard_count),
                )
                if ctx.bot.shard_count > 1
                else ""
            )
            # Logic from: https://github.com/TrustyJAID/Trusty-cogs/blob/master/serverstats/serverstats.py#L159
            online_stats = {
                _("Humans: "): lambda x: not x.bot,
                _(" • Bots: "): lambda x: x.bot,
                "\N{LARGE GREEN CIRCLE}": lambda x: x.status is discord.Status.online,
                "\N{LARGE ORANGE CIRCLE}": lambda x: x.status is discord.Status.idle,
                "\N{LARGE RED CIRCLE}": lambda x: x.status is discord.Status.do_not_disturb,
                "\N{MEDIUM WHITE CIRCLE}\N{VARIATION SELECTOR-16}": lambda x: (
                    x.status is discord.Status.offline
                ),
                "\N{LARGE PURPLE CIRCLE}": lambda x: any(
                    a.type is discord.ActivityType.streaming for a in x.activities
                ),
                "\N{MOBILE PHONE}": lambda x: x.is_on_mobile(),
            }
            member_msg = _("Users online: **{online}/{total_users}**\n").format(
                online=online, total_users=total_users
            )
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

            verif = {
                "none": _("0 - None"),
                "low": _("1 - Low"),
                "medium": _("2 - Medium"),
                "high": _("3 - High"),
                "highest": _("4 - Highest"),
            }

            joined_on = _(
                "{bot_name} joined this server on {bot_join}. That's over {since_join} days ago."
            ).format(
                bot_name=ctx.bot.user.name,
                bot_join=guild.me.joined_at.strftime("%d %b %Y %H:%M:%S"),
                since_join=humanize_number((ctx.message.created_at - guild.me.joined_at).days),
            )

            data = discord.Embed(
                description=(f"{guild.description}\n\n" if guild.description else "") + created_at,
                colour=await ctx.embed_colour(),
            )
            data.set_author(
                name=guild.name,
                icon_url="https://cdn.discordapp.com/emojis/457879292152381443.png"
                if "VERIFIED" in guild.features
                else "https://cdn.discordapp.com/emojis/508929941610430464.png"
                if "PARTNERED" in guild.features
                else None,
            )
            if guild.icon:
                data.set_thumbnail(url=guild.icon)
            data.add_field(name=_("Members:"), value=member_msg)
            data.add_field(
                name=_("Channels:"),
                value=_(
                    "\N{SPEECH BALLOON} Text: {text}\n"
                    "\N{SPEAKER WITH THREE SOUND WAVES} Voice: {voice}\n"
                    "\N{STUDIO MICROPHONE} Stage: {stage}"
                ).format(
                    text=bold(text_channels),
                    voice=bold(voice_channels),
                    stage=bold(stage_channels),
                ),
            )
            data.add_field(
                name=_("Utility:"),
                value=_(
                    "Owner: {owner}\nVerif. level: {verif}\nServer ID: {id}{shard_info}"
                ).format(
                    owner=bold(str(guild.owner)),
                    verif=bold(verif[str(guild.verification_level)]),
                    id=bold(str(guild.id)),
                    shard_info=shard_info,
                ),
                inline=False,
            )
            data.add_field(
                name=_("Misc:"),
                value=_(
                    "AFK channel: {afk_chan}\nAFK timeout: {afk_timeout}\nCustom emojis: {emoji_count}\nRoles: {role_count}"
                ).format(
                    afk_chan=bold(str(guild.afk_channel))
                    if guild.afk_channel
                    else bold(_("Not set")),
                    afk_timeout=bold(humanize_timedelta(seconds=guild.afk_timeout)),
                    emoji_count=bold(humanize_number(len(guild.emojis))),
                    role_count=bold(humanize_number(len(guild.roles))),
                ),
                inline=False,
            )

            excluded_features = {
                # available to everyone since forum channels private beta
                "THREE_DAY_THREAD_ARCHIVE",
                "SEVEN_DAY_THREAD_ARCHIVE",
                # rolled out to everyone already
                "NEW_THREAD_PERMISSIONS",
                "TEXT_IN_VOICE_ENABLED",
                "THREADS_ENABLED",
                # available to everyone sometime after forum channel release
                "PRIVATE_THREADS",
            }
            custom_feature_names = {
                "VANITY_URL": "Vanity URL",
                "VIP_REGIONS": "VIP regions",
            }
            features = sorted(guild.features)
            if "COMMUNITY" in features:
                features.remove("NEWS")
            feature_names = [
                custom_feature_names.get(feature, " ".join(feature.split("_")).capitalize())
                for feature in features
                if feature not in excluded_features
            ]
            if guild.features:
                data.add_field(
                    name=_("Server features:"),
                    value="\n".join(
                        f"\N{WHITE HEAVY CHECK MARK} {feature}" for feature in feature_names
                    ),
                )

            if guild.premium_tier != 0:
                nitro_boost = _(
                    "Tier {boostlevel} with {nitroboosters} boosts\n"
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
                data.add_field(name=_("Nitro Boost:"), value=nitro_boost)
            if guild.splash:
                data.set_image(url=guild.splash.replace(format="png"))
            data.set_footer(text=joined_on)

        await ctx.send(embed=data)
