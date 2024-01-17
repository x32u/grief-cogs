sin
resent
Do Not Disturb

sin — Today at 3:19 PM
u can make it into multiple if u want
Sam — Today at 3:20 PM
Nah I mean I don't have access to whatever these are
Image
So I have no idea what these do
sin — Today at 3:21 PM
the grief.core.bot import Grief just imports the shit for the self, bot: Grief 
and sec for the other 2 files
i would js give u access to the repo but i could see u doing some gay shit
Sam — Today at 3:23 PM
💀
Like what
sin — Today at 3:24 PM
leaking the code
Sam — Today at 3:24 PM
My ass does not care about the grief source code
sin — Today at 3:24 PM
there u go
Sam — Today at 3:25 PM
:dead:
Why is Github Desktop being so faggot
sin — Today at 3:28 PM
i see u opening a bunch of files
Sam — Today at 3:28 PM
im trying
to find
the
stupid
fucking
vanity file
sin — Today at 3:29 PM
thts
Sam — Today at 3:29 PM
Image
sin — Today at 3:29 PM
ona diff repo
cogs and main code are seperate
Sam — Today at 3:29 PM
:AMkannamiddlefinger:
sin — Today at 3:30 PM
that vanity cog is just one file though
so you dont need added to it
Image
Sam — Today at 3:31 PM
ic
sin — Today at 3:31 PM
the reason why its setup that way is so i dont gotta restart the bot each time i change a cog
Sam — Today at 3:31 PM
So like whats the main issue apart from you overcomplicate giving the role
:stare:
sin — Today at 3:32 PM
its not caching
so basically i have to reload the cog before it starts giving the role out after its set
which is obv bad
Sam — Today at 3:33 PM
Hmm
okie
sin — Today at 3:34 PM
im not dumb but im not smart enough to fuck with something as complicated as that yet
i have ADHD so too much shit going on 💀
Sam — Today at 3:34 PM
So just issues with the caching after you toggle the shit
;sle
:sleepyCat:
or after setting the role
sin — Today at 3:35 PM
yea
p sure i broke more shit tryna fix it tho
les load it rq n ill show u what i mean
Sam — Today at 3:37 PM
:stare:
which server
sin — Today at 3:37 PM
Image
im not good w caching, well i dont have much experience tryna code with needing it
Sam — Today at 3:39 PM
either im just hella retarded
but don't you have to like first set the vanity_cache to a default value
in the constructor
    def __init__(self, bot: Grief):
        self.bot: Grief = bot
        self.logger: Logger = getLogger("grief.vanity")
        self.config = Config.get_conf(self, identifier=12039492, force_registration=True)
        default_guild = {"role": None, "toggled": False, "channel": None, "vanity": None,}
        self.cached = {}
        self.config.register_global(**default_guild)
        self.settings = {}
        self.first_run = True
Cause that has nothing for vanity_cache
sin — Today at 3:39 PM
yea but u still gotta cache the van, no?
i read that wrong
yea prob
ill show you what worked for dpy1
Sam — Today at 3:40 PM
also like
what's the point of self.cached
self.vanity_cache is already a cache
wouldn't this already try update cache
Image
I'd do like
sin — Today at 3:42 PM
import asyncio
import typing
from logging import Logger, getLogger

import discord
from grief.core import Config, commands
Expand
init__.py
10 KB
that worked for dpy1 but obv shit changed
Sam — Today at 3:42 PM
what is dpy1
also that is done so retardedly in that one
sin — Today at 3:43 PM
discordpy1
discordpy 11
discordpy 1 
sin — Today at 3:43 PM
i mean
js update it how you think would work n ill try it i guess
Sam — Today at 3:44 PM
what is x in this
Image
does this return guild ids?
sin — Today at 3:44 PM
either the invite code or guildid
yea it’s the server if
yea it’s the server id 
Sam — Today at 3:44 PM
welp let's hope it's guild id rq
sin — Today at 3:44 PM
i’m a bit high
Sam — Today at 3:46 PM
I don't expect this to exactly work I just wanna see what happens
import asyncio
import typing
from logging import Logger, getLogger

import discord
from grief.core import Config, commands
Expand
init__.py
10 KB
oh wait
oops 1 sec
don't use that
import asyncio
import typing
from logging import Logger, getLogger

import discord
from grief.core import Config, commands
Expand
init__.py
11 KB
there we go
Don't have any auto complete is pain
sin
 started a call.
 — Today at 3:47 PM
Sam — Today at 3:47 PM
bleh
sin — Today at 3:47 PM
jvc
Sam — Today at 3:47 PM
I did
sin — Today at 3:49 PM
this
not
takes
forever
to boot
Sam — Today at 3:49 PM
💀
:dead:
sin — Today at 3:50 PM
Image
Sam — Today at 3:51 PM
import asyncio
import typing
from logging import Logger, getLogger

import discord
from grief.core import Config, commands
from grief.core.bot import Grief

LISTENER_NAME: str = "on_presence_update" if discord.version_info.major == 2 else "on_member_update"

class Vanity(commands.Cog):
    """For level 3 servers, award your users for advertising the vanity in their status. """

    def format_help_for_context(self, ctx: commands.Context) -> str:
        pre_processed = super().format_help_for_context(ctx)
        return (f"{pre_processed}\n")

    def __init__(self, bot: Grief):
        self.bot: Grief = bot
        self.logger: Logger = getLogger("grief.vanity")
        self.config = Config.get_conf(self, identifier=12039492, force_registration=True)
        default_guild = {"role": None, "toggled": False, "channel": None, "vanity": None,}
        self.config.register_global(**default_guild)
        self.settings = {}
        self.first_run = True
        self.vanity_cache = {}
        self.update_cache()

    async def update_cache(self):
        await self.bot.wait_until_red_ready()
        data = await self.config.all_guilds()
        for x in data:
            vanity = data[x]["vanity"]
            if vanity:
                return self.vanity_cache[x] = vanity
        
        return self.vanity_cache

    async def safe_send(self, channel: discord.TextChannel, embed: discord.Embed) -> None:
        try:
            await channel.send(embed=embed)
        except (discord.Forbidden, discord.HTTPException) as e:
            self.logger.warning(
                f"Failed to send message to {channel.name} in {channel.guild.name}/{channel.guild.id}: {str(e)}"
            )

    @commands.Cog.listener(LISTENER_NAME)
    async def on_vanity_trigger(self, before: discord.Member, after: discord.Member) -> None:
        if not self.vanity_cache[after.guild.id]:
            await self.update_cache()
            
        if before.bot:
            return
        guild: discord.Guild = after.guild
        data = await self.config.guild(guild).all()
        if not data["toggled"]:
            return
        if not data["role"] or not data["channel"]:
            return
        #if not "VANITY_URL" in guild.features:
            #return
        vanity: str = "/" + self.vanity_cache[guild.id]
        role: discord.Role = guild.get_role(int(data["role"]))
        log_channel: discord.TextChannel = guild.get_channel(int(data["channel"]))
        if not role:
            self.logger.info(f"Vanity role not found for {guild.name}/{guild.id}, skipping")
            return
        if not log_channel:
            self.logger.info(f"Vanity log channel not found for {guild.name}/{guild.id}, skipping")
            return
        if role.position >= guild.me.top_role.position:
            self.logger.info(f"Vanity role is higher than me in {guild.name}/{guild.id}, skipping")
            return
        
        before_custom_activity: typing.List[discord.CustomActivity] = [
            activity
            for activity in before.activities
            if isinstance(activity, discord.CustomActivity)
        ]
        after_custom_activity: typing.List[discord.CustomActivity] = [
            activity
            for activity in after.activities
            if isinstance(activity, discord.CustomActivity)
        ]
        has_in_status_embed = discord.Embed(
            color=0x2F3136,
            description=f"Thanks {after.mention} for having {vanity} in your status.\nI rewarded you with {role.mention}",
        )
        has_in_status_embed.set_footer(
            text=self.bot.user.name,
            icon_url="https://cdn.discordapp.com/emojis/886356428116357120.gif",
        )

        if not before_custom_activity and after_custom_activity:
            if after_custom_activity[0].name is not None:
                if vanity.lower() in after_custom_activity[0].name.lower():
                    if role.id not in after._roles:
                        try:
                            await after.add_roles(role)
                        except (discord.Forbidden, discord.HTTPException) as e:
... (122 lines left)
Collapse
init__.py
10 KB
Not nice to have no auto complete
:sad:
﻿
import asyncio
import typing
from logging import Logger, getLogger

import discord
from grief.core import Config, commands
from grief.core.bot import Grief

LISTENER_NAME: str = "on_presence_update" if discord.version_info.major == 2 else "on_member_update"

class Vanity(commands.Cog):
    """For level 3 servers, award your users for advertising the vanity in their status. """

    def format_help_for_context(self, ctx: commands.Context) -> str:
        pre_processed = super().format_help_for_context(ctx)
        return (f"{pre_processed}\n")

    def __init__(self, bot: Grief):
        self.bot: Grief = bot
        self.logger: Logger = getLogger("grief.vanity")
        self.config = Config.get_conf(self, identifier=12039492, force_registration=True)
        default_guild = {"role": None, "toggled": False, "channel": None, "vanity": None,}
        self.config.register_global(**default_guild)
        self.settings = {}
        self.first_run = True
        self.vanity_cache = {}
        self.update_cache()

    async def update_cache(self):
        await self.bot.wait_until_red_ready()
        data = await self.config.all_guilds()
        for x in data:
            vanity = data[x]["vanity"]
            if vanity:
                return self.vanity_cache[x] = vanity
        
        return self.vanity_cache

    async def safe_send(self, channel: discord.TextChannel, embed: discord.Embed) -> None:
        try:
            await channel.send(embed=embed)
        except (discord.Forbidden, discord.HTTPException) as e:
            self.logger.warning(
                f"Failed to send message to {channel.name} in {channel.guild.name}/{channel.guild.id}: {str(e)}"
            )

    @commands.Cog.listener(LISTENER_NAME)
    async def on_vanity_trigger(self, before: discord.Member, after: discord.Member) -> None:
        if not self.vanity_cache[after.guild.id]:
            await self.update_cache()
            
        if before.bot:
            return
        guild: discord.Guild = after.guild
        data = await self.config.guild(guild).all()
        if not data["toggled"]:
            return
        if not data["role"] or not data["channel"]:
            return
        #if not "VANITY_URL" in guild.features:
            #return
        vanity: str = "/" + self.vanity_cache[guild.id]
        role: discord.Role = guild.get_role(int(data["role"]))
        log_channel: discord.TextChannel = guild.get_channel(int(data["channel"]))
        if not role:
            self.logger.info(f"Vanity role not found for {guild.name}/{guild.id}, skipping")
            return
        if not log_channel:
            self.logger.info(f"Vanity log channel not found for {guild.name}/{guild.id}, skipping")
            return
        if role.position >= guild.me.top_role.position:
            self.logger.info(f"Vanity role is higher than me in {guild.name}/{guild.id}, skipping")
            return
        
        before_custom_activity: typing.List[discord.CustomActivity] = [
            activity
            for activity in before.activities
            if isinstance(activity, discord.CustomActivity)
        ]
        after_custom_activity: typing.List[discord.CustomActivity] = [
            activity
            for activity in after.activities
            if isinstance(activity, discord.CustomActivity)
        ]
        has_in_status_embed = discord.Embed(
            color=0x2F3136,
            description=f"Thanks {after.mention} for having {vanity} in your status.\nI rewarded you with {role.mention}",
        )
        has_in_status_embed.set_footer(
            text=self.bot.user.name,
            icon_url="https://cdn.discordapp.com/emojis/886356428116357120.gif",
        )

        if not before_custom_activity and after_custom_activity:
            if after_custom_activity[0].name is not None:
                if vanity.lower() in after_custom_activity[0].name.lower():
                    if role.id not in after._roles:
                        try:
                            await after.add_roles(role)
                        except (discord.Forbidden, discord.HTTPException) as e:
                            self.logger.warning(
                                f"Failed to add role to {after} in {guild.name}/{guild.id}: {str(e)}"
                            )
                            return
                    self.bot.loop.create_task(self.safe_send(log_channel, has_in_status_embed))
        elif before_custom_activity and not after_custom_activity:
            if before_custom_activity[0].name is not None:
                if vanity.lower() in before_custom_activity[0].name.lower():
                    if role.id in after._roles:
                        try:
                            await after.remove_roles(role)
                        except (discord.Forbidden, discord.HTTPException) as e:
                            self.logger.warning(
                                f"Failed to remove role from {after} in {guild.name}/{guild.id}: {str(e)}"
                            )
        elif (
            before_custom_activity
            and after_custom_activity
            and before_custom_activity[0] != after_custom_activity[0]
        ):
            if before_custom_activity[0].name is None:
                before_match = False
            else:
                before_match = vanity.lower() in before_custom_activity[0].name.lower()
            if after_custom_activity[0].name is None:
                after_match = False
            else:
                after_match = vanity.lower() in after_custom_activity[0].name.lower()
            if not before_match and after_match:
                if role.id not in after._roles:
                    try:
                        await after.add_roles(role)
                    except (discord.Forbidden, discord.HTTPException) as e:
                        self.logger.warning(
                            f"Failed to add role to {after} in {guild.name}/{guild.id}: {str(e)}"
                        )
                        return
                self.bot.loop.create_task(self.safe_send(log_channel, has_in_status_embed))
            elif before_match and not after_match:
                if role.id in after._roles:
                    try:
                        await after.remove_roles(role)
                    except (discord.Forbidden, discord.HTTPException) as e:
                        self.logger.warning(
                            f"Failed to remove role from {after} in {guild.name}/{guild.id}: {str(e)}"
                        )
        if not before_custom_activity and not after_custom_activity:
            # cope with the case where the user does not have a custom status
            if role.id in after._roles:
                try:
                    await after.remove_roles(role)
                except (discord.Forbidden, discord.HTTPException) as e:
                    self.logger.warning(
                        f"Failed to remove role from {after} in {guild.name}/{guild.id}: {str(e)}"
                    )

    @commands.group(name="vanity",)
    @commands.guild_only()
    @commands.has_guild_permissions(manage_guild=True)
    async def vanity(self, ctx: commands.Context) -> None:
        """Vanity management for Grief."""

    @vanity.command()
    async def toggle(self, ctx: commands.Context, on: bool, vanity: str) -> None:
        """Toggle vanity checker for current server on/off."""
        await self.config.guild(ctx.guild).toggled.set(on)
        await self.config.guild(ctx.guild).vanity.set(vanity)
        #if "VANITY_URL" in ctx.guild.features:
        self.vanity_cache[ctx.guild.id] = vanity
        await ctx.send(
            f"Vanity status tracking for current server is now {'on' if on else 'off'} and set to {vanity}."
        )

    @vanity.command()
    @commands.guild_only()
    @commands.has_guild_permissions(manage_guild=True)
    async def role(self, ctx: commands.Context, role: discord.Role) -> None:
        """Setup the role to be rewarded."""
        if role.position >= ctx.author.top_role.position:
            await ctx.send(
                "Your role is lower or equal to the vanity role, please choose a lower role than yourself."
            )
            return
        if role.position >= ctx.guild.me.top_role.position:
            await ctx.send("The role is higher than me, please choose a lower role than me.")
        if ctx.guild.owner:
            await ctx.send(f"Vanity role has been updated to {role.mention}",
            allowed_mentions=discord.AllowedMentions.none(),
        )
            return
        await self.config.guild(ctx.guild).role.set(role.id)
        await ctx.send(
            f"Vanity role has been updated to {role.mention}",
            allowed_mentions=discord.AllowedMentions.none(),
        )

    @vanity.command()
    @commands.guild_only()
    @commands.has_guild_permissions(manage_guild=True)
    async def channel(self, ctx: commands.Context, channel: discord.TextChannel) -> None:
        """Setup the log channel."""
        if not channel.permissions_for(ctx.guild.me).send_messages:
            await ctx.send(
                f"I don't have permission to send messages in {channel.mention}, please give me permission to send messages."
            )
            return
        if not channel.permissions_for(ctx.guild.me).embed_links:
            await ctx.send(
                f"I don't have permission to embed links in {channel.mention}, please give me permission to embed links."
            )
            return
        await self.config.guild(ctx.guild).channel.set(channel.id)
        await ctx.send(
            f"Vanity log channel has been updated to {channel.mention}",
            allowed_mentions=discord.AllowedMentions.none(),
        )


async def setup(bot: Grief):
    cog = Vanity(bot)
    await discord.utils.maybe_coroutine(bot.add_cog, cog)
    asyncio.create_task(cog.update_cache())
init__.py
10 KB
