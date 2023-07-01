from typing import Literal

import discord
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.config import Config
from redbot.core.utils.chat_formatting import box

RequestType = Literal["discord_deleted_user", "owner", "user", "user_strict"]


class DevLogs(commands.Cog):
    """
    Keep a log of all that evals and debugs.
    """

    def __init__(self, bot: Red) -> None:
        self.bot = bot
        self.config = Config.get_conf(
            self,
            identifier=8573957264582037523,
            force_registration=True,
        )

        default_global = {"default_channel": None, "bypass": []}
        self.config.register_global(**default_global)

    __author__ = ["sravan"]
    __version__ = "1.0.5"

    def format_help_for_context(self, ctx: commands.Context) -> str:
        """
        Thanks Sinbad!
        """
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\n\nAuthors: {', '.join(self.__author__)}\nCog Version: {self.__version__}"

    async def red_delete_data_for_user(
        self, *, requester: RequestType, user_id: int
    ) -> None:
        # TODO: Replace this with the proper end user data removal handling.
        super().red_delete_data_for_user(requester=requester, user_id=user_id)

    async def send_log(self, ctx) -> None:
        """
        sends a embed in the channel and also returns DM if the command was ran
        in Dms.
        """
        partialchannel = await self.config.default_channel()
        if partialchannel is None:
            return
        # remove the codeblock in the message if it exists or add a codeblock if it doesn't
        content = ctx.message.content.replace("```", "")
        if content.startswith("```"):
            content = content.replace("```", "")
        embed = discord.Embed(
            title=f"{ctx.command.name.upper()} Logs",
            description=box(content, lang="py"),
            color=await self.bot.get_embed_color(self.bot.user.colour),
        )
        embed.set_author(name=ctx.author, icon_url=ctx.author.avatar_url)
        try:
            embed.add_field(
                name="Channel", value=f"{ctx.channel.mention} \n ({ctx.channel.id})"
            )
            embed.add_field(name="Guild", value=f"{ctx.guild.name} \n ({ctx.guild.id})")
        except AttributeError:
            embed.add_field(name="Channel", value="DMs")
        embed.add_field(
            name="Author", value=f"{ctx.author.name} \n ({ctx.author.id})", inline=False
        )
        embed.timestamp = ctx.message.created_at
        await self.bot.get_channel(partialchannel).send(embed=embed)

    @commands.group()
    @commands.guild_only()
    @commands.is_owner()
    async def devset(self, ctx: commands.Context) -> None:
        """
        Configure DevLogs settings.
        """

    @devset.command()
    async def channel(
        self, ctx: commands.Context, channel: discord.TextChannel = None
    ) -> None:
        """
        Set the channel to log to.
        """
        if channel is None:
            await self.config.default_channel.clear()
            await ctx.send("Default channel cleared.")
        else:
            await self.config.default_channel.set(channel.id)
            await ctx.send(f"Logging to {channel.mention}")

    @devset.group()
    async def bypass(self, ctx: commands.Context) -> None:
        """
        Manage the bypass list.
        """

    @bypass.command()
    async def add(self, ctx: commands.Context, user: discord.User) -> None:
        """
        Add a user to the bypass list.
        """
        async with self.config.bypass() as bypass:
            if user.id in bypass:
                await ctx.send("User is already in the bypass list.")
            else:
                bypass.append(user.id)
                await ctx.send(f"{user.mention} added to the bypass list.")

    @bypass.command()
    async def remove(self, ctx: commands.Context, user: discord.User) -> None:
        """
        Remove a user from the bypass list.
        """
        async with self.config.bypass() as bypass:
            if user.id in bypass:
                bypass.remove(user.id)
                await ctx.send(f"{user.mention} removed from the bypass list.")
            else:
                await ctx.send("User is not in the bypass list.")

    @bypass.command()
    async def list(self, ctx: commands.Context) -> None:
        """
        list the users in the bypass list.
        """
        async with self.config.bypass() as bypass:
            if len(bypass) == 0:
                await ctx.send("There are no users in the bypass list.")
            else:
                embed = discord.Embed(
                    title="Bypass List",
                    description="A list of users that bypass the DevLogs module.",
                    color=await self.bot.get_embed_color(ctx.author),
                )
                for user in bypass:
                    try:
                        user_obj = ctx.guild.get_member(user)
                        embed.add_field(name=user_obj.name, value=user_obj.id)
                    except AttributeError:
                        embed.add_field(name=user, value=user)
                await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_command(self, ctx: commands.Context) -> None:
        """
        Log the command and send it to the channel.
        """
        async with self.config.bypass() as bypass:
            if ctx.author.id in bypass:
                return
        if ctx.author.id not in self.bot.owner_ids:
            return
        if ctx.command.name in ["eval", "debug"]:
            await self.send_log(ctx)
