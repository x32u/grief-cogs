import discord
from discord.utils import get
from grief.core import commands
from grief.core.bot import Red
import time


class Owner(commands.Cog):

    async def red_delete_data_for_user(self, **kwargs):
        """
        Nothing to delete.
        """
        return

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
        await ctx.send(f"Sent message to {destination}.")

    @commands.cooldown(2, 5, commands.BucketType.user)
    @commands.command(invoke_without_command=True)
    async def ping(self, ctx):
        """View bot latency."""
        start = time.monotonic()
        ref = ctx.message.to_reference(fail_if_not_exists=False)
        message = await ctx.send("Pinging...", reference=ref)
        end = time.monotonic()
        totalPing = round((end - start) * 1000, 2)
        e = discord.Embed(title="Pinging..", description=f"Overall Latency: {totalPing}ms")
        await asyncio.sleep(0.25)
        try:
            await message.edit(content=None, embed=e)
        except discord.NotFound:
            return

        botPing = round(self.bot.latency * 1000, 2)
        e.description = e.description + f"\nDiscord WebSocket Latency: {botPing}ms"
        await asyncio.sleep(0.25)

        averagePing = (botPing + totalPing) / 2
        if averagePing >= 1000:
            color = discord.Colour.dark_theme()
        elif averagePing >= 200:
            color = discord.Colour.dark_theme()
        else:
            color = discord.Colour.dark_theme()

        if not self.settings["host_latency"]:
            e.title = "Pong!"

        e.color = color
        try:
            await message.edit(embed=e)
        except discord.NotFound:
            return
        if not self.settings["host_latency"]:
            return

        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        loop = asyncio.get_event_loop()
        try:
            s = speedtest.Speedtest(secure=True)
            await loop.run_in_executor(executor, s.get_servers)
            await loop.run_in_executor(executor, s.get_best_server)
        except Exception as exc:
            log.exception("An exception occured while fetching host latency.", exc_info=exc)
            host_latency = "`Failed`"
        else:
            result = s.results.dict()
            host_latency = round(result["ping"], 2)
            host_latency = f"{host_latency}ms"

        e.title = "Pong!"
        e.description = e.description + f"\nHost Latency: {host_latency}"
        await asyncio.sleep(0.25)
        try:
            await message.edit(embed=e)
        except discord.NotFound:
            return    

async def setup(bot: Red) -> None:
    cog = Owner(bot)
    await discord.utils.maybe_coroutine(bot.add_cog, cog)