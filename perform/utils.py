from typing import Optional
import discord
from grief.core import commands

async def send_embed(
    self,
    ctx: commands.Context,
    embed: discord.Embed,
    user: Optional[discord.Member] = None,
):
    await ctx.reply(embed=embed, mention_author=False)