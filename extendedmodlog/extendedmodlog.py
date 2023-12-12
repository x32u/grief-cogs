import asyncio
import logging
from typing import Union

import discord
from grief.core import Config, checks, commands
from grief.core.i18n import Translator, cog_i18n
from grief.core.utils.chat_formatting import humanize_list
### FROM REACTLOG
import logging
import re
from grief.core import Config, app_commands, commands
from grief.core.bot import Grief
from grief.core.utils.chat_formatting import humanize_list

from .eventmixin import EventChooser, EventMixin
from .settings import inv_settings

_ = Translator("ExtendedModLog", __file__)
logger = logging.getLogger("grief.extendedmodlog")


@cog_i18n(_)
class ExtendedModLog(EventMixin, commands.Cog):
    """Extended modlogs"""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, 154457677895, force_registration=True)
        self.config.register_guild(**inv_settings, blacklist=[],
            channel=None,
            ignored=[],
            log_all=False,
            react_add=False,
            react_remove=False,)
        self.config.register_global(version="0.0.0")
        self.settings = {}
        self._ban_cache = {}
        self.invite_links_loop.start()
        self.allowed_mentions = discord.AllowedMentions(users=False, roles=False, everyone=False)

    async def cog_unload(self):
        self.invite_links_loop.stop()

    async def initialize(self) -> None:
        all_data = await self.config.all_guilds()
        for guild_id, data in all_data.items():
            guild = discord.Object(id=guild_id)
            for entry, default in inv_settings.items():
                if entry not in data:
                    all_data[guild_id][entry] = inv_settings[entry]
                if type(default) == dict:

                    for key, _default in inv_settings[entry].items():
                        if not isinstance(all_data[guild_id][entry], dict):
                            all_data[guild_id][entry] = default
                        try:
                            if key not in all_data[guild_id][entry]:
                                all_data[guild_id][entry][key] = _default
                        except TypeError:
                            # del all_data[guild_id][entry]
                            logger.error("Somehow your dict was invalid.")
                            continue
        self.settings = all_data

    async def modlog_settings(self, ctx: commands.Context) -> None:
        guild = ctx.message.guild
        cur_settings = {
            "message_edit": _("Message edits"),
            "message_delete": _("Message delete"),
            "user_change": _("Member changes"),
            "role_change": _("Role changes"),
            "role_create": _("Role created"),
            "role_delete": _("Role deleted"),
            "voice_change": _("Voice changes"),
            "user_join": _("Member join"),
            "user_left": _("Member left"),
            "channel_change": _("Channel changes"),
            "channel_create": _("Channel created"),
            "channel_delete": _("Channel deleted"),
            "guild_change": _("Guild changes"),
            "emoji_change": _("Emoji changes"),
            "stickers_change": _("Stickers changes"),
            "invite_created": _("Invite created"),
            "invite_deleted": _("Invite deleted"),
            "thread_create": _("Thread created"),
            "thread_delete": _("Thread deleted"),
            "thread_change": _("Thread changed"),
        }
        if guild.id not in self.settings:
            self.settings[guild.id] = inv_settings

        data = self.settings[guild.id]
        ign_chans = data["ignored_channels"]
        ignored_channels = []
        for c in ign_chans:
            chn = guild.get_channel(c)
            if chn is None:
                # a bit of automatic cleanup so things don't break
                data["ignored_channels"].remove(c)
            else:
                ignored_channels.append(chn)
        enabled = ""
        disabled = ""
        for settings, name in cur_settings.items():
            msg += f"{name}: **{data[settings]['enabled']}**"
            if settings == "":
                msg += "\n" + humanize_list(data[settings]["privs"])
            if data[settings]["channel"]:
                chn = guild.get_channel(data[settings]["channel"])
                if chn is None:
                    # a bit of automatic cleanup so things don't break
                    data[settings]["channel"] = None
                else:
                    msg += f" {chn.mention}\n"
            else:
                msg += "\n"

        if enabled == "":
            enabled = _("None  ")
        if disabled == "":
            disabled = _("None  ")
        if ignored_channels:
            chans = ", ".join(c.mention for c in ignored_channels)
            msg += _("Ignored Channels") + ": " + chans
        await self.config.guild(ctx.guild).set(data)
        # save the data back to config incase we had some deleted channels
        await ctx.maybe_send_embed(msg)

    @commands.has_permissions(manage_channels=True)
    @commands.group(name="modlog", aliases=["modlogtoggle", "modlogs"])
    @commands.guild_only()
    async def _modlog(self, ctx: commands.Context) -> None:
        """
        Toggle various extended modlog notifications

        Can be sent to separate channels with `[p]modlog channel #channel event_name`
        """
        pass

    @_modlog.command(name="settings")
    async def _show_modlog_settings(self, ctx: commands.Context):
        """
        Show the servers current ExtendedModlog settings
        """
        if ctx.guild.id not in self.settings:
            self.settings[ctx.guild.id] = inv_settings
        if await self.config.guild(ctx.message.guild).all() == {}:
            await self.config.guild(ctx.message.guild).set(inv_settings)
        await self.modlog_settings(ctx)

    @_modlog.command(name="toggle")
    async def _set_event_on_or_off(
        self,
        ctx: commands.Context,
        true_or_false: bool,
        *events: EventChooser,
    ) -> None:
        """
        Turn on and off specific modlog actions

        `<true_or_false>` Either on or off.

        `[events...]` must be any of the following options (more than one event can be provided at once):
            `channel_change` - Updates to channel name, etc.
            `channel_create` - Log created channels.
            `channel_delete` - Log deleted channels.
            `emoji_change`   - Emojis added or deleted.
            `guild_change`   - Server settings changed.
            `message_edit`   - Log edited messages.
            `message_delete` - Log deleted messages.
            `member_change`  - Member changes like roles added/removed and nicknames.
            `role_change`    - Role updates like permissions.
            `role_create`    - Log created roles.
            `role_delete`    - Log deleted roles.
            `voice_change`   - Voice channel join/leave.
            `member_join`    - Log member joins.
            `member_left`    - Log member leaves.
            `invite_created` - Log creation of invites
            `invite_deleted` - Log deletion of invites.
            `thread_create`  - Log thread creations.
            `thread_delete`  - Log thread deletions.
            `thread_change`  - Log sticker changes.
            `stickers_change` - Log sticker changes.
        """
        if len(events) == 0:
            return await ctx.send(_("You must provide which events should be included."))
        if ctx.guild.id not in self.settings:
            self.settings[ctx.guild.id] = inv_settings
        for event in events:
            self.settings[ctx.guild.id][event]["enabled"] = true_or_false
            await self.config.guild(ctx.guild).set_raw(
                event, value=self.settings[ctx.guild.id][event]
            )
        await ctx.send(
            _("{event} logs have been set to {true_or_false}").format(
                event=humanize_list([e.replace("user_", "member_") for e in events]),
                true_or_false=str(true_or_false),
            )
        )

    @_modlog.command(name="channel")
    async def _set_event_channel(
        self,
        ctx: commands.Context,
        channel: discord.TextChannel,
        *events: EventChooser,
    ) -> None:
        """
        Set the channel for modlogs.

        `<channel>` The text channel to send the events to.

        `[events...]` must be any of the following options (more than one event can be provided at once):
            `channel_change` 
            `channel_create`
            `channel_delete`
            `emoji_change`  
            `guild_change`  
            `message_edit`
            `message_delete`
            `member_change` 
            `role_change`   
            `role_create`
            `role_delete`
            `voice_change`
            `member_join`
            `member_left`
            `invite_created`
            `invite_deleted`
            `thread_create`
            `thread_delete`
            `thread_change`
            `stickers_change`
        """
        if len(events) == 0:
            return await ctx.send(_("You must provide which events should be included."))
        if ctx.guild.id not in self.settings:
            self.settings[ctx.guild.id] = inv_settings
        for event in events:
            self.settings[ctx.guild.id][event]["channel"] = channel.id
            await self.config.guild(ctx.guild).set_raw(
                event, value=self.settings[ctx.guild.id][event]
            )
        await ctx.send(
            _("{event} logs have been set to {channel}").format(
                event=humanize_list([e.replace("user_", "member_") for e in events]),
                channel=channel.mention,
            )
        )

    @_modlog.command(name="resetchannel")
    async def _reset_event_channel(
        self,
        ctx: commands.Context,
        *events: EventChooser,
    ) -> None:
        """
        Reset the modlog event to the default modlog channel.

        `[events...]` must be any of the following options (more than one event can be provided at once):
            `channel_change` - Updates to channel name, etc.
            `channel_create` - Log created channels.
            `channel_delete` - Log deleted channels.
            `emoji_change`   - Emojis added or deleted.
            `guild_change`   - Server settings changed.
            `message_edit`   - Log edited messages.
            `message_delete` - Log deleted messages.
            `member_change`  - Member changes like roles added/removed and nicknames.
            `role_change`    - Role updates like permissions.
            `role_create`    - Log created roles.
            `role_delete`    - Log deleted roles.
            `voice_change`   - Voice channel join/leave.
            `member_join`    - Log member joins.
            `member_left`    - Log member leaves.
            `invite_created` - Log creation of invites
            `invite_deleted` - Log deletion of invites.
            `thread_create`  - Log thread creations.
            `thread_delete`  - Log thread deletions.
            `thread_change`  - Log sticker changes.
            `stickers_change` - Log sticker changes.
        """
        if len(events) == 0:
            return await ctx.send(_("You must provide which events should be included."))
        if ctx.guild.id not in self.settings:
            self.settings[ctx.guild.id] = inv_settings
        for event in events:
            self.settings[ctx.guild.id][event]["channel"] = None
            await self.config.guild(ctx.guild).set_raw(
                event, value=self.settings[ctx.guild.id][event]
            )
        await ctx.send(
            _("{event} logs channel have been reset.").format(event=humanize_list(events))
        )

    @_modlog.command(name="all", aliaes=["all_settings", "toggle_all"])
    async def _toggle_all_logs(self, ctx: commands.Context, true_or_false: bool) -> None:
        """
        Turn all logging options on or off

        `<true_or_false>` what to set all logging settings to must be `true`, `false`, `yes`, `no`.
        """
        if ctx.guild.id not in self.settings:
            self.settings[ctx.guild.id] = inv_settings
        for setting in inv_settings.keys():
            if "enabled" in self.settings[ctx.guild.id][setting]:
                self.settings[ctx.guild.id][setting]["enabled"] = true_or_false
        await self.config.guild(ctx.guild).set(self.settings[ctx.guild.id])
        await self.modlog_settings(ctx)

    @_modlog.command(name="botedits", aliases=["botedit"])
    async def _edit_toggle_bots(self, ctx: commands.Context) -> None:
        """
        Toggle message edit notifications for bot users
        """
        if ctx.guild.id not in self.settings:
            self.settings[ctx.guild.id] = inv_settings
        guild = ctx.message.guild
        msg = _("Bots edited messages ")
        if not await self.config.guild(guild).message_edit.bots():
            await self.config.guild(guild).message_edit.bots.set(True)
            self.settings[guild.id]["message_edit"]["bots"] = True
            verb = _("enabled")
        else:
            await self.config.guild(guild).message_edit.bots.set(False)
            self.settings[guild.id]["message_edit"]["bots"] = False
            verb = _("disabled")
        await ctx.send(msg + verb)

    @_modlog.command(name="botdeletes", aliases=["botdelete"])
    async def _delete_bots(self, ctx: commands.Context) -> None:
        """
        Toggle message delete notifications for bot users

        This will not affect delete notifications for messages that aren't in bot's cache.
        """
        if ctx.guild.id not in self.settings:
            self.settings[ctx.guild.id] = inv_settings
        guild = ctx.message.guild
        msg = _("Bot delete logs ")
        if not await self.config.guild(guild).message_delete.bots():
            await self.config.guild(guild).message_delete.bots.set(True)
            self.settings[ctx.guild.id]["message_delete"]["bots"] = True
            verb = _("enabled")
        else:
            await self.config.guild(guild).message_delete.bots.set(False)
            self.settings[ctx.guild.id]["message_delete"]["bots"] = False
            verb = _("disabled")
        await ctx.send(msg + verb)

    @_modlog.group(name="delete")
    async def _delete(self, ctx: commands.Context) -> None:
        """
        Delete logging settings
        """
        pass

    @_delete.command(name="bulkdelete")
    async def _delete_bulk_toggle(self, ctx: commands.Context) -> None:
        """
        Toggle bulk message delete notifications
        """
        if ctx.guild.id not in self.settings:
            self.settings[ctx.guild.id] = inv_settings
        guild = ctx.message.guild
        msg = _("Bulk message delete logs ")
        if not await self.config.guild(guild).message_delete.bulk_enabled():
            await self.config.guild(guild).message_delete.bulk_enabled.set(True)
            self.settings[ctx.guild.id]["message_delete"]["bulk_enabled"] = True
            verb = _("enabled")
        else:
            await self.config.guild(guild).message_delete.bulk_enabled.set(False)
            self.settings[ctx.guild.id]["message_delete"]["bulk_enabled"] = False
            verb = _("disabled")
        await ctx.send(msg + verb)

    @_delete.command(name="individual")
    async def _delete_bulk_individual(self, ctx: commands.Context) -> None:
        """
        Toggle individual message delete notifications for bulk message delete
        """
        if ctx.guild.id not in self.settings:
            self.settings[ctx.guild.id] = inv_settings
        guild = ctx.message.guild
        msg = _("Individual message delete logs for bulk message delete ")
        if not await self.config.guild(guild).message_delete.bulk_individual():
            await self.config.guild(guild).message_delete.bulk_individual.set(True)
            self.settings[ctx.guild.id]["message_delete"]["bulk_individual"] = True
            verb = _("enabled")
        else:
            await self.config.guild(guild).message_delete.bulk_individual.set(False)
            self.settings[ctx.guild.id]["message_delete"]["bulk_individual"] = False
            verb = _("disabled")
        await ctx.send(msg + verb)

    @_delete.command(name="cachedonly")
    async def _delete_cachedonly(self, ctx: commands.Context) -> None:
        """
        Toggle message delete notifications for non-cached messages

        Delete notifications for non-cached messages
        will only show channel info without content of deleted message or its author.
        """
        if ctx.guild.id not in self.settings:
            self.settings[ctx.guild.id] = inv_settings
        guild = ctx.message.guild
        msg = _("Delete logs for non-cached messages ")
        if not await self.config.guild(guild).message_delete.cached_only():
            await self.config.guild(guild).message_delete.cached_only.set(True)
            self.settings[ctx.guild.id]["message_delete"]["cached_only"] = True
            verb = _("disabled")
        else:
            await self.config.guild(guild).message_delete.cached_only.set(False)
            self.settings[ctx.guild.id]["message_delete"]["cached_only"] = False
            verb = _("enabled")
        await ctx.send(msg + verb)

    @_modlog.command(name="botchange")
    async def _user_bot_logging(self, ctx: commands.Context) -> None:
        """
        Toggle bots from being logged in user updates

        This includes roles and nickname.
        """
        if ctx.guild.id not in self.settings:
            self.settings[ctx.guild.id] = inv_settings
        setting = self.settings[ctx.guild.id]["user_change"]["bots"]
        self.settings[ctx.guild.id]["user_change"]["bots"] = not setting
        await self.config.guild(ctx.guild).user_change.bots.set(not setting)
        if setting:
            await ctx.send(_("Bots will no longer be tracked in user change logs."))
        else:
            await ctx.send(_("Bots will be tracked in user change logs."))

    @_modlog.command(name="botvoice")
    async def _user_bot_voice_logging(self, ctx: commands.Context) -> None:
        """
        Toggle bots from being logged in voice state updates
        """
        if ctx.guild.id not in self.settings:
            self.settings[ctx.guild.id] = inv_settings
        setting = self.settings[ctx.guild.id]["voice_change"]["bots"]
        self.settings[ctx.guild.id]["voice_change"]["bots"] = not setting
        await self.config.guild(ctx.guild).voice_change.bots.set(not setting)
        if setting:
            await ctx.send(_("Bots will no longer be tracked in voice update logs."))
        else:
            await ctx.send(_("Bots will be tracked in voice update logs."))

    @_modlog.command(name="nickname", aliases=["nicknames"])
    async def _user_nickname_logging(self, ctx: commands.Context) -> None:
        """
        Toggle nickname updates for user changes
        """
        if ctx.guild.id not in self.settings:
            self.settings[ctx.guild.id] = inv_settings
        setting = self.settings[ctx.guild.id]["user_change"]["nicknames"]
        self.settings[ctx.guild.id]["user_change"]["nicknames"] = not setting
        await self.config.guild(ctx.guild).user_change.nicknames.set(not setting)
        if setting:
            await ctx.send(_("Nicknames will no longer be tracked in user change logs."))
        else:
            await ctx.send(_("Nicknames will be tracked in user change logs."))

    @_modlog.command()
    async def ignore(
        self,
        ctx: commands.Context,
        channel: Union[discord.TextChannel, discord.CategoryChannel, discord.VoiceChannel],
    ) -> None:
        """
        Ignore a channel from message delete/edit events and bot commands

        `channel` the channel or category to ignore events in
        """
        if ctx.guild.id not in self.settings:
            self.settings[ctx.guild.id] = inv_settings
        guild = ctx.message.guild
        if channel is None:
            channel = ctx.channel
        cur_ignored = await self.config.guild(guild).ignored_channels()
        if channel.id not in cur_ignored:
            cur_ignored.append(channel.id)
            await self.config.guild(guild).ignored_channels.set(cur_ignored)
            self.settings[guild.id]["ignored_channels"] = cur_ignored
            await ctx.send(_(" Now ignoring events in ") + channel.mention)
        else:
            await ctx.send(channel.mention + _(" is already being ignored."))

    @_modlog.command()
    async def unignore(
        self,
        ctx: commands.Context,
        channel: Union[discord.TextChannel, discord.CategoryChannel, discord.VoiceChannel],
    ) -> None:
        """
        Unignore a channel from message delete/edit events and bot commands

        `channel` the channel to unignore message delete/edit events
        """
        if ctx.guild.id not in self.settings:
            self.settings[ctx.guild.id] = inv_settings
        guild = ctx.message.guild
        if channel is None:
            channel = ctx.channel
        cur_ignored = await self.config.guild(guild).ignored_channels()
        if channel.id in cur_ignored:
            cur_ignored.remove(channel.id)
            await self.config.guild(guild).ignored_channels.set(cur_ignored)
            self.settings[guild.id]["ignored_channels"] = cur_ignored
            await ctx.send(_(" Now tracking events in ") + channel.mention)
        else:
            await ctx.send(channel.mention + _(" is not being ignored."))

    @_modlog.command()
    async def explain(self, ctx: commands.Context):
        """Explanation of the events grief supports."""

        msg = """
            **Events:**\n
            **message_edit:** Message edits
            **message_delete:** Message delete
            **user_change:** Member changes
            **role_change:** Role changes
            **role_create:** Role created
            **role_delete:** Role deleted
            **voice_change:** Voice changes
            **user_join:** Member join
            **user_left:** Member left
            **channel_change:** Channel changes
            **channel_create:** Channel created
            **channel_delete:** Channel deleted
            **guild_change:** Guild changes
            **emoji_change:** Emoji changes
            **stickers_change:** Stickers changes
            **invite_created:** Invite created
            **invite_deleted:** Invite deleted
            **thread_create:** Thread created
            **thread_delete:** Thread deleted
            **thread_change:** Thread changed\n
            **You can run multiple events at once to configure multiple events to the same channel.**\n
            **Note: run {prefix}modlogset to configure moderation logs.**""".format(
            prefix=ctx.clean_prefix
        )
        embed = discord.Embed(
            title="ExtendedModLog Events", description=msg, color=await ctx.embed_color()
        )
        await ctx.send(embed=embed)


    ### FROM REACTLOG
    @commands.has_permissions(manage_guild=True)
    @commands.guild_only()
    @commands.hybrid_group(aliases=["reactionlog"])
    async def reactlog(self, ctx: commands.Context):
        """Reaction logging configuration commands."""
        pass

    @reactlog.command()
    @app_commands.describe(channel="The channel to log reactions to.")
    async def channel(self, ctx: commands.Context, channel: discord.TextChannel = None):
        """Set the reactions logging channel."""
        if not channel:
            await self.config.guild(ctx.guild).channel.clear()
            await ctx.send("Reaction logging channel has been unset.")
            return
        if not ctx.channel.permissions_for(channel.guild.me).send_messages:
            await ctx.send("Please grant me permission to send message in that channel first.")
            return
        await self.config.guild(ctx.guild).channel.set(channel.id)
        await ctx.send(f"Reaction logging channel has been set to: {channel.mention}")

    @reactlog.command()
    @app_commands.describe(toggle="True or False")
    async def reactadd(self, ctx: commands.Context, toggle: bool = None):
        """Enable/disable logging when reactions added."""
        current = await self.config.guild(ctx.guild).react_add()
        if toggle is None:
            await self.config.guild(ctx.guild).react_add.set(not current)
        else:
            await self.config.guild(ctx.guild).react_add.set(toggle)

        if await self.config.guild(ctx.guild).react_add():
            await ctx.send("I will log when reactions added.")
            return
        await ctx.send("I won't log when reactions added.")

    @reactlog.command()
    @app_commands.describe(toggle="True or False")
    async def reactdel(self, ctx: commands.Context, toggle: bool = None):
        """Enable/disable logging when reactions removed."""
        current = await self.config.guild(ctx.guild).react_remove()
        if toggle is None:
            await self.config.guild(ctx.guild).react_remove.set(not current)
        else:
            await self.config.guild(ctx.guild).react_remove.set(toggle)

        if await self.config.guild(ctx.guild).react_remove():
            await ctx.send("I will log when reactions removed.")
            return
        await ctx.send("I won't log when reactions removed.")

    @reactlog.command()
    async def settings(self, ctx: commands.Context):
        """Show current reaction log settings."""
        channel = await self.config.guild(ctx.guild).channel()
        if channel:
            channel_mention = self.bot.get_channel(channel).mention
        else:
            channel_mention = "Not Set"
        react_add_status = await self.config.guild(ctx.guild).react_add()
        react_remove_status = await self.config.guild(ctx.guild).react_remove()
        log_all_status = await self.config.guild(ctx.guild).log_all()
        if await ctx.embed_requested():
            embed = discord.Embed(title="Reaction Log Settings", color=await ctx.embed_color())
            embed.add_field(name="Log On Reaction Add?", value=react_add_status, inline=True)
            embed.add_field(name="Log On Reaction Remove?", value=react_remove_status, inline=True)
            embed.add_field(name="Channel", value=channel_mention, inline=True)
            embed.set_footer(text=ctx.guild.name, icon_url=getattr(ctx.guild.icon, "url", None))
            await ctx.send(embed=embed)
        else:
            await ctx.send(
                f"**Reaction Log Settings for {ctx.guild.name}**\n"
                f"Channel: {channel_mention}\n"
                f"Log On Reaction Add: {react_add_status}\n"
                f"Log On Reaction Remove: {react_remove_status}\n"
            )

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.Member):
        message = reaction.message
        if not message.guild:
            return
        if not await self.channel_check(message.guild):
            return
        if not await self.config.guild(message.guild).react_add():
            return
        log_all = await self.config.guild(message.guild).log_all()
        if not log_all and reaction.count != 1:
            return
        await self.send_to_log(message, str(reaction.emoji), user, True)

    @commands.Cog.listener()
    async def on_reaction_remove(self, reaction: discord.Reaction, user: discord.Member):
        message = reaction.message
        if not message.guild:
            return
        if not await self.channel_check(message.guild):
            return
        if not await self.config.guild(message.guild).react_remove():
            return
        log_all = await self.config.guild(message.guild).log_all()
        if not log_all and reaction.count != 0:
            return
        await self.send_to_log(message, str(reaction.emoji), user, False)

    async def channel_check(self, guild: discord.Guild) -> bool:
        if not (channel := await self.config.guild(guild).channel()):
            return False
        if not self.bot.get_channel(channel):
            log.info(f"Channel with ID {channel} not found in {guild} (ID: {guild.id}), ignoring.")
            return False
        return True

    async def send_to_log(
        self, message: discord.Message, emoji: str, user: discord.Member, added: bool
    ) -> discord.Message:
        if user.bot:
            return
        channel_id = await self.config.guild(message.guild).channel()
        if not channel_id:
            return

        # https://github.com/Rapptz/discord.py/blob/462ba84809/discord/ext/commands/converter.py#L700
        match = re.match(r"<a?:([a-zA-Z0-9\_]{1,32}):([0-9]{15,20})>$", emoji)
        if match:
            description = (
                f"**Channel:** {message.channel.mention}\n"
                f"**Emoji:** {match.group(1)} (ID: {match.group(2)})\n"
                f"**Message:** [Jump to Message ►]({message.jump_url})"
            )
            url = f"https://cdn.discordapp.com/emojis/{match.group(2)}"
            url += ".gif" if emoji.startswith("<a") else ".png"
        else:  # Default Emoji
            description = (
                f"**Channel:** {message.channel.mention}\n"
                f"**Emoji:** {emoji.strip(':')}\n"
                f"**Message:** [Jump to Message ►]({message.jump_url})"
            )
            # https://github.com/flapjax/FlapJack-Cogs/blob/red-v3-rewrites/bigmoji/bigmoji.py#L69-L93
            chars = [str(hex(ord(c)))[2:] for c in emoji]
            if len(chars) == 2:
                if "fe0f" in chars:
                    chars.remove("fe0f")
            if "20e3" in chars:
                chars.remove("fe0f")
            url = f"https://twemoji.maxcdn.com/v/14.0.2/72x72/{'-'.join(chars)}.png"
        color = discord.Color.dark_theme()
        embed = discord.Embed(
            description=description, color=color, timestamp=discord.utils.utcnow()
        )
        embed.set_author(name=f"{user} ({user.id})", icon_url=user.display_avatar.url)
        embed.set_thumbnail(url=url)
        added_or_removed = "Added" if added else "Removed"
        embed.set_footer(text=f"Reaction {added_or_removed} | #{message.channel.name}")

        log_channel = self.bot.get_channel(channel_id)
        await log_channel.send(embed=embed)
