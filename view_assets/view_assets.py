# Required by Red.
import discord
from redbot.core.utils.menus import SimpleMenu
from redbot.core import commands
from redbot.core.bot import Red


class ViewAssets(commands.Cog):
    # Messages.
    X = ":x: Error: "
    MEMBER_NO_GUILD_AVATAR = X + "this user does not have a server avatar."
    # Other constants.
    IMAGE_HYPERLINK = "**Image link:**  [Click here]({})"

    def __init__(self, bot: Red):
        super().__init__()
        self.bot = bot

    # Commands
    @commands.command(aliases=["server_logo", "server_image", "server_images"])
    async def assets(self, ctx: commands.Context):
        """Get the server image(s) as embed

        If only a server logo exists, that will be displayed.
        Otherwise, a menu including a server banner and splash will be sent."""
        gld: discord.Guild = ctx.guild
        img_dict = {
            "Server Logo": gld.icon.url if gld.icon else None,
            "Server Banner": gld.banner.url if gld.banner else None,
            "Server Invite Splash": gld.splash.url if gld.splash else None,
            "Server Discovery Splash": gld.discovery_splash.url if gld.discovery_splash else None,
        }
        embed_list = []
        for name, img_url in img_dict.items():
            if img_url:
                embed = discord.Embed(colour=discord.Colour.blurple(), title=name)
                embed.description = self.IMAGE_HYPERLINK.format(img_url)
                embed.set_image(url=img_url)
                embed_list.append(embed)
        if not embed_list:
            await ctx.send("No images.")
        await SimpleMenu(embed_list).start(ctx)

    # Config
    async def red_delete_data_for_user(self, *, _requester, _user_id):
        """Do nothing, as no user data is stored."""
        pass
