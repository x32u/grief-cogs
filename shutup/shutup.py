from __future__ import annotations

import aiohttp
import asyncio
import contextlib
from contextlib import suppress
from pydantic import BaseModel
import discord
import msgpack
import orjson
import unidecode
from aiomisc.periodic import PeriodicCallback
from grief.core import Config, checks, commands
from grief.core.bot import Grief
import webhook.webhook
from discord.ext.commands import BadArgument, Converter

class Shutup(commands.Cog):
    def __init__(self, bot: Grief) -> None:
        self.bot = bot
        self.config = Config.get_conf(self, identifier=694835810347909161, force_registration=True, )
        default_guild = {"enabled": True, "target_members": []}
        self.config.register_guild(**default_guild)

    @commands.has_permissions(manage_messages=True)
    @commands.command()
    async def stfu(self, ctx, user: discord.User):
        """
        Add a certain user to get auto kicked.
        """

        author = ctx.author


        if user >= ctx.guild.me.top_role:
                raise BadArgument(
                    (
                        "That {user} is higher than my highest role in the discord hierarchy."
                    ).format(role=user.mention)
                )
        if user >= author.top_role and author.id != ctx.guild.owner_id:
                raise BadArgument(
                    (
                        "The {user} is higher than your "
                        "highest role in the discord hierarchy."
                    ).format(role=user.mention)
                )
        
        
        enabled_list: list = await self.config.guild(ctx.guild).target_members()

        
        if user.id in enabled_list:
            enabled_list.remove(user.id)
            async with ctx.typing():
                await self.config.guild(ctx.guild).target_members.set(enabled_list)
            return await ctx.send(f"{user} has been unstfu'ed.")
        
        enabled_list.append(user.id)
    
        async with ctx.typing():
            await self.config.guild(ctx.guild).target_members.set(enabled_list)
            await ctx.send(f"{user} will have messages auto-deleted.")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild: return

        if await self.config.guild(message.guild).enabled():
            if message.author.id in await self.config.guild(message.guild).target_members():
                await message.delete()