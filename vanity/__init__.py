import asyncio
import typing
from logging import Logger, getLogger

import discord
from grief.core import Config, commands
from grief.core.bot import Red

LISTENER_NAME: str = "on_presence_update" if discord.version_info.major == 2 else "on_member_update"

class Vanity(commands.Cog):
    """For level 3 servers, award your users for advertising the vanity in their status."""

    def __init__(self, bot: Red):
        self.bot: Red = bot
        self.logger: Logger = getLogger("grief.vanity")
        self.config: Config = Config.get_conf(self, identifier=12039492, force_registration=True)
        default_guild = {
            "role": None,
            "toggled": False,
            "channel": None,
            "vanity": None,
        }
        self.cached = False
        self.vanity_cache = {}
        self.config.register_guild(**default_guild)

    async def update_cache(self):
        data = await self.config.all_guilds()
        for x in data:
            vanity = data[x]["vanity"]
            if vanity:
                self.vanity_cache[x] = vanity
        if not self.cached:
            self.cached = True

    async def safe_send(self, channel: discord.TextChannel, embed: discord.Embed) -> None:
        try:
            await channel.send(embed=embed)
        except (discord.Forbidden, discord.HTTPException) as e:
            self.logger.warning(
                f"Failed to send message to {channel.name} in {channel.guild.name}/{channel.guild.id}: {str(e)}"
            )

    @commands.Cog.listener(LISTENER_NAME)
    async def on_vanity_trigger(self, before: discord.Member, after: discord.Member) -> None:
        if not self.cached:
            await self.update_cache()
        if before.bot:
            return
        guild: discord.Guild = after.guild
        data = await self.config.guild(guild).all()
        if not data["toggled"]:
            return
        if not data["role"] or not data["channel"]:
            return
        if not "VANITY_URL" in guild.features:
            return
        vanity: str = "/" + self.vanity_cache[guild.id]
        role: discord.Role = guild.get_role(int(data["role"]))
        log_channel: discord.TextChannel = guild.get_channel(int(data["channel"]))
        if not role:
            return
        if not log_channel:
            return
        if role.position >= guild.me.top_role.position:
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
    @commands.cooldown(1, 3, commands.BucketType.guild)
    async def vanity(self, ctx: commands.Context) -> None:
        """Vanity roles for grief."""

        vanity = await ctx.guild.vanity_invite()
        vanity = vanity.url.replace("discord.gg", "")
        vanity = vanity.replace("https://", "")

    @vanity.command(usage="true yor")
    @commands.has_permissions(manage_guild=True)
    async def toggle(self, ctx: commands.Context, on: bool, vanity: str) -> None:
        """Toggle vanity checker for current server on/off. Do not use "/"."""
        await self.config.guild(ctx.guild).toggled.set(on)
        await self.config.guild(ctx.guild).vanity.set(vanity)
        if "VANITY_URL" not in ctx.guild.features:
            return await ctx.send("This guild does not currently have a vanity URL. This feature is for level 3 vanity servers only.")
        if "VANITY_URL" in ctx.guild.features:
            embed = discord.Embed(description=f"> Vanity status tracking for current server is now {'on' if on else 'off'} and set to {vanity}.", color=0x313338)
            return await ctx.reply(embed=embed, mention_author=False)

    @vanity.command()
    @commands.guild_only()
    @commands.cooldown(1, 3, commands.BucketType.guild)
    @commands.has_permissions(manage_guild=True)
    async def role(self, ctx: commands.Context, role: discord.Role) -> None:
        """Setup the role to be rewarded."""
        if role.position >= ctx.author.top_role.position:
            embed = discord.Embed(description=f"> Your role is lower or equal to the vanity role, please choose a lower role than yourself.", color=0x313338)
            return await ctx.reply(embed=embed, mention_author=False)
        if role.position >= ctx.guild.me.top_role.position:
            embed = discord.Embed(description=f"> The role is higher than me, please choose a lower role than me.", color=0x313338)
            return await ctx.reply(embed=embed, mention_author=False)
        await self.config.guild(ctx.guild).role.set(role.id)
        embed = discord.Embed(description=f"> Vanity role has been updated to {role.mention}", color=0x313338)
        await ctx.reply(embed=embed, mention_author=False)

    @vanity.command()
    @commands.guild_only()
    @commands.cooldown(1, 3, commands.BucketType.guild)
    @commands.has_permissions(manage_guild=True)
    async def channel(self, ctx: commands.Context, channel: discord.TextChannel) -> None:
        """Setup the log channel."""
        if not channel.permissions_for(ctx.guild.me).send_messages:
            embed = discord.Embed(description=f"> I don't have permission to send messages in {channel.mention}, please give me permission to send messages.", color=0x313338)
            return await ctx.reply(embed=embed, mention_author=False)
        if not channel.permissions_for(ctx.guild.me).embed_links:
            embed = discord.Embed(description=f"> I don't have permission to embed links in {channel.mention}, please give me permission to embed links.", color=0x313338)
            return await ctx.reply(embed=embed, mention_author=False)
        await self.config.guild(ctx.guild).channel.set(channel.id)
        embed = discord.Embed(description=f"> Vanity log channel has been updated to {channel.mention}", color=0x313338)
        return await ctx.reply(embed=embed, mention_author=False)
        

async def setup(bot: Red):
    cog = Vanity(bot)
    await discord.utils.maybe_coroutine(bot.add_cog, cog)
    await cog.update_cache()