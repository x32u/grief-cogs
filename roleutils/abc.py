
from abc import ABC, ABCMeta, abstractmethod
from typing import Any, Dict

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
    cache: dict

    def __init__(self, *_args):
        self.config: Config
        self.bot: Grief
        self.cache: dict

    @abstractmethod
    async def initialize(self):
        ...


class CompositeMetaClass(commands.CogMeta, ABCMeta):
    """
    This allows the metaclass used for proper type detection to
    coexist with discord.py's metaclass
    """
