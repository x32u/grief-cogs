from AAA3A_utils import Cog  # isort:skip
from grief.core import commands, Config  # isort:skip
from grief.core.bot import Grief, NotMessage  # isort:skip
from grief.core.i18n import Translator, cog_i18n  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import io
from copy import deepcopy

# Credits:
# General repo credits.
# The idea for this cog came from @OnlyEli on Red cogs support (https://discord.com/channels/240154543684321280/430582201113903114/944075297127538730)!

_ = Translator("MemberPrefix", __file__)


@cog_i18n(_)
class MemberPrefix(Cog):
    """A cog to allow a member to choose custom prefixes, just for them!"""

    def __init__(self, bot: Grief) -> None:
        super().__init__(bot=bot)

        self.config: Config = Config.get_conf(
            self,
            identifier=205192943327321000143939875896557571750,  # 647053803629
            force_registration=True,
        )
        self.memberprefix_global: typing.Dict[str, bool] = {
            "use_normal_prefixes": True,
        }
        self.memberprefix_member: typing.Dict[str, typing.List[str]] = {
            "custom_prefixes": [],
        }
        self.config.register_global(**self.memberprefix_global)
        self.config.register_user(**self.memberprefix_member)

        self.original_prefix_manager = self.bot.command_prefix

        # _settings: typing.Dict[
        #     str, typing.Dict[str, typing.Union[typing.List[str], bool, str]]
        # ] = {
        #     "use_normal_prefixes": {
        #         "converter": bool,
        #         "description": "Use server/global prefixes in addition to those customized for each member.",
        #     },
        # }
        # self.settings: Settings = Settings(
        #     bot=self.bot,
        #     cog=self,
        #     config=self.config,
        #     group=self.config.GLOBAL,
        #     settings=_settings,
        #     global_path=[],
        #     use_profiles_system=False,
        #     can_edit=True,
        #     commands_group=self.configuration,
        # )

    async def cog_load(self) -> None:
        await super().cog_load()
        # await self.settings.add_commands()
        self.bot.command_prefix = self.prefix_manager

    async def cog_unload(self) -> None:
        if self.original_prefix_manager is not None:
            self.bot.command_prefix = self.original_prefix_manager
        await super().cog_unload()
    
    async def prefix_manager(
        self, bot: Grief, message: typing.Union[discord.Message, NotMessage]
    ) -> typing.List[str]:
        if (
            not isinstance(message, discord.Message)
            or message.guild is None
            or await bot.cog_disabled_in_guild(cog=self, guild=message.guild)
            or not await bot.allowed_by_whitelist_blacklist(who=message.author)
        ):
            return await self.original_prefix_manager(bot, message)
        custom_prefixes = await self.config.user_from_ids(
            message.guild.id, message.author.id
        ).custom_prefixes()
        if custom_prefixes == []:
            return await self.original_prefix_manager(bot, message)
        if (
            await self.config.use_normal_prefixes()
        ):  # Always `True` because the setting has been removed.
            prefixes = await bot._prefix_cache.get_prefixes(message.guild)
        prefixes.extend(custom_prefixes)
        prefixes = sorted(prefixes, reverse=True)
        return commands.when_mentioned_or(*prefixes)(bot, message)

    class StrConverter(commands.Converter):
        async def convert(self, ctx: commands.Context, argument: str) -> str:
            return argument

    @commands.guild_only()
    @commands.hybrid_command(aliases=["memberprefixes"], invoke_without_command=True)
    async def memberprefix(
        self, ctx: commands.Context, prefixes: commands.Greedy[StrConverter]
    ) -> None:
        """Sets [botname]'s prefix(es) for you only.
        Warning: This is not additive. It will replace all current prefixes.
        The real prefixes will no longer work for you.

        **Examples:**
            - `[p]memberprefix !`
            - `[p]memberprefix "! "` - Quotes are needed to use spaces in prefixes.
            - `[p]memberprefix ! ? .` - Sets multiple prefixes.
        **Arguments:**
            - `<prefixes...>` - The prefixes the bot will respond for you only.
        """
        if len(prefixes) == 0:
            await self.config.user(ctx.author).custom_prefixes.clear()
            await ctx.send(_("You now use this server or global prefixes."))
            return
        if any(len(x) > 10 for x in prefixes):
            raise commands.UserFeedbackCheckFailure(
                _(
                    "A prefix is above the maximal length (10 characters).\nThis is possible for global or per-server prefixes, but not for per-member prefixes."
                )
            )
        if any(prefix.startswith("/") for prefix in prefixes):
            raise commands.UserFeedbackCheckFailure(
                _("Prefixes cannot start with `/`, as it conflicts with Discord's slash commands.")
            )
        await self.config.user(ctx.author).custom_prefixes.set(prefixes)
        if len(prefixes) == 1:
            await ctx.send(
                _(
                    "Prefix for you only set. You can use current prefixes or mention the bot to invoke a command, or reset your prefixes with the same command if you forget them."
                )
            )
        else:
            await ctx.send(
                _(
                    "Prefixes for you only set. You can use current prefixes or mention the bot to invoke a command, or reset your prefixes with the same command if you forget them."
                )
            )

    @commands.is_owner()
    @commands.guild_only()
    @commands.hybrid_group(name="setmemberprefix")
    async def configuration(self, ctx: commands.Context) -> None:
        """Configure MemberPrefix."""

    @configuration.command()
    async def resetmemberprefix(
        self, ctx: commands.Context, guild: discord.Guild, user: discord.User
    ) -> None:
        """Clear prefixes for a specified member in a specified server."""
        await self.config.member_from_ids(guild.id, user.id).clear()
        await ctx.send(_("Prefixes cleared for this member in this guild."))

    @configuration.command(hidden=True)
    async def purge(self, ctx: commands.Context, guild: discord.Guild) -> None:
        """Clear all members prefixes for a specified server."""
        await self.config.clear_all_members(guild=guild)
        await ctx.send(_("All members prefixes purged in this guild."))

async def setup(bot: Grief) -> None:
    cog = MemberPrefix(bot)
    await bot.add_cog(cog)