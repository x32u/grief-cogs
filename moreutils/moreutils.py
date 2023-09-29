import asyncio
import datetime
import json
import logging
import math
import os
import platform
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from io import StringIO
from sys import executable
from typing import Optional, Union

import cpuinfo
import discord
import psutil
import speedtest
from redbot.cogs.downloader.converters import InstalledCog
from redbot.core import commands, version_info
from redbot.core.bot import Red
from redbot.core.data_manager import cog_data_path
from redbot.core.utils import AsyncIter
from redbot.core.utils.chat_formatting import (
    box,
    humanize_number,
    humanize_timedelta,
    pagify,
)

from .diskspeed import get_disk_speed

log = logging.getLogger("grief.moreutils")
dpy = discord.__version__
if dpy > "1.7.4":
    from .dpymenu import DEFAULT_CONTROLS, confirm, menu

    DPY2 = True
else:
    from .dislashmenu import DEFAULT_CONTROLS, confirm, menu

    DPY2 = False


async def wait_reply(ctx: commands.Context, timeout: int = 60):
    def check(message: discord.Message):
        return message.author == ctx.author and message.channel == ctx.channel

    try:
        reply = await ctx.bot.wait_for("message", timeout=timeout, check=check)
        res = reply.content
        try:
            await reply.delete()
        except (
            discord.Forbidden,
            discord.NotFound,
            discord.DiscordServerError,
        ):
            pass
        return res
    except asyncio.TimeoutError:
        return None


class MoreUtils(commands.Cog):


    async def red_delete_data_for_user(self, *, requester, user_id: int):
        """No data to delete"""

    def __init__(self, bot: Red, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot
        if not DPY2:
            from dislash import InteractionClient

            InteractionClient(bot, sync_commands=False)
        self.path = cog_data_path(self)
        self.threadpool = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="more_utils"
        )

    # -/-/-/-/-/-/-/-/FORMATTING-/-/-/-/-/-/-/-/
    @staticmethod
    def get_size(num: float) -> str:
        for unit in ["B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB"]:
            if abs(num) < 1024.0:
                return "{0:.1f}{1}".format(num, unit)
            num /= 1024.0
        return "{0:.1f}{1}".format(num, "YB")

    @staticmethod
    def get_bitsize(num: float) -> str:
        for unit in ["B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB"]:
            if abs(num) < 1000.0:
                return "{0:.1f}{1}".format(num, unit)
            num /= 1000.0
        return "{0:.1f}{1}".format(num, "YB")

    @staticmethod
    def get_bar(progress, total, perc=None, width: int = 20) -> str:
        if perc is not None:
            ratio = perc / 100
        else:
            ratio = progress / total
        bar = "█" * round(ratio * width) + "-" * round(width - (ratio * width))
        return f"|{bar}| {round(100 * ratio, 1)}%"

    async def do_shell_command(self, command: str):
        cmd = f"{executable} -m {command}"

        def exe():
            results = subprocess.run(
                cmd, stdout=subprocess.PIPE, shell=True
            ).stdout.decode("utf-8")
            return results

        res = await self.bot.loop.run_in_executor(self.threadpool, exe)
        return res

    async def run_disk_speed(
        self,
        block_count: int = 128,
        block_size: int = 1048576,
        passes: int = 1,
    ) -> dict:
        reads = []
        writes = []
        with ThreadPoolExecutor(max_workers=1) as pool:
            futures = [
                self.bot.loop.run_in_executor(
                    pool,
                    lambda: get_disk_speed(self.path, block_count, block_size),
                )
                for _ in range(passes)
            ]
            results = await asyncio.gather(*futures)
            for i in results:
                reads.append(i["read"])
                writes.append(i["write"])
        results = {
            "read": sum(reads) / len(reads),
            "write": sum(writes) / len(writes),
        }
        return results

    # -/-/-/-/-/-/-/-/COMMANDS-/-/-/-/-/-/-/-/
    @commands.command(name="pull")
    @commands.is_owner()
    async def update_cog(self, ctx, *cogs: InstalledCog):
        """Auto update & reload cogs"""
        ctx.assume_yes = True
        cog_update_command = ctx.bot.get_command("cog update")
        if cog_update_command is None:
            return await ctx.send(
                f"Make sure you first `{ctx.prefix}load downloader` before you can use this command."
            )
        await ctx.invoke(cog_update_command, *cogs, reload=True)

    @commands.command(aliases=["diskbench"])
    @commands.is_owner()
    async def diskspeed(self, ctx: commands.Context):
        """
        Get disk R/W performance for the server your bot is on

        The results of this test may vary, Python isn't fast enough for this kind of byte-by-byte writing,
        and the file buffering and similar adds too much overhead.
        Still this can give a good idea of where the bot is at I/O wise.
        """

        def diskembed(data: dict) -> discord.Embed:
            if (
                data["write5"] != "Waiting..."
                and data["write5"] != "Running..."
            ):
                embed = discord.Embed(
                    title="Disk I/O", color=discord.Color.green()
                )
                embed.description = "Disk Speed Check COMPLETE"
            else:
                embed = discord.Embed(title="Disk I/O", color=ctx.author.color)
                embed.description = "Running Disk Speed Check"
            first = f"Write: {data['write1']}\n" f"Read:  {data['read1']}"
            embed.add_field(
                name="128 blocks of 1048576 bytes (128MB)",
                value=box(first, lang="python"),
                inline=False,
            )
            second = f"Write: {data['write2']}\n" f"Read:  {data['read2']}"
            embed.add_field(
                name="128 blocks of 2097152 bytes (256MB)",
                value=box(second, lang="python"),
                inline=False,
            )
            third = f"Write: {data['write3']}\n" f"Read:  {data['read3']}"
            embed.add_field(
                name="256 blocks of 1048576 bytes (256MB)",
                value=box(third, lang="python"),
                inline=False,
            )
            fourth = f"Write: {data['write4']}\n" f"Read:  {data['read4']}"
            embed.add_field(
                name="256 blocks of 2097152 bytes (512MB)",
                value=box(fourth, lang="python"),
                inline=False,
            )
            fifth = f"Write: {data['write5']}\n" f"Read:  {data['read5']}"
            embed.add_field(
                name="256 blocks of 4194304 bytes (1GB)",
                value=box(fifth, lang="python"),
                inline=False,
            )
            return embed

        results = {
            "write1": "Running...",
            "read1": "Running...",
            "write2": "Waiting...",
            "read2": "Waiting...",
            "write3": "Waiting...",
            "read3": "Waiting...",
            "write4": "Waiting...",
            "read4": "Waiting...",
            "write5": "Waiting...",
            "read5": "Waiting...",
        }
        msg = None
        for i in range(6):
            stage = i + 1
            em = diskembed(results)
            if not msg:
                msg = await ctx.send(embed=em)
            else:
                await msg.edit(embed=em)
            count = 128
            size = 1048576
            if stage == 2:
                count = 128
                size = 2097152
            elif stage == 3:
                count = 256
                size = 1048576
            elif stage == 4:
                count = 256
                size = 2097152
            elif stage == 6:
                count = 256
                size = 4194304
            res = await self.run_disk_speed(
                block_count=count, block_size=size, passes=3
            )
            write = f"{humanize_number(round(res['write'], 2))}MB/s"
            read = f"{humanize_number(round(res['read'], 2))}MB/s"
            results[f"write{stage}"] = write
            results[f"read{stage}"] = read
            if f"write{stage + 1}" in results:
                results[f"write{stage + 1}"] = "Running..."
                results[f"read{stage + 1}"] = "Running..."
            await asyncio.sleep(1)

    # @commands.command()
    # async def latency(self, ctx: commands.Context):
    #     """Check the bots latency"""
    #     try:
    #         socket_latency = round(self.bot.latency * 1000)
    #     except OverflowError:
    #         return await ctx.send("Bot is up but missed had connection issues the last few seconds.")

    @commands.command()
    @commands.is_owner()
    async def pip(self, ctx, *, command: str):
        """Run a pip command from within your bots venv"""
        async with ctx.typing():
            command = f"pip {command}"
            res = await self.do_shell_command(command)
            embeds = []
            page = 1
            for p in pagify(res):
                embed = discord.Embed(
                    title="Pip Command Results", description=box(p)
                )
                embed.set_footer(text=f"Page {page}")
                page += 1
                embeds.append(embed)
            if len(embeds) > 1:
                await menu(ctx, embeds, DEFAULT_CONTROLS)
            else:
                if embeds:
                    await ctx.send(embed=embeds[0])
                else:
                    await ctx.send("Command ran with no results")

    @commands.command()
    @commands.is_owner()
    async def runshell(self, ctx, *, command: str):
        """Run a shell command from within your bots venv"""
        async with ctx.typing():
            command = f"{command}"
            res = await self.do_shell_command(command)
            embeds = []
            page = 1
            for p in pagify(res):
                embed = discord.Embed(
                    title="Shell Command Results", description=box(p)
                )
                embed.set_footer(text=f"Page {page}")
                page += 1
                embeds.append(embed)
            if len(embeds) > 1:
                await menu(ctx, embeds, DEFAULT_CONTROLS)
            else:
                if embeds:
                    await ctx.send(embed=embeds[0])
                else:
                    await ctx.send("Command ran with no results")

    @commands.command()
    @commands.is_owner()
    async def findguildbyid(self, ctx, guild_id: int):
        """Find a guild by ID"""
        guild = self.bot.get_guild(guild_id)
        if not guild:
            try:
                guild = await self.bot.fetch_guild(guild_id)
            except discord.Forbidden:
                guild = None
        if not guild:
            return await ctx.send("Could not find that guild")
        await ctx.send(f"That ID belongs to the guild `{guild.name}`")

    # Inspired by kennnyshiwa's imperialtoolkit botstat command
    # https://github.com/kennnyshiwa/kennnyshiwa-cogs
    @commands.command()
    async def botinfo(self, ctx: commands.Context):
        """
        Get info about the bot
        """
        async with ctx.typing():
            # -/-/-/CPU-/-/-/
            cpu_count = psutil.cpu_count()  # Int
            cpu_perc = await self.bot.loop.run_in_executor(
                None, lambda: psutil.cpu_percent(interval=3, percpu=True)
            )  # List of floats
            cpu_freq = psutil.cpu_freq(percpu=True)  # List of Objects
            cpu_info = cpuinfo.get_cpu_info()  # Dict
            cpu_type = (
                cpu_info["brand_raw"] if "brand_raw" in cpu_info else "Unknown"
            )

            # -/-/-/MEM-/-/-/
            ram = psutil.virtual_memory()  # Obj
            ram_total = self.get_size(ram.total)
            ram_used = self.get_size(ram.used)
            disk = psutil.disk_usage(os.getcwd())
            disk_total = self.get_size(disk.total)
            disk_used = self.get_size(disk.used)

            p = psutil.Process()
            io_counters = p.io_counters()
            disk_usage_process = (
                io_counters[2] + io_counters[3]
            )  # read_bytes + write_bytes
            # Disk load
            disk_io_counter = psutil.disk_io_counters()
            if disk_io_counter:
                disk_io_total = (
                    disk_io_counter[2] + disk_io_counter[3]
                )  # read_bytes + write_bytes
                disk_usage = (disk_usage_process / disk_io_total) * 100
            else:
                disk_usage = 0

            # -/-/-/NET-/-/-/
            net = psutil.net_io_counters()  # Obj
            sent = self.get_size(net.bytes_sent)
            recv = self.get_size(net.bytes_recv)

            # -/-/-/OS-/-/-/
            if os.name == "nt":
                osdat = platform.uname()
                ostype = (
                    f"{osdat.system} {osdat.release} (version {osdat.version})"
                )
            elif sys.platform == "darwin":
                osdat = platform.mac_ver()
                ostype = f"Mac OS {osdat[0]} {osdat[1]}"
            elif sys.platform == "linux":
                import distro

                ostype = f"{distro.name()} {distro.version()}"
            else:
                ostype = "Unknown"

            td = datetime.datetime.utcnow() - datetime.datetime.fromtimestamp(
                psutil.boot_time()
            )
            sys_uptime = humanize_timedelta(timedelta=td)

            # -/-/-/BOT-/-/-/
            servers = "{:,}".format(len(self.bot.guilds))
            shards = self.bot.shard_count
            users = "{:,}".format(len(self.bot.users))
            channels = "{:,}".format(
                sum(len(guild.channels) for guild in self.bot.guilds)
            )
            emojis = "{:,}".format(len(self.bot.emojis))
            cogs = "{:,}".format(len(self.bot.cogs))
            commandcount = 0
            for cog in self.bot.cogs:
                for __ in self.bot.get_cog(cog).walk_commands():
                    commandcount += 1
            commandcount = "{:,}".format(commandcount)
            td = datetime.datetime.utcnow() - self.bot.uptime
            uptime = humanize_timedelta(timedelta=td)

            # -/-/-/LIBS-/-/-/
            red_version = version_info
            ver = sys.version_info
            py_version = f"{ver.major}.{ver.minor}.{ver.micro}"

            embed = discord.Embed(
                title=f"Stats for {self.bot.user.name}",
                description="Below are various stats about the bot and the system it runs on.",
                color=await ctx.embed_color(),
            )

            botstats = (
                f"Servers:  {servers} ({shards} {'shard' if shards == 1 else 'shards'})\n"
                f"Users:    {users}\n"
                f"Channels: {channels}\n"
                f"Emojis:   {emojis}\n"
                f"Cogs:     {cogs}\n"
                f"Commands: {commandcount}\n"
                f"Uptime:   {uptime}\n"
                f"DPy:      {dpy}\n"
                f"Python:   {py_version}\n"
                f"Owner:    evincement")
                
            embed.add_field(
                name="\N{ROBOT FACE} BOT",
                value=box(botstats, lang="python"),
                inline=False,
            )

            cpustats = f"CPU:    {cpu_type}\n" f"Cores:  {cpu_count}\n"
            if len(cpu_freq) == 1:
                cpustats += f"{cpu_freq[0].current}/{cpu_freq[0].max} Mhz\n"
            else:
                for i, obj in enumerate(cpu_freq):
                    maxfreq = f"/{round(obj.max, 2)}" if obj.max else ""
                    cpustats += (
                        f"Core {i}: {round(obj.current, 2)}{maxfreq} Mhz\n"
                    )
            if isinstance(cpu_perc, list):
                for i, perc in enumerate(cpu_perc):
                    space = " "
                    if i >= 10:
                        space = ""
                    bar = self.get_bar(0, 0, perc)
                    cpustats += f"Core {i}:{space} {bar}\n"
            embed.add_field(
                name="\N{DESKTOP COMPUTER} CPU",
                value=box(cpustats, lang="python"),
                inline=False,
            )

            rambar = self.get_bar(0, 0, ram.percent, width=30)
            diskbar = self.get_bar(0, 0, disk.percent, width=30)
            memtext = (
                f"RAM ({ram_used}/{ram_total})\n"
                f"{rambar}\n"
                f"DISK ({disk_used}/{disk_total})\n"
                f"{diskbar}\n"
            )
            embed.add_field(
                name="\N{FLOPPY DISK} MEM",
                value=box(memtext, lang="python"),
                inline=False,
            )

            disk_usage_bar = self.get_bar(0, 0, disk_usage, width=30)
            i_o = f"DISK LOAD\n" f"{disk_usage_bar}"
            embed.add_field(
                name="\N{GEAR}\N{VARIATION SELECTOR-16} I/O",
                value=box(i_o, lang="python"),
                inline=False,
            )

            netstat = f"Sent:     {sent}\n" f"Received: {recv}"
            embed.add_field(
                name="\N{SATELLITE ANTENNA} Network",
                value=box(netstat, lang="python"),
                inline=False,
            )

            if DPY2:
                bot_icon = self.bot.user.avatar.url.format("png")
            else:
                bot_icon = self.bot.user.avatar_url_as(format="png")
            embed.set_thumbnail(url=bot_icon)
            embed.set_footer(text=f"System: {ostype}\nUptime: {sys_uptime}")
            await ctx.send(embed=embed)

    @commands.command()
    async def getuser(self, ctx, *, user_id: Union[int, discord.User]):
        """Find a user by ID"""
        if isinstance(user_id, int):
            try:
                member = await self.bot.get_or_fetch_user(int(user_id))
            except discord.NotFound:
                return await ctx.send(
                    f"I could not find any users with the ID `{user_id}`"
                )
        else:
            try:
                member = await self.bot.get_or_fetch_user(user_id.id)
            except discord.NotFound:
                return await ctx.send(
                    f"I could not find any users with the ID `{user_id.id}`"
                )
        since_created = f"<t:{int(member.created_at.replace(tzinfo=datetime.timezone.utc).timestamp())}:R>"
        user_created = f"<t:{int(member.created_at.replace(tzinfo=datetime.timezone.utc).timestamp())}:D>"
        created_on = f"Joined Discord on {user_created}\n({since_created})"
        embed = discord.Embed(
            title=f"{member.name} - {member.id}",
            description=created_on,
            color=await ctx.embed_color(),
        )
        if DPY2:
            if member.avatar:
                embed.set_image(url=member.avatar.url)
        else:
            embed.set_image(url=member.avatar_url)
        await ctx.send(embed=embed)

    @commands.command()
    @commands.is_owner()
    async def botip(self, ctx: commands.Context):
        """Get the bots public IP address (in DMs)"""
        async with ctx.typing():
            test = speedtest.Speedtest(secure=True)
            embed = discord.Embed(
                title=f"{self.bot.user.name}'s public IP",
                description=test.results.dict()["client"]["ip"],
            )
            try:
                await ctx.author.send(embed=embed)
                await ctx.tick()
            except discord.Forbidden:
                await ctx.send(
                    "Your DMs appear to be disabled, please enable them and try again."
                )

    async def leave_guild(self, instance, interaction):
        ctx = instance.ctx
        data = instance.pages[instance.page].title.split("--")
        guildname = data[0].strip()
        guildid = data[1].strip()
        msg = await ctx.send(
            f"Are you sure you want me to leave **{guildname}**?"
        )
        yes = await confirm(ctx, msg)
        await msg.delete()
        if yes is None:
            return
        if yes:
            guild = self.bot.get_guild(int(guildid))
            await guild.leave()
            await instance.respond(interaction, f"I have left **{guildname}**")
        else:
            await instance.respond(interaction, f"Not leaving **{guildname}**")
        await menu(
            ctx,
            instance.pages,
            instance.controls,
            instance.message,
            instance.page,
            instance.timeout,
        )

    async def get_invite(self, instance, interaction):
        ctx = instance.ctx
        data = instance.pages[instance.page].title.split("--")
        guildid = data[1].strip()
        guild = self.bot.get_guild(int(guildid))
        invite = None
        my_perms: discord.Permissions = guild.me.guild_permissions
        if my_perms.manage_guild or my_perms.administrator:
            if "VANITY_URL" in guild.features:
                # guild has a vanity url so use it as the one to send
                try:
                    return await guild.vanity_invite()
                except discord.errors.Forbidden:
                    pass
            invites = await guild.invites()
        else:
            invites = []
        for inv in invites:  # Loop through the invites for the guild
            if not (inv.max_uses or inv.max_age or inv.temporary):
                invite = inv
                break
        else:  # No existing invite found that is valid
            channel = None
            if not DPY2:
                channels_and_perms = zip(
                    guild.text_channels,
                    map(guild.me.permissions_in, guild.text_channels),
                )
                channel = next(
                    (
                        channel
                        for channel, perms in channels_and_perms
                        if perms.create_instant_invite
                    ),
                    None,
                )
            else:
                for channel in guild.text_channels:
                    if channel.permissions_for(guild.me).create_instant_invite:
                        break
            try:
                if channel is not None:
                    # Create invite that expires after max_age
                    invite = await channel.create_invite(max_age=3600)
            except discord.HTTPException:
                pass
        if invite:
            await instance.respond(interaction, str(invite))
        else:
            await instance.respond(
                interaction, "I could not get an invite for that server!"
            )
        await menu(
            ctx,
            instance.pages,
            instance.controls,
            instance.message,
            instance.page,
            instance.timeout,
        )

    @commands.command()
    @commands.guild_only()
    async def oldestchannels(self, ctx, amount: int = 10):
        """See which channel is the oldest"""
        async with ctx.typing():
            channels = [
                c
                for c in ctx.guild.channels
                if not isinstance(c, discord.CategoryChannel)
            ]
            c_sort = sorted(channels, key=lambda x: x.created_at)
            txt = "\n".join(
                [
                    f"{i + 1}. {c.mention} "
                    f"created <t:{int(c.created_at.timestamp())}:f> (<t:{int(c.created_at.timestamp())}:R>)"
                    for i, c in enumerate(c_sort[:amount])
                ]
            )
            for p in pagify(txt, page_length=4000):
                em = discord.Embed(description=p, color=ctx.author.color)
                await ctx.send(embed=em)

    @commands.command(aliases=["oldestusers"])
    @commands.guild_only()
    async def oldestmembers(
        self,
        ctx,
        amount: Optional[int] = 10,
        include_bots: Optional[bool] = False,
    ):
        """
        See which users have been in the server the longest

        **Arguments**
        `amount:` how many members to display
        `include_bots:` (True/False) whether to include bots
        """
        async with ctx.typing():
            if include_bots:
                members = [m for m in ctx.guild.members]
            else:
                members = [m for m in ctx.guild.members if not m.bot]
            m_sort = sorted(members, key=lambda x: x.joined_at)
            txt = "\n".join(
                [
                    f"{i + 1}. {m} "
                    f"joined <t:{int(m.joined_at.timestamp())}:f> (<t:{int(m.joined_at.timestamp())}:R>)"
                    for i, m in enumerate(m_sort[:amount])
                ]
            )
            for p in pagify(txt, page_length=4000):
                em = discord.Embed(description=p, color=ctx.author.color)
                await ctx.send(embed=em)

    @commands.command()
    @commands.guild_only()
    async def oldestaccounts(
        self,
        ctx,
        amount: Optional[int] = 10,
        include_bots: Optional[bool] = False,
    ):
        """
        See which users have the oldest Discord accounts

        **Arguments**
        `amount:` how many members to display
        `include_bots:` (True/False) whether to include bots
        """
        async with ctx.typing():
            if include_bots:
                members = [m for m in ctx.guild.members]
            else:
                members = [m for m in ctx.guild.members if not m.bot]
            m_sort = sorted(members, key=lambda x: x.created_at)
            txt = "\n".join(
                [
                    f"{i + 1}. {m} "
                    f"created <t:{int(m.created_at.timestamp())}:f> (<t:{int(m.created_at.timestamp())}:R>)"
                    for i, m in enumerate(m_sort[:amount])
                ]
            )
            for p in pagify(txt, page_length=4000):
                em = discord.Embed(description=p, color=ctx.author.color)
                await ctx.send(embed=em)

    @commands.command()
    @commands.guildowner()
    @commands.guild_only()
    async def wipevcs(self, ctx: commands.Context):
        """
        Clear all voice channels from a server
        """
        msg = await ctx.send(
            "Are you sure you want to clear **ALL** Voice Channels from this server?"
        )
        yes = await confirm(ctx, msg)
        if yes is None:
            return
        if not yes:
            return await msg.edit(content="Not deleting all VC's")
        perm = ctx.guild.me.guild_permissions.manage_channels
        if not perm:
            return await msg.edit(
                content="I dont have perms to manage channels"
            )
        deleted = 0
        for chan in ctx.guild.channels:
            if isinstance(chan, discord.TextChannel):
                continue
            try:
                await chan.delete()
                deleted += 1
            except Exception:
                pass
        if deleted:
            await msg.edit(content=f"Deleted {deleted} VCs!")
        else:
            await msg.edit(content="No VCs to delete!")

    @commands.command()
    @commands.guildowner()
    @commands.guild_only()
    async def wipethreads(self, ctx: commands.Context):
        """
        Clear all threads from a server
        """
        msg = await ctx.send(
            "Are you sure you want to clear **ALL** threads from this server?"
        )
        yes = await confirm(ctx, msg)
        if yes is None:
            return
        if not yes:
            return await msg.edit(content="Not deleting all threads")
        perm = ctx.guild.me.guild_permissions.manage_threads
        if not perm:
            return await msg.edit(
                content="I dont have perms to manage threads"
            )
        deleted = 0
        for thread in ctx.guild.threads:
            await thread.delete()
            deleted += 1
        if deleted:
            await msg.edit(content=f"Deleted {deleted} threads!")
        else:
            await msg.edit(content="No threads to delete!")

    @commands.command(name="syncslash")
    @commands.is_owner()
    async def sync_slash(self, ctx: commands.Context, global_sync: bool):
        """
        Sync slash commands

        **Arguments**
        `global_sync:` If True, syncs global slash commands, syncs current guild by default
        """
        if not DPY2:
            return await ctx.send("This command can only be used with DPy2")
        if global_sync:
            await self.bot.tree.sync()
            await ctx.send("Synced global slash commands!")
        else:
            await self.bot.tree.sync(guild=ctx.guild)
            await ctx.send("Synced slash commands for this guild!")
        await ctx.tick()
    
    @commands.is_owner()
    async def traceback(self, ctx: commands.Context, public: bool = True) -> None:
        """Sends to the owner the last command exception that has occurred.

        If public (yes is specified), it will be sent to the chat instead.

        Warning: Sending the traceback publicly can accidentally reveal sensitive information about your computer or configuration.

        **Examples:**
            - `[p]traceback` - Sends the traceback to your DMs.
            - `[p]traceback True` - Sends the last traceback in the current context.

        **Arguments:**
            - `[public]` - Whether to send the traceback to the current context. Default is `True`.
        """
        if not ctx.bot._last_exception:
            raise commands.UserFeedbackCheckFailure(_("No exception has occurred yet."))
        _last_exception = ctx.bot._last_exception.split("\n")
        _last_exception[0] = _last_exception[0] + (
            "" if _last_exception[0].endswith(":") else ":\n"
        )
        _last_exception = "\n".join(_last_exception)
        _last_exception = self.cogsutils.replace_var_paths(_last_exception)
        if public:
            try:
                await Menu(pages=_last_exception, timeout=180, lang="py").start(ctx)
            except discord.HTTPException:
                pass
            else:
                return
        for page in pagify(_last_exception, shorten_by=15):
            try:
                await ctx.author.send(box(page, lang="py"))
            except discord.HTTPException:
                raise commands.UserFeedbackCheckFailure(
                    "I couldn't send the traceback message to you in DM. "
                    "Either you blocked me or you disabled DMs in this server."
                )

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        if isinstance(error):
            return
        traceback_error = "".join(
            traceback.format_exception(type(error), error, error.__traceback__)
        )
        traceback_error = self.cogsutils.replace_var_paths(traceback_error)
        self.tracebacks.append(traceback_error)
        if ctx.author.id not in ctx.bot.owner_ids:
            return
        pages = [box(page, lang="py") for page in pagify(traceback_error, shorten_by=15)]
        try:
            await Menu(pages=pages, timeout=180, delete_after_timeout=False).start(ctx)
        except discord.HTTPException:
            pass
