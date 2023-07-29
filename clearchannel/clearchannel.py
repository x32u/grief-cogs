
from AAA3A_utils import Cog, CogsUtils, Settings  # isort:skip
from redbot.core import commands, Config  # isort:skip
from redbot.core.bot import Red  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

from AAA3A_utils.settings import CustomMessageConverter

from .dashboard_integration import DashboardIntegration

# Credits:
# General repo credits.

_ = Translator("ClearChannel", __file__)


@cog_i18n(_)
class ClearChannel(Cog, DashboardIntegration):

    def __init__(self, bot: Red) -> None:
        super().__init__(bot=bot)

        self.config: Config = Config.get_conf(
            self,
            identifier=205192943327321000143939875896557571750,  # 837018163805
            force_registration=True,
        )

    async def cog_load(self):
        await super().cog_load()

    async def red_delete_data_for_user(self, *args, **kwargs) -> None:
        """Nothing to delete."""
        return

    async def red_get_data_for_user(self, *args, **kwargs) -> typing.Dict[str, typing.Any]:
        """Nothing to get."""
        return {}

    @commands.guild_only()
    @commands.bot_has_permissions(manage_channels=True)
    @commands.admin_or_permissions(manage_channels=True)
    @commands.hybrid_command(name="nuke")
    async def nuke_channel(self, ctx: commands.Context, confirmation: bool = False) -> None:
        """Delete all messages from the current channel by duplicating it and then deleting it.
        """
        config = await self.config.guild(ctx.guild).all()
        old_channel = ctx.channel
        channel_position = old_channel.position

        if not confirmation and not ctx.assume_yes:
            embed: discord.Embed = discord.Embed()
            embed.title = _("Nuke")
            embed.description = _(
                "Nuke channel {old_channel.mention} ({old_channel.id})?\n The channel will be deleted and recreated."
            ).format(old_channel=old_channel)
            embed.color = 0x313338
            if not await CogsUtils.ConfirmationAsk(
                ctx, content=f"{ctx.author.mention}", embed=embed
            ):
                await CogsUtils.delete_message(ctx.message)
                return

        reason = _("Nuke requested by {ctx.author} ({ctx.author.id}).").format(ctx=ctx)
        new_channel = await old_channel.clone(reason=reason)
        await old_channel.delete(reason=reason)
        await new_channel.edit(
            position=channel_position,
            reason=reason,
        )
        self.log.info(
            f"{ctx.author} ({ctx.author.id}) deleted all messages in channel {old_channel.name} ({old_channel.id})."
        ),
        await new_channel.send("first")