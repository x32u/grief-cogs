import discord
from grief.core import Config, commands
from grief.core.bot import Grief
from grief.core.utils.chat_formatting import box, humanize_list

from .listen import Listen


class AntiNuke(Listen, commands.Cog):
    """
    Anti-Nuke System for guild owners.

    Monitors the following events:
    Kicks & Bans
    Channel Creation/Edit/Deletion
    Role Creation/Edit/Deletion

    Set a cooldown(in seconds)
    Set an overload count(X events in X seconds)
    Set an action(kick, ban, strip, notify)

    If a user or bot exceeds X mod events within X seconds, the set action will be performed
    """

    def format_help_for_context(self, ctx):
        helpcmd = super().format_help_for_context(ctx)
        return f"{helpcmd}"

    def __init__(self, bot: Grief):
        super().__init__()
        self.bot = bot
        self.config = Config.get_conf(self, 117, force_registration=True)

        default_guild = {
            "enabled": False,
            "log": 0,  # Log channel
            "cooldown": 10,  # Seconds in between actions
            "overload": 3,  # Actions within cooldown time
            "dm": False,  # Whether to DM the user the bot kicks
            "action": "notify",  # Valid types are 'kick', 'ban', 'strip', and 'notify'
            "ignore_bots": False,  # Whether to ignore other bots
            "whitelist": [],  # passport of trusted users(or bots)
        }
        self.config.register_guild(**default_guild)

        self.settings = {}
        self.cache = {}
        self.first_run = True

    async def initialize(self, guild_id: int = 0):
        await self.bot.wait_until_red_ready()
        conf = await self.config.all_guilds()
        for gid, settings in conf.items():
            if not settings:
                continue
            if guild_id and gid != guild_id:
                continue
            self.settings[gid] = settings

    @commands.group()
    @commands.is_owner()
    @commands.guild_only()
    async def antinuke(self, ctx):
        """
        Anti-Nuke System for guild owners.

        Monitors the following events:
        Kicks & Bans
        Channel Creation/Edit/Deletion
        Role Creation/Edit/Deletion

        Set a cooldown(in seconds)
        Set an overload count(X events in X seconds)
        Set an action(kick, ban, strip, notify)

        If a user or bot exceeds X mod events within X seconds, the set action will be performed
        """

    @antinuke.command()
    async def enable(self, ctx):
        """Enable/Disable the antinuke system"""
        toggle = await self.config.guild(ctx.guild).enabled()
        if toggle:
            await self.config.guild(ctx.guild).enabled.set(False)
            await ctx.send("antinuke system **Disabled**")
        else:
            await self.config.guild(ctx.guild).enabled.set(True)
            await ctx.send("antinuke system **Enabled**")
        await self.initialize(ctx.guild)

    @antinuke.command(hidden=True)
    async def ignorebots(self, ctx):
        """
        Toggle whether other bots are ignored

        **NOTE:** Bot specific roles (the role created when the bot joins) cannot be removed.
        If antinuke is set to strip roles, and a bot triggers it while having an integrated role, antinuke will fail
        to remove the role from it.
        """
        toggle = await self.config.guild(ctx.guild).ignore_bots()
        if toggle:
            await self.config.guild(ctx.guild).ignore_bots.set(False)
            await ctx.send("Other bots will **not** be ignored")
        else:
            await self.config.guild(ctx.guild).ignore_bots.set(True)
            await ctx.send("Other bots will be ignored")
        await self.initialize(ctx.guild)

    @antinuke.command(hidden=True)
    async def dm(self, ctx):
        """Toggle whether the bot sends the user a DM when a kick or ban action is performed"""
        toggle = await self.config.guild(ctx.guild).dm()
        if toggle:
            await self.config.guild(ctx.guild).dm.set(False)
            await ctx.send("antinuke trigger DM **Disabled**")
        else:
            await self.config.guild(ctx.guild).dm.set(True)
            await ctx.send("antinuke trigger DM **Enabled**")
        await self.initialize(ctx.guild)

    @antinuke.command()
    async def logchannel(self, ctx: commands.Context, channel: discord.TextChannel):
        """Set the log channel for Anti-Nuke kicks"""
        if not channel.permissions_for(ctx.me).embed_links:
            return await ctx.send("I dont have permission to send embeds in that channel!")
        await self.config.guild(ctx.guild).log.set(channel.id)
        await ctx.tick()
        await self.initialize(ctx.guild)

    @antinuke.command()
    async def cooldown(self, ctx: commands.Context, cooldown: int):
        """Cooldown (in seconds) for antinuke to trigger"""
        await self.config.guild(ctx.guild).cooldown.set(cooldown)
        await ctx.tick()
        await self.initialize(ctx.guild)

    @antinuke.command()
    async def overload(self, ctx: commands.Context, overload: int):
        """How many mod actions can be done within the set cooldown

        **Mod actions include:**
        Kicks & Bans
        Channel Creation/Edit/Deletion
        Role Creation/Edit/Deletion
        """
        if not ctx.guild.me.guild_permissions.view_audit_log:
            return await ctx.send(
                "I do not have permission to view the audit log for this server!"
            )
        action = await self.config.guild(ctx.guild).action()
        if action == "kick":
            if not ctx.guild.me.guild_permissions.kick_members:
                return await ctx.send("I do not have permission to kick members!")
        elif action == "ban":
            if not ctx.guild.me.guild_permissions.ban_members:
                return await ctx.send("I do not have permission to ban members!")
        elif action == "strip":
            if not ctx.guild.me.guild_permissions.manage_roles:
                return await ctx.send("I do not have permission to manage roles!")
        await self.config.guild(ctx.guild).overload.set(overload)
        await ctx.tick()
        await self.initialize(ctx.guild)

    @antinuke.command()
    async def action(self, ctx: commands.Context, action: str):
        """
        Set the action for the bot to take when antinuke is triggered

        **Actions**
        `kick` - kick the user
        `ban` - ban the user
        `strip` - strip all roles with permissions from user
        `notify` - just sends a report to the log channel
        """
        if not ctx.guild.me.guild_permissions.view_audit_log:
            return await ctx.send(
                "I do not have permission to view the audit log for this server!"
            )
        action = action.lower()
        if action not in ["kick", "ban", "notify", "strip"]:
            return await ctx.send("That is not a valid action type!")
        if action == "kick":
            if not ctx.guild.me.guild_permissions.kick_members:
                return await ctx.send("I do not have permission to kick members!")
        elif action == "ban":
            if not ctx.guild.me.guild_permissions.ban_members:
                return await ctx.send("I do not have permission to ban members!")
        elif action == "strip":
            if not ctx.guild.me.guild_permissions.manage_roles:
                return await ctx.send("I do not have permission to manage roles!")
        await self.config.guild(ctx.guild).action.set(action)
        await ctx.tick()
        await ctx.send(f"Action has been set to `{action}`")
        await self.initialize(ctx.guild)

    @antinuke.command()
    async def whitelist(self, ctx: commands.Context, user: discord.Member):
        """Add/Remove users from the trust"""
        async with self.config.guild(ctx.guild).whitelist() as whitelist:
            if user.id in whitelist:
                whitelist.remove(user.id)
                await ctx.send(f"{user} has been removed from the whitelist!")
            else:
                whitelist.append(user.id)
                await ctx.send(f"{user} has been added to the whitelist!")

    @antinuke.command()
    @commands.bot_has_permissions(embed_links=True)
    async def view(self, ctx):
        """View the antinuke settings"""
        conf = await self.config.guild(ctx.guild).all()
        lchan = self.bot.get_channel(conf["log"]) if conf["log"] else "Not Set"
        em = discord.Embed(
            title="antinuke settings",
            description=f"`Enabled:    `{conf['enabled']}\n"
            f"`Cooldown:   `{conf['cooldown']}\n"
            f"`Overload:   `{conf['overload']}\n"
            f"`Action:     `{conf['action']}\n"
            f"`LogChannel: `{lchan}",
        )
        await ctx.send(embed=em)
        perms = {
            "manage_roles": ctx.guild.me.guild_permissions.manage_roles,
            "ban_members": ctx.guild.me.guild_permissions.ban_members,
            "kick_members": ctx.guild.me.guild_permissions.kick_members,
            "view_audit_log": ctx.guild.me.guild_permissions.view_audit_log,
        }
        missing = [k for k, v in perms.items() if not v]
        if missing:
            await ctx.send(
                f"Just a heads up, I do not have the following permissions\n{box(humanize_list(missing))}"
            )
