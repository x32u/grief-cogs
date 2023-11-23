

from .menus import AvatarPages, BaseView, GuildPages, ListPages

from .servers import Owner

async def setup(bot):
    await bot.add_cog(Owner(bot))