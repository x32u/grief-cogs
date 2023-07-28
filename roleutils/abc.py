
from abc import ABC, abstractmethod

from redbot.core import Config
from redbot.core.bot import Red


class MixinMeta(ABC):
    """
    Base class for well behaved type hint detection with composite class.
    Basically, to keep developers sane when not all attributes are defined in each mixin.

    Strategy borrowed from redbot.cogs.mutes.abc
    """

    config: Config
    bot: Red
    cache: dict

    def __init__(self, *_args):
        self.config: Config
        self.bot: Red
        self.cache: dict

    @abstractmethod
    async def initialize(self):
        ...
