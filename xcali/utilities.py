from functools import partial

from grief.core.bot import Red


async def sync_as_async(bot: Red, func, *args, **kwargs):
    """Run a sync function as async."""
    return await bot.loop.run_in_executor(None, partial(func, *args, **kwargs))
