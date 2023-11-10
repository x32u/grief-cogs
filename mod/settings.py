import asyncio
from collections import defaultdict, deque
from datetime import timedelta

from grief.core import commands, i18n
from grief.core.utils import AsyncIter
from grief.core.utils.chat_formatting import box, humanize_timedelta, inline

from .abc import MixinMeta

_ = i18n.Translator("Mod", __file__)


class ModSettings(MixinMeta):
    """
    This is a mixin for the mod cog containing all settings commands.
    """

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
        """Delete all stored usernames and nicknames.

        Examples:
        - `[p]modset deletenames` - Did not confirm. Shows the help message.
        - `[p]modset deletenames yes` - Deletes all stored usernames and nicknames.

        **Arguments**

        - `<confirmation>` This will default to false unless specified.
        """
        if not confirmation:
            await ctx.send(
                _(
                    "This will delete all stored usernames and nicknames the bot has stored."
                    "\nIf you're sure, type {command}"
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

            # Username data
            async with self.config._get_base_group(self.config.USER).all() as mod_user_data:
                users_to_remove = []
                async for user_id, user_data in AsyncIter(mod_user_data.items(), steps=100):
                    if "past_names" in user_data:
                        del user_data["past_names"]
                    if not user_data:
                        users_to_remove.append(user_id)

                async for user_id in AsyncIter(users_to_remove, steps=100):
                    del mod_user_data[user_id]

        await ctx.send(_("Usernames and nicknames have been deleted from Mod config."))
