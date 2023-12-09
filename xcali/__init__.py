import datetime
from io import BytesIO
from typing import Any, Optional, Tuple, Union

import aiohttp
import discord
import pytube
import yarl
import requests

from grief.core import Config, commands
from grief.core.bot import Grief

from .constants import (TIKTOK_DESKTOP_PATTERN, TIKTOK_MOBILE_PATTERN,
                        YOUTUBE_PATTERN, ydl_tok)
from .utilities import sync_as_async


class TikTokLinkBUtton(discord.ui.Button):
    def __init__(self, username: str, custom_emoji: Union[discord.Emoji, str] = None):
        self.username = username
        super().__init__(
            style=discord.ButtonStyle.link,
            label=None,
            url=f"https://www.tiktok.com/@{self.username}?lang=en",
            emoji=custom_emoji,
        )

class XCali(commands.Cog):
    """
    Repost TikTok and YouTube videos.
    """

    def __init__(self, bot: Grief):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=0x28411747)
        self.config.register_guild(enabled=False)
        self.session = aiohttp.ClientSession()

    if discord.version_info.major >= 2:

        async def cog_unload(self) -> None:
            await self.session.close()

    else:

        def cog_unload(self) -> None:
            self.bot.loop.create_task(self.session.close())

    def _extract_video_id(self, url: str) -> Optional[str]:
        """
        Extracts the video ID from a YouTube URL.
        """
        match = YOUTUBE_PATTERN.search(url)
        if match:
            return match["id"]

    async def _download_file(self, url: str, filename: str) -> Tuple[int, discord.File]:  # noqa
        async with self.session.get(url, allow_redirects=True, timeout=300) as response:  # noqa
            if response.status != 200:
                return
            data = await response.read()
            return len(data), discord.File(BytesIO(data), filename)

    async def _extract_video_info(self, url: yarl.URL) -> Union[dict[str, Any], None]:  # noqa
        ydl = ydl_tok
        info = await sync_as_async(self.bot, ydl.extract_info, str(url), download=False)  # noqa

        if not info:
            return

        return info

    def _extract_youtube(self, url: str) -> Union[dict[str, Any], None]:
        """
        Extracts the video data from a YouTube URL.
        """
        obj = pytube.YouTube(url)
        videos = obj.streams.filter(progressive=True)
        if not videos:
            return None
        stream = videos.order_by("resolution").desc().first()
        data = {}
        data["title"] = stream.title
        data["uploader"] = obj.author
        data["uploader_url"] = obj.channel_url
        data["description"] = obj.description
        data["views"] = obj.views
        data["size"] = stream.filesize_approx
        data["url"] = stream.url
        data["filename"] = stream.default_filename
        return data

    def find_proper_url(self, video_info: dict) -> str:
        for format in video_info["formats"]:
            if format["format_id"] == "download_addr-0":
                return format
        # not found, search for the next best one
        for format in video_info["formats"]:
            if format["url"].startswith("http://api"):
                return format
        # not found, return the first one
        return video_info["formats"][0]

    def format_date(self, date: str) -> str:
        year = date[:4]
        date = date.replace(year, "")
        month = date[:2]
        day = date.replace(month, "")
        return f"{day}/{month}/{year}"

    @commands.Cog.listener("on_message")
    async def on_youtube_trigger(self, message: discord.Message) -> None:
        if message.author.bot:
            return
        if message.guild is None:
            return
        if not message.channel.permissions_for(message.guild.me).attach_files:
            return
        video_id = self._extract_video_id(message.content)
        if not video_id:
            return
        if not await self.config.guild(message.guild).enabled():
            return
        limit = message.guild.filesize_limit
        async with message.channel.typing():
            url: str = f"https://www.youtube.com/watch?v={video_id}"
            video_info = await sync_as_async(self.bot, self._extract_youtube, str(url))  # noqa
            if not video_info:
                return
            if video_info["size"] > limit:
                return
            embed = discord.Embed(color=0x2F3136)
            embed.title = video_info["title"]
            embed.set_author(
                name=video_info["uploader"],
                url=video_info["uploader_url"],
            )
            if video_info["description"]:
                _desc = video_info["description"].split("\n")
                if len(_desc) > 2:
                    desc = "".join(_desc[:2])
                else:
                    desc = "".join(_desc)
                embed.description = desc
            embed.set_footer(text=f"📺 {video_info['views']:,}")  # noqa
            count, dlvideo = await self._download_file(
                video_info["url"], video_info["filename"]
            )  # noqa
            if count > limit:
                return
            await message.channel.send(
                embed=embed,
                file=dlvideo,
            )
            await message.delete()

    @commands.Cog.listener("on_message")
    async def on_tiktok_trigger(self, message: discord.Message) -> None:
        if message.author.bot:
            return
        if message.guild is None:
            return
        if not message.channel.permissions_for(message.guild.me).attach_files:
            return
        if match := TIKTOK_MOBILE_PATTERN.search(message.content):
            url = match[1]
        elif match := TIKTOK_DESKTOP_PATTERN.search(message.content):
            url = match[1]
        else:
            return
        if not await self.config.guild(message.guild).enabled():
            return
        url = yarl.URL(url)
        async with message.channel.typing():
            info = await self._extract_video_info(url)
            if not info:
                return
            filesize_limit = (message.guild and message.guild.filesize_limit) or 8388608  # noqa
            count, dlvideo = await self._download_file(
                self.find_proper_url(info)["url"], f"tiktok.{info['ext']}"
            )
            if count > filesize_limit:
                return
            embed = discord.Embed(color=0x2F3136)
            embed.title = info["title"]
            embed.set_author(name=info["uploader"], url=info["uploader_url"])
            embed.description = info["description"]
            embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
            embed.set_footer(
                text=f"❤️ {info['like_count']:,} | 💬 {info['comment_count']:,} | 📺 {info['view_count']:,} | 🔁 {info['repost_count']:,}"  # noqa
            )
            await message.channel.send(
                embed=embed,
                file=dlvideo,
            )
            await message.delete()

    @commands.command()
    @commands.has_permissions(manage_guild=True)
    async def rpst(self, ctx: commands.Context) -> None:
        """Toggle reposting."""
        old = await self.config.guild(ctx.guild).enabled()
        await self.config.guild(ctx.guild).enabled.set(not old)
        embed = discord.Embed(description=f"> Reposting is now {'enabled' if not old else 'disabled'}.", color=0x313338)
        return await ctx.reply(embed=embed, mention_author=False)
    
    @commands.is_owner()
    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.guild)
    async def tiktok(self, ctx, username):
        url = f"https://www.tiktok.com/@{username}?lang=en"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
        }
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            embed = discord.Embed(
                title="Error",
                description=f">>> ***{e}***",
                color=0x2B2D31,
            )
            await ctx.send(embed=embed)
            return

        html = response.text
        try:
            nickname = html.split('nickname":"')[1].split('"')[0]
            followers = html.split('followerCount":')[1].split(",")[0]
            following = html.split('followingCount":')[1].split(",")[0]
            likes = html.split('heartCount":')[1].split(",")[0]
            videos = html.split('videoCount":')[1].split(",")[0]
            bio = html.split('desc":"')[1].split('"')[0]
            profile_pic_url = html.split('og:image" content="')[1].split('"')[0]
        except IndexError as e:
            embed = discord.Embed(
                title="<:deny:1121826907739144412> Error",
                description=f">>> ***{e}***",
                color=0x2B2D31,
            )
            await ctx.send(embed=embed)
            return

        embed = discord.Embed(
            title=f"{nickname}",
            color=0x2B2D31,
        )

        embed.set_thumbnail(url=profile_pic_url)

        embed.add_field(
            name="Username:",
            value=f"> `{username}`",
            inline=False,
        )
        embed.add_field(
            name="Posts:",
            value=f"> `{videos}`",
            inline=False,
        )
        embed.add_field(
            name="Likes:",
            value=f"> `{likes}`",
            inline=False,
        )
        embed.add_field(
            name="Followers:",
            value=f"> `{followers}`",
            inline=False,
        )
        embed.add_field(
            name="Following:",
            value=f"> `{following}`",
            inline=False,
        )
        embed.add_field(
            name=" Bio:",
            value=f"> *{bio}*",
            inline=False,
        )

        button = TikTokLinkBUtton(
            username, custom_emoji="<:tiktok:1114291908659908719>"
        )
        view = discord.ui.View()
        view.add_item(button)

        await ctx.send(embed=embed, view=view)


    # @commands.is_owner()
    # @commands.command()
    # async def instaprofile(self, ctx, username):
        # api_key = (
            # "claqz_Qt5c73ExW5pEtjjCknvL4djlPUK6RA1D4Ll4vx8SJcp1HPfFchYiWCarMHtuNCbm"
        # )

        # headers = {"Authorization": api_key}

        # sync with aiohttp.ClientSession() as session:
            # response = await session.get(
                # f"https://dev.lains.life/instagram/profile?username={username}",
                #  headers=headers,
            # )
            # data = await response.json()

        # if response.status != 200:
            # return await ctx.send("An error occurred while fetching the profile.")

        # profile = data

        # embed = discord.Embed(
            # title=f"Instagram Profile - {profile['username']}", color=self.bot.color
        # )
        # embed.set_thumbnail(url=profile["avatar_url"])
        # embed.add_field(name="Full Name", value=profile["display_name"], inline=False)
        # embed.add_field(
            # name="Followers", value=profile["statistics"]["followers"], inline=True
        # )
        # embed.add_field(
            # name="Following", value=profile["statistics"]["following"], inline=True
        # )
        # embed.add_field(name="Posts", value=profile["statistics"]["posts"], inline=True)
        # mbed.add_field(name="Bio", value=profile["description"], inline=False)
        # embed.set_footer(text="Api by lain")

        # await ctx.send(embed=embed)


async def setup(bot: Grief) -> None:
    cog = XCali(bot)
    await discord.utils.maybe_coroutine(bot.add_cog, cog)
