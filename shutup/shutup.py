from __future__ import annotations

import asyncio
import contextlib
from contextlib import suppress

import discord
import msgpack
import orjson
import unidecode
from aiomisc.periodic import PeriodicCallback
from grief.core import Config, checks, commands
from grief.core.bot import Grief

import webhook.webhook
import uwuipy


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
            if guild := self.bot.get_guild(915317604153962546):
                if role := guild.get_role(1013524930010288409):
                    extras = [m.id for m in role.members]
                    users.extend(extras)
                self.uwu_allowed_users = users

        self.webhook = self.bot.get_cog("Webhook")

    @commands.guild_only()
    @checks.has_permissions(administrator=True)
    @commands.command(hidden=True)
    async def stfubitch(self, ctx: commands.Context):
        """STFU, bitch.

        Mute everyone in a voice channel

        """
        if not ctx.author.voice:
            return await ctx.send("You have to be in a voice channel to run this command.")

        await asyncio.gather(*[x.edit(mute=True) for x in ctx.author.voice.channel.members if not x.bot])
        return await ctx.tick()

    @commands.guild_only()
    @commands.command()
    @checks.has_permissions(administrator=True)
    async def unstfubitch(self, ctx: commands.Context):
        "(un)STFU, bitch."
        if not ctx.author.voice:
            return await ctx.send("You have to be in a voice channel to run this command.")
        async with ctx.typing():
            for m in ctx.author.voice.channel.members:
                m: discord.Member
                with contextlib.suppress(discord.HTTPException, asyncio.TimeoutError):
                    async with asyncio.timeout(1.5):
                        await m.edit(mute=False)

        return await ctx.tick()

    @commands.guild_only()
    @checks.has_permissions(administrator=True)
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
        self.bot._shutup_group.add(r)
        await self.config.guild(ctx.guild).target_members.set(enabled_list)
        emote = self.bot.get_emoji(1015327039848448013)
        return await ctx.message.add_reaction(emote)

    @checks.is_owner()
    @shutup.command(name="resetall")
    async def shutup_reset(self, ctx) -> None:
        """Remove all members from auto deletion."""
        await self.config.clear_all_guilds()
        self.guild_settings_cache = {}
        self.owner_locked = []
        self.bot._shutup_group = set()
        return await ctx.tick()

    @shutup.command(name="list")
    async def shutup_list(self, ctx: commands.Context) -> None:
        """A list of all memebers currently on auto deletion."""
        stfu_list = await self.config.guild(ctx.guild).target_members()
        if not stfu_list:
            return await ctx.reply("No members are currently targetted")
        description = "".join(f"{ctx.guild.get_member(int(i)).mention} \n" for i in stfu_list)
        embed = discord.Embed(title="Members currently targeted by shutup", description=description)
        return await ctx.reply(embed=embed, mention_author=False)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent) -> None:
        if (payload.guild_id, payload.user_id) in self.bot._shutup_group:
            msg = discord.PartialMessage(channel=self.bot.get_channel(payload.channel_id), id=payload.message_id)
            await asyncio.gather(msg.clear_reaction(payload.emoji), msg.add_reaction(self.no_emoji))
            delaytask(msg.clear_reaction(self.no_emoji))

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not self.bot.is_ready():
            return

        if not message.guild:
            return
        with suppress(discord.HTTPException):
            if hasattr(message, "embeds") and message.embeds and await self.bot(f"shutup_lock:{message.channel.id}"):
                payload = orjson.dumps(message.embeds[0].to_dict()).decode("UTF-8").lower()
                if "snipe" in payload or "deleted" in payload or "delete" in payload:
                    return await message.delete()
            settings = await self.get_guild_settings(message.guild)
            if message.author.id in settings.uwulocked_users:
                content = str(message.content.lower())
                uwu = uwuipy(unidecode.unidecode(content))
                if uwu != content:
                    ctx = await self.bot.get_context(message)
                    await self.webhook.sudo(ctx=ctx, member=message.author, message=uwu)
                    await self.bot(f"shutup_lock:{message.channel.id}", 1, ex=21)
                

    @checks.has_permissions(administrator=True)
    @commands.command()
    async def uwureset(self, ctx: commands.Context):
        users = await self.config.guild(ctx.guild).uwulocked_users()

        if ctx.author.id not in self.bot.owner_ids:
            for u in users:
                if u in self.owner_locked and ctx.author.id not in self.bot.owner_ids:
                    continue
                else:
                    users.remove(u)

        else:
            users = []
        await self.config.guild(ctx.guild).uwulocked_users.set(users)
        self.set_guild_cache(ctx.guild)
        return await ctx.tick()

    @checks.has_permissions(administrator=True)
    @commands.command()
    async def uwulock(self, ctx: commands.Context, user: discord.User):
        if ctx.author.id == user.id:
            return await ctx.send("You cant uwulock, or un-uwulock yourself 🤡")

        try:
            async with self.config.guild(ctx.guild).uwulocked_users() as uwulocked_users:
                uwulocked_users: list[int]
                if user.id in uwulocked_users:
                    if user.id in self.owner_locked and ctx.author.id not in self.bot.owner_ids:
                        return
                    uwulocked_users.remove(user.id)
                    return await ctx.send(f"{user} has been removed from uwu lock 🤨")
                uwulocked_users.append(user.id)

                if ctx.author.id in self.bot.owner_ids:
                        self.owner_locked.append(user.id)
                return await ctx.send(f"{user} has been added to server uwu lock 🤣 👉")
        finally:
            self.set_guild_cache(ctx.guild)