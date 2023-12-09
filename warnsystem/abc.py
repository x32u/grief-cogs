from abc import ABC
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from grief.core import Config
    from grief.core.bot import Grief
    from .cache import MemoryCache
    from .api import API


class MixinMeta(ABC):
    """
    Base class for well behaved type hint detection with composite class.

    Basically, to keep developers sane when not all attributes are defined in each mixin.

    Credit to https://github.com/Cog-Creators/Grief-DiscordBot (mod cog) for all mixin stuff.
    """

    def __init__(self):
        self.bot: Grief
        self.data: Config
        self.cache: MemoryCache
        self.api: API
