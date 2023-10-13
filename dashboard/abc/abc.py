from abc import ABC, abstractmethod

from grief.core import Config, commands, checks
from grief.core.bot import Red


class MixinMeta(ABC):
    """Base class for well behaved type hint detection with composite class.
    Basically, to keep developers sane when not all attributes are defined in each mixin.
    """

    def __init__(self, *_args):
        self.config: Config
        self.bot: Red

    @checks.is_owner()
    @commands.group(name="dashboard")
    async def dashboard(self, ctx: commands.Context):
        """Group command for controlling the web dashboard for Red."""
        pass
