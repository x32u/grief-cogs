import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Literal, Union, cast

import discord
from discord.utils import snowflake_time
from grief import VersionInfo, version_info
from grief.core import Config, commands
from grief.core.bot import Red
from grief.core.i18n import Translator, cog_i18n
from grief.core.utils import AsyncIter
from grief.core.utils.chat_formatting import humanize_timedelta

from .clownboard_entry import FakePayload, ClownboardEntry, ClownboardMessage

_ = Translator("clownboard", __file__)
log = logging.getLogger("grief.clownboard")


@cog_i18n(_)
class ClownboardEvents:
    bot: Red
    config: Config
    clownboards: Dict[int, ClownboardEntry]
    ready: asyncio.Event

    async def _build_embed(
        self, guild: discord.Guild, message: discord.Message, clownboard: ClownboardEntry
    ) -> List[discord.Embed]:
        channel = cast(discord.TextChannel, message.channel)
        author = message.author
        embeds = []
        if message.embeds:
            embeds = message.embeds
            for em in embeds:
                if em.type in ["image", "gifv"]:
                    if em.thumbnail:
                        em.set_image(url=em.thumbnail.url)
                        em.set_thumbnail(url=None)

                if em.description is not None:
                    em.description = "{}\n\n{}".format(message.system_content, em.description)[
                        :4096
                    ]
                else:
                    em.description = message.system_content
                # if not author.bot:
                em.set_author(
                    name=author.display_name,
                    url=message.jump_url,
                    icon_url=author.display_avatar,
                )
                if clownboard.colour in ["user", "member", "author"]:
                    em.color = author.colour
                elif clownboard.colour == "bot":
                    em.color = await self.bot.get_embed_colour(channel)
                else:
                    em.color = discord.Colour(clownboard.colour)
                if msg_ref := getattr(message, "reference", None):
                    ref_msg = getattr(msg_ref, "resolved", None)
                    try:
                        ref_text = ref_msg.system_content
                        ref_link = _("\n[Click Here to view reply context]({link})").format(
                            link=ref_msg.jump_url
                        )
                        if len(ref_text + ref_link) > 1024:
                            ref_text = ref_text[: len(ref_link) - 1] + "\N{HORIZONTAL ELLIPSIS}"
                        ref_text += ref_link
                        em.add_field(
                            name=_("Replying to {author}").format(
                                author=ref_msg.author.display_name
                            ),
                            value=ref_text,
                        )
                    except Exception:
                        pass
                em.timestamp = message.created_at
                jump_link = _("\n\nOriginal message {link}").format(link=message.jump_url)
                if em.description:
                    with_context = f"{em.description}{jump_link}"
                    if len(with_context) > 4096:
                        em.add_field(name=_("Context"), value=jump_link)
                    else:
                        em.description = with_context
                else:
                    em.description = jump_link
                em.set_footer(text=f"{channel.guild.name} | {channel.name}")
        else:
            em = discord.Embed(timestamp=message.created_at, url=message.jump_url)
            if clownboard.colour in ["user", "member", "author"]:
                em.color = author.colour
            elif clownboard.colour == "bot":
                em.color = await self.bot.get_embed_colour(channel)
            else:
                em.color = discord.Colour(clownboard.colour)
            em.description = message.system_content
            em.set_author(
                name=author.display_name, url=message.jump_url, icon_url=author.display_avatar
            )
            if msg_ref := getattr(message, "reference", None):
                ref_msg = getattr(msg_ref, "resolved", None)
                try:
                    ref_text = ref_msg.system_content
                    ref_link = ref_msg.jump_url
                    if len(ref_text + ref_link) > 1024:
                        ref_text = ref_text[: len(ref_link) - 1] + "\N{HORIZONTAL ELLIPSIS}"
                    ref_text += ref_link
                    em.add_field(
                        name=_("Replying to {author}").format(author=ref_msg.author.display_name),
                        value=ref_text,
                    )
                except Exception:
                    pass
            em.timestamp = message.created_at
            jump_link = _("\n\n{link}").format(link=message.jump_url)
            if em.description:
                with_context = f"{em.description}{jump_link}"
                if len(with_context) > 2048:
                    em.add_field(name=_("Context"), value=jump_link)
                else:
                    em.description = with_context
            else:
                em.description = jump_link
            em.set_footer(text=f"{channel.guild.name} | {channel.name}")
            if message.attachments:
                for attachment in message.attachments:
                    new_em = em.copy()
                    spoiler = attachment.is_spoiler()
                    if spoiler:
                        new_em.add_field(
                            name="Attachment",
                            value=f"||[{attachment.filename}]({attachment.url})||",
                        )
                    elif not attachment.url.lower().endswith(
                        ("png", "jpeg", "jpg", "gif", "webp")
                    ):
                        new_em.add_field(
                            name="Attachment", value=f"[{attachment.filename}]({attachment.url})"
                        )
                    else:
                        new_em.set_image(url=attachment.url)
                    embeds.append(new_em)
            else:
                embeds.append(em)
        return embeds

    async def _save_clownboards(self, guild: discord.Guild) -> None:
        async with self.config.guild(guild).clownboards() as clownboards:
            for name, clownboard in self.clownboards[guild.id].items():
                clownboards[name] = await clownboard.to_json()

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent) -> None:
        await self.ready.wait()
        await self._update_clowns(payload)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent) -> None:
        await self.ready.wait()
        await self._update_clowns(payload)

    @commands.Cog.listener()
    async def on_raw_reaction_clear(self, payload: discord.RawReactionActionEvent) -> None:
        await self.ready.wait()
        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return
        if version_info >= VersionInfo.from_str("3.4.0"):
            if await self.bot.cog_disabled_in_guild(self, guild):
                return
        if guild.id not in self.clownboards:
            return
        # clownboards = await self.config.guild(guild).clownboards()
        for name, clownboard in self.clownboards[guild.id].items():
            # clownboard = clownboardEntry.from_json(s_board)
            clown_channel = guild.get_channel(clownboard.channel)
            if not clown_channel:
                continue
            async with clownboard.lock:
                await self._loop_messages(payload, clownboard, clown_channel)

    async def is_bot_or_server_owner(self, member: discord.Member) -> bool:
        guild = member.guild
        if not guild:
            return False
        if guild.owner_id == member.id:
            return True
        return await self.bot.is_owner(member)

    async def _update_clowns(
        self, payload: Union[discord.RawReactionActionEvent, FakePayload]
    ) -> None:
        """
        This handles updating the clownboard with a new message
        based on the reactions added.
        This covers all reaction event types
        """
        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return
        if guild.me.is_timed_out():
            return
        channel = guild.get_channel_or_thread(payload.channel_id)

        if guild.id not in self.clownboards:
            return
        if version_info >= VersionInfo.from_str("3.4.0"):
            if await self.bot.cog_disabled_in_guild(self, guild):
                return

        member = guild.get_member(payload.user_id)
        if member and member.bot:
            return
        clownboard = None
        for name, s_board in self.clownboards[guild.id].items():
            if s_board.emoji == str(payload.emoji):
                clownboard = s_board
        if not clownboard:
            return
        if not clownboard.enabled:
            return
        allowed_roles = clownboard.check_roles(member)
        allowed_channel = clownboard.check_channel(self.bot, channel)
        if any((not allowed_roles, not allowed_channel)):
            log.debug("User or channel not in allowlist")
            return

        clown_channel = guild.get_channel(clownboard.channel)
        if not clown_channel:
            return
        if (
            not clown_channel.permissions_for(guild.me).send_messages
            or not clown_channel.permissions_for(guild.me).embed_links
        ):
            return

        async with clownboard.lock:
            clown_message = await self._loop_messages(payload, clownboard, clown_channel)
            if clown_message is True:
                return

            if clown_message is False:
                if getattr(payload, "event_type", None) == "REACTION_REMOVE":
                    # Return early so we don't create a new clownboard message
                    # when the first time we're seeing the message is on a
                    # reaction remove event
                    return
                try:
                    msg = await channel.fetch_message(payload.message_id)
                except (discord.errors.NotFound, discord.Forbidden):
                    return
                reactions = [payload.user_id]
                if payload.user_id == msg.author.id:
                    if not clownboard.selfclown:
                        reactions.remove(payload.user_id)
                clown_message = ClownboardMessage(
                    guild=guild.id,
                    original_message=payload.message_id,
                    original_channel=payload.channel_id,
                    new_message=None,
                    new_channel=None,
                    author=msg.author.id,
                    reactions=reactions,
                )
            clownboard.clowns_added += 1
            key = f"{payload.channel_id}-{payload.message_id}"
            # await clown_message.update_count(self.bot, clownboard, remove)
            count = len(clown_message.reactions)
            log.debug(f"First time {count=} {clownboard.threshold=}")
            if count < clownboard.threshold:
                if key not in clownboard.messages:
                    self.clownboards[guild.id][clownboard.name].messages[key] = clown_message
                await self._save_clownboards(guild)
                return
            try:
                msg = await channel.fetch_message(payload.message_id)
            except (discord.errors.NotFound, discord.Forbidden):
                return
            if not clownboard.selfclown and msg.author.id == payload.user_id:
                log.debug("Is a selfclown so let's return")
                # this is here to prevent 1 threshold selfclowns
                return
            embeds = await self._build_embed(guild, msg, clownboard)
            count_msg = "{} **#{}**".format(payload.emoji, count)
            post_msg = await clown_channel.send(count_msg, embeds=embeds)
            if clownboard.autoclown:
                try:
                    await post_msg.add_reaction(clownboard.emoji)
                except Exception:
                    log.exception("Error adding autoclown.")
            if key not in clownboard.messages:
                self.clownboards[guild.id][clownboard.name].messages[key] = clown_message
            clown_message.new_message = post_msg.id
            clown_message.new_channel = clown_channel.id
            clownboard.clownred_messages += 1
            index_key = f"{clown_channel.id}-{post_msg.id}"
            self.clownboards[guild.id][clownboard.name].messages[key] = clown_message
            self.clownboards[guild.id][clownboard.name].clownboarded_messages[index_key] = key
            await self._save_clownboards(guild)

    async def red_delete_data_for_user(
        self,
        *,
        requester: Literal["discord_deleted_user", "owner", "user", "user_strict"],
        user_id: int,
    ) -> None:
        """
        Method for finding users data inside the cog and deleting it.
        """
        for guild_id, clownboards in self.clownboards.items():
            for clownboard, entry in clownboards.items():
                for message_ids, message in entry.messages.items():
                    if message.author == user_id:
                        index_key = f"{message.new_channel}-{message.new_message}"
                        try:
                            del self.clownboards[guild_id][clownboard].messages[message_ids]
                            del self.clownboards[guild_id][clownboard].clownboarded_messages[
                                index_key
                            ]
                        except Exception:
                            pass
            async with self.config.guild_from_id(guild_id).clownboards() as clownboards:
                for name, clownboard in self.clownboards[guild_id].items():
                    clownboards[name] = await clownboard.to_json()

    async def cleanup_old_messages(self) -> None:
        """This will periodically iterate through old messages
        and prune them based on age to help keep data relatively easy to work
        through
        """
        purge_time = await self.config.purge_time()

        if not purge_time:
            return
        purge = timedelta(seconds=purge_time)
        while True:
            total_pruned = 0
            guilds_ignored = 0
            to_purge = datetime.now(timezone.utc) - purge
            # Prune only the last 30 days worth of data
            for guild_id, clownboards in self.clownboards.items():
                guild = self.bot.get_guild(guild_id)
                if not guild:
                    guilds_ignored += 1
                    continue
                # log.debug(f"Cleaning clownboard data for {guild.name} ({guild.id})")
                for name, clownboard in clownboards.items():
                    async with clownboard.lock:
                        to_rem = []
                        to_rem_index = []
                        try:
                            async for message_ids, message in AsyncIter(
                                clownboard.messages.items(), steps=500
                            ):
                                if message.new_message:
                                    if snowflake_time(message.new_message) < to_purge:
                                        to_rem.append(message_ids)
                                        index_key = f"{message.new_channel}-{message.new_message}"
                                        to_rem_index.append(index_key)
                                else:
                                    if snowflake_time(message.original_message) < to_purge:
                                        to_rem.append(message_ids)
                            for m in to_rem:
                                log.debug(f"Removing {m}")
                                del clownboard.messages[m]
                                total_pruned += 1
                            for m in to_rem_index:
                                del clownboard.clownboarded_messages[m]
                            if len(to_rem) > 0:
                                log.info(
                                    f"clownboard pruned {len(to_rem)} messages that are "
                                    f"{humanize_timedelta(timedelta=purge)} old from "
                                    f"{guild.name} ({guild.id})"
                                )
                        except Exception:
                            log.exception("Error trying to clenaup old clownboard messages.")
                await self._save_clownboards(guild)
            if total_pruned:
                log.info(
                    f"clownboard has pruned {total_pruned} messages and ignored {guilds_ignored} guilds."
                )
            # Sleep 1 day but also run on cog reload
            await asyncio.sleep(60 * 60 * 24)

    async def _loop_messages(
        self,
        payload: Union[discord.RawReactionActionEvent, FakePayload],
        clownboard: ClownboardEntry,
        clown_channel: discord.TextChannel,
        is_clear: bool = False,
    ) -> Union[ClownboardMessage, bool]:
        """
        This handles finding if we have already saved a message internally

        Parameters
        ----------
            paylod: Union[discord.RawReactionActionEvent, FakePayload]
                Represents the raw reaction payload for the clownred message
            clownboard: clownboardEntry
                The clownboard which matched the reaction emoji.
            clown_channel: discord.TextChannel
                The channel which we want to send clownboard messages into.
            is_clear: bool
                Whether or not the reaction event was for clearing all emojis.

        Returns
        -------
            Union[clownboardMessage, bool]
                clownboardMessage object if we have already saved this message
                but have not posted the new message yet.

                True if we have found the clownboard object and no further action is
                required.

                False if we want to post the new clownboard message.

        """
        try:
            guild = clown_channel.guild
        except AttributeError:
            return False
        key = f"{payload.channel_id}-{payload.message_id}"
        if key in clownboard.messages:
            # the clownred message was an original clownboard message
            clownboard_msg = clownboard.messages[key]
        elif key in clownboard.clownboarded_messages:
            # the clownred message was the clownboarded message
            key = clownboard.clownboarded_messages[key]
            clownboard_msg = clownboard.messages[key]
            pass
        else:
            return False

        # await clownboard_msg.update_count(self.bot, clownboard, remove)
        if not clownboard.selfclown and payload.user_id == clownboard_msg.author:
            return True

        if getattr(payload, "event_type", None) == "REACTION_ADD":
            if (user_id := getattr(payload, "user_id", 0)) not in clownboard_msg.reactions:
                clownboard_msg.reactions.append(user_id)
                log.debug("Adding user in _loop_messages")
                clownboard.clowns_added += 1
        else:
            if (user_id := getattr(payload, "user_id", 0)) in clownboard_msg.reactions:
                clownboard_msg.reactions.remove(user_id)
                log.debug("Removing user in _loop_messages")
                clownboard.clowns_added -= 1

        if not clownboard_msg.new_message or not clownboard_msg.new_channel:
            return clownboard_msg
        count = len(clownboard_msg.reactions)
        log.debug(f"Existing {count=} {clownboard.threshold=}")
        if count < clownboard.threshold:
            try:
                index_key = f"{clownboard_msg.new_channel}-{clownboard_msg.new_message}"
                del clownboard.clownboarded_messages[index_key]
                log.debug("Removed old message from index")
            except KeyError:
                pass
            await clownboard_msg.delete(clown_channel)
            clownboard.clownred_messages -= 1
            await self._save_clownboards(guild)
            return True
        log.debug("Editing clownboard")
        count_message = f"{clownboard.emoji} **#{count}**"
        asyncio.create_task(clownboard_msg.edit(clown_channel, count_message))
        # create a task because otherwise we could wait up to an hour to open the lock.
        # This is thanks to announcement channels and published messages.
        return True
