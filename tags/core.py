

import asyncio
import logging
import re
from collections import defaultdict
from operator import itemgetter
from typing import Coroutine, List, Optional

import aiohttp
import discord
from rapidfuzz import fuzz, process
from grief.core import commands
from grief.core.bot import Grief
from grief.core.config import Config
from grief.core.utils import AsyncIter
from grief.core.utils.chat_formatting import humanize_list

from .abc import CompositeMetaClass
from .errors import MissingTagPermissions, TagCharacterLimitReached
from .mixins import Commands, OwnerCommands, Processor
from .objects import Tag

log = logging.getLogger("red.phenom4n4n.tags")

TAGSCRIPT_LIMIT = 10_000


class Tags(
    Commands,
    OwnerCommands,
    Processor,
    commands.Cog,
    metaclass=CompositeMetaClass,
):
    """
    Create and use tags.

    The TagScript documentation can be found [here](https://docs.grief.cloud/tags-documentation/tags).
    """

    def format_help_for_context(self, ctx: commands.Context):
        pre_processed = super().format_help_for_context(ctx)
        n = "\n" if "\n\n" not in pre_processed else ""
        text = [
            f"{pre_processed}{n}",]
        return "\n".join(text)

    def __init__(self, bot: Grief) -> None:
        self.bot = bot
        self.config = Config.get_conf(
            self,
            identifier=567234895692346562369,
            force_registration=True,
        )
        default_guild = {"tags": {}}
        default_global = {"tags": {}, "blocks": {}, "async_enabled": False, "dot_parameter": False}
        self.config.register_guild(**default_guild)
        self.config.register_global(**default_global)

        self.guild_tag_cache = defaultdict(dict)
        self.global_tag_cache = {}
        self.initialize_task = None
        self.dot_parameter: bool = None
        self.async_enabled: bool = None
        self.initialize_task = self.create_task(self.initialize())

        self.session = aiohttp.ClientSession()
        self.docs: list = []
        if bot._cli_flags.logging_level == logging.DEBUG:
            logging.getLogger("TagScriptEngine").setLevel(logging.DEBUG)

        bot.add_dev_env_value("tags", lambda ctx: self)
        super().__init__()

    async def cog_unload(self):
        try:
            await self.__unload()
        except Exception as e:
            log.exception("An error occurred during cog unload.", exc_info=e)

    async def __unload(self):
        self.bot.remove_dev_env_value("tags")
        if self.initialize_task:
            self.initialize_task.cancel()
        await self.session.close()
        await super().cog_unload()

    async def red_delete_data_for_user(self, *, requester: str, user_id: int):
        if requester not in ("discord_deleted_user", "user"):
            return
        guilds_data = await self.config.all_guilds()
        for guild_id, data in guilds_data.items():
            guild = self.bot.get_guild(guild_id)
            if guild and data["tags"]:
                for name, tag in data["tags"].items():
                    if str(user_id) in str(tag["author_id"]):
                        async with self.config.guild(guild).tags() as t:
                            del t[name]

    def task_done_callback(self, task: asyncio.Task):
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

    async def initialize(self):
        data = await self.config.all()
        await self.initialize_interpreter(data)

        global_tags = data["tags"]
        async for global_tag_name, global_tag_data in AsyncIter(global_tags.items(), steps=50):
            tag = Tag.from_dict(self, global_tag_name, global_tag_data)
            tag.add_to_cache()
            if "created_at" not in global_tag_data:
                await tag.update_config()

        guilds_data = await self.config.all_guilds()
        async for guild_id, guild_data in AsyncIter(guilds_data.items(), steps=100):
            await self.cache_guild(guild_id, guild_data)

        log.debug("Built tag cache.")

    async def cache_guild(self, guild_id: int, guild_data: dict):
        async for tag_name, tag_data in AsyncIter(guild_data["tags"].items(), steps=50):
            tag = Tag.from_dict(self, tag_name, tag_data, guild_id=guild_id)
            tag.add_to_cache()
            if "created_at" not in tag_data:
                await tag.update_config()

    def search_tag(self, tag_name: str, guild: Optional[discord.Guild] = None) -> List[Tag]:
        tags = self.get_unique_tags(guild)
        matches = []
        for tag in tags:
            name_score = fuzz.ratio(tag_name.lower(), tag.name.lower())

            if alias_search := process.extractOne(tag_name, tag.aliases, scorer=fuzz.QRatio):
                alias_score = alias_search[1]
            else:
                alias_score = 0

            if tag_name.lower() in tag.tagscript.lower():
                script_score = 100
            elif script_search := process.extractOne(
                tag_name, re.findall(r"\w+", tag.tagscript), scorer=fuzz.QRatio
            ):
                script_score = script_search[1]
            else:
                script_score = 0

            scores = (name_score, alias_score, script_score)
            final_score = sum(scores)
            log.debug(
                "search: %r | %s NAME: %s ALIAS: %s SCRIPT %s FINAL %s",
                tag_name,
                tag.name,
                name_score,
                alias_score,
                script_score,
                final_score,
            )
            if any(score >= 70 for score in scores) or final_score > 180:
                matches.append((final_score, tag))
        return [match[1] for match in sorted(matches, key=itemgetter(0), reverse=True)]

    def get_tag(
        self,
        guild: Optional[discord.Guild],
        tag_name: str,
        *,
        check_global: bool = True,
        global_priority: bool = False,
    ) -> Optional[Tag]:
        tag = None
        if global_priority and check_global:
            return self.global_tag_cache.get(tag_name)
        if guild is not None:
            tag = self.guild_tag_cache[guild.id].get(tag_name)
        if tag is None and check_global:
            tag = self.global_tag_cache.get(tag_name)
        return tag

    def get_unique_tags(self, guild: Optional[discord.Guild] = None) -> List[Tag]:
        path = self.guild_tag_cache[guild.id] if guild else self.global_tag_cache
        return sorted(set(path.values()), key=lambda t: t.name)

    async def validate_tagscript(self, ctx: commands.Context, tagscript: str):
        length = len(tagscript)
        if length > TAGSCRIPT_LIMIT:
            raise TagCharacterLimitReached(TAGSCRIPT_LIMIT, length)
        output = self.engine.process(tagscript)
        if self.async_enabled:
            output = await output
        is_owner = await self.bot.is_owner(ctx.author)
        if is_owner:
            return True
        author_perms = ctx.channel.permissions_for(ctx.author)
        if output.actions.get("overrides") and not author_perms.manage_guild:
            raise MissingTagPermissions(
                "You must have **Manage Server** permissions to use the `override` block."
            )
        if output.actions.get("allowed_mentions") and not is_owner:
            raise MissingTagPermissions(
                "You must have **Mention Everyone** permissions to use the `allowedmentions` block."
            )
        return True
