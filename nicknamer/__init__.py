from .nicknamer import NickNamer

async def setup(bot):
    cog = NickNamer(bot)
    await cog.initialize()
    await bot.add_cog(cog)