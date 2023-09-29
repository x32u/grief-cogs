


import logging
from random import randint

import discord
from redbot.core import Config, commands
from redbot.core.bot import Red

log = logging.getLogger("grief.roleplay")


class Perform(commands.Cog):
    """
    Perform different actions, like cuddle, poke etc.
    """

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=8423644625413, force_registration=True
        )
        default_global = {
            "feed": [
                "https://cdn.grief.cloud/roleplay/feed/feed1.gif",
                "https://cdn.grief.cloud/roleplay/feed/feed2.gif",
                "https://cdn.grief.cloud/roleplay/feed/feed3.gif",
                "https://cdn.grief.cloud/roleplay/feed/feed4.gif",
                "https://cdn.grief.cloud/roleplay/feed/feed5.gif",
                "https://cdn.grief.cloud/roleplay/feed/feed6.gif",
                "https://cdn.grief.cloud/roleplay/feed/feed7.gif",
                "https://cdn.grief.cloud/roleplay/feed/feed8.gif",
                "https://cdn.grief.cloud/roleplay/feed/feed9.gif",
                "https://cdn.grief.cloud/roleplay/feed/feed10.gif",
                "https://cdn.grief.cloud/roleplay/feed/feed11.gif",
            ],
            "spank": [
                "https://cdn.grief.cloud/roleplay/spank/spank1.gif",
                "https://cdn.grief.cloud/roleplay/spank/spank2.gif",
                "https://cdn.grief.cloud/roleplay/spank/spank3.gif",
                "https://cdn.grief.cloud/roleplay/spank/spank4.gif",
                "https://cdn.grief.cloud/roleplay/spank/spank5.gif",
                "https://cdn.grief.cloud/roleplay/spank/spank6.gif",
                "https://cdn.grief.cloud/roleplay/spank/spank7.gif",
                "https://cdn.grief.cloud/roleplay/spank/spank8.gif",
                "https://cdn.grief.cloud/roleplay/spank/spank9.gif",
                "https://cdn.grief.cloud/roleplay/spank/spank10.gif",
                "https://cdn.grief.cloud/roleplay/spank/spank11.gif",
                "https://cdn.grief.cloud/roleplay/spank/spank12.gif",
            ],
            "nut": [
                "https://cdn.grief.cloud/roleplay/nutkick/nutkick1.gif",
                "https://cdn.grief.cloud/roleplay/nutkick/nutkick2.gif",
                "https://cdn.grief.cloud/roleplay/nutkick/nutkick3.gif",
                "https://cdn.grief.cloud/roleplay/nutkick/nutkick4.gif",
                "https://cdn.grief.cloud/roleplay/nutkick/nutkick5.gif",
                "https://cdn.grief.cloud/roleplay/nutkick/nutkick6.gif",
                "https://cdn.grief.cloud/roleplay/nutkick/nutkick7.gif",
                "https://cdn.grief.cloud/roleplay/nutkick/nutkick8.gif",
            ],
            "fuck": [
                "https://cdn.grief.cloud/roleplay/fuck/fuck1.gif",
                "https://cdn.grief.cloud/roleplay/fuck/fuck2.gif",
                "https://cdn.grief.cloud/roleplay/fuck/fuck3.gif",
                "https://cdn.grief.cloud/roleplay/fuck/fuck4.gif",
                "https://cdn.grief.cloud/roleplay/fuck/fuck5.gif",
                "https://cdn.grief.cloud/roleplay/fuck/fuck6.gif",
                "https://cdn.grief.cloud/roleplay/fuck/fuck7.gif",
                "https://cdn.grief.cloud/roleplay/fuck/fuck8.gif",
                "https://cdn.grief.cloud/roleplay/fuck/fuck9.gif",
                "https://cdn.grief.cloud/roleplay/fuck/fuck10.gif",
                "https://cdn.grief.cloud/roleplay/fuck/fuck11.gif",
            ],
        }
        default_member = {
            "cuddle_s": 0,
            "poke_s": 0,
            "kiss_s": 0,
            "hug_s": 0,
            "slap_s": 0,
            "pat_s": 0,
            "tickle_s": 0,
            "smug_s": 0,
            "lick_s": 0,
            "cry": 0,
            "sleep": 0,
            "spank_s": 0,
            "pout": 0,
            "blush": 0,
            "feed_s": 0,
            "punch_s": 0,
            "confused": 0,
            "amazed": 0,
            "highfive_s": 0,
            "plead_s": 0,
            "clap": 0,
            "facepalm": 0,
            "facedesk": 0,
            "kill_s": 0,
            "love_s": 0,
            "hide": 0,
            "laugh": 0,
            "lurk": 0,
            "bite_s": 0,
            "dance": 0,
            "yeet_s": 0,
            "dodge": 0,
            "happy": 0,
            "cute": 0,
            "lonely": 0,
            "mad": 0,
            "nosebleed": 0,
            "protect_s": 0,
            "run": 0,
            "scared": 0,
            "shrug": 0,
            "scream": 0,
            "stare": 0,
            "wave_s": 0,
            "nut_s": 0,
            "fuck_s": 0,
        }
        default_target = {
            "cuddle_r": 0,
            "poke_r": 0,
            "kiss_r": 0,
            "hug_r": 0,
            "slap_r": 0,
            "pat_r": 0,
            "tickle_r": 0,
            "smug_r": 0,
            "lick_r": 0,
            "spank_r": 0,
            "feed_r": 0,
            "punch_r": 0,
            "highfive_r": 0,
            "plead_r": 0,
            "kill_r": 0,
            "love_r": 0,
            "bite_r": 0,
            "yeet_r": 0,
            "protect_r": 0,
            "wave_r": 0,
            "nut_r": 0,
            "fuck_r": 0,
        }
        self.config.register_global(**default_global)
        self.config.register_user(**default_member)
        self.config.init_custom("Target", 2)
        self.config.register_custom("Target", **default_target)
        self.cache = {}

    def cog_unload(self):
        global hug
        if hug:
            try:
                self.bot.remove_command("hug")
            except Exception as e:
                log.info(e)
            self.bot.add_command(hug)

    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.command()
    @commands.guild_only()
    async def cuddle(self, ctx: commands.Context, user: discord.Member):
        """
        Cuddle a user.
        """
        embed = await kawaiiembed(self, ctx, "cuddled", "cuddle", user)
        if not isinstance(embed, discord.Embed):
            return await ctx.send(embed)
        target = await self.config.custom("Target", ctx.author.id, user.id).cuddle_r()
        used = await self.config.user(ctx.author).cuddle_s()
        embed.set_footer(
            text=f"{ctx.author.name}'s total cuddles: {used + 1} | {ctx.author.name} has cuddled {user.name} {target + 1} times"
        )
        await send_embed(self, ctx, embed, user)
        await self.config.user(ctx.author).cuddle_s.set(used + 1)
        await self.config.custom("Target", ctx.author.id, user.id).cuddle_r.set(
            target + 1
        )

    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.command(name="poke")
    @commands.bot_has_permissions(embed_links=True)
    async def poke(self, ctx: commands.Context, user: discord.Member):
        """
        Poke a user.
        """
        embed = await kawaiiembed(self, ctx, "poked", "poke", user)
        if not isinstance(embed, discord.Embed):
            return await ctx.send(embed)
        target = await self.config.custom("Target", ctx.author.id, user.id).poke_r()
        used = await self.config.user(ctx.author).poke_s()
        embed.set_footer(
            text=f"{ctx.author.name}'s total pokes: {used + 1} | {ctx.author.name} has poked {user.name} {target + 1} times"
        )
        await send_embed(self, ctx, embed, user)
        await self.config.user(ctx.author).poke_s.set(used + 1)
        await self.config.custom("Target", ctx.author.id, user.id).poke_r.set(
            target + 1
        )

    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.command(name="kiss")
    @commands.bot_has_permissions(embed_links=True)
    async def kiss(self, ctx: commands.Context, user: discord.Member):
        """
        Kiss a user.
        """
        embed = await kawaiiembed(self, ctx, "just kissed", "kiss", user)
        if not isinstance(embed, discord.Embed):
            return await ctx.send(embed)
        target = await self.config.custom("Target", ctx.author.id, user.id).kiss_r()
        used = await self.config.user(ctx.author).kiss_s()
        embed.set_footer(
            text=f"{ctx.author.name}'s total kisses: {used + 1} | {ctx.author.name} has kissed {user.name} {target + 1} times"
        )
        await send_embed(self, ctx, embed, user)
        await self.config.user(ctx.author).kiss_s.set(used + 1)
        await self.config.custom("Target", ctx.author.id, user.id).kiss_r.set(
            target + 1
        )

    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.command(name="hug")
    @commands.bot_has_permissions(embed_links=True)
    async def hug(self, ctx: commands.Context, user: discord.Member):
        """
        Hugs a user.
        """
        embed = await kawaiiembed(self, ctx, "just hugged", "hug", user)
        if not isinstance(embed, discord.Embed):
            return await ctx.send(embed)
        target = await self.config.custom("Target", ctx.author.id, user.id).hug_r()
        used = await self.config.user(ctx.author).hug_s()
        embed.set_footer(
            text=f"{ctx.author.name}'s total hugs: {used + 1} | {ctx.author.name} has hugged {user.name} {target + 1} times"
        )
        await send_embed(self, ctx, embed, user)
        await self.config.user(ctx.author).hug_s.set(used + 1)
        await self.config.custom("Target", ctx.author.id, user.id).hug_r.set(target + 1)

    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.command(name="pat")
    @commands.bot_has_permissions(embed_links=True)
    async def pat(self, ctx: commands.Context, user: discord.Member):
        """
        Pats a user.
        """
        embed = await kawaiiembed(self, ctx, "just patted", "pat", user)
        if not isinstance(embed, discord.Embed):
            return await ctx.send(embed)
        target = await self.config.custom("Target", ctx.author.id, user.id).pat_r()
        used = await self.config.user(ctx.author).pat_s()
        embed.set_footer(
            text=f"{ctx.author.name}'s total pats: {used + 1} | {ctx.author.name} has patted {user.name} {target + 1} times"
        )
        await send_embed(self, ctx, embed, user)
        await self.config.user(ctx.author).pat_s.set(used + 1)
        await self.config.custom("Target", ctx.author.id, user.id).pat_r.set(target + 1)

    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.command(name="tickle")
    @commands.bot_has_permissions(embed_links=True)
    async def tickle(self, ctx: commands.Context, user: discord.Member):
        """
        Tickles a user.
        """
        embed = await kawaiiembed(self, ctx, "just tickled", "tickle", user)
        if not isinstance(embed, discord.Embed):
            return await ctx.send(embed)
        target = await self.config.custom("Target", ctx.author.id, user.id).tickle_r()
        used = await self.config.user(ctx.author).tickle_s()
        embed.set_footer(
            text=f"{ctx.author.name}'s total tickles: {used + 1} | {ctx.author.name} has tickled {user.name} {target + 1} times"
        )
        await send_embed(self, ctx, embed, user)
        await self.config.user(ctx.author).tickle_s.set(used + 1)
        await self.config.custom("Target", ctx.author.id, user.id).tickle_r.set(
            target + 1
        )

    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.command(name="lick")
    @commands.bot_has_permissions(embed_links=True)
    async def lick(self, ctx: commands.Context, user: discord.Member):
        """
        Licks a user.
        """
        embed = await kawaiiembed(self, ctx, "just licked", "lick", user)
        if not isinstance(embed, discord.Embed):
            return await ctx.send(embed)
        target = await self.config.custom("Target", ctx.author.id, user.id).lick_r()
        used = await self.config.user(ctx.author).lick_s()
        embed.set_footer(
            text=f"{ctx.author.name}'s total licks: {used + 1} | {ctx.author.name} has licked {user.name} {target + 1} times"
        )
        await send_embed(self, ctx, embed, user)
        await self.config.user(ctx.author).lick_s.set(used + 1)
        await self.config.custom("Target", ctx.author.id, user.id).lick_r.set(
            target + 1
        )

    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.command(name="slap")
    @commands.bot_has_permissions(embed_links=True)
    async def slap(self, ctx: commands.Context, user: discord.Member):
        """
        Slaps a user.
        """
        embed = await kawaiiembed(self, ctx, "just slapped", "slap", user)
        if not isinstance(embed, discord.Embed):
            return await ctx.send(embed)
        target = await self.config.custom("Target", ctx.author.id, user.id).slap_r()
        used = await self.config.user(ctx.author).slap_s()
        embed.set_footer(
            text=f"{ctx.author.name}'s total slaps: {used + 1} | {ctx.author.name} has slapped {user.name} {target + 1} times"
        )
        await send_embed(self, ctx, embed, user)
        await self.config.user(ctx.author).slap_s.set(used + 1)
        await self.config.custom("Target", ctx.author.id, user.id).slap_r.set(
            target + 1
        )

    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.command(name="spank")
    @commands.bot_has_permissions(embed_links=True)
    async def spank(self, ctx: commands.Context, user: discord.Member):
        """
        Spanks a user.
        """

        images = await self.config.spank()

        mn = len(images)
        i = randint(0, mn - 1)

        embed = discord.Embed(
            colour=discord.Colour.dark_theme(),
            description=f"**{ctx.author.mention}** just spanked {f'**{str(user.mention)}**' if user else 'themselves'}!",
        )

        embed.set_author(name=self.bot.user.display_name, icon_url=self.bot.user.avatar)
        embed.set_image(url=images[i])
        target = await self.config.custom("Target", ctx.author.id, user.id).spank_r()
        used = await self.config.user(ctx.author).spank_s()
        embed.set_footer(
            text=f"{ctx.author.name}'s total spanks: {used + 1} | {ctx.author.name} has spanked {user.name} {target + 1} times"
        )
        await send_embed(self, ctx, embed, user)
        await self.config.user(ctx.author).spank_s.set(used + 1)
        await self.config.custom("Target", ctx.author.id, user.id).spank_r.set(
            target + 1
        )

    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.command(name="feed")
    @commands.bot_has_permissions(embed_links=True)
    async def feed(self, ctx: commands.Context, user: discord.Member):
        """
        Feeds a user.
        """

        images = await self.config.feed()

        mn = len(images)
        i = randint(0, mn - 1)

        embed = discord.Embed(
            colour=discord.Colour.dark_theme(),
            description=f"**{ctx.author.mention}** feeds {f'**{str(user.mention)}**' if user else 'themselves'}!",
        )

        embed.set_author(name=self.bot.user.display_name, icon_url=self.bot.user.avatar)
        embed.set_image(url=images[i])
        target = await self.config.custom("Target", ctx.author.id, user.id).feed_r()
        used = await self.config.user(ctx.author).feed_s()
        embed.set_footer(
            text=f"{ctx.author.name}'s total feeds: {used + 1} | {ctx.author.name} has feeded {user.name} {target + 1} times"
        )
        await send_embed(self, ctx, embed, user)
        await self.config.user(ctx.author).feed_s.set(used + 1)
        await self.config.custom("Target", ctx.author.id, user.id).feed_r.set(
            target + 1
        )

    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.command(name="punch")
    @commands.bot_has_permissions(embed_links=True)
    async def punch(self, ctx: commands.Context, user: discord.Member):
        """
        Punch a user.
        """
        embed = await kawaiiembed(self, ctx, "just punched", "punch", user)
        if embed is False:
            return await ctx.send("api is down")
        target = await self.config.custom("Target", ctx.author.id, user.id).punch_r()
        used = await self.config.user(ctx.author).punch_s()
        embed.set_footer(
            text=f"{ctx.author.name}'s total punches: {used + 1} | {ctx.author.name} has punched {user.name} {target + 1} times"
        )
        await send_embed(self, ctx, embed, user)
        await self.config.custom("Target", ctx.author.id, user.id).punch_r.set(
            target + 1
        )

    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.command()
    @commands.guild_only()
    async def highfive(self, ctx: commands.Context, user: discord.Member):
        """
        Highfive a user.
        """
        embed = await kawaiiembed(self, ctx, "highfived", "highfive", user)
        if not isinstance(embed, discord.Embed):
            return await ctx.send(embed)
        target = await self.config.custom("Target", ctx.author.id, user.id).highfive_r()
        used = await self.config.user(ctx.author).highfive_s()
        embed.set_footer(
            text=f"{ctx.author.name}'s total highfives: {used + 1} | {ctx.author.name} has highfived {user.name} {target + 1} times"
        )
        await send_embed(self, ctx, embed, user)
        await self.config.user(ctx.author).highfive_s.set(used + 1)
        await self.config.custom("Target", ctx.author.id, user.id).highfive_r.set(
            target + 1
        )

    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.command()
    @commands.guild_only()
    async def kill(self, ctx: commands.Context, user: discord.Member):
        """
        Kill a user.
        """
        embed = await kawaiiembed(self, ctx, "killed", "kill", user)
        if not isinstance(embed, discord.Embed):
            return await ctx.send(embed)
        target = await self.config.custom("Target", ctx.author.id, user.id).kill_r()
        used = await self.config.user(ctx.author).kill_s()
        embed.set_footer(
            text=f"{ctx.author.name}'s total kills: {used + 1} | {ctx.author.name} has killed {user.name} {target + 1} times"
        )
        await send_embed(self, ctx, embed, user)
        await self.config.user(ctx.author).kill_s.set(used + 1)
        await self.config.custom("Target", ctx.author.id, user.id).kill_r.set(
            target + 1
        )

    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.command()
    @commands.guild_only()
    async def bite(self, ctx: commands.Context, user: discord.Member):
        """
        Bite a user.
        """
        embed = await kawaiiembed(self, ctx, "is biting", "bite", user)
        if not isinstance(embed, discord.Embed):
            return await ctx.send(embed)
        target = await self.config.custom("Target", ctx.author.id, user.id).bite_r()
        used = await self.config.user(ctx.author).bite_s()
        embed.set_footer(
            text=f"{ctx.author.name}'s total bites: {used + 1} | {ctx.author.name} has bitten {user.name} {target + 1} times"
        )
        await send_embed(self, ctx, embed, user)
        await self.config.user(ctx.author).bite_s.set(used + 1)
        await self.config.custom("Target", ctx.author.id, user.id).bite_r.set(
            target + 1
        )

    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.command()
    @commands.guild_only()
    async def yeet(self, ctx: commands.Context, user: discord.Member):
        """
        Yeet someone.
        """
        embed = await kawaiiembed(self, ctx, "yeeted", "yeet", user)
        if not isinstance(embed, discord.Embed):
            return await ctx.send(embed)
        target = await self.config.custom("Target", ctx.author.id, user.id).yeet_r()
        used = await self.config.user(ctx.author).yeet_s()
        embed.set_footer(
            text=f"{ctx.author.name}'s total yeets: {used + 1} | {ctx.author.name} has yeeted {user.name} {target + 1} times"
        )
        await send_embed(self, ctx, embed, user)
        await self.config.user(ctx.author).yeet_s.set(used + 1)
        await self.config.custom("Target", ctx.author.id, user.id).yeet_r.set(
            target + 1
        )

    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.command(name="nutkick", aliases=["kicknuts"])
    @commands.bot_has_permissions(embed_links=True)
    async def kicknuts(self, ctx: commands.Context, user: discord.Member):
        """
        Kick a user in the balls.
        """

        images = await self.config.nut()

        mn = len(images)
        i = randint(0, mn - 1)

        embed = discord.Embed(
            colour=discord.Colour.dark_theme(),
            description=f"**{ctx.author.mention}** just kicked nuts of {f'**{str(user.mention)}**' if user else 'themselves'}!",
        )

        embed.set_author(name=self.bot.user.display_name, icon_url=self.bot.user.avatar)
        embed.set_image(url=images[i])
        target = await self.config.custom("Target", ctx.author.id, user.id).nut_r()
        used = await self.config.user(ctx.author).nut_s()
        embed.set_footer(
            text=f"{ctx.author.name}'s total nutkicks: {used + 1} | {ctx.author.name} has nutkicked {user.name} {target + 1} times"
        )
        await send_embed(self, ctx, embed, user)
        await self.config.user(ctx.author).nut_s.set(used + 1)
        await self.config.custom("Target", ctx.author.id, user.id).nut_r.set(target + 1)

    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    async def fuck(self, ctx: commands.Context, user: discord.Member):
        """
        Fuck a user.
        """

        images = await self.config.fuck()

        mn = len(images)
        i = randint(0, mn - 1)

        embed = discord.Embed(
            colour=discord.Colour.dark_theme(),
            description=f"**{ctx.author.mention}** just fucked {f'**{str(user.mention)}**' if user else 'themselves'}!",
        )

        embed.set_author(name=self.bot.user.display_name, icon_url=self.bot.user.avatar)
        embed.set_image(url=images[i])
        target = await self.config.custom("Target", ctx.author.id, user.id).fuck_r()
        used = await self.config.user(ctx.author).fuck_s()
        embed.set_footer(
            text=f"{ctx.author.name}'s total fucks: {used + 1} | {ctx.author.name} has fucked {user.name} {target + 1} times"
        )
        await send_embed(self, ctx, embed, user)
        await self.config.user(ctx.author).fuck_s.set(used + 1)
        await self.config.custom("Target", ctx.author.id, user.id).fuck_r.set(target + 1)


async def setup(bot):
    global hug

    hug = bot.remove_command("hug")
    await bot.add_cog(Perform(bot))
