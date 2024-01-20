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


class Shutup(commands.Cog):
    def __init__(self, bot: Grief) -> None:
        self.bot = bot
        self.config = Config.get_conf(self, identifier=694835810347909161, force_registration=True,)
        default_guild = {"enabled": True, "target_members": []}
        self.config.register_guild(**default_guild)
    
    @commands.command()
    async def stfu(self, ctx, user: discord.User):
        """
        Add a certain user to get auto kicked.
        """
        enabled_list: list = await self.config.guild(ctx.guild).target_members()
        enabled_list.append(user.id)
        
        async with ctx.typing():
            await self.config.guild(ctx.guild).target_members.set(enabled_list)
        await ctx.send(f"{user} will have messages auto-deleted.")

                
    @commands.Cog.listener()
    async def on_message(self, ctx: discord.Guild, message: discord.Message, member: discord.Member):
        isEnabled = await self.config.guild(member.guild).enabled()
        if isEnabled:
            targetMembers = await self.config.guild(member.guild).target_members()
            ctx.channel.send(f"{targetMembers}")
            if member.id in targetMembers:
                ctx.channel.send(f"{member} is in the list.")
                await message.delete()