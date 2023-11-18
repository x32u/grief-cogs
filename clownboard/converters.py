from typing import Union

import discord
from grief.core import commands
from grief.core.i18n import Translator

from .clownboard_entry import ClownboardEntry

_ = Translator("Starboard", __file__)


class clownboardExists(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> ClownboardEntry:
        cog = ctx.cog
        guild = ctx.guild
        if guild.id not in cog.clownboards:
            raise commands.BadArgument(_("There are no starboards setup on this server!"))
        try:
            clownboard = cog.clownboards[guild.id][argument.lower()]
        except KeyError:
            raise commands.BadArgument(
                _("There is no clownboard named {name}").format(name=argument)
            )
        return clownboard


class RealEmoji(commands.EmojiConverter):
    async def convert(self, ctx: commands.Context, argument: str) -> Union[discord.Emoji, str]:
        try:
            emoji = await super().convert(ctx, argument)
        except commands.BadArgument:
            try:
                await ctx.message.add_reaction(argument)
            except discord.HTTPException:
                raise commands.EmojiNotFound(argument)
            else:
                emoji = argument
        return emoji
