

from __future__ import annotations

import asyncio
import io
import logging
from typing import Any, Dict, Final, List, Literal, Optional

import discord
from grief.core import commands
from grief.core.bot import Red
from grief.core.i18n import Translator, cog_i18n
from grief.core.utils.chat_formatting import humanize_list
from grief.core.utils.predicates import MessagePredicate

log: logging.Logger = logging.getLogger("red.seina.massunban")

RequestType = Literal["discord_deleted_user", "owner", "user", "user_strict"]

_ = Translator("MassUnban", __file__)


@cog_i18n(_)
class MassUnban(commands.Cog):
    """
    Unban all users, or users with a specific ban reason.
    """

    def __init__(self, bot: Red) -> None:
        super().__init__()
        self.bot: Red = bot

    async def red_get_data_for_user(
        self, *, requester: RequestType, user_id: int
    ) -> Dict[str, io.BytesIO]:
        """
        Nothing to delete
        """
        data: Final[str] = "No data is stored for user with ID {}.\n".format(user_id)
        return {"User_data.txt": io.BytesIO(data.encode())}

    async def red_delete_data_for_user(self, **kwargs: Any) -> Dict[str, io.BytesIO]:
        """
        Delete a user's personal data.
        No personal data is stored in this cog.
        """
        user_id: Optional[int] = kwargs.get("user_id")
        data: Final[str] = "No data is stored for user with ID {}.\n".format(user_id)
        return {"user_data.txt": io.BytesIO(data.encode())}
    
    @commands.command()
    @commands.guild_only()
    @commands.guildowner()
    async def massunban(self, ctx: commands.Context, *, ban_reason: Optional[str] = None):
        """
        Mass unban everyone, or specific people.

        **Arguments**
        - [`ban_reason`] is what the bot looks for in the original ban reason to qualify a user for an unban. It is case-insensitive.

        When [botname] is used to ban a user, the ban reason looks like:
        `action requested by resent (id 214753146512080907). reason: bad person`
        Using `[p]massunban bad person` will unban this user as "bad person" is contained in the original ban reason.
        Using `[p]massunban resent` will unban every user banned by aikaterna, if [botname] was used to ban them in the first place.
        For users banned using the right-click ban option in Discord, the ban reason is only what the mod puts when it asks for a reason, so using the mod name to unban won't work.

        Every unban will show up in your modlog if mod logging is on for unbans. Check `[p]modlogset cases` to verify if mod log creation on unbans is on.
        This can mean that your bot will be ratelimited on sending messages if you unban lots of users as it will create a modlog entry for each unban.
        """
        try:
            banlist: List[discord.BanEntry] = [entry async for entry in ctx.guild.bans()]
        except discord.errors.Forbidden:
            msg = _("I need the `Ban Members` permission to fetch the ban list for the guild.")
            await ctx.send(msg)
            return
        except (discord.HTTPException, TypeError):
            log.exception("Something went wrong while fetching the ban list!", exc_info=True)
            return

        bancount: int = len(banlist)
        if bancount == 0:
            await ctx.send(_("No users are banned from this server."))
            return

        unban_count: int = 0
        if not ban_reason:
            warning_string = _(
                "Are you sure you want to unban every banned person on this server?\n"
                f"**Please read** `{ctx.prefix}help massunban` **as this action can cause a LOT of modlog messages!**\n"
                "Type `Yes` to confirm, or `No` to cancel."
            )
            await ctx.send(warning_string)
            pred = MessagePredicate.yes_or_no(ctx)
            try:
                await self.bot.wait_for("message", check=pred, timeout=15)
                if pred.result is True:
                    async with ctx.typing():
                        for ban_entry in banlist:
                            await ctx.guild.unban(
                                ban_entry.user,
                                reason=_("Mass Unban requested by {name} ({id})").format(
                                    name=str(ctx.author.display_name), id=ctx.author.id
                                ),
                            )
                            await asyncio.sleep(0.5)
                            unban_count += 1
                else:
                    return await ctx.send(_("Alright, I'm not unbanning everyone."))
            except asyncio.TimeoutError:
                return await ctx.send(
                    _(
                        "Response timed out. Please run this command again if you wish to try again."
                    )
                )
        else:
            async with ctx.typing():
                for ban_entry in banlist:
                    if not ban_entry.reason:
                        continue
                    if ban_reason.lower() in ban_entry.reason.lower():
                        await ctx.guild.unban(
                            ban_entry.user,
                            reason=_("Mass Unban requested by {name} ({id})").format(
                                name=str(ctx.author.display_name), id=ctx.author.id
                            ),
                        )
                        await asyncio.sleep(1)
                        unban_count += 1

        await ctx.send(_("Done. Unbanned {unban_count} users.").format(unban_count=unban_count))
