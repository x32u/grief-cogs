from grief.core.bot import Red

from .admin import Admin
from .editguild import EditGuild
from .edittextchannel import EditTextChannel
from .editthread import EditThread
from .editvoicechannel import EditVoiceChannel


async def setup(bot: Red) -> None:
    await bot.add_cog(Admin(bot))
