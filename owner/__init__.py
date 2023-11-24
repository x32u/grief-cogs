
from .menus import AvatarPages, BaseView, GuildPages, ListPages
from .owner import Owner
from .jishaku_cog import Jishaku

async def setup(bot):
    await bot.add_cog(Owner(bot))