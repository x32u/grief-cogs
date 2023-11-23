# simport discord
# simport re
# sfrom .abc import MixinMeta
# sfrom datetime import timedelta
# sfrom grief.core import commands, i18n
# sfrom grief.core.utils.chat_formatting import humanize_timedelta

# s_ = i18n.Translator("Mod", __file__)


# sclass Slowmode(MixinMeta):
   # s """
    # sCommands regarding channel slowmode management.
    # s"""

    # @commands.command()
    # @commands.guild_only()
    # @commands.bot_can_manage_channel()
    # @commands.admin_or_can_manage_channel()
    # async def slowmode(
        # self,
        # sctx,
        # s*,
   # s     interval: commands.TimedeltaConverter(
    # s        minimum=timedelta(seconds=0), maximum=timedelta(hours=6), default_unit="seconds"
    # s    ) = timedelta(seconds=0),
   # s ):
     # s   """Changes thread's or text channel's slowmode setting.

     # s   Interval can be anything from 0 seconds to 6 hours.
     # s   Use without parameters to disable.
    # s    """
     # s   seconds = interval.total_seconds()
     # s   await ctx.channel.edit(slowmode_delay=seconds)
     # s   if seconds > 0:
          # s  await ctx.send(
             # s   _("Slowmode interval is now {interval}.").format(
             # s       interval=humanize_timedelta(timedelta=interval)
            # s    )
           # s )
        # else:
           # await ctx.send(_("Slowmode has been disabled."))
