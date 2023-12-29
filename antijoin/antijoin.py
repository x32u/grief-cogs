import asyncio
import datetime
import discord
from grief.core import commands
from grief.core.bot import Grief
from grief.core.config import Config


class AntiJoin(commands.Cog):
    """Instead of banning, have grief automatically kick certain users on join."""

    def __init__(self, bot: Grief) -> None:
        self.bot = bot
        self.config = Config.get_conf(self, identifier="0", force_registration=True)
        default_guild = {"enabled": "False"}
        self.config.register_guild(**default_guild)

    @commands.group(name="antijoin", aliases=["aj"])
    @commands.has_permissions(kick_members=True)
    @commands.guild_only()
    async def antijoinset(self, ctx):
        """
        Auto Kick settings.
        """

    @antijoinset.command(name="enable")
    async def antijoinset_enable(self, ctx):
        """
        Enable the antijoin feature.
        """
        await self.config.guild(ctx.guild).enabled.set(True)
        await ctx.send("Auto kicking all members has been enabled for this guild.")

    @antijoinset.command(name="disable")
    async def antijoinset_disable(self, ctx):
        """
        Disable the antijoin feature.
        """
        await self.config.guild(ctx.guild).enabled.clear()
        await ctx.reply(embed=discord.Embed(description="Autokicking all members has been disabled for this guild."))

    @commands.Cog.listener()
    async def on_member_join(self, ctx: discord.Guild, member: discord.Member):
        if await self.config.guild(ctx.guild).enabled(True):
                    await member.guild.kick(member, reason="antijoin: autokicking all members is enabled, run ;antijoin disable to disable this.")

