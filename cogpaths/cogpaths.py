import inspect
import os
import pathlib

from grief.core import commands, data_manager
from grief.core.bot import Red
from grief.core.commands import CogConverter
from grief.core.config import Config
from grief.core.utils.chat_formatting import box


class CogPaths(commands.Cog):
    
    def __init__(self, bot: Red):
        self.bot = bot

    async def red_delete_data_for_user(self, **kwargs):
        return

    @commands.is_owner()
    @commands.command(aliases=["cogpaths"])
    async def cogpath(self, ctx: commands.Context, cog: CogConverter):
        """Get the paths for a cog."""
        cog_path = pathlib.Path(inspect.getfile(cog.__class__)).parent.resolve()
        cog_data_path = pathlib.Path(data_manager.cog_data_path() / cog.qualified_name).resolve()
        if not os.path.exists(cog_data_path):
            cog_data_path = None
            if not isinstance(getattr(cog, "config", None), Config):
                reason = "This cog does not store any data, or does not use Red's Config API."
            else:
                reason = "This cog had its data directory removed."
        message = "Cog path: {}\nData path: {}".format(cog_path, cog_data_path or reason)
        await ctx.send(box(message, lang="yaml"))
