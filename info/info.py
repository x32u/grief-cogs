
import discord
from grief.core.utils.menus import SimpleMenu
from grief.core import commands
from grief.core.bot import Red

import asyncio
import datetime
import discord
import inspect
import itertools
import logging
import re

from discord.ui import Button, View
from discord.ext import tasks
from discord import Embed, File, TextChannel, Member, User, Role 

from contextlib import suppress as sps
from tabulate import tabulate
from typing import Optional

from grief.core import checks, commands
from grief.core.utils import chat_formatting as cf
from grief.core.utils.common_filters import filter_invites
from grief.core.utils.menus import menu, DEFAULT_CONTROLS, close_menu

from .views import URLView
from discord.ui import View, Button
from grief.core.commands import GuildContext

from .converter import FuzzyMember

from asyncio import TimeoutError as AsyncTimeoutError
from textwrap import shorten
from types import SimpleNamespace
from typing import Optional, Union
from datetime import datetime

from fixcogsutils.dpy_future import TimestampStyle, get_markdown_timestamp
from fixcogsutils.formatting import bool_emojify

from .common_variables import CHANNEL_TYPE_EMOJIS, GUILD_FEATURES, KNOWN_CHANNEL_TYPES
from .embeds import emoji_embed
from .menus import ActivityPager, BaseMenu, ChannelsMenu, ChannelsPager, EmojiPager, PagePager
from .utils import _

from grief.core import commands
from grief.core.i18n import cog_i18n
from grief.core.utils import chat_formatting as chat
from grief.core.utils.predicates import ReactionPredicate
from grief.core.utils.chat_formatting import (
    bold,
    escape,
    italics,
    humanize_number,
    humanize_timedelta,
)

DISCORD_API_LINK = "https://discord.com/api/invite/"

class Info(commands.Cog):
    """Suite of tools to grab banners, icons, etc."""
    
    # Messages.
    X = ":x: Error: "
    MEMBER_NO_GUILD_AVATAR = X + "this user does not have a server avatar."
    # Other constants.
    IMAGE_HYPERLINK = "**Image link:**  [Click here]({})"

    def __init__(self, bot: Red):
        super().__init__()
        self.bot = bot

    @commands.command(aliases=["av"])
    async def avatar(self, ctx: commands.Context, user: discord.User = None):
        """Get someone's avatar."""
        
        if user is None:
            user = ctx.author
        avatar_url = user.avatar.url

        embed = discord.Embed(colour=discord.Colour.dark_theme())
        embed.title = f"Avatar of {user.display_name}"
        embed.description = self.IMAGE_HYPERLINK.format(avatar_url)
        embed.set_image(url=avatar_url)
        embed.set_footer(text=f"User ID: {user.id}")
        await ctx.reply(embed=embed, mention_author=False)

    @commands.command(aliases=["sav"])
    async def serveravatar(self, ctx: commands.Context, user: discord.Member = None):
        """Get someone's server avatar (if they have one)."""
        
        if user is None:
            user = ctx.author
        gld_avatar = user.guild_avatar
        if not gld_avatar:
            await ctx.reply(self.MEMBER_NO_GUILD_AVATAR)
        else:
            gld_avatar_url = gld_avatar.url
            embed = discord.Embed(colour=discord.Colour.dark_theme())
            embed.title = f"Server avatar of {user.display_name}"
            embed.description = self.IMAGE_HYPERLINK.format(gld_avatar_url)
            embed.set_image(url=gld_avatar_url)
            embed.set_footer(text=f"User ID: {user.id}")
            await ctx.reply(embed=embed, mention_author=False)
    
    @commands.command(aliases=["sicon"])
    async def icon(self, ctx: commands.Context):
        """Get the server's icon."""
        
        gld: discord.Guild = ctx.guild
        img_dict = {
            "Server Icon": gld.icon.url if gld.icon else None,
        }
        embed_list = []
        for name, img_url in img_dict.items():
            if img_url:
                embed = discord.Embed(colour=discord.Colour.dark_theme(), title=name)
                embed.description = self.IMAGE_HYPERLINK.format(img_url)
                embed.set_image(url=img_url)
                embed_list.append(embed)
        if not embed_list:
            await ctx.send("This server doesn't have a icon set.")
        if embed_list:
            await SimpleMenu(embed_list).start(ctx) 

    @commands.command()
    async def sbanner(self, ctx: commands.Context):
        """Get the server's banner."""
        
        gld: discord.Guild = ctx.guild
        img_dict = {
            "Server Banner": gld.banner.url if gld.banner else None,
        }
        embed_list = []
        for name, img_url in img_dict.items():
            if img_url:
                embed = discord.Embed(colour=discord.Colour.dark_theme(), title=name)
                embed.description = self.IMAGE_HYPERLINK.format(img_url)
                embed.set_image(url=img_url)
                embed_list.append(embed)
        if not embed_list:
            await ctx.send("This server doesn't have a banner set.")
        if embed_list:
            await SimpleMenu(embed_list).start(ctx) 
        
    @commands.command()
    async def invsplash(self, ctx: commands.Context):
        """Get the server's invite splash."""
        
        gld: discord.Guild = ctx.guild
        img_dict = {
            "Server Invite Splash": gld.splash.url if gld.splash else None,
        }
        embed_list = []
        for name, img_url in img_dict.items():
            if img_url:
                embed = discord.Embed(colour=discord.Colour.dark_theme(), title=name)
                embed.description = self.IMAGE_HYPERLINK.format(img_url)
                embed.set_image(url=img_url)
                embed_list.append(embed)
        if not embed_list:
            await ctx.send("This server doesn't have a invite splash set.")
        if embed_list:
            await SimpleMenu(embed_list).start(ctx) 


    @commands.command(aliases=["invsplash, isplash"])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def invitesplash(self, ctx: commands.Context):
        """Grab a servers discovery splash."""
        if member == None:member = ctx.author
        if discord.Guild.discovery_splash == None:
            em = discord.Embed(color=0x313338, description=f"{member.mention} doesn't have a banner on their profile")
            await ctx.reply(embed=em, mention_author=False)
        else:
            banner_url = ctx.guild.splash
            button1 = Button(label="Banner", url=ctx.guild.splash.url)
            e = discord.Embed(color=0x313338)
            e.set_image(url=banner_url)
            view = View()
            view.add_item(button1)
            await ctx.reply(embed=e, view=view, mention_author=False)

    @commands.command(aliases=["bnr"])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def banner(self, ctx: commands.Context, *, member: discord.User = None):
        """Grab a users banner."""
        if member == None:member = ctx.author
        user = await self.bot.fetch_user(member.id)
        if user.banner == None:
            em = discord.Embed(color=0x313338, description=f"{member.mention} doesn't have a banner on their profile")
            await ctx.reply(embed=em, mention_author=False)
        else:
            banner_url = user.banner.url
            button1 = Button(label="Banner", url=banner_url)
            e = discord.Embed(color=0x313338)
            e.set_image(url=banner_url)
            view = View()
            view.add_item(button1)
            await ctx.reply(embed=e, view=view, mention_author=False)

    @commands.guild_only()
    @commands.command()
    async def onlinestatus(self, ctx):
        """Print how many people are using each type of device."""
        device = {
			(True, True, True): 0,
			(False, True, True): 1,
			(True, False, True): 2,
			(True, True, False): 3,
			(False, False, True): 4,
			(True, False, False): 5,
			(False, True, False): 6,
			(False, False, False): 7
		}
        store = [0, 0, 0, 0, 0, 0, 0, 0]
        for m in ctx.guild.members:
                value = (
				    m.desktop_status == discord.Status.offline,
				    m.web_status == discord.Status.offline,
				    m.mobile_status == discord.Status.offline
			)
        store[device[value]] += 1
        msg = (
			f'offline all: {store[0]}'
			f'\ndesktop only: {store[1]}'
			f'\nweb only: {store[2]}'
			f'\nmobile only: {store[3]}'
			f'\ndesktop web: {store[4]}'
			f'\nweb mobile: {store[5]}'
			f'\ndesktop mobile: {store[6]}'
			f'\nonline all: {store[7]}'
		)
        await ctx.send(f'```py\n{msg}```')

    
    @commands.guild_only()
    @commands.command(aliases=["mc"])
    async def membercount(self, ctx: GuildContext) -> None:
        """Get count of all members + humans and bots separately."""
        guild = ctx.guild
        member_count = 0
        human_count = 0
        bot_count = 0
        for member in guild.members:
            if member.bot:
                bot_count += 1
            else:
                human_count += 1
            member_count += 1
        if await ctx.embed_requested():
            embed = discord.Embed(
                timestamp=datetime.now(), color=await ctx.embed_color()
            )
            embed.add_field(name="Members", value=str(member_count))
            embed.add_field(name="Humans", value=str(human_count))
            embed.add_field(name="Bots", value=str(bot_count))
            await ctx.send(embed=embed)
        else:
            await ctx.send(
                f"**Members:** {member_count}\n"
                f"**Humans:** {human_count}\n"
                f"**Bots:** {bot_count}"
            )
    
    @commands.guild_only()
    @commands.command()
    async def devices(self, ctx, *, member: discord.Member=None):
        """Show what devices a member is using."""
        if member is None:
            member = ctx.author
        d = str(member.desktop_status)
        m = str(member.mobile_status)
        w = str(member.web_status)
		#because it isn't supported in d.py, manually override if streaming
        if any([isinstance(a, discord.Streaming) for a in member.activities]):
            d = d if d == 'offline' else 'streaming'
            m = m if m == 'offline' else 'streaming'
            w = w if w == 'offline' else 'streaming'
        status = {
			'online': '\U0001f7e2',
			'idle': '\U0001f7e0',
			'dnd': '\N{LARGE RED CIRCLE}',
			'offline': '\N{MEDIUM WHITE CIRCLE}',
			'streaming': '\U0001f7e3'
		}
        embed = discord.Embed(
			title=f'**{member.display_name}\'s devices:**',
			description=(
				f'{status[d]} Desktop\n'
				f'{status[m]} Mobile\n'
				f'{status[w]} Web'
			),
			color=await ctx.embed_color()
		)
        if discord.version_info.major == 1:
            embed.set_thumbnail(url=member.avatar_url)
        else:
            embed.set_thumbnail(url=member.display_avatar.url)
        try:
            await ctx.send(embed=embed)
        except discord.errors.Forbidden:
            await ctx.send(
				f'{member.display_name}\'s devices:\n'
				f'{status[d]} Desktop\n'
				f'{status[m]} Mobile\n'
				f'{status[w]} Web'
			)
    
    @commands.guild_only()
    @commands.command()
    @checks.mod_or_permissions(manage_guild=True)
    async def banlist(self, ctx):
        """Displays the server's banlist."""
        try:
            banlist = [bans async for bans in ctx.guild.bans()]
        except discord.errors.Forbidden:
            await ctx.send("I do not have the `Ban Members` permission.")
            return
        bancount = len(banlist)
        ban_list = []
        if bancount == 0:
            msg = "No users are banned from this server."
        else:
            msg = ""
            for user_obj in banlist:
                user_name = f"{user_obj.user.name}#{user_obj.user.discriminator}"
                msg += f"`{user_obj.user.id} - {user_name}`\n"

        banlist = sorted(msg)
        if ctx.channel.permissions_for(ctx.guild.me).embed_links:
            embed_list = []
            for page in cf.pagify(msg, shorten_by=1400):
                embed = discord.Embed(
                    description=f"**Total bans:** {bancount}\n\n{page}",
                    colour=await ctx.embed_colour(),
                )
                embed_list.append(embed)
            await menu(ctx, embed_list, DEFAULT_CONTROLS)
        else:
            text_list = []
            for page in cf.pagify(msg, shorten_by=1400):
                text = f"**Total bans:** {bancount}\n{page}"
                text_list.append(text)
            await menu(ctx, text_list, DEFAULT_CONTROLS)

    @commands.guild_only()
    @commands.command()
    async def einfo(self, ctx, emoji: discord.Emoji):
        """Emoji information."""
        yesno = {True: "Yes", False: "No"}
        header = f"{str(emoji)}\n"
        m = (
            f"[Name]:       {emoji.name}\n"
            f"[Guild]:      {emoji.guild}\n"
            f"[URL]:        {emoji.url}\n"
            f"[Animated]:   {yesno[emoji.animated]}"
        )
        await ctx.send(header + cf.box(m, lang="ini"))

    @commands.guild_only()
    @commands.command()
    @checks.mod_or_permissions(manage_guild=True)
    async def inrole(self, ctx, *, rolename: str):
        """Check members in the role specified."""
        guild = ctx.guild
        await ctx.typing()
        if rolename.startswith("<@&"):
            role_id = int(re.search(r"<@&(.{17,19})>$", rolename)[1])
            role = discord.utils.get(ctx.guild.roles, id=role_id)
        elif len(rolename) in [17, 18, 19] and rolename.isdigit():
            role = discord.utils.get(ctx.guild.roles, id=int(rolename))
        else:
            role = discord.utils.find(lambda r: r.name.lower() == rolename.lower(), guild.roles)

        if role is None:
            roles = []
            for r in guild.roles:
                if rolename.lower() in r.name.lower():
                    roles.append(r)

            if len(roles) == 1:
                role = roles[0]
            elif len(roles) < 1:
                await ctx.send(f"No roles containing `{rolename}` were found.")
                return
            else:
                msg = (
                    f"**{len(roles)} roles found with** `{rolename}` **in the name.**\n"
                    f"Type the number of the role you wish to see.\n\n"
                )
                tbul8 = []
                for num, role in enumerate(roles):
                    tbul8.append([num + 1, role.name])
                m1 = await ctx.send(msg + tabulate(tbul8, tablefmt="plain"))

                def check(m):
                    if (m.author == ctx.author) and (m.channel == ctx.channel):
                        return True

                try:
                    response = await self.bot.wait_for("message", check=check, timeout=25)
                except asyncio.TimeoutError:
                    await m1.delete()
                    return
                if not response.content.isdigit():
                    await m1.delete()
                    return
                else:
                    response = int(response.content)

                if response not in range(0, len(roles) + 1):
                    return await ctx.send("Cancelled.")
                elif response == 0:
                    return await ctx.send("Cancelled.")
                else:
                    role = roles[response - 1]

        users_in_role = "\n".join(sorted(m.display_name for m in guild.members if role in m.roles))
        if len(users_in_role) == 0:
            if ctx.channel.permissions_for(ctx.guild.me).embed_links:
                embed = discord.Embed(
                    description=cf.bold(f"0 users found in the {role.name} role."),
                    colour=await ctx.embed_colour(),
                )
                return await ctx.send(embed=embed)
            else:
                return await ctx.send(cf.bold(f"0 users found in the {role.name} role."))

        embed_list = []
        role_len = len([m for m in guild.members if role in m.roles])
        if ctx.channel.permissions_for(ctx.guild.me).embed_links:
            for page in cf.pagify(users_in_role, delims=["\n"], page_length=200):
                embed = discord.Embed(
                    description=cf.bold(f"{role_len} users found in the {role.name} role.\n"),
                    colour=await ctx.embed_colour(),
                )
                embed.add_field(name="Users", value=page)
                embed_list.append(embed)
            final_embed_list = []
            for i, embed in enumerate(embed_list):
                embed.set_footer(text=f"Page {i + 1}/{len(embed_list)}")
                final_embed_list.append(embed)
            if len(embed_list) == 1:
                close_control = {"\N{CROSS MARK}": close_menu}
                await menu(ctx, final_embed_list, close_control)
            else:
                await menu(ctx, final_embed_list, DEFAULT_CONTROLS)
        else:
            for page in cf.pagify(users_in_role, delims=["\n"], page_length=200):
                msg = f"**{role_len} users found in the {role.name} role.**\n"
                msg += page
                embed_list.append(msg)
            if len(embed_list) == 1:
                close_control = {"\N{CROSS MARK}": close_menu}
                await menu(ctx, embed_list, close_control)
            else:
                await menu(ctx, embed_list, DEFAULT_CONTROLS)

    @commands.guild_only()
    @commands.command()
    async def joined(self, ctx, user: discord.Member = None):
        """Show when a user joined the guild."""
        if not user:
            user = ctx.author
        if user.joined_at:
            user_joined = user.joined_at.strftime("%d %b %Y %H:%M")
            since_joined = (ctx.message.created_at - user.joined_at).days
            joined_on = f"{user_joined} ({since_joined} days ago)"
        else:
            joined_on = "a mysterious date that not even Discord knows."

        if ctx.channel.permissions_for(ctx.guild.me).embed_links:
            embed = discord.Embed(
                description=f"{user.mention} joined this guild on {joined_on}.",
                color=await ctx.embed_colour(),
            )
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"**{user.display_name}** joined this guild on **{joined_on}**.")

    @commands.guild_only()
    @commands.command()
    @checks.mod_or_permissions(manage_guild=True)
    async def perms(self, ctx, user: discord.Member = None):
        """Fetch a specific user's permissions."""
        if user is None:
            user = ctx.author

        perms = iter(ctx.channel.permissions_for(user))
        perms_we_have = ""
        perms_we_dont = ""
        for x in sorted(perms):
            if "True" in str(x):
                perms_we_have += "+ {0}\n".format(str(x).split("'")[1])
            else:
                perms_we_dont += "- {0}\n".format(str(x).split("'")[1])
        await ctx.send(cf.box(f"{perms_we_have}{perms_we_dont}", lang="diff"))

    @commands.guild_only()
    @commands.command(aliases=["listroles"])
    @checks.mod_or_permissions(manage_guild=True)
    async def rolelist(self, ctx):
        """Displays the server's roles."""
        form = "`{rpos:0{zpadding}}` - `{rid}` - `{rcolor}` - {rment} "
        max_zpadding = max([len(str(r.position)) for r in ctx.guild.roles])
        rolelist = [
            form.format(rpos=r.position, zpadding=max_zpadding, rid=r.id, rment=r.mention, rcolor=r.color)
            for r in ctx.guild.roles
        ]
        rolelist = sorted(rolelist, reverse=True)
        rolelist = "\n".join(rolelist)
        embed_list = []
        if ctx.channel.permissions_for(ctx.guild.me).embed_links:
            for page in cf.pagify(rolelist, shorten_by=1400):
                embed = discord.Embed(
                    description=f"**Total roles:** {len(ctx.guild.roles)}\n\n{page}",
                    colour=await ctx.embed_colour(),
                )
                embed_list.append(embed)
        else:
            for page in cf.pagify(rolelist, shorten_by=1400):
                msg = f"**Total roles:** {len(ctx.guild.roles)}\n{page}"
                embed_list.append(msg)

        await menu(ctx, embed_list, DEFAULT_CONTROLS)

    @commands.command(hidden=True)
    async def sharedservers(self, ctx, user: discord.Member = None):
        """Shows shared server info. Defaults to author."""
        if not user:
            user = ctx.author

        mutual_guilds = user.mutual_guilds
        data = f"[Guilds]:     {len(mutual_guilds)} shared\n"
        shared_servers = sorted([g.name for g in mutual_guilds], key=lambda v: (v.upper(), v[0].islower()))
        data += f"[In Guilds]:  {cf.humanize_list(shared_servers, style='unit')}"

        for page in cf.pagify(data, ["\n"], page_length=1800):
            await ctx.send(cf.box(data, lang="ini"))
    
    @commands.command()
    @commands.has_permissions(read_message_history=True)
    @commands.bot_has_permissions(read_message_history=True)
    async def firstmessage(
        self,
        ctx: commands.Context,
        channel: Optional[
            discord.TextChannel
            | discord.Thread
            | discord.DMChannel
            | discord.GroupChannel
            | discord.User
            | discord.Member
        ] = commands.CurrentChannel,
    ):
        """
        Provide a link to the first message in current or provided channel.
        """
        try:
            messages = [message async for message in channel.history(limit=1, oldest_first=True)]

            chan = (
                f"<@{channel.id}>"
                if isinstance(channel, discord.DMChannel | discord.User | discord.Member)
                else f"<#{channel.id}>"
            )

            embed: discord.Embed = discord.Embed(
                color=await ctx.embed_color(),
                timestamp=messages[0].created_at,
                description=f"[First message in]({messages[0].jump_url}) {chan}",
            )
            embed.set_author(
                name=messages[0].author.display_name,
                icon_url=messages[0].author.avatar.url
                if messages[0].author.avatar
                else messages[0].author.display_avatar.url,
            )

        except (discord.Forbidden, discord.HTTPException, IndexError, AttributeError):
            return await ctx.maybe_send_embed("Unable to read message history for that channel.")

        view = URLView(label="Jump to message", jump_url=messages[0].jump_url)

        await ctx.send(embed=embed, view=view)


    @staticmethod
    def count_months(days):
        lens = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        cy = itertools.cycle(lens)
        months = 0
        m_temp = 0
        mo_len = next(cy)
        for i in range(1, days + 1):
            m_temp += 1
            if m_temp == mo_len:
                months += 1
                m_temp = 0
                mo_len = next(cy)
                if mo_len == 28 and months >= 48:
                    mo_len += 1

        weeks, days = divmod(m_temp, 7)
        return months, weeks, days

    def category_format(self, cat_chan_tuple: tuple):
        cat = cat_chan_tuple[0]
        chs = cat_chan_tuple[1]

        chfs = self.channels_format(chs)
        if chfs != []:
            ch_forms = ["\t" + f for f in chfs]
            return "\n".join([f"{cat.name} :: {cat.id}"] + ch_forms)
        else:
            return "\n".join([f"{cat.name} :: {cat.id}"] + ["\tNo Channels"])

    @staticmethod
    def channels_format(channels: list):
        if channels == []:
            return []

        channel_form = "{name} :: {ctype} :: {cid}"

        def type_name(channel):
            return channel.__class__.__name__[:-7]

        name_justify = max([len(c.name[:24]) for c in channels])
        type_justify = max([len(type_name(c)) for c in channels])

        return [
            channel_form.format(
                name=c.name[:24].ljust(name_justify),
                ctype=type_name(c).ljust(type_justify),
                cid=c.id,
            )
            for c in channels
        ]

    def _dynamic_time(self, time):
        try:
            date_join = datetime.datetime.strptime(str(time), "%Y-%m-%d %H:%M:%S.%f%z")
        except ValueError:
            time = f"{str(time)}.0"
            date_join = datetime.datetime.strptime(str(time), "%Y-%m-%d %H:%M:%S.%f%z")
        date_now = discord.utils.utcnow()
        since_join = date_now - date_join

        mins, secs = divmod(int(since_join.total_seconds()), 60)
        hrs, mins = divmod(mins, 60)
        days, hrs = divmod(hrs, 24)
        mths, wks, days = self.count_months(days)
        yrs, mths = divmod(mths, 12)

        m = f"{yrs}y {mths}mth {wks}w {days}d {hrs}h {mins}m {secs}s"
        m2 = [x for x in m.split() if x[0] != "0"]
        s = " ".join(m2[:2])
        if s:
            return f"{s} ago"
        else:
            return ""

    @staticmethod
    def fetch_joined_at(user, guild):
        return user.joined_at

    async def message_from_message_link(self, ctx: commands.Context, message_link: str):
        bad_link_msg = "That doesn't look like a message link, I can't reach that message, "
        bad_link_msg += "or you didn't attach a sticker to the command message."
        no_guild_msg = "You aren't in that guild."
        no_channel_msg = "You can't view that channel."
        no_message_msg = "That message wasn't found."
        no_sticker_msg = "There are no stickers attached to that message."

        if not "discord.com/channels/" in message_link:
            return bad_link_msg
        ids = message_link.split("/")
        if len(ids) != 7:
            return bad_link_msg

        guild = self.bot.get_guild(int(ids[4]))
        if not guild:
            return bad_link_msg

        channel = guild.get_channel_or_thread(int(ids[5]))
        if not channel:
            channel = self.bot.get_channel(int(ids[5]))
        if not channel:
            return bad_link_msg

        if ctx.author not in guild.members:
            return no_guild_msg
        if not channel.permissions_for(ctx.author).read_messages:
            return no_channel_msg

        try:
            message = await channel.fetch_message(int(ids[6]))
        except discord.errors.NotFound:
            return no_message_msg

        if not message.stickers:
            return no_sticker_msg

        return message

    @staticmethod
    def role_from_string(guild, rolename, roles=None):
        if roles is None:
            roles = guild.roles
        if rolename.startswith("<@&"):
            role_id = int(re.search(r"<@&(.{17,19})>$", rolename)[1])
            role = guild.get_role(role_id)
        else:
            role = discord.utils.find(lambda r: r.name.lower() == str(rolename).lower(), roles)
        return role

    def sort_channels(self, channels):
        temp = {}

        channels = sorted(channels, key=lambda c: c.position)

        for c in channels[:]:
            if isinstance(c, discord.CategoryChannel):
                channels.pop(channels.index(c))
                temp[c] = list()

        for c in channels[:]:
            if c.category:
                channels.pop(channels.index(c))
                temp[c.category].append(c)

        category_channels = sorted(
            [(cat, sorted(chans, key=lambda c: c.position)) for cat, chans in temp.items()],
            key=lambda t: t[0].position,
        )
        return channels, category_channels
    
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
            
    @commands.command()
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

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def roleinfo(self, ctx, *, role: discord.Role):
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
        created_at = _("Created on {date_and_time}. That's {relative_time}.").format(
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
            if guild.banner:
                data.set_image(url=guild.banner)
            data.set_footer(text=joined_on)

        await ctx.send(embed=data)
