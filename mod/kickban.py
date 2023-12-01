import asyncio
import contextlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple, Union

import discord
from grief.core import commands, i18n
from grief.core.commands import RawUserIdConverter
from grief.core.utils import AsyncIter
from grief.core.utils.chat_formatting import (
    pagify,
    humanize_number,
    bold,
    humanize_list,
    format_perms_list,
)
from grief.core.utils.mod import get_audit_reason
from .abc import MixinMeta
from .utils import is_allowed_by_hierarchy
from io import BytesIO
from grief.core.commands.converter import TimedeltaConverter
from discord.utils import utcnow
from grief.core.utils.views import ConfirmView
from .converters import ImageFinder

log = logging.getLogger("grief.mod")
_ = i18n.Translator("Mod", __file__)


class KickBanMixin(MixinMeta):
    """
    Kick and ban commands and tasks go here.
    """

    @staticmethod
    async def get_invite_for_reinvite(ctx: commands.Context, max_age: int = 86400) -> str:
        """Handles the reinvite logic for getting an invite to send the newly unbanned user"""
        guild = ctx.guild
        my_perms: discord.Permissions = guild.me.guild_permissions
        if my_perms.manage_guild or my_perms.administrator:
            if guild.vanity_url is not None:
                return guild.vanity_url
            invites = await guild.invites()
        else:
            invites = []
        for inv in invites:  # Loop through the invites for the guild
            if not (inv.max_uses or inv.max_age or inv.temporary):
                # Invite is for the guild's default channel,
                # has unlimited uses, doesn't expire, and
                # doesn't grant temporary membership
                # (i.e. they won't be kicked on disconnect)
                return inv.url
        else:  # No existing invite found that is valid
            channels_and_perms = (
                (channel, channel.permissions_for(guild.me)) for channel in guild.text_channels
            )
            channel = next(
                (channel for channel, perms in channels_and_perms if perms.create_instant_invite),
                None,
            )
            if channel is None:
                return ""
            try:
                # Create invite that expires after max_age
                return (await channel.create_invite(max_age=max_age)).url
            except discord.HTTPException:
                return ""
                

    @staticmethod
    async def _voice_perm_check(
        ctx: commands.Context, user_voice_state: Optional[discord.VoiceState], **perms: bool
    ) -> bool:
        """Check if the bot and user have sufficient permissions for voicebans.

        This also verifies that the user's voice state and connected
        channel are not ``None``.

        Returns
        -------
        bool
            ``True`` if the permissions are sufficient and the user has
            a valid voice state.

        """
        if user_voice_state is None or user_voice_state.channel is None:
            await ctx.send(_("That user is not in a voice channel."))
            return False
        voice_channel: discord.VoiceChannel = user_voice_state.channel
        required_perms = discord.Permissions()
        required_perms.update(**perms)
        if not voice_channel.permissions_for(ctx.me) >= required_perms:
            await ctx.send(
                _("I require the {perms} permission(s) in that user's channel to do that.").format(
                    perms=format_perms_list(required_perms)
                )
            )
            return False
        if (
            ctx.permission_state is commands.PermState.NORMAL
            and not voice_channel.permissions_for(ctx.author) >= required_perms
        ):
            await ctx.send(
                _(
                    "You must have the {perms} permission(s) in that user's channel to use this "
                    "command."
                ).format(perms=format_perms_list(required_perms))
            )
            return False
        return True

    async def ban_user(
        self,
        user: Union[discord.Member, discord.User, discord.Object],
        ctx: commands.Context,
        days: int = 0,
        reason: str = None,
    ) -> Tuple[bool, str]:
        author = ctx.author
        guild = ctx.guild

        removed_temp = False

        if not (0 <= days <= 7):
            return False, _("Invalid days. Must be between 0 and 7.")

        if isinstance(user, discord.Member):
            if author == user:
                return (
                    False,
                    _("You cannot ban yourself."),
                )
            elif not await is_allowed_by_hierarchy(self.bot, self.config, guild, author, user):
                return (
                    False,
                    _(
                        "I cannot let you do that. You are "
                        "not higher than the user in the role "
                        "hierarchy."
                    ),
                )
            elif guild.me.top_role <= user.top_role or user == guild.owner:
                return False, _("I cannot do that due to Discord hierarchy rules.")

            toggle = await self.config.guild(guild).dm_on_kickban()
            if toggle:
                with contextlib.suppress(discord.HTTPException):
                    em = discord.Embed(
                        title=bold(_("You have been banned from {guild}.").format(guild=guild)),
                        color=await self.bot.get_embed_color(user),
                    )
                    em.add_field(
                        name=_("**Reason**"),
                        value=reason if reason is not None else _("No reason was given."),
                        inline=False,
                    )
                    await user.send(embed=em)

            ban_type = "ban"
        else:
            tempbans = await self.config.guild(guild).current_tempbans()

            try:
                await guild.fetch_ban(user)
            except discord.NotFound:
                pass
            else:
                if user.id in tempbans:
                    async with self.config.guild(guild).current_tempbans() as tempbans:
                        tempbans.remove(user.id)
                    removed_temp = True
                else:
                    return (
                        False,
                        _("User with ID {user_id} is already banned.").format(user_id=user.id),
                    )

            ban_type = "hackban"

        audit_reason = get_audit_reason(author, reason, shorten=True)

        if removed_temp:
            log.info(
                "{}({}) upgraded the tempban for {} to a permaban.".format(
                    author.name, author.id, user.id
                )
            )
            success_message = _(
                "User with ID {user_id} was upgraded from a temporary to a permanent ban."
            ).format(user_id=user.id)
        else:
            username = user.name if hasattr(user, "name") else "Unknown"
            try:
                await guild.ban(user, reason=audit_reason, delete_message_seconds=days * 86400)
                log.info(
                    "{}({}) {}ned {}({}), deleting {} days worth of messages.".format(
                        author.name, author.id, ban_type, username, user.id, str(days)
                    )
                )
                success_message = _("User has been banned.")
            except discord.Forbidden:
                return False, _("I'm not allowed to do that.")
            except discord.NotFound:
                return False, _("User with ID {user_id} not found").format(user_id=user.id)
            except Exception:
                log.exception(
                    "{}({}) attempted to {} {}({}), but an error occurred.".format(
                        author.name, author.id, ban_type, username, user.id
                    )
                )
                return False, _("An unexpected error occurred.")

        return True, success_message

    async def tempban_expirations_task(self) -> None:
        while True:
            try:
                await self._check_tempban_expirations()
            except Exception:
                log.exception("Something went wrong in check_tempban_expirations:")

            await asyncio.sleep(60)

    async def _check_tempban_expirations(self) -> None:
        guilds_data = await self.config.all_guilds()
        async for guild_id, guild_data in AsyncIter(guilds_data.items(), steps=100):
            if not (guild := self.bot.get_guild(guild_id)):
                continue
            if guild.unavailable or not guild.me.guild_permissions.ban_members:
                continue
            if await self.bot.cog_disabled_in_guild(self, guild):
                continue

            guild_tempbans = guild_data["current_tempbans"]
            if not guild_tempbans:
                continue
            async with self.config.guild(guild).current_tempbans.get_lock():
                if await self._check_guild_tempban_expirations(guild, guild_tempbans):
                    await self.config.guild(guild).current_tempbans.set(guild_tempbans)

    async def _check_guild_tempban_expirations(
        self, guild: discord.Guild, guild_tempbans: List[int]
    ) -> bool:
        changed = False
        for uid in guild_tempbans.copy():
            unban_time = datetime.fromtimestamp(
                await self.config.member_from_ids(guild.id, uid).banned_until(),
                timezone.utc,
            )
            if datetime.now(timezone.utc) > unban_time:
                try:
                    await guild.unban(discord.Object(id=uid), reason=_("Tempban finished"))
                except discord.NotFound:
                    # user is not banned anymore
                    guild_tempbans.remove(uid)
                    changed = True
                except discord.HTTPException as e:
                    # 50013: Missing permissions error code or 403: Forbidden status
                    if e.code == 50013 or e.status == 403:
                        log.info(
                            f"Failed to unban ({uid}) user from "
                            f"{guild.name}({guild.id}) guild due to permissions."
                        )
                        break  # skip the rest of this guild
                    log.info(f"Failed to unban member: error code: {e.code}")
                else:
                    # user unbanned successfully
                    guild_tempbans.remove(uid)
                    changed = True
        return changed

    @commands.command(autohelp=True, aliases=["k"])
    @commands.guild_only()
    @commands.cooldown(1, 3, commands.BucketType.guild)
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx: commands.Context, member: discord.Member, *, reason: str = None):
        """
        Kick a user.
        """
        author = ctx.author
        guild = ctx.guild

        if reason == None:
            reason = "No reason given"
        
        if author == member:
            await ctx.send(
                _(_("You cannot kick yourself.")
                )
            )
            return
        elif not await is_allowed_by_hierarchy(self.bot, self.config, guild, author, member):
            await ctx.send(
                _(
                    "I cannot let you do that. You are "
                    "not higher than the user in the role "
                    "hierarchy."
                )
            )
            return
        elif ctx.guild.me.top_role <= member.top_role or member == ctx.guild.owner:
            await ctx.send(_("I cannot do that due to Discord hierarchy rules."))
            return
        audit_reason = get_audit_reason(author, reason, shorten=True)
        toggle = await self.config.guild(guild).dm_on_kickban()
        if toggle:
            with contextlib.suppress(discord.HTTPException):
                em = discord.Embed(
                    title=bold(_("You have been kicked from {guild}.").format(guild=guild)),
                    color=await self.bot.get_embed_color(member),
                )
                em.add_field(
                    name=_("**Reason**"),
                    value=reason if reason is not None else _("No reason was given."),
                    inline=False,
                )
                await member.send(embed=em)
        try:
            await guild.kick(member, reason=audit_reason)
            embed = discord.Embed(description=f"> {ctx.author.mention}: Kicked {member} for {reason}", color=0x313338)
            return await ctx.reply(embed=embed, mention_author=False)
        except discord.errors.Forbidden:
            await ctx.send(_("I'm not allowed to do that."))
        except Exception:
            log.exception(
                "{}({}) attempted to kick {}({}), but an error occurred.".format(
                    author.name, author.id, member.name, member.id
                )
            )

    @commands.command(autohelp=True, aliases=["b"])
    @commands.guild_only()
    @commands.cooldown(1, 3, commands.BucketType.guild)
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx: commands.Context, user: Union[discord.Member, RawUserIdConverter], days: Optional[int] = None, *, reason: str = None,):
        """Ban a user from this server and optionally delete days of messages."""
        guild = ctx.guild
        if days is None:
            days = await self.config.guild(guild).default_days()
        if isinstance(user, int):
            user = self.bot.get_user(user) or discord.Object(id=user)

        success_, message = await self.ban_user(
            user=user, ctx=ctx, days=days, reason=reason
        )

        await ctx.tick()

    @commands.command(aliases=["hackban", "mb"], usage="<user_ids...> [days] [reason]")
    @commands.guild_only()
    @commands.cooldown(1, 3, commands.BucketType.guild)
    @commands.has_permissions(ban_members=True)
    async def massban(
        self,
        ctx: commands.Context,
        user_ids: commands.Greedy[RawUserIdConverter],
        days: Optional[int] = None,
        *,
        reason: str = None,
    ):
        """Mass bans users from the server."""
        banned = []
        errors = {}
        upgrades = []

        async def show_results():
            text = _("Banned {num} users from the server.").format(
                num=humanize_number(len(banned))
            )
            if errors:
                text += _("\nErrors:\n")
                text += "\n".join(errors.values())
            if upgrades:
                text += _(
                    "\nFollowing user IDs have been upgraded from a temporary to a permanent ban:\n"
                )
                text += humanize_list(upgrades)

            for p in pagify(text):
                await ctx.send(p)

        def remove_processed(ids):
            return [_id for _id in ids if _id not in banned and _id not in errors]

        user_ids = list(set(user_ids))  # No dupes

        author = ctx.author
        guild = ctx.guild

        if not user_ids:
            await ctx.send_help()
            return

        if days is None:
            days = await self.config.guild(guild).default_days()

        if not (0 <= days <= 7):
            await ctx.send(_("Invalid days. Must be between 0 and 7."))
            return

        if not guild.me.guild_permissions.ban_members:
            return await ctx.send(_("I lack the permissions to do this."))

        tempbans = await self.config.guild(guild).current_tempbans()

        for user_id in user_ids:
            if user_id in tempbans:
                # We need to check if a user is tempbanned here because otherwise they won't be processed later on.
                continue
            try:
                await guild.fetch_ban(discord.Object(user_id))
            except discord.NotFound:
                pass
            else:
                errors[user_id] = _("User with ID {user_id} is already banned.").format(
                    user_id=user_id
                )

        user_ids = remove_processed(user_ids)

        if not user_ids:
            await show_results()
            return

        # We need to check here, if any of the users isn't a member and if they are,
        # we need to use our `ban_user()` method to do hierarchy checks.
        members: Dict[int, discord.Member] = {}
        to_query: List[int] = []

        for user_id in user_ids:
            member = guild.get_member(user_id)
            if member is not None:
                members[user_id] = member
            elif not guild.chunked:
                to_query.append(user_id)

        # If guild isn't chunked, we might possibly be missing the member from cache,
        # so we need to make sure that isn't the case by querying the user IDs for such guilds.
        while to_query:
            queried_members = await guild.query_members(user_ids=to_query[:100], limit=100)
            members.update((member.id, member) for member in queried_members)
            to_query = to_query[100:]

        # Call `ban_user()` method for all users that turned out to be guild members.
        for user_id, member in members.items():
            try:
                # using `reason` here would shadow the reason passed to command
                success, failure_reason = await self.ban_user(
                    user=member, ctx=ctx, days=days, reason=reason
                )
                if success:
                    banned.append(user_id)
                else:
                    errors[user_id] = _("Failed to ban user {user_id}: {reason}").format(
                        user_id=user_id, reason=failure_reason
                    )
            except Exception as e:
                errors[user_id] = _("Failed to ban user {user_id}: {reason}").format(
                    user_id=user_id, reason=e
                )

        user_ids = remove_processed(user_ids)

        if not user_ids:
            await show_results()
            return

        for user_id in user_ids:
            user = discord.Object(id=user_id)
            audit_reason = get_audit_reason(author, reason, shorten=True)
            async with self.config.guild(guild).current_tempbans() as tempbans:
                if user_id in tempbans:
                    tempbans.remove(user_id)
                    upgrades.append(str(user_id))
                    log.info(
                        "{}({}) upgraded the tempban for {} to a permaban.".format(
                            author.name, author.id, user_id
                        )
                    )
                    banned.append(user_id)
                else:
                    try:
                        await guild.ban(
                            user, reason=audit_reason, delete_message_seconds=days * 86400
                        )
                        log.info("{}({}) hackbanned {}".format(author.name, author.id, user_id))
                    except discord.NotFound:
                        errors[user_id] = _("User with ID {user_id} not found").format(
                            user_id=user_id
                        )
                        continue
                    except discord.Forbidden:
                        errors[user_id] = _(
                            "Could not ban user with ID {user_id}: missing permissions."
                        ).format(user_id=user_id)
                        continue
                    else:
                        banned.append(user_id)

    @commands.command()
    @commands.guild_only()
    @commands.cooldown(1, 3, commands.BucketType.guild)
    @commands.has_permissions(ban_members=True)
    async def tempban(
        self,
        ctx: commands.Context,
        member: discord.Member,
        duration: Optional[commands.TimedeltaConverter] = None,
        days: Optional[int] = None,
        *,
        reason: str = None,
    ):
        """Temporarily ban a user from this server.
        """
        guild = ctx.guild
        author = ctx.author

        if author == member:
            await ctx.send(
                _("You cannot ban yourself.")
            )
            return
        elif not await is_allowed_by_hierarchy(self.bot, self.config, guild, author, member):
            await ctx.send(
                _(
                    "I cannot let you do that. You are "
                    "not higher than the user in the role "
                    "hierarchy."
                )
            )
            return
        elif guild.me.top_role <= member.top_role or member == guild.owner:
            await ctx.send(_("I cannot do that due to Discord hierarchy rules."))
            return

        guild_data = await self.config.guild(guild).all()

        if duration is None:
            duration = timedelta(seconds=guild_data["default_tempban_duration"])
        unban_time = datetime.now(timezone.utc) + duration

        if days is None:
            days = guild_data["default_days"]

        if not (0 <= days <= 7):
            await ctx.send(_("Invalid days. Must be between 0 and 7."))
            return
        invite = await self.get_invite_for_reinvite(ctx, int(duration.total_seconds() + 86400))

        await self.config.member(member).banned_until.set(unban_time.timestamp())
        async with self.config.guild(guild).current_tempbans() as current_tempbans:
            current_tempbans.append(member.id)

        with contextlib.suppress(discord.HTTPException):
            # We don't want blocked DMs preventing us from banning
            msg = _("You have been temporarily banned from {server_name} until {date}.").format(
                server_name=guild.name, date=discord.utils.format_dt(unban_time)
            )
            if guild_data["dm_on_kickban"] and reason:
                msg += _("\n\n**Reason:** {reason}").format(reason=reason)
            if invite:
                msg += _("\n\nHere is an invite for when your ban expires: {invite_link}").format(
                    invite_link=invite
                )
            await member.send(msg)

        audit_reason = get_audit_reason(author, reason, shorten=True)

        try:
            await guild.ban(member, reason=audit_reason, delete_message_seconds=days * 86400)
        except discord.Forbidden:
            await ctx.send(_("I can't do that for some reason."))
        except discord.HTTPException:
            await ctx.send(_("Something went wrong while banning."))

    @commands.command(autohelp=True, aliases=["sbn"])
    @commands.guild_only()
    @commands.cooldown(1, 3, commands.BucketType.guild)
    @commands.has_permissions(ban_members=True)
    async def softban(self, ctx: commands.Context, member: discord.Member, *, reason: str = None):
        """Kick a user and delete 1 day's worth of their messages."""
        guild = ctx.guild
        author = ctx.author

        if author == member:
            await ctx.send(
                ("You cannot ban yourself.")
            )
            return
        elif not await is_allowed_by_hierarchy(self.bot, self.config, guild, author, member):
            await ctx.send(
                _(
                    "I cannot let you do that. You are "
                    "not higher than the user in the role "
                    "hierarchy."
                )
            )
            return

        audit_reason = get_audit_reason(author, reason, shorten=True)

        invite = await self.get_invite_for_reinvite(ctx)

        try:  # We don't want blocked DMs preventing us from banning
            msg = await member.send(
                _(
                    "You have been banned and "
                    "then unbanned as a quick way to delete your messages.\n"
                    "You can now join the server again. {invite_link}"
                ).format(invite_link=invite)
            )
        except discord.HTTPException:
            msg = None
        try:
            await guild.ban(member, reason=audit_reason, delete_message_seconds=86400)
        except discord.errors.Forbidden:
            await ctx.send(_("My role is not high enough to softban that user."))
            if msg is not None:
                await msg.delete()
            return
        except discord.HTTPException:
            log.exception(
                "{}({}) attempted to softban {}({}), but an error occurred trying to ban them.".format(
                    author.name, author.id, member.name, member.id
                )
            )
            return
        try:
            await guild.unban(member)
        except discord.HTTPException:
            log.exception(
                "{}({}) attempted to softban {}({}), but an error occurred trying to unban them.".format(
                    author.name, author.id, member.name, member.id
                )
            )
            return
        else:
            log.info(
                "{}({}) softbanned {}({}), deleting 1 day worth "
                "of messages.".format(author.name, author.id, member.name, member.id)
            )

    @commands.command(autohelp=True, aliases=["vk"])
    @commands.cooldown(1, 3, commands.BucketType.guild)
    @commands.has_permissions(move_members=True)
    async def voicekick(
        self, ctx: commands.Context, member: discord.Member, *, reason: str = None
    ):
        """Kick a member from a voice channel."""
        author = ctx.author
        guild = ctx.guild
        user_voice_state: discord.VoiceState = member.voice

        if await self._voice_perm_check(ctx, user_voice_state, move_members=True) is False:
            return
        elif not await is_allowed_by_hierarchy(self.bot, self.config, guild, author, member):
            await ctx.send(
                _(
                    "I cannot let you do that. You are "
                    "not higher than the user in the role "
                    "hierarchy."
                )
            )
            return
        await ctx.tick()

        try:
            await member.move_to(None)
        except discord.Forbidden:  # Very unlikely that this will ever occur
            await ctx.send(_("I am unable to kick this member from the voice channel."))
            return
        except discord.HTTPException:
            await ctx.send(_("Something went wrong while attempting to kick that member."))
            return

    @commands.command()
    @commands.guild_only()
    @commands.cooldown(1, 3, commands.BucketType.guild)
    @commands.has_permissions(mute_members=True, deafen_members=True)
    async def voiceunban(
        self, ctx: commands.Context, member: discord.Member, *, reason: str = None
    ):
        """Unban a user from speaking and listening in the server's voice channels."""
        user_voice_state = member.voice
        if (
            await self._voice_perm_check(
                ctx, user_voice_state, deafen_members=True, mute_members=True
            )
            is False
        ):
            return
        await ctx.tick()

        needs_unmute = True if user_voice_state.mute else False
        needs_undeafen = True if user_voice_state.deaf else False
        audit_reason = get_audit_reason(ctx.author, reason, shorten=True)
        if needs_unmute and needs_undeafen:
            await member.edit(mute=False, deafen=False, reason=audit_reason)
        elif needs_unmute:
            await member.edit(mute=False, reason=audit_reason)
        elif needs_undeafen:
            await member.edit(deafen=False, reason=audit_reason)
        else:
            await ctx.send(_("That user isn't muted or deafened by the server."))
            return

    @commands.command(autohelp=True, aliases=["vb"])
    @commands.guild_only()
    @commands.cooldown(1, 3, commands.BucketType.guild)
    @commands.has_permissions(mute_members=True, deafen_members=True)
    async def voiceban(self, ctx: commands.Context, member: discord.Member, *, reason: str = None):
        """Ban a user from speaking and listening in the server's voice channels."""
        user_voice_state: discord.VoiceState = member.voice
        if (
            await self._voice_perm_check(
                ctx, user_voice_state, deafen_members=True, mute_members=True
            )
            is False
        ):
            return
        await ctx.tick()
        
        needs_mute = True if user_voice_state.mute is False else False
        needs_deafen = True if user_voice_state.deaf is False else False
        audit_reason = get_audit_reason(ctx.author, reason, shorten=True)
        author = ctx.author
        guild = ctx.guild
        if needs_mute and needs_deafen:
            await member.edit(mute=True, deafen=True, reason=audit_reason)
        elif needs_mute:
            await member.edit(mute=True, reason=audit_reason)
        elif needs_deafen:
            await member.edit(deafen=True, reason=audit_reason)
        else:
            await ctx.send(_("That user is already muted and deafened server-wide."))
            return

    @commands.command(autohelp=True, aliases=["ub"])
    @commands.guild_only()
    @commands.cooldown(1, 3, commands.BucketType.guild)
    @commands.has_permissions(ban_members=True)
    async def unban(
        self, ctx: commands.Context, user_id: RawUserIdConverter, *, reason: str = None
    ):
        """Unban a user from this server."""
        guild = ctx.guild
        author = ctx.author
        audit_reason = get_audit_reason(ctx.author, reason, shorten=True)
        try:
            ban_entry = await guild.fetch_ban(discord.Object(user_id))
        except discord.NotFound:
            await ctx.send(_("It seems that user isn't banned!"))
            return
        try:
            await guild.unban(ban_entry.user, reason=audit_reason)
        except discord.HTTPException:
            await ctx.send(_("Something went wrong while attempting to unban that user."))
            return

        if await self.config.guild(guild).reinvite_on_unban():
            user = ctx.bot.get_user(user_id)
            if not user:
                await ctx.send(
                    _("I don't share another server with this user. I can't reinvite them.")
                )
                return
            await ctx.tick()

            invite = await self.get_invite_for_reinvite(ctx)
            if invite:
                try:
                    await user.send(
                        _(
                            "You've been unbanned from {server}.\n"
                            "Here is an invite for that server: {invite_link}"
                        ).format(server=guild.name, invite_link=invite)
                    )
                except discord.Forbidden:
                    await ctx.send(
                        _(
                            "I failed to send an invite to that user. "
                            "Perhaps you may be able to send it for me?\n"
                            "Here's the invite link: {invite_link}"
                        ).format(invite_link=invite)
                    )
                except discord.HTTPException:
                    await ctx.send(
                        _(
                            "Something went wrong when attempting to send that user "
                            "an invite. Here's the link so you can try: {invite_link}"
                        ).format(invite_link=invite)
                    )
    
    @commands.group(aliases=["gedit", "sedit", "serveredit"], hidden=True)
    @commands.is_owner()
    async def guildedit(self, ctx: commands.Context) -> None:
        """Edit various guild settings."""
   
    @commands.command(name="seticon", hidden=True)
    async def guild_icon(self, ctx, image: ImageFinder = None):
        """Set the icon of the server.

        `<image>` URL to the image or image uploaded with running the
        command

        """
        if image is None:
            image = await ImageFinder().search_for_images(ctx)

        url = image[0]

        b, mime = await self.bytes_download(url)
        if not b:
            return await ctx.send("That's not a valid image.")

        await ctx.guild.edit(icon=b.getvalue())
        return await ctx.tick()

    @commands.command(name="setinvitesplash", aliases=["splash"], hidden=True)
    async def guild_invite(self, ctx, image: ImageFinder = None):
        """Set the invite splash screen of the server.

        `<image>` URL to the image or image uploaded with running the
        command

        """
        if image is None:
            image = await ImageFinder().search_for_images(ctx)
        url = image[0]

        b, mime = await self.bytes_download(url)
        if not b:
            return await ctx.send("That's not a valid image.")

        await ctx.guild.edit(splash=b.getvalue())
        return await ctx.tick()

    @commands.command(name="setbanner", hidden=True)
    async def guild_banner(self, ctx, image: ImageFinder = None):
        """Set the banner of the server.

        `<image>` URL to the image or image uploaded with running the
        command

        """
        if image is None:
            image = await ImageFinder().search_for_images(ctx)
        url = image[0]

        b, mime = await self.bytes_download(url)
        if not b:
            return await ctx.send("That's not a valid image.")

        await ctx.guild.edit(banner=b.getvalue())
        return await ctx.tick()
           
    @commands.command(aliases=["invitepurge", "staleinvites"], hidden=True)
    @commands.max_concurrency(1, commands.BucketType.guild)
    @commands.is_owner()
    async def inviteprune(self, ctx: commands.Context):
        """Remove invites with 0 uses."""
        guild: discord.Guild = ctx.guild

        invites = await guild.invites()

        not_used = [i for i in invites if i.uses == 0]
        if not not_used:
            return await ctx.send("There are no stale invites!")

        confirmed = await ctx.send(f"There are {len(not_used)} invites with 0 uses.", "Can I delete them?")

        if confirmed:
            return

        status = await ctx.send("Deleted 0/{len(not_used)}")

        try:
            i: discord.Invite
            total_errors = 0

            for idx, i in enumerate(not_used, start=1):
                try:
                    async with asyncio.timeout(3):
                        try:
                            await i.delete()
                            log.info(f"Deleted {i} from {ctx.guild} OK")
                            await status.edit("Deleted {idx}/{len(not_used)}")
                        except discord.HTTPException:
                            total_errors += 1

                            if total_errors > 9:
                                log.error(f"Bailing on {ctx.guild}")
                                return await ctx.send("Bailing on the request to delete invites. Too many errors from Discord", 2)
                except TimeoutError:
                    total_errors += 1
                    log.warning(f"Timeout for {i}")
                    if total_errors > 9:
                        log.error(f"Bailing on {ctx.guild}")
                        return await ctx.send("Bailing on the request to delete invites. Too many errors from Discord", 2)

                await asyncio.sleep(3)

            return await ctx.send("Stale invites deleted!")

        finally:
            await status.delete()

    @commands.is_owner()
    @commands.command(hidden=True)
    async def naughty(self, ctx: commands.Context):
        """Temporarily make the current channel NSFW for 30 seconds."""
        channel: discord.TextChannel = ctx.channel
        if not hasattr(channel, "nsfw"):
            return await ctx.send("This channel cannot be set as NSFW", 3)
        if channel.nsfw:
            return await ctx.send("The current channel is already NSFW!")
        await channel.edit(nsfw=True)
        self.bot.ioloop.call_later(30, channel.edit, nsfw=False)
        return await ctx.send("The current channel is NSFW now for 30 seconds")