

import asyncio
import asyncio.subprocess as asp
import contextlib
import os
from typing import Any, Dict, List, Literal

from grief.core import commands
from grief.core.bot import Grief
from grief.core.commands import NoParseOptional as Optional
from grief.core.config import Config
from grief.core.utils.chat_formatting import inline

from .errors import ProcessTerminatedEarly
from .utils import get_env, send_pages, strip_code_block, wait_for_result

RequestType = Literal["discord_deleted_user", "owner", "user", "user_strict"]


class Shell(commands.Cog):
    """Run shell commands on bot's system from Discord."""

    replacement_shell: Optional[str]

    def __init__(self, bot: Grief) -> None:
        self.bot = bot
        self.config = Config.get_conf(self, 176070082584248320, force_registration=True)
        self.config.register_global(replacement_shell=None)
        self.active_processes: List[asp.Process] = []
        self._killing_lock = asyncio.Lock()

    async def cog_load(self) -> None:
        self.replacement_shell = (
            await self.config.replacement_shell() if os.name == "posix" else None
        )

    async def red_get_data_for_user(self, *, user_id: int) -> Dict[str, Any]:
        # this cog does not story any data
        return {}

    async def red_delete_data_for_user(
        self, *, requester: RequestType, user_id: int
    ) -> None:
        # this cog does not story any data
        pass

    @commands.is_owner()
    @commands.command()
    async def shell(self, ctx: commands.Context, *, command: str) -> None:
        """Run shell command."""
        await self._shell_command(ctx, command)

    @commands.is_owner()
    @commands.command()
    async def shellq(self, ctx: commands.Context, *, command: str) -> None:
        """
        Run shell command quietly.

        If command's exit code is 0, `[p]shellq` will only send a tick reaction.
        Otherwise, the result will be shown as with regular `[p]shell` command.
        """
        await self._shell_command(ctx, command, send_message_on_success=False)

    async def _shell_command(
        self,
        ctx: commands.Context,
        command: str,
        *,
        send_message_on_success: bool = True,
    ) -> None:
        command = strip_code_block(command)
        async with ctx.typing():
            async with self._killing_lock:
                try:
                    p = await asp.create_subprocess_shell(
                        command,
                        stdout=asp.PIPE,
                        stderr=asp.STDOUT,
                        env=get_env(),
                        executable=self.replacement_shell,
                    )
                except (FileNotFoundError, NotADirectoryError, PermissionError):
                    command_1 = inline(f"{ctx.clean_prefix}shellset shell")
                    command_2 = inline(f"{ctx.clean_prefix}shellset shell reset")
                    await ctx.send(
                        "It appears the shell you have set does not exist."
                        f" Try to set another one with {command_1} or reset it to"
                        f" default with {command_2}."
                    )
                    return
                self.active_processes.append(p)

            try:
                output = await wait_for_result(p)
            except ProcessTerminatedEarly as e:
                output = e.partial_output
                prefix = (
                    "**Command was terminated early and this is a partial output.**\n"
                )
            else:
                prefix = ""

            async with self._killing_lock:
                with contextlib.suppress(ValueError):
                    self.active_processes.remove(p)

        if not send_message_on_success and p.returncode == 0:
            await ctx.tick()
        else:
            await send_pages(ctx, command=command, output=output, prefix=prefix)

    @commands.is_owner()
    @commands.command()
    async def killshells(self, ctx: commands.Context) -> None:
        """Kill all shell processes started by Shell cog."""
        async with self._killing_lock:
            for p in reversed(self.active_processes):
                # in case some Process is still here after it terminated
                if p.returncode is None:
                    p.kill()
                self.active_processes.pop()
        await ctx.send("Killed all active shell processes.")

    if os.name == "posix":

        @commands.is_owner()
        @commands.group()
        async def shellset(self, ctx: commands.Context) -> None:
            """Manage settings of the Shell cog."""

        @shellset.group(name="shell", invoke_without_command=True)
        async def shellset_shell(
            self, ctx: commands.Context, replacement_shell: str
        ) -> None:
            """
            Set a replacement shell for the default ``/bin/sh``.

            This needs to be a full path to the replacement shell.
            The input is not validated.

            Only works on POSIX systems.
            """
            await self.config.replacement_shell.set(replacement_shell)
            self.replacement_shell = replacement_shell
            await ctx.send("This shell will now be used instead of the default.")

        @shellset_shell.command(name="reset")
        async def shellset_shell_reset(self, ctx: commands.Context) -> None:
            """Reset the replacement shell back to the default."""
            await self.config.replacement_shell.clear()
            self.replacement_shell = None
            await ctx.send("The default shell will now be used.")
