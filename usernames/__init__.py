
from typing import List, Tuple, cast, Optional
import asyncio
from collections import defaultdict
import discord
from grief.core import commands, i18n
from grief.core.utils.chat_formatting import bold, pagify
from grief.core.utils.common_filters import (
    filter_invites,
    filter_various_mentions,
    escape_spoilers_and_mass_mentions,
)
from .abc import MixinMeta
import discord
from grief.core import Config, commands
from grief.core.bot import Grief
from logging import Logger, getLogger
from grief.core.i18n import Translator, cog_i18n
from grief.core.utils import AsyncIter
from grief.core.utils.chat_formatting import box, humanize_timedelta, inline

_ = i18n.Translator("Mod", __file__)

@cog_i18n(_)
class Names(commands.Cog):
    """Moderation tools."""
    
    def format_help_for_context(self, ctx: commands.Context) -> str:
        pre_processed = super().format_help_for_context(ctx)
        return (f"{pre_processed}\n")
    
    default_member_settings = {"past_nicks": []}
    default_user_settings = {"past_names": [], "past_display_names": []}
    default_global_settings = { "track_all_names": True,}
    default_guild_settings = {"track_nicknames": True,}
    
    def __init__(self, bot: Grief):
        super().__init__()
        self.bot: Grief = bot
        self.logger: Logger = getLogger("grief.vanity")
        self.config = Config.get_conf(self, 4961522000, force_registration=True)
        self.config.register_member(**self.default_member_settings)
        self.config.register_user(**self.default_user_settings)
        self.config.register_global(**self.default_global_settings)
        self.config.register_guild(**self.default_guild_settings)
        self.cache: dict = {}

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
            (_(f"Past 20 usernames: \n"), usernames),
            (_(f"Past 20 global display names:\n"), display_names),
            (_(f"Past 20 server nicknames:\n"), nicks),
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

    @commands.is_owner()
    @commands.command()
    @commands.guild_only()
    async def tracknicknames(self, ctx: commands.Context, enabled: bool = None):
        """
        Toggle whether server nickname changes should be tracked.

        This setting will be overridden if trackallnames is disabled.
        """
        guild = ctx.guild
        if enabled is None:
            state = await self.config.guild(guild).track_nicknames()
            if state:
                msg = _("Nickname changes are currently being tracked.")
            else:
                msg = _("Nickname changes are not currently being tracked.")
            await ctx.send(msg)
            return

        if enabled:
            msg = _("Nickname changes will now be tracked.")
        else:
            msg = _("Nickname changes will no longer be tracked.")
        await self.config.guild(guild).track_nicknames.set(enabled)
        await ctx.send(msg)

    @commands.command()
    @commands.is_owner()
    async def trackallnames(self, ctx: commands.Context, enabled: bool = None):
        """
        Toggle whether all name changes should be tracked.

        Toggling this off also overrides the tracknicknames setting.
        """
        if enabled is None:
            state = await self.config.track_all_names()
            if state:
                msg = _("Name changes are currently being tracked.")
            else:
                msg = _("All name changes are currently not being tracked.")
            await ctx.send(msg)
            return

        if enabled:
            msg = _("Name changes will now be tracked.")
        else:
            msg = _(
                "All name changes will no longer be tracked.\n"
                "To delete existing name data, use {command}."
            ).format(command=inline(f"{ctx.clean_prefix}modset deletenames"))
        await self.config.track_all_names.set(enabled)
        await ctx.send(msg)

    @commands.command()
    @commands.max_concurrency(1, commands.BucketType.default)
    @commands.is_owner()
    async def deletenames(self, ctx: commands.Context, confirmation: bool = False) -> None:
        """Delete all stored usernames, global display names, and server nicknames.

        Examples:
        - `[p]modset deletenames` - Did not confirm. Shows the help message.
        - `[p]modset deletenames yes` - Deletes all stored usernames, global display names, and server nicknames.

        **Arguments**

        - `<confirmation>` This will default to false unless specified.
        """
        if not confirmation:
            await ctx.send(
                _(
                    "This will delete all stored usernames, global display names,"
                    " and server nicknames the bot has stored.\nIf you're sure, type {command}"
                ).format(command=inline(f"{ctx.clean_prefix}modset deletenames yes"))
            )
            return

        async with ctx.typing():
            # Nickname data
            async with self.config._get_base_group(self.config.MEMBER).all() as mod_member_data:
                guilds_to_remove = []
                for guild_id, guild_data in mod_member_data.items():
                    await asyncio.sleep(0)
                    members_to_remove = []

                    async for member_id, member_data in AsyncIter(guild_data.items(), steps=100):
                        if "past_nicks" in member_data:
                            del member_data["past_nicks"]
                        if not member_data:
                            members_to_remove.append(member_id)

                    async for member_id in AsyncIter(members_to_remove, steps=100):
                        del guild_data[member_id]
                    if not guild_data:
                        guilds_to_remove.append(guild_id)

                async for guild_id in AsyncIter(guilds_to_remove, steps=100):
                    del mod_member_data[guild_id]

            # Username and global display name data
            async with self.config._get_base_group(self.config.USER).all() as mod_user_data:
                users_to_remove = []
                async for user_id, user_data in AsyncIter(mod_user_data.items(), steps=100):
                    if "past_names" in user_data:
                        del user_data["past_names"]
                    if "past_display_names" in user_data:
                        del user_data["past_display_names"]
                    if not user_data:
                        users_to_remove.append(user_id)

                async for user_id in AsyncIter(users_to_remove, steps=100):
                    del mod_user_data[user_id]

        await ctx.send(
            _(
                "Usernames, global display names, and server nicknames"
                " have been deleted from Mod config."
            )
        )

    @staticmethod
    def _update_past_names(name: str, name_list: List[Optional[str]]) -> None:
        while None in name_list:  # clean out null entries from a bug
            name_list.remove(None)
        if name in name_list:
            # Ensure order is maintained without duplicates occurring
            name_list.remove(name)
        name_list.append(name)
        while len(name_list) > 20:
            name_list.pop(0)

    @commands.Cog.listener()
    async def on_user_update(self, before: discord.User, after: discord.User):
        if before.name != after.name:
            track_all_names = await self.config.track_all_names()
            if not track_all_names:
                return
            async with self.config.user(before).past_names() as name_list:
                self._update_past_names(before.name, name_list)
        if before.display_name != after.display_name:
            track_all_names = await self.config.track_all_names()
            if not track_all_names:
                return
            async with self.config.user(before).past_display_names() as name_list:
                self._update_past_names(before.display_name, name_list)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if before.nick != after.nick and before.nick is not None:
            guild = after.guild
            if (not guild) or await self.bot.cog_disabled_in_guild(self, guild):
                return
            track_all_names = await self.config.track_all_names()
            track_nicknames = await self.config.guild(guild).track_nicknames()
            if (not track_all_names) or (not track_nicknames):
                return
            async with self.config.member(before).past_nicks() as nick_list:
                self._update_past_names(before.nick, nick_list)

async def setup(bot: Grief) -> None:
        await bot.add_cog(Names(bot))