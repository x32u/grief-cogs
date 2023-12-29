from antijoin import AntiJoin

async def setup(bot):
    await bot.add_cog(AntiJoin(bot))