

import logging
import re

import discord
from grief.core import Config, app_commands, commands
from grief.core.bot import Red
from grief.core.utils.chat_formatting import humanize_list

log = logging.getLogger("red.kuro-cogs.reactlog")


class ReactLog(commands.Cog):
    """Log when reactions are added or removed."""

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, 9517306284, True)
        self.config.register_guild(
            channel=None, log_all=False, react_add=False, react_remove=False
        )

    @commands.has_permissions(manage_guild=True)
    @commands.guild_only()
    @commands.hybrid_group(aliases=["reactionlog"])
    async def reactlog(self, ctx: commands.Context):
        """Reaction logging configuration commands."""
        pass

    @reactlog.command()
    @app_commands.describe(channel="The channel to log reactions to.")
    async def channel(self, ctx: commands.Context, channel: discord.TextChannel = None):
        """Set the reactions logging channel."""
        if not channel:
            await self.config.guild(ctx.guild).channel.clear()
            await ctx.send("Reaction logging channel has been unset.")
            return
        if not ctx.channel.permissions_for(channel.guild.me).send_messages:
            await ctx.send("Please grant me permission to send message in that channel first.")
            return
        await self.config.guild(ctx.guild).channel.set(channel.id)
        await ctx.send(f"Reaction logging channel has been set to: {channel.mention}")

    @reactlog.command()
    @app_commands.describe(toggle="True or False")
    async def reactadd(self, ctx: commands.Context, toggle: bool = None):
        """Enable/disable logging when reactions added."""
        current = await self.config.guild(ctx.guild).react_add()
        if toggle is None:
            await self.config.guild(ctx.guild).react_add.set(not current)
        else:
            await self.config.guild(ctx.guild).react_add.set(toggle)

        if await self.config.guild(ctx.guild).react_add():
            await ctx.send("I will log when reactions added.")
            return
        await ctx.send("I won't log when reactions added.")

    @reactlog.command()
    @app_commands.describe(toggle="True or False")
    async def reactdel(self, ctx: commands.Context, toggle: bool = None):
        """Enable/disable logging when reactions removed."""
        current = await self.config.guild(ctx.guild).react_remove()
        if toggle is None:
            await self.config.guild(ctx.guild).react_remove.set(not current)
        else:
            await self.config.guild(ctx.guild).react_remove.set(toggle)

        if await self.config.guild(ctx.guild).react_remove():
            await ctx.send("I will log when reactions removed.")
            return
        await ctx.send("I won't log when reactions removed.")

    @reactlog.command()
    async def settings(self, ctx: commands.Context):
        """Show current reaction log settings."""
        channel = await self.config.guild(ctx.guild).channel()
        if channel:
            channel_mention = self.bot.get_channel(channel).mention
        else:
            channel_mention = "Not Set"
        react_add_status = await self.config.guild(ctx.guild).react_add()
        react_remove_status = await self.config.guild(ctx.guild).react_remove()
        log_all_status = await self.config.guild(ctx.guild).log_all()
        if await ctx.embed_requested():
            embed = discord.Embed(title="Reaction Log Settings", color=await ctx.embed_color())
            embed.add_field(name="Log On Reaction Add?", value=react_add_status, inline=True)
            embed.add_field(name="Log On Reaction Remove?", value=react_remove_status, inline=True)
            embed.add_field(name="Channel", value=channel_mention, inline=True)
            embed.set_footer(text=ctx.guild.name, icon_url=getattr(ctx.guild.icon, "url", None))
            await ctx.send(embed=embed)
        else:
            await ctx.send(
                f"**Reaction Log Settings for {ctx.guild.name}**\n"
                f"Channel: {channel_mention}\n"
                f"Log On Reaction Add: {react_add_status}\n"
                f"Log On Reaction Remove: {react_remove_status}\n"
            )

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.Member):
        message = reaction.message
        if not message.guild:
            return
        if not await self.channel_check(message.guild):
            return
        if not await self.config.guild(message.guild).react_add():
            return
        log_all = await self.config.guild(message.guild).log_all()
        if not log_all and reaction.count != 1:
            return
        await self.send_to_log(message, str(reaction.emoji), user, True)

    @commands.Cog.listener()
    async def on_reaction_remove(self, reaction: discord.Reaction, user: discord.Member):
        message = reaction.message
        if not message.guild:
            return
        if not await self.channel_check(message.guild):
            return
        if not await self.config.guild(message.guild).react_remove():
            return
        log_all = await self.config.guild(message.guild).log_all()
        if not log_all and reaction.count != 0:
            return
        await self.send_to_log(message, str(reaction.emoji), user, False)

    async def channel_check(self, guild: discord.Guild) -> bool:
        if not (channel := await self.config.guild(guild).channel()):
            return False
        if not self.bot.get_channel(channel):
            log.info(f"Channel with ID {channel} not found in {guild} (ID: {guild.id}), ignoring.")
            return False
        return True

    async def send_to_log(
        self, message: discord.Message, emoji: str, user: discord.Member, added: bool
    ) -> discord.Message:
        if user.bot:
            return
        channel_id = await self.config.guild(message.guild).channel()
        if not channel_id:
            return

        # https://github.com/Rapptz/discord.py/blob/462ba84809/discord/ext/commands/converter.py#L700
        match = re.match(r"<a?:([a-zA-Z0-9\_]{1,32}):([0-9]{15,20})>$", emoji)
        if match:
            description = (
                f"**Channel:** {message.channel.mention}\n"
                f"**Emoji:** {match.group(1)} (ID: {match.group(2)})\n"
                f"**Message:** [Jump to Message ►]({message.jump_url})"
            )
            url = f"https://cdn.discordapp.com/emojis/{match.group(2)}"
            url += ".gif" if emoji.startswith("<a") else ".png"
        else:  # Default Emoji
            description = (
                f"**Channel:** {message.channel.mention}\n"
                f"**Emoji:** {emoji.strip(':')}\n"
                f"**Message:** [Jump to Message ►]({message.jump_url})"
            )
            # https://github.com/flapjax/FlapJack-Cogs/blob/red-v3-rewrites/bigmoji/bigmoji.py#L69-L93
            chars = [str(hex(ord(c)))[2:] for c in emoji]
            if len(chars) == 2:
                if "fe0f" in chars:
                    chars.remove("fe0f")
            if "20e3" in chars:
                chars.remove("fe0f")
            url = f"https://twemoji.maxcdn.com/v/14.0.2/72x72/{'-'.join(chars)}.png"
        color = discord.Color.dark_theme()
        embed = discord.Embed(
            description=description, color=color, timestamp=discord.utils.utcnow()
        )
        embed.set_author(name=f"{user} ({user.id})", icon_url=user.display_avatar.url)
        embed.set_thumbnail(url=url)
        added_or_removed = "Added" if added else "Removed"
        embed.set_footer(text=f"Reaction {added_or_removed} | #{message.channel.name}")

        log_channel = self.bot.get_channel(channel_id)
        await log_channel.send(embed=embed)
