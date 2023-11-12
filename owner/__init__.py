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
from grief.core.bot import Red
from grief.core import Config, commands
from grief.core.utils.chat_formatting import humanize_list
from discord.utils import get


class Owner(commands.Cog):

    def __init__(self, bot: Red):
        self.bot = bot

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
    @commands.cooldown(2, 5, commands.BucketType.user)
    @commands.group(invoke_without_command=True)
    async def ping(self, ctx):
        """View bot latency."""
        start = time.monotonic()
        ref = ctx.message.to_reference(fail_if_not_exists=False,)
        message = await ctx.reply("Pinging...", reference=ref)
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

async def setup(bot: Red) -> None:
    cog = Owner(bot)
    await discord.utils.maybe_coroutine(bot.add_cog, cog)