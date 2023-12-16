

from abc import ABC

from grief.core import Config, commands
from grief.core.bot import Grief


class MixinMeta(ABC):
    """
    Base class for well behaved type hint detection with composite class.
    Basically, to keep developers sane when not all attributes are defined in each mixin.

    Strategy borrowed from grief.cogs.mutes.abc
    """

    config: Config
    bot: Grief

    def __init__(self, *_args):
        super().__init__()

    async def cog_unload(self):
        await super().cog_unload()


class CompositeMetaClass(type(commands.Cog), type(ABC)):
    """
    This allows the metaclass used for proper type detection to
    coexist with discord.py's metaclass
    """
