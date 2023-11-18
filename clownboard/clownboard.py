import asyncio
import logging
from datetime import timedelta
from typing import Dict, Optional, Union

import discord
from grief.core import Config, checks, commands
from grief.core.i18n import Translator, cog_i18n
from grief.core.utils.chat_formatting import humanize_timedelta, pagify

from .converters import RealEmoji, clownboardExists
from .events import clownboardEvents
from .menus import BaseMenu, clownboardPages
from .clownboard_entry import FakePayload, clownboardEntry

_ = Translator("clownboard", __file__)
log = logging.getLogger("grief.clownboard")

TimeConverter = commands.converter.TimedeltaConverter(
    minimum=timedelta(days=7), allowed_units=["days", "weeks"], default_unit="days"
)


@cog_i18n(_)
class clownboard(clownboardEvents, commands.Cog):
    """
    Create a clownboard to pin those special comments indefinitely.
    """

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, 356488795)
        self.config.register_global(purge_time=None)
        self.config.register_guild(clownboards={})
        self.clownboards: Dict[int, Dict[str, clownboardEntry]] = {}
        self.ready = asyncio.Event()
        self.cleanup_loop: Optional[asyncio.Task] = None

    async def cog_load(self) -> None:
        log.debug("Started building clownboards cache from config.")
        for guild_id in await self.config.all_guilds():
            self.clownboards[guild_id] = {}
            all_data = await self.config.guild_from_id(int(guild_id)).clownboards()
            for name, data in all_data.items():
                try:
                    clownboard = await clownboardEntry.from_json(data, guild_id)
                except Exception:
                    log.exception("error converting clownboard")
                self.clownboards[guild_id][name] = clownboard

        self.cleanup_loop = asyncio.create_task(self.cleanup_old_messages())
        self.ready.set()
        log.debug("Done building clownboards cache from config.")

    async def cog_unload(self) -> None:
        self.ready.clear()
        self.init_task.cancel()
        if self.cleanup_loop:
            self.cleanup_loop.cancel()

    async def cog_check(self, ctx: commands.Context) -> bool:
        return self.ready.is_set()

    @commands.group()
    @commands.has_permissions(manage_channels=True)
    @commands.guild_only()
    async def clownboard(self, ctx: commands.Context) -> None:
        """
        Commands for managing the clownboard
        """

    @clownboard.command(name="purge")
    @commands.is_owner()
    async def purge_threshold(
        self, ctx: commands.Context, *, time: TimeConverter = timedelta(seconds=0)
    ) -> None:
        """
        Define how long to keep message ID's for every clownboard

        `<time>` is the number of days or weeks you want to keep clownboard messages for.

        e.g. `[p]clownboard purge 2 weeks`
        """
        if time.total_seconds() < 1:
            await self.config.purge_time.clear()
            await ctx.send(_("I will now keep message ID's indefinitely."))
            return
        await self.config.purge_time.set(int(time.total_seconds()))
        await ctx.send(
            _(
                "I will now prun messages that are {time} "
                "old or more every 24 hours.\n"
                "This will take effect after the next reload."
            ).format(time=humanize_timedelta(timedelta=time))
        )

    @clownboard.command(name="info")
    @commands.bot_has_permissions(read_message_history=True, embed_links=True)
    async def clownboard_info(self, ctx: commands.Context) -> None:
        """
        Display info on clownboards setup on the server.
        """
        guild = ctx.guild
        await ctx.typing()
        if guild.id in self.clownboards:
            await BaseMenu(source=clownboardPages(list(self.clownboards[guild.id].values()))).start(
                ctx=ctx
            )

    @clownboard.command(name="create", aliases=["add"])
    async def setup_clownboard(
        self,
        ctx: commands.Context,
        name: str,
        channel: Optional[discord.TextChannel] = None,
        emoji: RealEmoji = "⭐",
    ) -> None:
        """
        Create a clownboard on this server

        `<name>` is the name for the clownboard and will be lowercase only
        `[channel]` is the channel where posts will be made defaults to current channel
        `[emoji=⭐]` is the emoji that will be used to add to the clownboard defaults to ⭐
        """
        guild = ctx.message.guild
        name = name.lower()
        if channel is None:
            channel = ctx.message.channel
        if type(emoji) == discord.Emoji:
            if emoji not in guild.emojis:
                await ctx.send(_("That emoji is not on this guild!"))
                return
        if not channel.permissions_for(guild.me).send_messages:
            send_perms = _("I don't have permission to post in ")

            await ctx.send(send_perms + channel.mention)
            return

        if not channel.permissions_for(guild.me).embed_links:
            embed_perms = _("I don't have permission to embed links in ")
            await ctx.send(embed_perms + channel.mention)
            return
        if guild.id not in self.clownboards:
            self.clownboards[guild.id] = {}
        clownboards = self.clownboards[guild.id]
        if name in clownboards:
            await ctx.send(_("{name} clownboard name is already being used").format(name=name))
            return
        clownboard = clownboardEntry(name=name, channel=channel.id, emoji=str(emoji), guild=guild.id)
        self.clownboards[guild.id][name] = clownboard
        await self._save_clownboards(guild)
        msg = _("clownboard set to {channel} with emoji {emoji}").format(
            channel=channel.mention, emoji=emoji
        )
        await ctx.send(msg)

    @clownboard.command(name="cleanup")
    async def cleanup(self, ctx: commands.Context) -> None:
        """
        Cleanup stored deleted channels or roles in the blocklist/allowlist
        """
        guild = ctx.guild
        if guild.id not in self.clownboards:
            await ctx.send(_("There are no clownboards setup on this server."))
            return
        channels = 0
        boards = 0
        for name, clownboard in self.clownboards[guild.id].items():
            channel = guild.get_channel(clownboard.channel)
            if channel is None:
                del self.clownboards[guild.id][name]
                boards += 1
                continue
            if clownboard.blacklist:
                for c in clownboard.blacklist:
                    channel = guild.get_channel(c)
                    role = guild.get_role(c)
                    if channel is None and role is None:
                        self.clownboards[guild.id][name].blacklist.remove(c)
                        channels += 1
            if clownboard.whitelist:
                for c in clownboard.whitelist:
                    channel = guild.get_channel(c)
                    role = guild.get_role(c)
                    if channel is None and role is None:
                        self.clownboards[guild.id][name].whitelist.remove(c)
                        channels += 1
        await self._save_clownboards(guild)
        msg = _(
            "Removed {channels} channels and roles, and {boards} boards " "that no longer exist"
        ).format(channels=channels, boards=boards)
        await ctx.send(msg)

    @clownboard.command(name="remove", aliases=["delete", "del"])
    async def remove_clownboard(
        self, ctx: commands.Context, clownboard: Optional[clownboardExists]
    ) -> None:
        """
        Remove a clownboard from the server

        `<name>` is the name for the clownboard and will be lowercase only
        """
        guild = ctx.guild
        if not clownboard:
            if guild.id not in self.clownboards:
                await ctx.send(_("There are no clownboards setup on this server!"))
                return
            if len(self.clownboards[guild.id]) > 1:
                await ctx.send(
                    _(
                        "There's more than one clownboard setup in this server. "
                        "Please provide a name for the clownboard you wish to use."
                    )
                )
                return
            clownboard = list(self.clownboards[guild.id].values())[0]

        async with self.config.guild(guild).clownboards() as clownboards:
            try:
                del self.clownboards[ctx.guild.id][clownboard.name]
                del clownboards[clownboard.name]
            except Exception:
                log.exception("Error removing clownboard")
                await ctx.send("Deleting the clownboard failed.")
                return
        await ctx.send(_("Deleted clownboard {name}").format(name=clownboard.name))

    @commands.command()
    @commands.guild_only()
    async def clown(
        self,
        ctx: commands.Context,
        clownboard: Optional[clownboardExists],
        message: discord.Message,
    ) -> None:
        """
        Manually star a message

        `<name>` is the name of the clownboard you would like to add the message to
        `<message>` is the message ID, `channel_id-message_id`, or a message link
        of the message you want to star
        """
        guild = ctx.guild
        if not clownboard:
            if guild.id not in self.clownboards:
                await ctx.send(_("There are no clownboards setup on this server!"))
                return
            if len(self.clownboards[guild.id]) > 1:
                await ctx.send(
                    _(
                        "There's more than one clownboard setup in this server. "
                        "Please provide a name for the clownboard you wish to use."
                    )
                )
                return
            clownboard = list(self.clownboards[guild.id].values())[0]
        if message.guild and message.guild.id != guild.id:
            await ctx.send(_("I cannot star messages from another server."))
            return
        if not clownboard.enabled:
            error_msg = _("clownboard {name} isn't enabled.").format(name=clownboard.name)
            await ctx.send(error_msg)
            return
        if not clownboard.check_roles(ctx.message.author):
            error_msg = _(
                "One of your roles is blocked on {clownboard} "
                "or you don't have a role that is allowed."
            ).format(clownboard=clownboard.name)
            await ctx.send(error_msg)
            return
        if not clownboard.check_channel(self.bot, message.channel):
            error_msg = _(
                "That messages channel is either blocked, not "
                "in the allowlist, or designated NSFW while the "
                "{clownboard} channel is not designated as NSFW."
            ).format(clownboard=clownboard.name)
            await ctx.send(error_msg)
            return
        fake_payload = FakePayload(
            guild_id=guild.id,
            message_id=message.id,
            channel_id=message.channel.id,
            user_id=ctx.author.id,
            emoji=clownboard.emoji,
            event_type="REACTION_ADD",
        )
        await self._update_stars(fake_payload)

    @commands.command()
    @commands.guild_only()
    async def unstar(
        self,
        ctx: commands.Context,
        clownboard: Optional[clownboardExists],
        message: discord.Message,
    ) -> None:
        """
        Manually unstar a message

        `<name>` is the name of the clownboard you would like to add the message to
        `<message>` is the message ID, `channe_id-message_id`, or a message link
        of the message you want to unstar
        """
        guild = ctx.guild
        if not clownboard:
            if guild.id not in self.clownboards:
                await ctx.send(_("There are no clownboards setup on this server!"))
                return
            if len(self.clownboards[guild.id]) > 1:
                await ctx.send(
                    _(
                        "There's more than one clownboard setup in this server. "
                        "Please provide a name for the clownboard you wish to use."
                    )
                )
                return
            clownboard = list(self.clownboards[guild.id].values())[0]
        if message.guild and message.guild.id != guild.id:
            await ctx.send(_("I cannot star messages from another server."))
            return
        if not clownboard.enabled:
            error_msg = _("clownboard {name} isn't enabled.").format(name=clownboard.name)
            await ctx.send(error_msg)
            return
        if not clownboard.check_roles(ctx.message.author):
            error_msg = _(
                "One of your roles is blocked on {clownboard} "
                "or you don't have a role that is allowed."
            ).format(clownboard=clownboard.name)
            await ctx.send(error_msg)
            return
        if not clownboard.check_channel(self.bot, message.channel):
            error_msg = _(
                "That messages channel is either blocked, not "
                "in the allowlist, or designated NSFW while the "
                "{clownboard} channel is not designated as NSFW."
            ).format(clownboard=clownboard.name)
            await ctx.send(error_msg)
            return
        fake_payload = FakePayload(
            guild_id=guild.id,
            message_id=message.id,
            channel_id=message.channel.id,
            user_id=ctx.author.id,
            emoji=clownboard.emoji,
            event_type="REACTION_REMOVE",
        )
        await self._update_stars(fake_payload)

    @clownboard.group(name="allowlist", aliases=["whitelist"])
    async def whitelist(self, ctx: commands.Context) -> None:
        """Add/Remove channels/roles from the allowlist"""
        pass

    @clownboard.group(name="blocklist", aliases=["blacklist"])
    async def blacklist(self, ctx: commands.Context) -> None:
        """Add/Remove channels/roles from the blocklist"""
        pass

    @blacklist.command(name="add")
    async def blacklist_add(
        self,
        ctx: commands.Context,
        clownboard: Optional[clownboardExists],
        channel_or_role: Union[discord.TextChannel, discord.CategoryChannel, discord.Role],
    ) -> None:
        """
        Add a channel to the clownboard blocklist

        `<name>` is the name of the clownboard to adjust
        `<channel_or_role>` is the channel or role you would like to add to the blocklist
        """
        guild = ctx.guild
        if not clownboard:
            if guild.id not in self.clownboards:
                await ctx.send(_("There are no clownboards setup on this server!"))
                return
            if len(self.clownboards[guild.id]) > 1:
                await ctx.send(
                    _(
                        "There's more than one clownboard setup in this server. "
                        "Please provide a name for the clownboard you wish to use."
                    )
                )
                return
            clownboard = list(self.clownboards[guild.id].values())[0]
        if channel_or_role.id in clownboard.blacklist:
            msg = _("{channel_or_role} is already blocked for clownboard {name}").format(
                channel_or_role=channel_or_role.name, name=clownboard.name
            )
            await ctx.send(msg)
            return
        else:
            self.clownboards[ctx.guild.id][clownboard.name].blacklist.append(channel_or_role.id)
            await self._save_clownboards(guild)
            msg = _("{channel_or_role} blocked on clownboard {name}").format(
                channel_or_role=channel_or_role.name, name=clownboard.name
            )
            await ctx.send(msg)

    @blacklist.command(name="remove")
    async def blacklist_remove(
        self,
        ctx: commands.Context,
        clownboard: Optional[clownboardExists],
        channel_or_role: Union[discord.TextChannel, discord.CategoryChannel, discord.Role],
    ) -> None:
        """
        Remove a channel to the clownboard blocklist

        `<name>` is the name of the clownboard to adjust
        `<channel_or_role>` is the channel or role you would like to remove from the blocklist
        """
        guild = ctx.guild
        if not clownboard:
            if guild.id not in self.clownboards:
                await ctx.send(_("There are no clownboards setup on this server!"))
                return
            if len(self.clownboards[guild.id]) > 1:
                await ctx.send(
                    _(
                        "There's more than one clownboard setup in this server. "
                        "Please provide a name for the clownboard you wish to use."
                    )
                )
                return
            clownboard = list(self.clownboards[guild.id].values())[0]
        if channel_or_role.id not in clownboard.blacklist:
            msg = _("{channel_or_role} is not on the blocklist for clownboard {name}").format(
                channel_or_role=channel_or_role.name, name=clownboard.name
            )
            await ctx.send(msg)
            return
        else:
            self.clownboards[ctx.guild.id][clownboard.name].blacklist.remove(channel_or_role.id)
            await self._save_clownboards(guild)
            msg = _("{channel_or_role} removed from the blocklist on clownboard {name}").format(
                channel_or_role=channel_or_role.name, name=clownboard.name
            )
            await ctx.send(msg)

    @whitelist.command(name="add")
    async def whitelist_add(
        self,
        ctx: commands.Context,
        clownboard: Optional[clownboardExists],
        channel_or_role: Union[discord.TextChannel, discord.CategoryChannel, discord.Role],
    ) -> None:
        """
        Add a channel to the clownboard allowlist

        `<name>` is the name of the clownboard to adjust
        `<channel_or_role>` is the channel or role you would like to add to the allowlist
        """
        guild = ctx.guild
        if not clownboard:
            if guild.id not in self.clownboards:
                await ctx.send(_("There are no clownboards setup on this server!"))
                return
            if len(self.clownboards[guild.id]) > 1:
                await ctx.send(
                    _(
                        "There's more than one clownboard setup in this server. "
                        "Please provide a name for the clownboard you wish to use."
                    )
                )
                return
            clownboard = list(self.clownboards[guild.id].values())[0]

        if channel_or_role.id in clownboard.whitelist:
            msg = _("{channel_or_role} is already allowed for clownboard {name}").format(
                channel_or_role=channel_or_role.name, name=clownboard.name
            )
            await ctx.send(msg)
            return
        else:
            self.clownboards[ctx.guild.id][clownboard.name].whitelist.append(channel_or_role.id)
            await self._save_clownboards(guild)
            msg = _("{channel_or_role} allowed on clownboard {name}").format(
                channel_or_role=channel_or_role.name, name=clownboard.name
            )
            await ctx.send(msg)
            if isinstance(channel_or_role, discord.TextChannel):
                star_channel = ctx.guild.get_channel(clownboard.channel)
                if channel_or_role.is_nsfw() and not star_channel.is_nsfw():
                    await ctx.send(
                        _(
                            "The channel you have provided is designated "
                            "as NSFW but your clownboard channel is not. "
                            "They will both need to be set the same "
                            "in order for this to work properly."
                        )
                    )

    @whitelist.command(name="remove")
    async def whitelist_remove(
        self,
        ctx: commands.Context,
        clownboard: Optional[clownboardExists],
        channel_or_role: Union[discord.TextChannel, discord.CategoryChannel, discord.Role],
    ) -> None:
        """
        Remove a channel to the clownboard allowlist

        `<name>` is the name of the clownboard to adjust
        `<channel_or_role>` is the channel or role you would like to remove from the allowlist
        """
        guild = ctx.guild
        if not clownboard:
            if guild.id not in self.clownboards:
                await ctx.send(_("There are no clownboards setup on this server!"))
                return
            if len(self.clownboards[guild.id]) > 1:
                await ctx.send(
                    _(
                        "There's more than one clownboard setup in this server. "
                        "Please provide a name for the clownboard you wish to use."
                    )
                )
                return
            clownboard = list(self.clownboards[guild.id].values())[0]
        if channel_or_role.id not in clownboard.whitelist:
            msg = _("{channel_or_role} is not on the allowlist for clownboard {name}").format(
                channel_or_role=channel_or_role.name, name=clownboard.name
            )
            await ctx.send(msg)
            return
        else:
            self.clownboards[ctx.guild.id][clownboard.name].whitelist.remove(channel_or_role.id)
            await self._save_clownboards(guild)
            msg = _("{channel_or_role} removed from the allowlist on clownboard {name}").format(
                channel_or_role=channel_or_role.name, name=clownboard.name
            )
            await ctx.send(msg)

    @clownboard.command(name="channel", aliases=["channels"])
    async def change_channel(
        self,
        ctx: commands.Context,
        clownboard: Optional[clownboardExists],
        channel: discord.TextChannel,
    ) -> None:
        """
        Change the channel that the clownboard gets posted to

        `<name>` is the name of the clownboard to adjust
        `<channel>` The channel of the clownboard.
        """
        guild = ctx.guild
        if not clownboard:
            if guild.id not in self.clownboards:
                await ctx.send(_("There are no clownboards setup on this server!"))
                return
            if len(self.clownboards[guild.id]) > 1:
                await ctx.send(
                    _(
                        "There's more than one clownboard setup in this server. "
                        "Please provide a name for the clownboard you wish to use."
                    )
                )
                return
            clownboard = list(self.clownboards[guild.id].values())[0]
        if not channel.permissions_for(guild.me).send_messages:
            send_perms = _("I don't have permission to post in ")
            await ctx.send(send_perms + channel.mention)
            return

        if not channel.permissions_for(guild.me).embed_links:
            embed_perms = _("I don't have permission to embed links in ")
            await ctx.send(embed_perms + channel.mention)
            return
        if channel.id == clownboard.channel:
            msg = _("clownboard {name} is already posting in {channel}").format(
                name=clownboard.name, channel=channel.mention
            )
            await ctx.send(msg)
            return
        self.clownboards[ctx.guild.id][clownboard.name].channel = channel.id
        await self._save_clownboards(guild)
        msg = _("clownboard {name} set to post in {channel}").format(
            name=clownboard.name, channel=channel.mention
        )
        await ctx.send(msg)

    @clownboard.command(name="toggle")
    async def toggle_clownboard(
        self, ctx: commands.Context, clownboard: Optional[clownboardExists]
    ) -> None:
        """
        Toggle a clownboard on/off

        `<name>` is the name of the clownboard to toggle
        """
        guild = ctx.guild
        if not clownboard:
            if guild.id not in self.clownboards:
                await ctx.send(_("There are no clownboards setup on this server!"))
                return
            if len(self.clownboards[guild.id]) > 1:
                await ctx.send(
                    _(
                        "There's more than one clownboard setup in this server. "
                        "Please provide a name for the clownboard you wish to use."
                    )
                )
                return
            clownboard = list(self.clownboards[guild.id].values())[0]
        if clownboard.enabled:
            msg = _("clownboard {name} disabled.").format(name=clownboard.name)
        else:
            msg = _("clownboard {name} enabled.").format(name=clownboard.name)
        self.clownboards[ctx.guild.id][clownboard.name].enabled = not clownboard.enabled
        await self._save_clownboards(guild)
        await ctx.send(msg)

    @clownboard.command(name="selfstar")
    async def toggle_selfstar(
        self, ctx: commands.Context, clownboard: Optional[clownboardExists]
    ) -> None:
        """
        Toggle whether or not a user can star their own post

        `<name>` is the name of the clownboard to toggle
        """
        guild = ctx.guild
        if not clownboard:
            if guild.id not in self.clownboards:
                await ctx.send(_("There are no clownboards setup on this server!"))
                return
            if len(self.clownboards[guild.id]) > 1:
                await ctx.send(
                    _(
                        "There's more than one clownboard setup in this server. "
                        "Please provide a name for the clownboard you wish to use."
                    )
                )
                return
            clownboard = list(self.clownboards[guild.id].values())[0]
        if clownboard.selfstar:
            msg = _("Selfstarring on clownboard {name} disabled.").format(name=clownboard.name)
        else:
            msg = _("Selfstarring on clownboard {name} enabled.").format(name=clownboard.name)
        self.clownboards[ctx.guild.id][clownboard.name].selfstar = not clownboard.selfstar
        await self._save_clownboards(guild)
        await ctx.send(msg)

    @clownboard.command(name="autostar")
    async def toggle_autostar(
        self, ctx: commands.Context, clownboard: Optional[clownboardExists]
    ) -> None:
        """
        Toggle whether or not the bot will add the emoji automatically to the clownboard message.

        `<name>` is the name of the clownboard to toggle
        """
        guild = ctx.guild
        if not clownboard:
            if guild.id not in self.clownboards:
                await ctx.send(_("There are no clownboards setup on this server!"))
                return
            if len(self.clownboards[guild.id]) > 1:
                await ctx.send(
                    _(
                        "There's more than one clownboard setup in this server. "
                        "Please provide a name for the clownboard you wish to use."
                    )
                )
                return
            clownboard = list(self.clownboards[guild.id].values())[0]
        if clownboard.autostar:
            msg = _("Autostarring on clownboard {name} disabled.").format(name=clownboard.name)
        else:
            msg = _("Autostarring on clownboard {name} enabled.").format(name=clownboard.name)
        self.clownboards[ctx.guild.id][clownboard.name].autostar = not clownboard.autostar
        await self._save_clownboards(guild)
        await ctx.send(msg)

    @clownboard.command(name="colour", aliases=["color"])
    async def colour_clownboard(
        self,
        ctx: commands.Context,
        clownboard: Optional[clownboardExists],
        colour: Union[discord.Colour, str],
    ) -> None:
        """
        Change the default colour for a clownboard

        `<name>` is the name of the clownboard to toggle
        `<colour>` The colour to use for the clownboard embed
        This can be a hexcode or integer for colour or `author/member/user` to use
        the original posters colour or `bot` to use the bots colour.
        Colour also accepts names from
        [discord.py](https://discordpy.readthedocs.io/en/latest/api.html#colour)
        """
        guild = ctx.guild
        if not clownboard:
            if guild.id not in self.clownboards:
                await ctx.send(_("There are no clownboards setup on this server!"))
                return
            if len(self.clownboards[guild.id]) > 1:
                await ctx.send(
                    _(
                        "There's more than one clownboard setup in this server. "
                        "Please provide a name for the clownboard you wish to use."
                    )
                )
                return
            clownboard = list(self.clownboards[guild.id].values())[0]
        if isinstance(colour, str):
            colour = 0x313338
            if colour not in ["user", "member", "author", "bot"]:
                await ctx.send(_("The provided colour option is not valid."))
                return
            else:
                clownboard.colour = colour
        else:
            self.clownboards[ctx.guild.id][clownboard.name].colour = colour.value
        await self._save_clownboards(guild)
        msg = _("clownboard `{name}` colour set to `{colour}`.").format(
            name=clownboard.name, colour=clownboard.colour
        )
        await ctx.send(msg)

    @clownboard.command(name="emoji")
    async def set_emoji(
        self,
        ctx: commands.Context,
        clownboard: Optional[clownboardExists],
        emoji: RealEmoji,
    ) -> None:
        """
        Set the emoji for the clownboard

        `<name>` is the name of the clownboard to change the emoji for
        `<emoji>` must be an emoji on the server or a default emoji
        """
        guild = ctx.guild
        if not clownboard:
            if guild.id not in self.clownboards:
                await ctx.send(_("There are no clownboards setup on this server!"))
                return
            if len(self.clownboards[guild.id]) > 1:
                await ctx.send(
                    _(
                        "There's more than one clownboard setup in this server. "
                        "Please provide a name for the clownboard you wish to use."
                    )
                )
                return
            clownboard = list(self.clownboards[guild.id].values())[0]
        if type(emoji) == discord.Emoji:
            if emoji not in guild.emojis:
                await ctx.send(_("That emoji is not on this guild!"))
                return
        self.clownboards[ctx.guild.id][clownboard.name].emoji = str(emoji)
        await self._save_clownboards(guild)
        msg = _("{emoji} set for clownboard {name}").format(emoji=emoji, name=clownboard.name)
        await ctx.send(msg)

    @clownboard.command(name="threshold")
    async def set_threshold(
        self,
        ctx: commands.Context,
        clownboard: Optional[clownboardExists],
        threshold: int,
    ) -> None:
        """
        Set the threshold before posting to the clownboard

        `<name>` is the name of the clownboard to change the threshold for
        `<threshold>` must be a number of reactions before a post gets
        moved to the clownboard
        """
        guild = ctx.guild
        if not clownboard:
            if guild.id not in self.clownboards:
                await ctx.send(_("There are no clownboards setup on this server!"))
                return
            if len(self.clownboards[guild.id]) > 1:
                await ctx.send(
                    _(
                        "There's more than one clownboard setup in this server. "
                        "Please provide a name for the clownboard you wish to use."
                    )
                )
                return
            clownboard = list(self.clownboards[guild.id].values())[0]
        if threshold <= 0:
            threshold = 1
        self.clownboards[ctx.guild.id][clownboard.name].threshold = threshold
        await self._save_clownboards(guild)
        msg = _("Threshold of {threshold} reactions set for {name}").format(
            threshold=threshold, name=clownboard.name
        )
        await ctx.send(msg)
