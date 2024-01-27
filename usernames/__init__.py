
from typing import List, Tuple, cast
import asyncio
from collections import defaultdict
import discord
from grief.core import commands, i18n
from grief.core.utils.chat_formatting import bold, pagify
from grief.core.utils.common_filters import (
    filter_invites,
    filter_various_mentions,
    escape_spoilers_and_mass_mentions,
)
from .abc import MixinMeta
import discord
from grief.core import Config, commands
from grief.core.bot import Grief
from logging import Logger, getLogger
from grief.core.i18n import Translator, cog_i18n

_ = i18n.Translator("Mod", __file__)

@cog_i18n(_)
class Names():
    """Moderation tools."""
    default_member_settings = {"past_nicks": []}
    default_user_settings = {"past_names": [], "past_display_names": []}
    
    def __init__(self, bot: Grief):
        super().__init__()
        self.bot: Grief = bot
        self.logger: Logger = getLogger("grief.vanity")
        self.config = Config.get_conf(self, 4961522000, force_registration=True)
        self.config.register_member(**self.default_member_settings)
        self.config.register_user(**self.default_user_settings)
        self.cache: dict = {}

    async def get_names(self, member: discord.Member) -> Tuple[List[str], List[str], List[str]]:
        user_data = await self.config.user(member).all()
        usernames, display_names = user_data["past_names"], user_data["past_display_names"]
        nicks = await self.config.member(member).past_nicks()
        usernames = list(map(escape_spoilers_and_mass_mentions, filter(None, usernames)))
        display_names = list(map(escape_spoilers_and_mass_mentions, filter(None, display_names)))
        nicks = list(map(escape_spoilers_and_mass_mentions, filter(None, nicks)))
        return usernames, display_names, nicks

    @commands.command()
    async def names(self, ctx: commands.Context, *, member: discord.Member):
        """Show previous usernames, global display names, and server nicknames of a member."""
        usernames, display_names, nicks = await self.get_names(member)
        parts = []
        for header, names in (
            (_("Past 20 usernames:"), usernames),
            (_("Past 20 global display names:"), display_names),
            (_("Past 20 server nicknames:"), nicks),
        ):
            if names:
                parts.append(bold(header) + ", ".join(names))
        if parts:
            # each name can have 32 characters, we store 3*20 names which totals to
            # 60*32=1920 characters which is quite close to the message length limit
            for msg in pagify(filter_various_mentions("\n\n".join(parts))):
                await ctx.send(msg)
        else:
            await ctx.send(_("That member doesn't have any recorded name or nickname change."))


    @commands.Cog.listener()
    async def on_user_update(self, before: discord.User, after: discord.User):
        if before.name != after.name:
            track_all_names = await self.config.track_all_names()
            if not track_all_names:
                return
            async with self.config.user(before).past_names() as name_list:
                self._update_past_names(before.name, name_list)
        if before.display_name != after.display_name:
            track_all_names = await self.config.track_all_names()
            if not track_all_names:
                return
            async with self.config.user(before).past_display_names() as name_list:
                self._update_past_names(before.display_name, name_list)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if before.nick != after.nick and before.nick is not None:
            guild = after.guild
            if (not guild) or await self.bot.cog_disabled_in_guild(self, guild):
                return
            track_all_names = await self.config.track_all_names()
            track_nicknames = await self.config.guild(guild).track_nicknames()
            if (not track_all_names) or (not track_nicknames):
                return
            async with self.config.member(before).past_nicks() as nick_list:
                self._update_past_names(before.nick, nick_list)

async def setup(bot: Grief) -> None:
        await bot.add_cog(Names(bot))