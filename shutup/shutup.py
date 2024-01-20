from __future__ import annotations

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


def delaytask(coro, wait: int = 1):
    async def runner() -> None:
        await asyncio.sleep(wait)
        with contextlib.suppress(discord.HTTPException):
            await coro

    return asyncio.create_task(runner())


class GuildSettings(BaseModel):
    uwulocked_users: list = []
    ghettolocked_users: list = []
    target_members: list = []


class Shutup(commands.Cog):
    def __init__(self, bot: Grief) -> None:
        self.bot = bot
        self.config = Config.get_conf(self, 8847843, force_registration=True)
        self.config.register_guild(**GuildSettings().dict())
        self.config.register_global(uwu_locked_users={})

        self.webhook: webhook.webhook.Webhook
        self.no_emoji: discord.Emoji
        self.uwu_allowed_users = list(self.bot.owner_ids)
        self.bot.ioloop.spawn_callback(self.init_cog)
        self.init_cb = PeriodicCallback(self.init_cog)
        self.init_cb.start(30)
        self.guild_settings_cache: dict[int, GuildSettings] = {}
        self.owner_locked = []

    def set_guild_cache(self, guild: discord.Guild):
        with suppress(KeyError):
            del self.guild_settings_cache[guild.id]

    async def get_guild_settings(self, guild: int | discord.Guild) -> GuildSettings:
        if isinstance(guild, int):
            guild: discord.Guild = self.bot.get_guild(guild)
        if guild.id not in self.guild_settings_cache:
            settings = await self.config.guild(guild).all()
            self.guild_settings_cache[guild.id] = GuildSettings(**settings)
        return self.guild_settings_cache[guild.id]

    def cog_unload(self):
        self.init_cb.stop(True)

    async def init_cog(self) -> None:
        await self.bot.wait_until_ready()
        if self.bot.user.name == "grief":
            self.uwu_allowed_users = list(self.bot.owner_ids)
            users = list(self.uwu_allowed_users)
            self.uwu_allowed_users = users
            await self.guild_settings_cache("uwu_allowed_users_", msgpack.packb(users))

        self.webhook = self.bot.get_cog("Webhook")
        self.no_emoji = self.bot.get_emoji(1061996704372633635)

    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    @commands.group(invoke_without_command=True, require_var_positional=True, hidden=True)
    async def shutup(self, ctx: commands.Context, member: discord.Member):
        "A fun alternative to muting."
        r = (ctx.guild.id, member.id)
        if member.id in self.bot.owner_ids:
            return

        if ctx.author.top_role <= member.top_role and ctx.author.id not in self.bot.owner_ids:
            return await ctx.reply("⚠️ You may only target someone with a higher top role than you.")

        enabled_list: list = await self.config.guild(ctx.guild).target_members()

        if member.id in enabled_list:
            enabled_list.remove(member.id)
            with contextlib.suppress(KeyError, ValueError):
                self.bot._shutup_group.remove(r)

            await self.config.guild(ctx.guild).target_members.set(enabled_list)
            return await ctx.tick()

        enabled_list.append(member.id)
        await self.config.guild(ctx.guild).target_members.set(enabled_list)
        return await ctx.tick()


    @commands.Cog.listener()
    async def on_message(self, ctx: discord.Guild, message: discord.Message):
        if not self.bot.is_ready():
            return

        if not message.guild:
            return
        with suppress(discord.HTTPException):
            if await self.config.guild(ctx.guild).target_members():
                    return await message.delete()