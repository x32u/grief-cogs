
import requests
import topgg
from discord.ext import commands, tasks

from dotenv import load_dotenv, dotenv_values
from discord.ext.commands import Context
from grief.core.bot import Grief

load_dotenv()
dotenv_values()

class Ok(commands.Cog):
    
    def format_help_for_context(self, ctx: commands.Context) -> str:
        pre_processed = super().format_help_for_context(ctx)
        return (f"{pre_processed}\n")
    
    def __init__(self, bot: Grief):
        self.bot: Grief = bot
        self.topggtoken = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjcxNjkzOTI5NzAwOTQzNDY1NiIsImJvdCI6dHJ1ZSwiaWF0IjoxNzA2MTU5NTM4fQ.sv_iYnZzcTMoSRm3Q7TPRBY517VPxDYRo6HKms2ksXU"  # Set this to your bot's Top.gg token
        self.topgg_client = topgg.DBLClient(self.bot, self.topggtoken, autopost=True)
        self.update_stats.start()
        

    @tasks.loop(minutes=25)
    async def update_stats(self):
        okkkk = self.bot.get_channel(1199945545117085746)
        """This function runs every 30 minutes to automatically update your server count."""
        try:
            await self.topggpy.post_guild_count()
            msg = await okkkk.send(f"**Top.gg API:** Posted server count ({self.topggpy.guild_count})")
            await msg.add_reaction("<:grief_check:1107472942830456892>")
        except Exception as e:
             msg = await okkkk.send(f"**Top.gg API:** Failed to post server count\n{e.__class__.__name__}: {e}")
             await msg.add_reaction("<:grief_x:1107472962333978655>")

    @update_stats.before_loop
    async def before_update_stats(self):
        await self.bot.wait_until_red_ready()

async def setup(bot: Grief):
    await bot.add_cog(Ok(bot))  