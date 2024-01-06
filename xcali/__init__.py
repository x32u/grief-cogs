import re
from typing import Any
from pydantic import BaseModel as BM
import asyncio
from typing import Optional, List, Any, Union
from grief.core import Config, commands
from grief.core.bot import Grief
import aiohttp
import discord
import button_paginator as pg
import aiohttp, discord,io, httpx

class BaseModel(BM):
    class Config:
        arbitrary_types_allowed = True

class TikTokVideoStatistics(BaseModel):
    aweme_id: Optional[str] = None
    comment_count: Optional[int] = 0
    digg_count: Optional[int] = 0
    download_count: Optional[int] = 0
    play_count: Optional[int] = 0
    share_count: Optional[int] = 0
    lose_count: Optional[int] = 0
    lose_comment_count: Optional[int] = 0
    whatsapp_share_count: Optional[int] = 0
    collect_count: Optional[int] = 0


class TikTokVideo(BaseModel):
    is_video: Optional[bool] = False
    items: Union[str,List[str]]
    desc: Optional[str] = None
    username: Optional[str] = None
    nickname: Optional[str] = None
    avatar: Optional[str] = None
    stats: TikTokVideoStatistics
    url: Optional[str] = None

class XCali(commands.Cog):
    """
    Repost TikTok and YouTube videos.
    """

    def __init__(self, bot: Grief):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=0x28411747)
        self.config.register_guild(enabled=True)


    @commands.command(aliases=["tt"])
    async def tiktok(self, ctx, url: str):
        "Repost a TikTok video in chat."
        session = httpx.AsyncClient()
        response = await session.get(f"https://api.rival.rocks/tiktok?url={url}&api-key=05eab8f3-f0f6-443b-9d5e-fba1339c4b04", headers={'User-Agent':"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:104.0) 20100101 Firefox/103.0"})
        data = TikTokVideo(**response.json())
        message = discord.Message
            
        embed = discord.Embed(description = data.desc, color = 0x313338)
        embed.add_field(name = 'Comments', value = data.stats.comment_count, inline = True)
        embed.add_field(name = 'Plays', value = data.stats.play_count, inline = True)
        embed.add_field(name = 'Shares', value = data.stats.share_count, inline = True)
        embed.add_field(name = 'User', value = data.username, inline = True)
        embed.set_footer(text='grief')
        if data.is_video == True:
            session = httpx.AsyncClient()
            f = await session.get(data.items,headers={'User-Agent':"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:104.0) 20100101 Firefox/103.0"})
            file = discord.File(fp=io.BytesIO(f.read()), filename='tiktok.mp4')
            await message.delete()   
            return await ctx.send(embed=embed, file=file)        
        else:
            file = None
            embeds = []
            for item in data.items:
                e = embed.copy()
                e.set_image(url=item)
                embeds.append(e)
            return await self.paginate(ctx,embeds)
        
    async def reposter(self, message: discord.Message, query:Any):
        results = query.findall(message.content)
        if results:
            for result in results:
                if "grief" in str(message.content).lower():
                    for d in message.content.split():
                        if "tiktok.com" in d.lower():
                            ctx = await self.bot.get_context(message)
                            import httpx, discord,io
                            session = httpx.AsyncClient()
                            response = await session.get(f"https://api.rival.rocks/tiktok?url={d}&api-key=05eab8f3-f0f6-443b-9d5e-fba1339c4b04", headers={'User-Agent':"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:104.0) 20100101 Firefox/103.0"})
                            data = TikTokVideo(**response.json())
                                
                            embed = discord.Embed(description = data.desc, color = 0x313338)
                            embed.add_field(name = 'Comments', value = data.stats.comment_count, inline = True)
                            embed.add_field(name = 'Plays', value = data.stats.play_count, inline = True)
                            embed.add_field(name = 'Shares', value = data.stats.share_count, inline = True)
                            embed.add_field(name = 'User', value = data.username, inline = True)
                            embed.set_footer(text='grief')
                            if data.is_video == True:
                                session = httpx.AsyncClient()
                                f = await session.get(data.items,headers={'User-Agent':"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:104.0) 20100101 Firefox/103.0"})
                                file = discord.File(fp=io.BytesIO(f.read()), filename='tiktok.mp4')
                                await message.delete()   
                                return await ctx.send(embed=embed, file=file)  
                            else:
                                file = None
                                embeds = []
                                for item in data.items:
                                    e = embed.copy()
                                    e.set_image(url=item)
                                    embeds.append(e)
                                return await self.paginate(ctx,embeds)
                            
    async def twitter_reposter(self, message: discord.Message, query:Any):
        results = query.findall(message.content)
        if results:
            for result in results:
                if "grief" in str(message.content).lower():
                    for d in message.content.split():
                        if "twitter.com" in d.lower():
                            ctx = await self.bot.get_context(message)
                            import httpx, discord,io
                            session = httpx.AsyncClient()
                            response = await session.get(f"https://api.rival.rocks/twitter/post?url={d}&api-key=05eab8f3-f0f6-443b-9d5e-fba1339c4b04", headers={'User-Agent':"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:104.0) 20100101 Firefox/103.0"})
                            data = TikTokVideo(**response.json())
                                
                            embed = discord.Embed(description = data.desc, color = 0x313338)
                            embed.add_field(name = 'Comments', value = data.stats.comment_count, inline = True)
                            embed.add_field(name = 'Plays', value = data.stats.play_count, inline = True)
                            embed.add_field(name = 'Shares', value = data.stats.share_count, inline = True)
                            embed.add_field(name = 'User', value = data.username, inline = True)
                            embed.set_footer(text='grief')
                            if data.is_video == True:
                                session = httpx.AsyncClient()
                                f = await session.get(data.items,headers={'User-Agent':"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:104.0) 20100101 Firefox/103.0"})
                                file = discord.File(fp=io.BytesIO(f.read()), filename='tiktok.mp4')
                                await message.delete()   
                                return await ctx.send(embed=embed, file=file)  
                            else:
                                file = None
                                embeds = []
                                for item in data.items:
                                    e = embed.copy()
                                    e.set_image(url=item)
                                    embeds.append(e)
                                return await self.paginate(ctx,embeds)
                            
                            
        
    async def do_repost(self, message: discord.Message):
        import re, asyncio
        regexes = [re.compile(r"(?:http\:|https\:)?\/\/(?:www\.)?tiktok\.com\/@.*\/video\/\d+"),re.compile(r"(?:http\:|https\:)?\/\/(?:www|vm|vt|m).tiktok\.com\/(?:t/)?(\w+)")]
        return await asyncio.gather(*[self.reposter(message,query) for query in regexes])
    
    @commands.Cog.listener('on_message')
    async def tiktok_repost(self, message: discord.Message):
        if message.guild:
            if not message.author.bot:
                return await self.do_repost(message)
        
    @commands.command(aliases=["ss"])
    async def screenshot(self, ctx, url: str):
        "Preview a website in chat."
        session = httpx.AsyncClient()
        response = await session.get(f"https://api.rival.rocks/screenshot?url={url}&api-key=05eab8f3-f0f6-443b-9d5e-fba1339c4b04", headers={'User-Agent':"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:104.0) 20100101 Firefox/103.0"})
        if response.status_code == 200:
            return await ctx.send(file=discord.File(fp=io.BytesIO(response.read()),filename='screenshot.png'))
        else:
            data = response.json()
            error = data['error']
            return await ctx.send(content = f"an error occured : {error}")
        
async def paginate(self, ctx: commands.Context, embeds: list):
    paginator = pg.Paginator(self.bot, embeds, ctx, invoker=ctx.author.id)
    if len(embeds) > 1:
        paginator.add_button('prev', emoji = '⬅️', style = discord.ButtonStyle.grey)
        paginator.add_button('next', emoji = '➡️', style = discord.ButtonStyle.grey)
    elif len(embeds) == 1:
            pass
    else:
        raise discord.ext.commands.errors.CommandError(f"No Embeds Supplied to Paginator")
    return await paginator.start()
        
async def setup(bot: Grief) -> None:
    cog = XCali(bot)
    await discord.utils.maybe_coroutine(bot.add_cog, cog)