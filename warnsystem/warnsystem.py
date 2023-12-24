# WarnSystem by retke, aka El Laggron
import discord
import logging
import asyncio

from io import BytesIO
from typing import Optional, TYPE_CHECKING
from asyncio import TimeoutError as AsyncTimeoutError
from abc import ABC
from datetime import datetime, timedelta, timezone

from grief.core import commands, Config, checks
from grief.core.commands.converter import TimedeltaConverter
from grief.core.i18n import Translator, cog_i18n
from grief.core.utils import predicates, menus, mod
from grief.core.utils.chat_formatting import pagify, text_to_file

from warnsystem.components import WarningsSelector

from . import errors
from .api import API, UnavailableMember
from .cache import MemoryCache
from .converters import AdvancedMemberSelect
from .settings import SettingsMixin

if TYPE_CHECKING:
    from grief.core.bot import Grief

log = logging.getLogger("grief.warnsystem")
_ = Translator("WarnSystem", __file__)

EMBED_MODLOG = lambda x: _("A member got a level {} warning.").format(x)
EMBED_USER = lambda x: _("The moderation team set you a warning.").format(x)


class CompositeMetaClass(type(commands.Cog), type(ABC)):


    pass


@cog_i18n(_)
class WarnSystem(SettingsMixin, commands.Cog, metaclass=CompositeMetaClass):
    """
    Providing a system of moderation similar to Dyno.
    """

    default_global = {
        "data_version": "0.0"  # will be edited after config update, current version is 1.0
    }
    default_guild = {
        "delete_message": True,  # if the [p]warn commands should delete the context message
        "show_mod": True,  # if the responsible mod should be revealed to the warned user
        "mute_role": None,  # the role used for mute
        "update_mute": True,  # if the bot should update perms of each new text channel/category
        "remove_roles": False,  # if the bot should remove all other roles on mute
        "respect_hierarchy": True,  # if the bot should check if the mod is allowed by hierarchy
        # TODO use bot settingfor respect_hierarchy ?
        "reinvite": True,  # if the bot should try to send an invite to an unbanned/kicked member
        "log_manual": True,  # if the bot should log manual kicks and bans
        "channels": {  # modlog channels
            "main": None,  # default
            "1": None,
            "2": None,
            "3": None,
            "4": None,
            "5": None,
        },
        "bandays": {  # the number of days of messages to delte in case of a ban/softban
            "softban": 7,
            "ban": 0,
        },
        "embed_description_modlog": {  # the description of each type of warn in modlog
            "1": EMBED_MODLOG(1),
            "2": EMBED_MODLOG(2),
            "3": EMBED_MODLOG(3),
            "4": EMBED_MODLOG(4),
            "5": EMBED_MODLOG(5),
        },
        "embed_description_user": {  # the description of each type of warn for the user
            "1": EMBED_USER(1),
            "2": EMBED_USER(2),
            "3": EMBED_USER(3),
            "4": EMBED_USER(4),
            "5": EMBED_USER(5),
        },
        "substitutions": {},
        "colors": {  # color bar of an embed
            "1": 0xF4AA42,
            "2": 0xD1ED35,
            "3": 0xED9735,
            "4": 0xED6F35,
            "5": 0xFF4C4C,
        },
        "url": None,  # URL set for the title of all embeds
        "temporary_warns": {},  # list of temporary warns (need to unmute/unban after some time)
        "automod": {  # everything related to auto moderation
            "enabled": False,
            "antispam": {
                "enabled": False,
                "max_messages": 5,  # maximum number of messages allowed within the delay
                "delay": 2,  # in seconds
                "delay_before_action": 60,  # if triggered twice within this delay, take action
                "warn": {  # data of the warn
                    "level": 1,
                    "reason": "Sending messages too fast!",
                    "time": None,
                },
                "whitelist": [],
            },
            "regex_edited_messages": False,  # if the bot should check message edits
            "regex": {},  # all regex expressions
            "warnings": [],  # all automatic warns
        },
    }
    default_custom_member = {"x": []}  # cannot set a list as base group

    def __init__(self, bot: "Grief"):
        self.bot = bot

        self.data = Config.get_conf(self, 260, force_registration=True)
        self.data.register_global(**self.default_global)
        self.data.register_guild(**self.default_guild)
        try:
            self.data.init_custom("MODLOGS", 2)
        except AttributeError:
            pass
        self.data.register_custom("MODLOGS", **self.default_custom_member)

        self.cache = MemoryCache(self.bot, self.data)
        self.api = API(self.bot, self.data, self.cache)

        self.task: asyncio.Task

    # helpers
    async def call_warn(
        self,
        ctx: commands.Context,
        level: int,
        member: discord.Member,
        reason: Optional[str] = None,
        time: Optional[timedelta] = None,
        ban_days: Optional[int] = None,
    ):
        """No need to repeat, let's do what's common to all 5 warnings."""
        reason = await self.api.format_reason(ctx.guild, reason)
        if reason and len(reason) > 2000:  # embed limits
            await ctx.send(
                _(
                    "The reason is too long for an embed.\n\n"
                    "*Tip: You can use Github Gist to write a long text formatted in Markdown, "
                    "create a new file with the extension `.md` at the end and write as if you "
                    "were on Discord.\n<https://gist.github.com/>*"
                    # I was paid $99999999 for this, you're welcome
                )
            )
            return
        try:
            fail = await self.api.warn(
                guild=ctx.guild,
                members=[member],
                author=ctx.author,
                level=level,
                reason=reason,
                time=time,
                ban_days=ban_days,
            )
            if fail:
                raise fail[0]
        except errors.MissingPermissions as e:
            await ctx.send(e)
        except errors.MemberTooHigh as e:
            await ctx.send(e)
        except errors.LostPermissions as e:
            await ctx.send(e)
        except errors.SuicidePrevention as e:
            await ctx.send(e)
        except errors.MissingMuteRole:
            await ctx.send(
                _(
                    "You need to set up the mute role before doing this.\n"
                    "Use the `[p]warnset mute` command for this."
                )
            )
        except errors.NotFound:
            await ctx.send(
                _(
                    "Please set up a modlog channel before warning a member.\n\n"
                    "**With WarnSystem**\n"
                    "*Use the `[p]warnset channel` command.*\n\n"
                    "**With Grief Modlog**\n"
                    "*Load the `modlogs` cog and use the `[p]modlogset modlog` command.*"
                )
            )
        except errors.NotAllowedByHierarchy:
            is_admin = mod.is_admin_or_superior(self.bot, member)
            await ctx.send(
                _(
                    "You are not allowed to do this, {member} is higher than you in the role "
                    "hierarchy. You can only warn members which top role is lower than yours.\n\n"
                ).format(member=str(member))
                + (
                    _("You can disable this check by using the `[p]warnset hierarchy` command.")
                    if is_admin
                    else ""
                )
            )
        except discord.errors.NotFound:
            await ctx.send(_("Hackban failed: No user found."))
        else:
            if ctx.channel.permissions_for(ctx.guild.me).add_reactions:
                try:
                    await ctx.message.add_reaction("✅")
                except discord.errors.NotFound:
                    # retrigger or scheduler probably executed the command
                    pass
            else:
                await ctx.send(_("Done."))

    async def call_masswarn(
        self,
        ctx: commands.Context,
        level: int,
        members: list[discord.Member],
        unavailable_members: list[UnavailableMember],
        log_modlog: bool,
        log_dm: bool,
        take_action: bool,
        reason: Optional[str] = None,
        time: Optional[timedelta] = None,
        confirm: bool = False,
    ):
        guild = ctx.guild
        message = None
        i = 0
        total_members = len(members)
        total_unavailable_members = len(unavailable_members)
        tick1 = "✅" if log_modlog else "❌"
        tick2 = "✅" if log_dm else "❌"
        tick3 = f"{'✅' if take_action else '❌'} Take action\n" if level != 1 else ""
        tick4 = f"{'✅' if time else '❌'} Time: " if (level == 2 or level == 5) else ""
        tick5 = "✅" if reason else "❌"
        time_str = (self.api._format_timedelta(time) + "\n") if time else ""

        async def update_count(count):
            nonlocal i
            i = count

        async def update_message():
            while True:
                nonlocal message
                content = _(
                    "Processing mass warning...\n"
                    "{i}/{total} {members} warned ({percent}%)\n\n"
                    "{tick1} Log to the modlog\n"
                    "{tick2} Send a DM to all members\n"
                    "{tick3}"
                    "{tick4} {time}\n"
                    "{tick5} Reason: {reason}"
                ).format(
                    i=i,
                    total=total_members + total_unavailable_members,
                    members=_("members") if i != 1 else _("member"),
                    percent=round((i / total_members) * 100, 2),
                    tick1=tick1,
                    tick2=tick2,
                    tick3=tick3,
                    tick4=tick4,
                    time=time_str,
                    tick5=tick5,
                    reason=reason or "Not set",
                )
                if message:
                    await message.edit(content=content)
                else:
                    message = await ctx.send(content)
                await asyncio.sleep(5)

        if unavailable_members and level < 5:
            await ctx.send(_("You can only use `--hackban-select` with a level 5 warn."))
            return
        reason = await self.api.format_reason(ctx.guild, reason)
        if (log_modlog or log_dm) and reason and len(reason) > 2000:  # embed limits
            await ctx.send(
                _(
                    "The reason is too long for an embed.\n\n"
                    "*Tip: You can use Github Gist to write a long text formatted in Markdown, "
                    "create a new file with the extension `.md` at the end and write as if you "
                    "were on Discord.\n<https://gist.github.com/>*"
                    # I was paid $99999999 for this, you're welcome
                )
            )
            return
        file = text_to_file(
            "\n".join([f"{str(x)} ({x.id})" for x in members + unavailable_members])
        )
        targets = []
        if members:
            targets.append(
                _("{total} {members} ({percent}% of the server)").format(
                    total=total_members,
                    members=_("members") if total_members > 1 else _("member"),
                    percent=round((total_members / len(guild.members) * 100), 2),
                )
            )
        if unavailable_members:
            targets.append(
                _("{total} {users} not in the server.").format(
                    total=total_unavailable_members,
                    users=_("users") if total_unavailable_members > 1 else _("user"),
                )
            )
        if not confirm:
            msg = await ctx.send(
                _(
                    "You're about to set a level {level} warning on {target}.\n\n"
                    "{tick1} Log to the modlog\n"
                    "{tick2} Send a DM to all members\n"
                    "{tick3}"
                    "{tick4} {time}\n"
                    "{tick5} Reason: {reason}\n\n{warning}"
                    "Continue?"
                ).format(
                    level=level,
                    target=_(" and ").join(targets),
                    tick1=tick1,
                    tick2=tick2,
                    tick3=tick3,
                    tick4=tick4,
                    time=time_str,
                    tick5=tick5,
                    reason=reason or _("Not set"),
                    warning=_(
                        ":warning: You're about to warn a lot of members! Avoid doing this to "
                        "prevent being rate limited by Discord, especially if you enabled DMs.\n\n"
                    )
                    if len(members) > 50 and level > 1
                    else "",
                ),
                file=file,
            )
            menus.start_adding_reactions(msg, predicates.ReactionPredicate.YES_OR_NO_EMOJIS)
            pred = predicates.ReactionPredicate.yes_or_no(msg, ctx.author)
            try:
                await self.bot.wait_for("reaction_add", check=pred, timeout=120)
            except AsyncTimeoutError:
                if ctx.guild.me.guild_permissions.manage_messages:
                    await msg.clear_reactions()
                else:
                    for reaction in msg.reactions():
                        await msg.remove_reaction(reaction, ctx.guild.me)
                return
            if not pred.result:
                await ctx.send(_("Mass warn cancelled."))
                return
            task = self.bot.loop.create_task(update_message())
        try:
            fails = await self.api.warn(
                guild=guild,
                members=members + unavailable_members,
                author=ctx.author,
                level=level,
                reason=reason,
                time=time,
                log_modlog=log_modlog,
                log_dm=log_dm,
                take_action=take_action,
                progress_tracker=update_count if not confirm else None,
            )
        except errors.MissingPermissions as e:
            await ctx.send(e)
        except errors.LostPermissions as e:
            await ctx.send(e)
        except errors.MissingMuteRole:
            if not confirm:
                await ctx.send(
                    _(
                        "You need to set up the mute role before doing this.\n"
                        "Use the `[p]warnset mute` command for this."
                    )
                )
        except errors.NotFound:
            if not confirm:
                await ctx.send(
                    _(
                        "Please set up a modlog channel before warning a member.\n\n"
                        "**With WarnSystem**\n"
                        "*Use the `[p]warnset channel` command.*\n\n"
                        "**With Grief Modlog**\n"
                        "*Load the `modlogs` cog and use the `[p]modlogset modlog` command.*"
                    )
                )
        else:
            if not confirm:
                if fails:
                    await ctx.send(
                        _("Done! {failed} {members} out of {total} couldn't be warned.").format(
                            failed=len(fails),
                            members=_("members") if len(fails) > 1 else _("member"),
                            total=total_members,
                        )
                    )
                else:
                    await ctx.send(
                        _("Done! {total} {members} successfully warned.").format(
                            total=total_members,
                            members=_("members") if total_members > 1 else _("member"),
                        )
                    )
            else:
                try:
                    await ctx.message.add_reaction("✅")
                except discord.errors.HTTPException:
                    pass
        finally:
            if not confirm:
                task.cancel()
            if message:
                await message.delete()

    # all warning commands
    @commands.group(invoke_without_command=True, name="warn")
    @checks.mod_or_permissions(administrator=True)
    @commands.guild_only()
    async def _warn(self, ctx: commands.Context, member: discord.Member, *, reason: str = None):
        """
        Take actions against a user and log it.
        The warned user will receive a DM.

        If not given, the warn level will be 1.
        """
        await self.call_warn(ctx, 1, member, reason)

    @commands.command()
    @commands.guild_only()
    @commands.cooldown(1, 3, commands.BucketType.member)
    async def warnings(
        self, ctx: commands.Context, user: Optional[UnavailableMember] = None, index: int = 0
    ):
        """
        Shows all warnings of a member.

        This command can be used by everyone, but only moderators can see other's warnings.
        Moderators can also edit or delete warnings by using the reactions.
        """
        if not user:
            await ctx.send_help()
            return
        if (
            not (
                await mod.is_mod_or_superior(self.bot, ctx.author)
                or ctx.author.guild_permissions.kick_members
            )
            and user != ctx.author
        ):
            await ctx.send(_("You are not allowed to see other's warnings!"))
            return
        cases = await self.api.get_all_cases(ctx.guild, user)
        if not cases:
            await ctx.send(_("That member was never warned."))
            return
        if 0 < index < len(cases):
            await ctx.send(_("That case doesn't exist."))
            return

        total = lambda level: len([x for x in cases if x["level"] == level])
        warning_str = lambda level, plural: {
            1: (_("Warning"), _("Warnings")),
            2: (_("Mute"), _("Mutes")),
            3: (_("Kick"), _("Kicks")),
            4: (_("Softban"), _("Softbans")),
            5: (_("Ban"), _("Bans")),
        }.get(level, _("unknown"))[1 if plural else 0]

        msg = []
        for i in range(6):
            total_warns = total(i)
            if total_warns > 0:
                msg.append(f"{warning_str(i, total_warns > 1)}: {total_warns}")
        warn_field = "\n".join(msg) if len(msg) > 1 else msg[0]
        embed = discord.Embed(description=_("User modlog summary."))
        embed.set_author(name=f"{user} | {user.id}", icon_url=user.display_avatar.url)
        embed.add_field(
            name=_("Total number of warnings: ") + str(len(cases)), value=warn_field, inline=False
        )
        embed.colour = discord.Colour.dark_theme

        paginator = WarningsSelector(ctx, user, cases)
        await paginator.start(embed=embed)

    @commands.command()
    @checks.mod_or_permissions(kick_members=True)
    @commands.cooldown(1, 10, commands.BucketType.channel)
    async def warnlist(self, ctx: commands.Context, short: bool = False):
        """
        List the latest warnings issued on the server.
        """
        guild = ctx.guild
        full_text = ""
        warns = await self.api.get_all_cases(guild)
        if not warns:
            await ctx.send(_("No warnings have been issued in this server yet."))
            return
        for i, warn in enumerate(warns, start=1):
            text = _(
                "--- Case {number} ---\n"
                "Member:    {member} (ID: {member.id})\n"
                "Level:     {level}\n"
                "Reason:    {reason}\n"
                "Author:    {author} (ID: {author.id})\n"
                "Date:      {time}\n"
            ).format(number=i, **warn)
            if warn["duration"]:
                duration = self.api._get_timedelta(warn["duration"])
                text += _("Duration:  {duration}\nUntil:     {until}\n").format(
                    duration=self.api._format_timedelta(duration),
                    until=self.api._format_datetime(warn["time"] + duration),
                )
            text += "\n\n"
            full_text = text + full_text
        pages = [
            x for x in pagify(full_text, delims=["\n\n", "\n"], priority=True, page_length=1900)
        ]
        total_pages = len(pages)
        total_warns = len(warns)
        pages = [
            f"```yml\n{x}```\n"
            + _("{total} warnings. Page {i}/{pages}").format(
                total=total_warns, i=i, pages=total_pages
            )
            for i, x in enumerate(pages, start=1)
        ]
        await menus.menu(ctx=ctx, pages=pages, controls=menus.DEFAULT_CONTROLS, timeout=60)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        guild = after.guild
        mute_role = guild.get_role(await self.cache.get_mute_role(guild))
        if not mute_role:
            return
        if not (mute_role in before.roles and mute_role not in after.roles):
            return
        if after.id in self.cache.temp_actions:
            await self.cache.remove_temp_action(guild, after)
            log.info(
                f"[Guild {guild.id}] The temporary mute of member {after} (ID: {after.id}) "
                "was ended due to a manual unmute (role removed)."
            )

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        guild = channel.guild
        if isinstance(channel, discord.VoiceChannel):
            return
        if not await self.data.guild(guild).update_mute():
            return
        role = guild.get_role(await self.cache.get_mute_role(guild))
        if not role:
            return
        try:
            await channel.set_permissions(
                role,
                send_messages=False,
                add_reactions=False,
                reason=_(
                    "Updating channel settings so the mute role will work here. "
                    "Disable the auto-update with [p]warnset autoupdate"
                ),
            )
        except discord.errors.Forbidden:
            log.warn(
                f"[Guild {guild.id}] Couldn't update permissions of new channel {channel.name} "
                f"(ID: {channel.id}) due to a permission error."
            )
        except discord.errors.HTTPException as e:
            log.error(
                f"[Guild {guild.id}] Couldn't update permissions of new channel {channel.name} "
                f"(ID: {channel.id}) due to an unknown error.",
                exc_info=e,
            )

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, member: discord.Member):
        await self.on_manual_action(guild, member, 5)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        await self.on_manual_action(member.guild, member, 3)

    async def on_manual_action(self, guild: discord.Guild, member: discord.Member, level: int):
        # most of this code is from Cog-Creators, modlog cog
        # https://github.com/Cog-Creators/Grief-DiscordBot/blob/bc21f779762ec9f460aecae525fdcd634f6c2d85/redbot/core/modlog.py#L68
        if not guild.me.guild_permissions.view_audit_log:
            return
        if not await self.data.guild(guild).log_manual():
            return
        # check for that before doing anything else, means WarnSystem isn't setup
        try:
            await self.api.get_modlog_channel(guild, level)
        except errors.NotFound:
            return
        when = datetime.now(timezone.utc)
        before = when + timedelta(minutes=1)
        after = when - timedelta(minutes=1)
        await asyncio.sleep(10)  # prevent small delays from causing a 5 minute delay on entry
        attempts = 0
        action = {
            3: discord.AuditLogAction.kick,
            5: discord.AuditLogAction.ban,
        }[level]
        # wait up to 15 min to find a matching case
        while attempts < 3:
            attempts += 1
            try:
                entry = await guild.audit_logs(action=action, before=before, after=after).find(
                    lambda e: e.target.id == member.id and after < e.created_at < before
                )
            except discord.Forbidden:
                break
            except discord.HTTPException:
                pass
            else:
                if entry:
                    if entry.user.id != guild.me.id:
                        # Don't create modlog entires for the bot's own bans, cogs do this.
                        mod, reason, date = entry.user, entry.reason, entry.created_at
                        if isinstance(member, discord.User):
                            member = UnavailableMember(self.bot, guild._state, member.id)
                        try:
                            await self.api.warn(
                                guild,
                                [member],
                                mod,
                                level,
                                reason,
                                date=date,
                                log_dm=True if level <= 2 else False,
                                take_action=False,
                            )
                        except Exception as e:
                            log.error(
                                f"[Guild {guild.id}] Failed to create a case "
                                "based on manual action. "
                                f"Member: {member} ({member.id}). Author: {mod} ({mod.id}). "
                                f"Reason: {reason}",
                                exc_info=e,
                            )
                    return
            await asyncio.sleep(300)

    def cog_unload(self):
        log.debug("Unloading cog...")

        # stop checking for unmute and unban
        self.task.cancel()
        self.api.disable_automod()
        self.api.re_pool.close()
