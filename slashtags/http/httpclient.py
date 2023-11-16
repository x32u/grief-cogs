

import json
import logging

import discord

log = logging.getLogger("grief.slashtags.http")


class Route(discord.http.Route):
    BASE = "https://discord.com/api/v8"


class SlashHTTP:
    def __init__(self, cog):
        self.cog = cog
        self.bot = cog.bot
        self.request = cog.bot.http.request

    @property
    def application_id(self):
        return self.cog.application_id

    def add_slash_command(self, command: dict):
        route = Route(
            "POST", "/applications/{application_id}/commands", application_id=self.application_id
        )
        return self.request(route, json=command)

    def edit_slash_command(self, command_id: int, command: dict):
        route = Route(
            "PATCH",
            "/applications/{application_id}/commands/{command_id}",
            application_id=self.application_id,
            command_id=command_id,
        )
        return self.request(route, json=command)

    def remove_slash_command(self, command_id: int):
        route = Route(
            "DELETE",
            "/applications/{application_id}/commands/{command_id}",
            application_id=self.application_id,
            command_id=command_id,
        )
        return self.request(route)

    def get_slash_commands(self):
        route = Route(
            "GET", "/applications/{application_id}/commands", application_id=self.application_id
        )
        return self.request(route)

    def put_slash_commands(self, commands: list):
        route = Route(
            "PUT", "/applications/{application_id}/commands", application_id=self.application_id
        )
        return self.request(route, json=commands)

    def add_guild_slash_command(self, guild_id: int, command: dict):
        route = Route(
            "POST",
            "/applications/{application_id}/guilds/{guild_id}/commands",
            application_id=self.application_id,
            guild_id=guild_id,
        )
        return self.request(route, json=command)

    def edit_guild_slash_command(self, guild_id: int, command_id: int, command: dict):
        route = Route(
            "PATCH",
            "/applications/{application_id}/guilds/{guild_id}/commands/{command_id}",
            application_id=self.application_id,
            guild_id=guild_id,
            command_id=command_id,
        )
        return self.request(route, json=command)

    def remove_guild_slash_command(self, guild_id: int, command_id: int):
        route = Route(
            "DELETE",
            "/applications/{application_id}/guilds/{guild_id}/commands/{command_id}",
            application_id=self.application_id,
            guild_id=guild_id,
            command_id=command_id,
        )
        return self.request(route)

    def get_guild_slash_commands(self, guild_id: int):
        route = Route(
            "GET",
            "/applications/{application_id}/guilds/{guild_id}/commands",
            application_id=self.application_id,
            guild_id=guild_id,
        )
        return self.request(route)

    def put_guild_slash_commands(self, guild_id: int, commands: list):
        route = Route(
            "PUT",
            "/applications/{application_id}/guilds/{guild_id}/commands",
            application_id=self.application_id,
            guild_id=guild_id,
        )
        return self.request(route, json=commands)

    @staticmethod
    def _to_json(obj) -> str:
        return json.dumps(obj, separators=(",", ":"), ensure_ascii=True)
