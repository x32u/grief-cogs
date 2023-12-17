

import asyncio
import logging
from typing import Any, Coroutine, Dict, Final, List, Literal, Optional, TypeAlias, Union

from grief.core import commands
from grief.core.bot import Grief
from grief.core.config import Config
from grief.core.utils.chat_formatting import humanize_list

from .abc import CompositeMetaClass
from .reactroles import ReactRoles
from .roles import Roles

log: logging.Logger = logging.getLogger("grief.roleutils")


class RoleUtils(
    Roles,
    ReactRoles,
    commands.Cog,
    metaclass=CompositeMetaClass,
):
    """
    Useful role commands.

    Includes massroling, role targeting, and reaction roles.
    """

    def format_help_for_context(self, ctx: commands.Context) -> str:
        pre_processed = super().format_help_for_context(ctx)
        n = "\n" if "\n\n" not in pre_processed else ""
        return (
            f"{pre_processed}{n}"
        )

    def __init__(self, bot: Grief, *_args: Any) -> None:
        self.bot: Grief = bot
        self.config: Config = Config.get_conf(
            self,
            identifier=326235423452394523,
            force_registration=True,
        )

        default_guild: Dict[
            str, Dict[str, Union[List[int], bool, Dict[str, Union[List[str], bool]]]]
        ] = {
            "reactroles": {"channels": [], "enabled": True},
            "autoroles": {
                "toggle": False,
                "roles": [],
                "bots": {
                    "toggle": False,
                    "roles": [],
                },
                "humans": {
                    "toggle": False,
                    "roles": [],
                },
            },
        }
        self.config.register_guild(**default_guild)

        default_guildmessage: Dict[str, Dict[str, Any]] = {"reactroles": {"react_to_roleid": {}}}
        self.config.init_custom("GuildMessage", 2)
        self.config.register_custom("GuildMessage", **default_guildmessage)

        self.initialize_task: asyncio.Task[Any] = self.create_task(self.initialize())

        self.register_cases: asyncio.Task[Any] = self.create_task(self._register_cases())

        self.cache: Dict[str, Any] = {}

        super().__init__(*_args)

    async def initialize(self) -> None:
        log.debug("RoleUtils initialize")
        await super().initialize()

    @staticmethod
    def task_done_callback(task: asyncio.Task) -> None:
        try:
            task.result()
        except asyncio.CancelledError:
            pass
        except Exception as error:
            log.exception("Task failed.", exc_info=error)

    def create_task(
        self, coroutine: Coroutine, *, name: Optional[str] = None
    ) -> asyncio.Task[Any]:
        task = asyncio.create_task(coroutine, name=name)
        task.add_done_callback(self.task_done_callback)
        return task