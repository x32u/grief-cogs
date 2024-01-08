from __future__ import annotations

import re
from typing import Any
from pydantic import BaseModel as BM
from pydantic import Field
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

class TwitterLinks(BaseModel):
    display_url: Optional[str] = Field(None, title='Display Url')
    expanded_url: Optional[str] = Field(None, title='Expanded Url')
    url: Optional[str] = Field(None, title='Url')
    indices: List[int] = Field(..., title='Indices')


class TwitterUser(BaseModel):
    error: Optional[str] = Field(None, title='Error')
    username: Optional[str] = Field(None, title='Username')
    nickname: Optional[str] = Field(None, title='Nickname')
    bio: Optional[str] = Field(None, title='Bio')
    location: Optional[str] = Field(None, title='Location')
    links: Optional[List[TwitterLinks]] = Field(None, title='Links')
    avatar: Optional[str] = Field(None, title='Avatar')
    banner: Optional[str] = Field(None, title='Banner')
    tweets: Optional[int] = Field(0, title='Tweets')
    media: Optional[int] = Field(None, title='Media')
    followers: Optional[int] = Field(0, title='Followers')
    following: Optional[int] = Field(0, title='Following')
    creation: Optional[int] = Field(0, title='Creation')
    private: Optional[bool] = Field(False, title='Private')
    verified: Optional[bool] = Field(False, title='Verified')
    id: Optional[Union[str, int]] = Field(None, title='Id')

class Website(BaseModel):
    url: str
    display_url: str

class TwitterAuthor(BaseModel):
    id: str
    name: str
    screen_name: str
    avatar_url: str
    banner_url: str
    description: str
    location: str
    url: str
    followers: int
    following: int
    joined: str
    likes: int
    website: Optional[List[Website]] = None
    tweets: int
    avatar_color: Optional[str] = None


class TwitterPostResponse(BaseModel):
    url: str
    id: str
    text: str
    author: TwitterAuthor
    replies: int
    retweets: int
    likes: int
    created_at: str
    created_timestamp: int
    possibly_sensitive: bool
    views: Optional[int] = 0
    is_note_tweet: bool
    lang: Optional[str] = None
    replying_to: Optional[str] = None
    replying_to_status: Optional[str] = None
    media: Optional[List[List[str]]] = None
    source: Optional[str] = None
    twitter_card: Optional[str] = None
    color: Optional[str] = None

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
        
    @commands.command(aliases=["tw"])
    async def twitter(self, ctx, url: str):
        "Repost a TikTok video in chat."
        session = httpx.AsyncClient()
        response = await session.get(f"https://api.rival.rocks/twitter/post?url={url}&api-key=05eab8f3-f0f6-443b-9d5e-fba1339c4b04", headers={'User-Agent':"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:104.0) 20100101 Firefox/103.0"})
        data = TwitterPostResponse(**response.json())
            
        embed = discord.Embed(description = data.source, color = 0x313338)
        embed.add_field(name = 'Replies', value = data.replies, inline = True)
        embed.add_field(name = 'Views', value = data.views, inline = True)
        embed.add_field(name = 'Retweets', value = data.retweets, inline = True)
        embed.add_field(name = 'Author', value = data.author, inline = True)
        embed.set_footer(text='grief')
        if data.media == True:
            session = httpx.AsyncClient()
            f = await session.get(data.media,headers={'User-Agent':"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:104.0) 20100101 Firefox/103.0"})
            file = discord.File(fp=io.BytesIO(f.read()), filename='twitter.mp4')  
            return await ctx.send(file=file)        
        else:
            file = None
        embed = []
        for source in data.source:
            e = embed.copy()
            e.set_image(url=source)
            embed.append(e)
            return await paginate(ctx,embed)
        
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