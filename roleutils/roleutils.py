

import asyncio
import logging
from abc import ABC
from typing import Coroutine, Literal

from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.config import Config

from .reactroles import ReactRoles
from .roles import Roles

log = logging.getLogger("red.phenom4n4n.roleutils")

RequestType = Literal["discord_deleted_user", "owner", "user", "user_strict"]


class CompositeMetaClass(type(commands.Cog), type(ABC)):
    """
    This allows the metaclass used for proper type detection to
    coexist with discord.py's metaclass
    """


class RoleUtils(
    Roles,
    ReactRoles,
    commands.Cog,
    metaclass=CompositeMetaClass,
):
    def __init__(self, bot: Red, *_args) -> None:
        self.cache = {}
        self.bot = bot
        self.config = Config.get_conf(
            self,
            identifier=326235423452394523,
            force_registration=True,
        )
        default_guild = {"reactroles": {"channels": [], "enabled": True}}
        self.config.register_guild(**default_guild)

        default_guildmessage = {"reactroles": {"react_to_roleid": {}}}
        self.config.init_custom("GuildMessage", 2)
        self.config.register_custom("GuildMessage", **default_guildmessage)
        super().__init__(*_args)
        self.initialize_task = self.create_task(self.initialize())

    async def red_delete_data_for_user(self, *, requester: RequestType, user_id: int) -> None:
        return

    async def initialize(self):
        log.debug("RoleUtils initialize")
        await super().initialize()

    @staticmethod
    def task_done_callback(task: asyncio.Task):
        try:
            task.result()
        except asyncio.CancelledError:
            pass
        except Exception as error:
            log.exception("Task failed.", exc_info=error)

    def create_task(self, coroutine: Coroutine, *, name: str = None):
        task = asyncio.create_task(coroutine, name=name)
        task.add_done_callback(self.task_done_callback)
        return task
