
from __future__ import annotations

import io
import logging
from typing import Any, Dict, Final, List, Literal, Optional

import discord
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import humanize_list

from .views import URLView

log: logging.Logger = logging.getLogger("red.seina.firstmesssage")

RequestType = Literal["discord_deleted_user", "owner", "user", "user_strict"]


class FirstMessage(commands.Cog):
    """
    Provides a link to the first message in the provided channel.
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
        user_id: int | None = kwargs.get("user_id")
        data: Final[str] = "No data is stored for user with ID {}.\n".format(user_id)
        return {"user_data.txt": io.BytesIO(data.encode())}

    @commands.command()
    @commands.has_permissions(read_message_history=True)
    @commands.bot_has_permissions(read_message_history=True)
    async def firstmessage(
        self,
        ctx: commands.Context,
        channel: Optional[
            discord.TextChannel
            | discord.Thread
            | discord.DMChannel
            | discord.GroupChannel
            | discord.User
            | discord.Member
        ] = commands.CurrentChannel,
    ):
        """
        Provide a link to the first message in current or provided channel.
        """
        try:
            messages = [message async for message in channel.history(limit=1, oldest_first=True)]

            chan = (
                f"<@{channel.id}>"
                if isinstance(channel, discord.DMChannel | discord.User | discord.Member)
                else f"<#{channel.id}>"
            )

            embed: discord.Embed = discord.Embed(
                color=await ctx.embed_color(),
                timestamp=messages[0].created_at,
                description=f"[First message in]({messages[0].jump_url}) {chan}",
            )
            embed.set_author(
                name=messages[0].author.display_name,
                icon_url=messages[0].author.avatar.url
                if messages[0].author.avatar
                else messages[0].author.display_avatar.url,
            )

        except (discord.Forbidden, discord.HTTPException, IndexError, AttributeError):
            log.exception(f"Unable to read message history for {channel.id}")
            return await ctx.maybe_send_embed("Unable to read message history for that channel.")

        view = URLView(label="Jump to message", jump_url=messages[0].jump_url)

        await ctx.send(embed=embed, view=view)
