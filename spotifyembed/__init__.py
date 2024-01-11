
from .spotifyembed import Spotifyembed

async def setup(bot):
    await bot.add_cog(Spotifyembed(bot))