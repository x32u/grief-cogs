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
    
    @commands.command()
    async def stfu(self, ctx, user: discord.User):
        """
        Add a certain user to get auto kicked.
        """
        async with ctx.typing():
            ids = await self.config.guild(ctx.guild).blacklisted_ids()
            ids.append(user.id)
            await self.config.guild(ctx.guild).blacklisted_ids.set(ids)
        await ctx.send(f"{user} will have messages auto-deleted.")

                
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message, member: discord.Member):
            if member.id in await self.config.guild(member.guild).blacklisted_ids():
              await message.delete()