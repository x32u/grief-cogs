
import logging
from random import randint
from typing import Optional

import discord
from grief.core import Config, commands
from grief.core.bot import Red

from .utils import send_embed

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
            "cuddle": [
                "https://cdn.grief.cloud/roleplay/cuddle/cuddle1.gif",
                "https://cdn.grief.cloud/roleplay/cuddle/cuddle2.gif",
                "https://cdn.grief.cloud/roleplay/cuddle/cuddle3.gif",
                "https://cdn.grief.cloud/roleplay/cuddle/cuddle4.gif",
                "https://cdn.grief.cloud/roleplay/cuddle/cuddle5.gif",
                "https://cdn.grief.cloud/roleplay/cuddle/cuddle6.gif",
                "https://cdn.grief.cloud/roleplay/cuddle/cuddle7.gif",
                "https://cdn.grief.cloud/roleplay/cuddle/cuddle8.gif",
                "https://cdn.grief.cloud/roleplay/cuddle/cuddle9.gif",
                "https://cdn.grief.cloud/roleplay/cuddle/cuddle10.gif",
                "https://cdn.grief.cloud/roleplay/cuddle/cuddle11.gif",
                "https://cdn.grief.cloud/roleplay/cuddle/cuddle12.gif",
                "https://cdn.grief.cloud/roleplay/cuddle/cuddle13.gif",
                "https://cdn.grief.cloud/roleplay/cuddle/cuddle14.gif",
                "https://cdn.grief.cloud/roleplay/cuddle/cuddle15.gif",
                "https://cdn.grief.cloud/roleplay/cuddle/cuddle16.gif",
                "https://cdn.grief.cloud/roleplay/cuddle/cuddle17.gif",
                "https://cdn.grief.cloud/roleplay/cuddle/cuddle18.gif",
                "https://cdn.grief.cloud/roleplay/cuddle/cuddle19.gif",
                "https://cdn.grief.cloud/roleplay/cuddle/cuddle20.gif",
                "https://cdn.grief.cloud/roleplay/cuddle/cuddle21.gif",
                "https://cdn.grief.cloud/roleplay/cuddle/cuddle22.gif",
                "https://cdn.grief.cloud/roleplay/cuddle/cuddle23.gif",
                "https://cdn.grief.cloud/roleplay/cuddle/cuddle24.gif",
                "https://cdn.grief.cloud/roleplay/cuddle/cuddle25.gif",
                "https://cdn.grief.cloud/roleplay/cuddle/cuddle26.gif",
                "https://cdn.grief.cloud/roleplay/cuddle/cuddle26.gif",
                "https://cdn.grief.cloud/roleplay/cuddle/cuddle27.gif",
                "https://cdn.grief.cloud/roleplay/cuddle/cuddle28.gif",
                "https://cdn.grief.cloud/roleplay/cuddle/cuddle29.gif",
                "https://cdn.grief.cloud/roleplay/cuddle/cuddle30.gif",
            ],
            "poke": [
                "https://cdn.grief.cloud/roleplay/poke/poke1.gif",
                "https://cdn.grief.cloud/roleplay/poke/poke2.gif",
                "https://cdn.grief.cloud/roleplay/poke/poke3.gif",
                "https://cdn.grief.cloud/roleplay/poke/poke4.gif",
                "https://cdn.grief.cloud/roleplay/poke/poke5.gif",
                "https://cdn.grief.cloud/roleplay/poke/poke6.gif",
                "https://cdn.grief.cloud/roleplay/poke/poke7.gif",
                "https://cdn.grief.cloud/roleplay/poke/poke8.gif",
                "https://cdn.grief.cloud/roleplay/poke/poke9.gif",
                "https://cdn.grief.cloud/roleplay/poke/poke10.gif",
                "https://cdn.grief.cloud/roleplay/poke/poke11.gif",
                "https://cdn.grief.cloud/roleplay/poke/poke12.gif",
                "https://cdn.grief.cloud/roleplay/poke/poke13.gif",
                "https://cdn.grief.cloud/roleplay/poke/poke14.gif",
                "https://cdn.grief.cloud/roleplay/poke/poke15.gif",
            ],
            "kiss": [
                "https://cdn.grief.cloud/roleplay/kiss/kiss1.gif",
                "https://cdn.grief.cloud/roleplay/kiss/kiss2.gif",
                "https://cdn.grief.cloud/roleplay/kiss/kiss3.gif",
                "https://cdn.grief.cloud/roleplay/kiss/kiss4.gif",
                "https://cdn.grief.cloud/roleplay/kiss/kiss5.gif",
                "https://cdn.grief.cloud/roleplay/kiss/kiss6.gif",
                "https://cdn.grief.cloud/roleplay/kiss/kiss7.gif",
                "https://cdn.grief.cloud/roleplay/kiss/kiss8.gif",
                "https://cdn.grief.cloud/roleplay/kiss/kiss9.gif",
                "https://cdn.grief.cloud/roleplay/kiss/kiss10.gif",
                "https://cdn.grief.cloud/roleplay/kiss/kiss11.gif",
                "https://cdn.grief.cloud/roleplay/kiss/kiss12.gif",
                "https://cdn.grief.cloud/roleplay/kiss/kiss13.gif",
                "https://cdn.grief.cloud/roleplay/kiss/kiss14.gif",
                "https://cdn.grief.cloud/roleplay/kiss/kiss15.gif",
            ],
            "hug": [
                "https://cdn.grief.cloud/roleplay/hug/hug1.gif",
                "https://cdn.grief.cloud/roleplay/hug/hug2.gif",
                "https://cdn.grief.cloud/roleplay/hug/hug3.gif",
                "https://cdn.grief.cloud/roleplay/hug/hug4.gif",
                "https://cdn.grief.cloud/roleplay/hug/hug5.gif",
                "https://cdn.grief.cloud/roleplay/hug/hug6.gif",
                "https://cdn.grief.cloud/roleplay/hug/hug7.gif",
                "https://cdn.grief.cloud/roleplay/hug/hug8.gif",
                "https://cdn.grief.cloud/roleplay/hug/hug9.gif",
                "https://cdn.grief.cloud/roleplay/hug/hug10.gif",
                "https://cdn.grief.cloud/roleplay/hug/hug11.gif",
                "https://cdn.grief.cloud/roleplay/hug/hug12.gif",
                "https://cdn.grief.cloud/roleplay/hug/hug13.gif",
                "https://cdn.grief.cloud/roleplay/hug/hug14.gif",
                "https://cdn.grief.cloud/roleplay/hug/hug15.gif",
                "https://cdn.grief.cloud/roleplay/hug/hug16.gif",
                "https://cdn.grief.cloud/roleplay/hug/hug17.gif",
                "https://cdn.grief.cloud/roleplay/hug/hug18.gif",
                "https://cdn.grief.cloud/roleplay/hug/hug19.gif",
                "https://cdn.grief.cloud/roleplay/hug/hug20.gif",
            ],
            "pat": [
                "https://cdn.grief.cloud/roleplay/pat/pat1.gif",
                "https://cdn.grief.cloud/roleplay/pat/pat2.gif",
                "https://cdn.grief.cloud/roleplay/pat/pat3.gif",
                "https://cdn.grief.cloud/roleplay/pat/pat4.gif",
                "https://cdn.grief.cloud/roleplay/pat/pat5.gif",
                "https://cdn.grief.cloud/roleplay/pat/pat6.gif",
                "https://cdn.grief.cloud/roleplay/pat/pat7.gif",
                "https://cdn.grief.cloud/roleplay/pat/pat8.gif",
                "https://cdn.grief.cloud/roleplay/pat/pat9.gif",
                "https://cdn.grief.cloud/roleplay/pat/pat10.gif",
                "https://cdn.grief.cloud/roleplay/pat/pat11.gif",
                "https://cdn.grief.cloud/roleplay/pat/pat12.gif",
                "https://cdn.grief.cloud/roleplay/pat/pat13.gif",
                "https://cdn.grief.cloud/roleplay/pat/pat14.gif",
                "https://cdn.grief.cloud/roleplay/pat/pat15.gif",
                "https://cdn.grief.cloud/roleplay/pat/pat16.gif",
                "https://cdn.grief.cloud/roleplay/pat/pat17.gif",
                "https://cdn.grief.cloud/roleplay/pat/pat18.gif",
                "https://cdn.grief.cloud/roleplay/pat/pat19.gif",
                "https://cdn.grief.cloud/roleplay/pat/pat20.gif",
            ],
            "tickle": [
                "https://cdn.grief.cloud/roleplay/tickle/tickle1.gif",
                "https://cdn.grief.cloud/roleplay/tickle/tickle2.gif",
                "https://cdn.grief.cloud/roleplay/tickle/tickle3.gif",
                "https://cdn.grief.cloud/roleplay/tickle/tickle4.gif",
                "https://cdn.grief.cloud/roleplay/tickle/tickle5.gif",
                "https://cdn.grief.cloud/roleplay/tickle/tickle6.gif",
                "https://cdn.grief.cloud/roleplay/tickle/tickle7.gif",
                "https://cdn.grief.cloud/roleplay/tickle/tickle8.gif",
                "https://cdn.grief.cloud/roleplay/tickle/tickle9.gif",
                "https://cdn.grief.cloud/roleplay/tickle/tickle10.gif",
                "https://cdn.grief.cloud/roleplay/tickle/tickle11.gif",
                "https://cdn.grief.cloud/roleplay/tickle/tickle12.gif",
                "https://cdn.grief.cloud/roleplay/tickle/tickle13.gif",
                "https://cdn.grief.cloud/roleplay/tickle/tickle14.gif",
                "https://cdn.grief.cloud/roleplay/tickle/tickle15.gif",
                "https://cdn.grief.cloud/roleplay/tickle/tickle16.gif",
                "https://cdn.grief.cloud/roleplay/tickle/tickle17.gif",
                "https://cdn.grief.cloud/roleplay/tickle/tickle18.gif",
            ],
            "lick": [
                "https://cdn.grief.cloud/roleplay/lick/lick1.gif",
                "https://cdn.grief.cloud/roleplay/lick/lick2.gif",
                "https://cdn.grief.cloud/roleplay/lick/lick3.gif",
                "https://cdn.grief.cloud/roleplay/lick/lick4.gif",
                "https://cdn.grief.cloud/roleplay/lick/lick5.gif",
                "https://cdn.grief.cloud/roleplay/lick/lick6.gif",
                "https://cdn.grief.cloud/roleplay/lick/lick7.gif",
                "https://cdn.grief.cloud/roleplay/lick/lick8.gif",
                "https://cdn.grief.cloud/roleplay/lick/lick9.gif",
                "https://cdn.grief.cloud/roleplay/lick/lick10.gif",
                "https://cdn.grief.cloud/roleplay/lick/lick11.gif",
                "https://cdn.grief.cloud/roleplay/lick/lick12.gif",
                "https://cdn.grief.cloud/roleplay/lick/lick13.gif",
                "https://cdn.grief.cloud/roleplay/lick/lick14.gif",
                "https://cdn.grief.cloud/roleplay/lick/lick15.gif",
                "https://cdn.grief.cloud/roleplay/lick/lick16.gif",
            ],
            "slap": [
                "https://cdn.grief.cloud/roleplay/slap/slap1.gif",
                "https://cdn.grief.cloud/roleplay/slap/slap2.gif",
                "https://cdn.grief.cloud/roleplay/slap/slap3.gif",
                "https://cdn.grief.cloud/roleplay/slap/slap4.gif",
                "https://cdn.grief.cloud/roleplay/slap/slap5.gif",
                "https://cdn.grief.cloud/roleplay/slap/slap6.gif",
                "https://cdn.grief.cloud/roleplay/slap/slap7.gif",
                "https://cdn.grief.cloud/roleplay/slap/slap8.gif",
                "https://cdn.grief.cloud/roleplay/slap/slap9.gif",
                "https://cdn.grief.cloud/roleplay/slap/slap10.gif",
                "https://cdn.grief.cloud/roleplay/slap/slap11.gif",
                "https://cdn.grief.cloud/roleplay/slap/slap12.gif",
                "https://cdn.grief.cloud/roleplay/slap/slap13.gif",
                "https://cdn.grief.cloud/roleplay/slap/slap14.gif",
                "https://cdn.grief.cloud/roleplay/slap/slap15.gif",
            ],
            "punch": [
                "https://cdn.grief.cloud/roleplay/punch/punch1.gif",
                "https://cdn.grief.cloud/roleplay/punch/punch2.gif",
                "https://cdn.grief.cloud/roleplay/punch/punch3.gif",
                "https://cdn.grief.cloud/roleplay/punch/punch4.gif",
                "https://cdn.grief.cloud/roleplay/punch/punch5.gif",
                "https://cdn.grief.cloud/roleplay/punch/punch6.gif",
                "https://cdn.grief.cloud/roleplay/punch/punch7.gif",
                "https://cdn.grief.cloud/roleplay/punch/punch8.gif",
                "https://cdn.grief.cloud/roleplay/punch/punch9.gif",
                "https://cdn.grief.cloud/roleplay/punch/punch10.gif",
                "https://cdn.grief.cloud/roleplay/punch/punch11.gif",
                "https://cdn.grief.cloud/roleplay/punch/punch12.gif",
                "https://cdn.grief.cloud/roleplay/punch/punch13.gif",
                "https://cdn.grief.cloud/roleplay/punch/punch14.gif",
                "https://cdn.grief.cloud/roleplay/punch/punch15.gif",
                "https://cdn.grief.cloud/roleplay/punch/punch16.gif",
                "https://cdn.grief.cloud/roleplay/punch/punch17.gif",
                "https://cdn.grief.cloud/roleplay/punch/punch18.gif",
                "https://cdn.grief.cloud/roleplay/punch/punch19.gif",
                "https://cdn.grief.cloud/roleplay/punch/punch20.gif",
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
            "lick_s": 0,
            "spank_s": 0,
            "feed_s": 0,
            "punch_s": 0,
            "highfive_s": 0,
            "kill_s": 0,
            "bite_s": 0,
            "dance": 0,
            "yeet_s": 0,
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
            "lick_r": 0,
            "spank_r": 0,
            "feed_r": 0,
            "punch_r": 0,
            "highfive_r": 0,
            "kill_r": 0,
            "bite_r": 0,
            "yeet_r": 0,
            "nut_r": 0,
            "fuck_r": 0,
        }
        self.config.register_global(**default_global)
        self.config.register_user(**default_member)
        self.config.init_custom("Target", 2)
        self.config.register_custom("Target", **default_target)
        self.cache = {}

    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    async def cuddle(self, ctx: commands.Context, user: discord.Member):
        """
        Cuddles a user.
        """

        images = await self.config.cuddle()

        mn = len(images)
        i = randint(0, mn - 1)

        embed = discord.Embed(
            colour=discord.Colour.dark_theme(),
            description=f"**{ctx.author.mention}** just cuddled {f'**{str(user.mention)}**' if user else 'themselves'}!",
        )

        embed.set_author(name=self.bot.user.display_name, icon_url=self.bot.user.avatar)
        embed.set_image(url=images[i])
        target = await self.config.custom("Target", ctx.author.id, user.id).cuddle_r()
        used = await self.config.user(ctx.author).fuck_s()
        embed.set_footer(
            text=f"{ctx.author.name}'s total cuddles: {used + 1} | {ctx.author.name} has cuddled {user.name} {target + 1} times"
        )
        await send_embed(self, ctx, embed, user)
        await self.config.user(ctx.author).cuddle_s.set(used + 1)
        await self.config.custom("Target", ctx.author.id, user.id).cuddle_r.set(target + 1)

    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    async def poke(self, ctx: commands.Context, user: discord.Member):
        """
        Pokes a user.
        """

        images = await self.config.poke()

        mn = len(images)
        i = randint(0, mn - 1)

        embed = discord.Embed(
            colour=discord.Colour.dark_theme(),
            description=f"**{ctx.author.mention}** just poked {f'**{str(user.mention)}**' if user else 'themselves'}!",
        )

        embed.set_author(name=self.bot.user.display_name, icon_url=self.bot.user.avatar)
        embed.set_image(url=images[i])
        target = await self.config.custom("Target", ctx.author.id, user.id).poke_r()
        used = await self.config.user(ctx.author).poke_s()
        embed.set_footer(
            text=f"{ctx.author.name}'s total pokes: {used + 1} | {ctx.author.name} has poked {user.name} {target + 1} times"
        )
        await send_embed(self, ctx, embed, user)
        await self.config.user(ctx.author).poke_s.set(used + 1)
        await self.config.custom("Target", ctx.author.id, user.id).poke_r.set(target + 1)

    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    async def kiss(self, ctx: commands.Context, user: discord.Member):
        """
        Kiss a user.
        """

        images = await self.config.kiss()

        mn = len(images)
        i = randint(0, mn - 1)

        embed = discord.Embed(
            colour=discord.Colour.dark_theme(),
            description=f"**{ctx.author.mention}** just kissed {f'**{str(user.mention)}**' if user else 'themselves'}!",
        )

        embed.set_author(name=self.bot.user.display_name, icon_url=self.bot.user.avatar)
        embed.set_image(url=images[i])
        target = await self.config.custom("Target", ctx.author.id, user.id).kiss_r()
        used = await self.config.user(ctx.author).kiss_s()
        embed.set_footer(
            text=f"{ctx.author.name}'s total kisses: {used + 1} | {ctx.author.name} has kissed {user.name} {target + 1} times"
        )
        await send_embed(self, ctx, embed, user)
        await self.config.user(ctx.author).kiss_s.set(used + 1)
        await self.config.custom("Target", ctx.author.id, user.id).kiss_r.set(target + 1)

    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    async def hug(self, ctx: commands.Context, user: discord.Member):
        """
        Hugs a user.
        """

        images = await self.config.hug()

        mn = len(images)
        i = randint(0, mn - 1)

        embed = discord.Embed(
            colour=discord.Colour.dark_theme(),
            description=f"**{ctx.author.mention}** just hugged {f'**{str(user.mention)}**' if user else 'themselves'}!",
        )

        embed.set_author(name=self.bot.user.display_name, icon_url=self.bot.user.avatar)
        embed.set_image(url=images[i])
        target = await self.config.custom("Target", ctx.author.id, user.id).hug_r()
        used = await self.config.user(ctx.author).hug_s()
        embed.set_footer(
            text=f"{ctx.author.name}'s total hugs: {used + 1} | {ctx.author.name} has hugged {user.name} {target + 1} times"
        )
        await send_embed(self, ctx, embed, user)
        await self.config.user(ctx.author).hug_s.set(used + 1)
        await self.config.custom("Target", ctx.author.id, user.id).hug_r.set(target + 1)

    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    async def pat(self, ctx: commands.Context, user: discord.Member):
        """
        Pats a user.
        """

        images = await self.config.pat()

        mn = len(images)
        i = randint(0, mn - 1)

        embed = discord.Embed(
            colour=discord.Colour.dark_theme(),
            description=f"**{ctx.author.mention}** just patted {f'**{str(user.mention)}**' if user else 'themselves'}!",
        )

        embed.set_author(name=self.bot.user.display_name, icon_url=self.bot.user.avatar)
        embed.set_image(url=images[i])
        target = await self.config.custom("Target", ctx.author.id, user.id).hug_r()
        used = await self.config.user(ctx.author).pat_s()
        embed.set_footer(
            text=f"{ctx.author.name}'s total pats: {used + 1} | {ctx.author.name} has patted {user.name} {target + 1} times"
        )
        await send_embed(self, ctx, embed, user)
        await self.config.user(ctx.author).pat_s.set(used + 1)
        await self.config.custom("Target", ctx.author.id, user.id).pat_r.set(target + 1)

    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    async def tickle(self, ctx: commands.Context, user: discord.Member):
        """
        Tickles a user.
        """

        images = await self.config.tickle()

        mn = len(images)
        i = randint(0, mn - 1)

        embed = discord.Embed(
            colour=discord.Colour.dark_theme(),
            description=f"**{ctx.author.mention}** just tickled {f'**{str(user.mention)}**' if user else 'themselves'}!",
        )

        embed.set_author(name=self.bot.user.display_name, icon_url=self.bot.user.avatar)
        embed.set_image(url=images[i])
        target = await self.config.custom("Target", ctx.author.id, user.id).hug_r()
        used = await self.config.user(ctx.author).tickle_s()
        embed.set_footer(
            text=f"{ctx.author.name}'s total tickles: {used + 1} | {ctx.author.name} has tickled {user.name} {target + 1} times"
        )
        await send_embed(self, ctx, embed, user)
        await self.config.user(ctx.author).tickle_s.set(used + 1)
        await self.config.custom("Target", ctx.author.id, user.id).tickle_r.set(target + 1)

    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    async def lick(self, ctx: commands.Context, user: discord.Member):
        """
        Licks a user.
        """

        images = await self.config.lick()

        mn = len(images)
        i = randint(0, mn - 1)

        embed = discord.Embed(
            colour=discord.Colour.dark_theme(),
            description=f"**{ctx.author.mention}** just licked {f'**{str(user.mention)}**' if user else 'themselves'}!",
        )

        embed.set_author(name=self.bot.user.display_name, icon_url=self.bot.user.avatar)
        embed.set_image(url=images[i])
        target = await self.config.custom("Target", ctx.author.id, user.id).lick_r()
        used = await self.config.user(ctx.author).lick_s()
        embed.set_footer(
            text=f"{ctx.author.name}'s total licks: {used + 1} | {ctx.author.name} has licked {user.name} {target + 1} times"
        )
        await send_embed(self, ctx, embed, user)
        await self.config.user(ctx.author).lick_s.set(used + 1)
        await self.config.custom("Target", ctx.author.id, user.id).lick_r.set(target + 1)

    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    async def slap(self, ctx: commands.Context, user: discord.Member):
        """
        Slaps a user.
        """

        images = await self.config.slap()

        mn = len(images)
        i = randint(0, mn - 1)

        embed = discord.Embed(
            colour=discord.Colour.dark_theme(),
            description=f"**{ctx.author.mention}** just slapped {f'**{str(user.mention)}**' if user else 'themselves'}!",
        )

        embed.set_author(name=self.bot.user.display_name, icon_url=self.bot.user.avatar)
        embed.set_image(url=images[i])
        target = await self.config.custom("Target", ctx.author.id, user.id).slap_r()
        used = await self.config.user(ctx.author).lick_s()
        embed.set_footer(
            text=f"{ctx.author.name}'s total slaps: {used + 1} | {ctx.author.name} has slapped {user.name} {target + 1} times"
        )
        await send_embed(self, ctx, embed, user)
        await self.config.user(ctx.author).slap_s.set(used + 1)
        await self.config.custom("Target", ctx.author.id, user.id).slap_r.set(target + 1)

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

        images = await self.config.punch()

        mn = len(images)
        i = randint(0, mn - 1)

        embed = discord.Embed(
            colour=discord.Colour.dark_theme(),
            description=f"**{ctx.author.mention}** punches {f'**{str(user.mention)}**' if user else 'themselves'}!",
        )

        embed.set_author(name=self.bot.user.display_name, icon_url=self.bot.user.avatar)
        embed.set_image(url=images[i])
        target = await self.config.custom("Target", ctx.author.id, user.id).feed_r()
        used = await self.config.user(ctx.author).punch_s()
        embed.set_footer(
            text=f"{ctx.author.name}'s total punches: {used + 1} | {ctx.author.name} has punched {user.name} {target + 1} times"
        )
        await send_embed(self, ctx, embed, user)
        await self.config.user(ctx.author).punch_s.set(used + 1)
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
    await bot.add_cog(Perform(bot))