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

from .common_variables import CHANNEL_TYPE_EMOJIS, GUILD_FEATURES, KNOWN_CHANNEL_TYPES
from .embeds import emoji_embed
from .menus import ActivityPager, BaseMenu, ChannelsMenu, ChannelsPager, EmojiPager, PagePager
from .utils import _


@cog_i18n(_)
class DataUtils(commands.Cog):
    """Commands for getting information about users or servers."""

    # noinspection PyMissingConstructor
    def __init__(self, bot):
        self.bot = bot

    def format_help_for_context(self, ctx: commands.Context) -> str:  # Thanks Sinbad!
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\n\n**Version**: {self.__version__}"

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