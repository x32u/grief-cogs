
from typing import List, Tuple, cast

import discord
from grief.core import commands, i18n
from grief.core.utils.chat_formatting import bold, pagify
from grief.core.utils.common_filters import (
    filter_invites,
    filter_various_mentions,
    escape_spoilers_and_mass_mentions,
)
from .abc import MixinMeta

_ = i18n.Translator("Mod", __file__)


class ModInfo(MixinMeta):
    """
    Commands regarding names, userinfo, etc.
    """

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