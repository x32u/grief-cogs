import logging
import re
from typing import List, Union

import discord
from discord.ext.commands.converter import IDConverter
from discord.ext.commands.errors import BadArgument
from rapidfuzz import process
from grief.core import commands
from grief.core.i18n import Translator
from unidecode import unidecode
from .classes import ScheduledMaintenance
from .utils import convert_time
import argparse

from grief.core.commands import BadArgument, Converter

_ = Translator("Server", __file__)
log = logging.getLogger("grief.owner")


class GuildConverter(discord.app_commands.Transformer):
    """
    This is a guild converter for fuzzy guild names which is used throughout
    this cog to search for guilds by part of their name and will also
    accept guild ID's

    Guidance code on how to do this from:
    https://github.com/Rapptz/discord.py/blob/rewrite/discord/ext/commands/converter.py#L85
    https://github.com/Cog-Creators/Red-DiscordBot/blob/V3/develop/redbot/cogs/mod/mod.py#L24
    """

    @classmethod
    async def convert(cls, ctx: commands.Context, argument: str) -> discord.Guild:
        bot = ctx.bot
        result = None
        if not argument.isdigit():
            # Not a mention
            for g in process.extractOne(argument, {g: unidecode(g.name) for g in bot.guilds}):
                result = g
        else:
            guild_id = int(argument)
            result = bot.get_guild(guild_id)

        if result is None:
            raise BadArgument('Guild "{}" not found'.format(argument))
        if ctx.author not in result.members and not await bot.is_owner(ctx.author):
            raise BadArgument(_("That option is only available for the bot owner."))

        return result

    @classmethod
    async def transform(cls, interaction: discord.Interaction, argument: str) -> discord.Guild:
        ctx = await interaction.client.get_context(interaction)
        return await cls.convert(ctx, argument)

    async def autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> List[discord.app_commands.Choice]:
        if await interaction.client.is_owner(interaction.user):
            choices = [
                discord.app_commands.Choice(name=g.name, value=str(g.id))
                for g in interaction.client.guilds
                if current.lower() in g.name.lower()
            ]
        else:
            choices = [
                discord.app_commands.Choice(name=g.name, value=str(g.id))
                for g in interaction.client.guilds
                if current.lower() in g.name.lower()
                and g.get_member(interaction.user.id) is not None
            ]
        return choices[:25]


class MultiGuildConverter(IDConverter):
    """
    This is a guild converter for fuzzy guild names which is used throughout
    this cog to search for guilds by part of their name and will also
    accept guild ID's

    Guidance code on how to do this from:
    https://github.com/Rapptz/discord.py/blob/rewrite/discord/ext/commands/converter.py#L85
    https://github.com/Cog-Creators/Red-DiscordBot/blob/V3/develop/redbot/cogs/mod/mod.py#L24
    """

    async def convert(self, ctx: commands.Context, argument: str) -> List[discord.Guild]:
        bot = ctx.bot
        match = self._get_id_match(argument)
        result = []
        if not await bot.is_owner(ctx.author):
            # Don't need to be snooping other guilds unless we're
            # the bot owner
            raise BadArgument(_("That option is only available for the bot owner."))
        if not match:
            # Not a mention
            for g in process.extract(
                argument, {g: unidecode(g.name) for g in bot.guilds}, limit=None, score_cutoff=75
            ):
                result.append(g[2])
        else:
            guild_id = int(match.group(1))
            guild = bot.get_guild(guild_id)
            if not guild:
                raise BadArgument('Guild "{}" not found'.format(argument))
            result.append(guild)

        if not result:
            raise BadArgument('Guild "{}" not found'.format(argument))

        return result


class PermissionConverter(IDConverter):
    """
    This is to convert to specific permission names

    add_reactions
    attach_files
    change_nickname
    connect
    create_instant_invite
    deafen_members
    embed_links
    external_emojis
    manage_channels
    manage_messages
    manage_permissions
    manage_roles
    manage_webhooks
    mention_everyone
    move_members
    mute_members
    priority_speaker
    read_message_history
    read_messages
    send_messages
    send_tts_messages
    speak
    stream
    use_external_emojis
    use_slash_commands
    use_voice_activation
    value
    view_channel
    """

    async def convert(self, ctx: commands.Context, argument: str) -> str:
        valid_perms = [
            "add_reactions",
            "attach_files",
            "connect",
            "create_instant_invite",
            "deafen_members",
            "embed_links",
            "external_emojis",
            "manage_messages",
            "manage_permissions",
            "manage_roles",
            "manage_webhooks",
            "move_members",
            "mute_members",
            "priority_speaker",
            "read_message_history",
            "read_messages",
            "send_messages",
            "send_tts_messages",
            "speak",
            "stream",
            "use_external_emojis",
            "use_slash_commands",
            "use_voice_activation",
            "view_channel",
        ]
        match = re.match(r"|".join(i for i in valid_perms), argument, flags=re.I)

        result = match.group(0)

        if not result:
            raise BadArgument(f"Permission `{argument}` not found")
        return result


class NoExitParser(argparse.ArgumentParser):
    def error(self, message):
        raise BadArgument()


class Margs(Converter):
    async def convert(self, ctx, argument):
        argument = argument.replace("—", "--")
        parser = NoExitParser(description="Maintenance Scheduler", add_help=False)
        parser.add_argument("--start-in", nargs="*", dest="start", default=[])
        parser.add_argument("--whitelist", nargs="*", dest="whitelist", default=[])
        _end = parser.add_mutually_exclusive_group()
        _end.add_argument("--end-after", nargs="*", dest="end", default=[])
        _end.add_argument("--end-in", nargs="*", dest="endin", default=[])
        try:
            vals = vars(parser.parse_args(argument.split(" ")))
        except Exception as exc:
            raise BadArgument() from exc
        start_seconds = convert_time(vals.get("start", None))
        end_seconds = convert_time(vals.get("end", None))
        whitelist = vals.get("whitelist", [])
        whitelist = list(map(int, whitelist))
        after = True
        if end_seconds == None:
            end_seconds = convert_time(vals.get("endin", None))
            after = False
        if start_seconds:
            if end_seconds:
                scheduled = ScheduledMaintenance(
                    start=start_seconds, end=end_seconds, after=after, whitelist=whitelist,
                )
            else:
                scheduled = ScheduledMaintenance(start=start_seconds, whitelist=whitelist)
        else:
            if end_seconds:
                scheduled = ScheduledMaintenance(end=end_seconds, after=after, whitelist=whitelist)
            else:
                scheduled = ScheduledMaintenance(whitelist=whitelist)
        return scheduled