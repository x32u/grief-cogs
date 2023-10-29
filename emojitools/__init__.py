import json
import asyncio
from pathlib import Path
from .emojitools import EmojiTools




async def setup(bot):
    await bot.add_cog(EmojiTools(bot))
