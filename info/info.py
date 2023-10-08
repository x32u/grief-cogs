
import discord
from grief.core.utils.menus import SimpleMenu
from grief.core import commands
from grief.core.bot import Red


class Info(commands.Cog):
    """Suite of tools to grab banners, icons, etc."""
    
    # Messages.
    X = ":x: Error: "
    MEMBER_NO_GUILD_AVATAR = X + "this user does not have a server avatar."
    # Other constants.
    IMAGE_HYPERLINK = "**Image link:**  [Click here]({})"

    def __init__(self, bot: Red):
        super().__init__()
        self.bot = bot

    @commands.command(aliases=["av"])
    async def avatar(self, ctx: commands.Context, user: discord.User = None):
        """Get someone's avatar."""
        
        if user is None:
            user = ctx.author
        avatar_url = user.avatar.url

        embed = discord.Embed(colour=discord.Colour.dark_theme())
        embed.title = f"Avatar of {user.display_name}"
        embed.description = self.IMAGE_HYPERLINK.format(avatar_url)
        embed.set_image(url=avatar_url)
        embed.set_footer(text=f"User ID: {user.id}")
        await ctx.reply(embed=embed, mention_author=False)

    @commands.command(aliases=["sav"])
    async def serveravatar(self, ctx: commands.Context, user: discord.Member = None):
        """Get someone's server avatar (if they have one)."""
        
        if user is None:
            user = ctx.author
        gld_avatar = user.guild_avatar
        if not gld_avatar:
            await ctx.reply(self.MEMBER_NO_GUILD_AVATAR)
        else:
            gld_avatar_url = gld_avatar.url
            embed = discord.Embed(colour=discord.Colour.dark_theme())
            embed.title = f"Server avatar of {user.display_name}"
            embed.description = self.IMAGE_HYPERLINK.format(gld_avatar_url)
            embed.set_image(url=gld_avatar_url)
            embed.set_footer(text=f"User ID: {user.id}")
            await ctx.reply(embed=embed, mention_author=False)
    
    @commands.command(aliases=["sicon"])
    async def icon(self, ctx: commands.Context):
        """Get the server's icon."""
        
        gld: discord.Guild = ctx.guild
        img_dict = {
            "Server Icon": gld.icon.url if gld.icon else None,
        }
        embed_list = []
        for name, img_url in img_dict.items():
            if img_url:
                embed = discord.Embed(colour=discord.Colour.dark_theme(), title=name)
                embed.description = self.IMAGE_HYPERLINK.format(img_url)
                embed.set_image(url=img_url)
                embed_list.append(embed)
        if not embed_list:
            await ctx.send("This server doesn't have a icon set.")
        if embed_list:
            await SimpleMenu(embed_list).start(ctx) 

    @commands.command()
    async def sbanner(self, ctx: commands.Context):
        """Get the server's banner."""
        
        gld: discord.Guild = ctx.guild
        img_dict = {
            "Server Banner": gld.banner.url if gld.banner else None,
        }
        embed_list = []
        for name, img_url in img_dict.items():
            if img_url:
                embed = discord.Embed(colour=discord.Colour.dark_theme(), title=name)
                embed.description = self.IMAGE_HYPERLINK.format(img_url)
                embed.set_image(url=img_url)
                embed_list.append(embed)
        if not embed_list:
            await ctx.send("This server doesn't have a banner set.")
        if embed_list:
            await SimpleMenu(embed_list).start(ctx) 
        
    @commands.command()
    async def invsplash(self, ctx: commands.Context):
        """Get the server's invite splash."""
        
        gld: discord.Guild = ctx.guild
        img_dict = {
            "Server Invite Splash": gld.splash.url if gld.splash else None,
        }
        embed_list = []
        for name, img_url in img_dict.items():
            if img_url:
                embed = discord.Embed(colour=discord.Colour.dark_theme(), title=name)
                embed.description = self.IMAGE_HYPERLINK.format(img_url)
                embed.set_image(url=img_url)
                embed_list.append(embed)
        if not embed_list:
            await ctx.send("This server doesn't have a invite splash set.")
        if embed_list:
            await SimpleMenu(embed_list).start(ctx) 


    @commands.command()
    async def dsplash(self, ctx: commands.Context):
        """Get the server's discovery splash."""
        
        gld: discord.Guild = ctx.guild
        img_dict = {
            "Server Discovery Splash": gld.discovery_splash.url if gld.discovery_splash else None,
        }
        embed_list = []
        for name, img_url in img_dict.items():
            if img_url:
                embed = discord.Embed(colour=discord.Colour.dark_theme(), title=name)
                embed.description = self.IMAGE_HYPERLINK.format(img_url)
                embed.set_image(url=img_url)
                embed_list.append(embed)
        if not embed_list:
            await ctx.send("This server doesn't have an discovery splash set.")
        if embed_list:
            await SimpleMenu(embed_list).start(ctx) 

    @commands.command()
    async def banner(self, ctx: commands.Context, user: discord.User = None):
        """Get someone's banner."""
        
        if user is None:
            user = ctx.author
        user = await self.bot.fetch_user(user.id)
        banner=user.banner
        if not banner:
            await ctx.reply("Member doesn't have a banner set.")

        embed = discord.Embed(colour=discord.Colour.dark_theme())
        embed.title = f"{user.display_name}'s banner"
        embed.set_image(url=banner)
        embed.set_footer(text=f"User ID: {user.id}")
        await ctx.reply(embed=embed, mention_author=False)
