import asyncio
import datetime
import discord
import inspect
import itertools
import logging
import re

from contextlib import suppress as sps
from tabulate import tabulate
from typing import Optional

from grief.core import checks, commands
from grief.core.utils import chat_formatting as cf
from grief.core.utils.common_filters import filter_invites
from grief.core.utils.menus import menu, DEFAULT_CONTROLS, close_menu

from .views import URLView
from grief.core.commands import GuildContext

from .converter import FuzzyMember

from asyncio import TimeoutError as AsyncTimeoutError
from textwrap import shorten
from types import SimpleNamespace
from typing import Optional, Union
from datetime import datetime

log = logging.getLogger("grief.modtools")


class ModTools(commands.Cog):
    """Mod and Admin tools."""

    async def red_delete_data_for_user(self, **kwargs):
        """Nothing to delete"""
        return

    def __init__(self, bot):
        self.bot = bot
    
    def valid_nickname(self, nickname: str):
        if len(nickname) <= 32:
            return True
        return False

    async def _Tools__error(self, ctx, error):
        if error.__cause__:
            cause = error.__cause__
            log.info(f"Tools Cog :: Error Occured ::\n{error}\n{cause}\n")
        else:
            cause = error
            log.info(f"Tools Cog :: Error Occured :: \n{cause}\n")

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
            log.exception(f"Unable to read message history for {channel.id}")
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
    
    @checks.mod()
    @commands.command()
    @checks.bot_has_permissions(manage_nicknames=True)
    async def nick(self, ctx, user: discord.Member, nickname: str=None):
        """Change a user's nickname."""
        valid_nick_check = self.valid_nickname(nickname=str)
        if not valid_nick_check:
            return await ctx.send(
                "That nickname is too long. Keep it under 32 characters, please."
            )
        try:
            await user.edit(nick=nickname)
            await ctx.tick()
        except discord.errors.Forbidden:
            await ctx.send("Missing permissions.")

    @checks.mod()
    @commands.command()
    @checks.bot_has_permissions(manage_nicknames=True)
    async def freezenick(self, ctx: commands.Context, user: discord.Member, nickname: str=None, reason: Optional[str] = "Nickname frozen.",):
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
            await ctx.send("Missing permissions.")

    @checks.mod()
    @commands.command()
    async def unfreezenick(self, ctx, user: discord.Member):
        """Unfreeze a user's nickname."""
        async with self.config.guild(ctx.guild).frozen() as frozen:
            for e in frozen:
                if user.id in e:
                    frozen.remove(e)
                    await ctx.tick()

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