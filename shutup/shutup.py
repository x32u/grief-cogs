from __future__ import annotations

import discord
from grief.core import Config, commands, checks
from grief.core.bot import Grief
from grief.core import i18n

T_ = i18n.Translator("Shutup", __file__)

_ = lambda s: s

class Shutup(commands.Cog):
    def __init__(self, bot: Grief) -> None:
        self.bot = bot
        self.config = Config.get_conf(self, identifier=694835810347909161, force_registration=True, )
        default_guild = {"enabled": True, "target_members": []}
        self.config.register_guild(**default_guild)


    @commands.command()
    async def stfu(self, ctx: commands.Context, user: discord.Member):
        """
        Add a certain user to get auto kicked.
        """
        if user.id in self.bot.owner_ids:
            return

        if ctx.author.top_role <= user.top_role and ctx.author.id:
            return await ctx.send("You may only target someone with a higher top role than you.")
        
        enabled_list: list = await self.config.guild(ctx.guild).target_members()
        
        if user.id in enabled_list:
            enabled_list.remove(user.id)
            await ctx.send(f"{user} has been unstfu'ed.")
            async with ctx.typing():
                await self.config.guild(ctx.guild).target_members.set(enabled_list)
            return
        
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