
import random
import datetime
import time
from enum import Enum
from random import randint, choice
from typing import Final
import urllib.parse
import aiohttp
import discord
from grief.core import commands
from grief.core import Config as RedDB
from grief.core.bot import Grief
from grief.core.i18n import Translator, cog_i18n
from grief.core.utils.menus import menu
from grief.core.utils.chat_formatting import (
    bold,
    escape,
    italics,
    humanize_number,
    humanize_timedelta,
    pagify,
)
from typing import Any, Dict, Optional
from . import constants as sub
from .core import Core
from uwuipy import uwuipy
import textwrap
import asyncio


_ = T_ = Translator("General", __file__)

DEFAULT_USER: Dict[str, Any] = {
    "afk": False,
    "reason": None,
    "timestamp": None,
}

class RPS(Enum):
    rock = "\N{MOYAI}"
    paper = "\N{PAGE FACING UP}"
    scissors = "\N{BLACK SCISSORS}\N{VARIATION SELECTOR-16}"



class RPSParser:
    def __init__(self, argument):
        argument = argument.lower()
        if argument == "rock":
            self.choice = RPS.rock
        elif argument == "paper":
            self.choice = RPS.paper
        elif argument == "scissors":
            self.choice = RPS.scissors
        else:
            self.choice = None



MAX_ROLL: Final[int] = 2**64 - 1


@cog_i18n(_)
class Fun(commands.Cog):
    """Fun commands."""

    global _
    _ = lambda s: s
    ball = [
        _("As I see it, yes"),
        _("It is certain"),
        _("It is decidedly so"),
        _("Most likely"),
        _("Outlook good"),
        _("Signs point to yes"),
        _("Without a doubt"),
        _("Yes"),
        _("Yes – definitely"),
        _("You may rely on it"),
        _("Reply hazy, try again"),
        _("Ask again later"),
        _("Better not tell you now"),
        _("Cannot predict now"),
        _("Concentrate and ask again"),
        _("Don't count on it"),
        _("My reply is no"),
        _("My sources say no"),
        _("Outlook not so good"),
        _("Very doubtful"),
    ]
    _ = T_

    def __init__(self, bot: Grief) -> None:
        super().__init__()
        self.bot = bot
        self.stopwatches = {}
        self.lmgtfy_endpoint = "https://cog-creators.github.io"


    async def red_delete_data_for_user(self, **kwargs):
        """Nothing to delete"""
        return

    @commands.command(usage="<first> <second> [others...]")
    async def choose(self, ctx, *choices):
        """Choose between multiple options.

        There must be at least 2 options to pick from.
        Options are separated by spaces.

        To denote options which include whitespace, you should enclose the options in double quotes.
        """
        choices = [escape(c, mass_mentions=True) for c in choices if c]
        if len(choices) < 2:
            await ctx.send(_("Not enough options to pick from."))
        else:
            await ctx.send(choice(choices))

    @commands.command()
    async def roll(self, ctx, number: int = 100):
        """Roll a random number.

        The result will be between 1 and `<number>`.

        `<number>` defaults to 100.
        """
        author = ctx.author
        if 1 < number <= MAX_ROLL:
            n = randint(1, number)
            await ctx.send(
                "{author.mention} :game_die: {n} :game_die:".format(
                    author=author, n=humanize_number(n)
                )
            )
        elif number <= 1:
            await ctx.send(_("{author.mention} Maybe higher than 1? ;P").format(author=author))
        else:
            await ctx.send(
                _("{author.mention} Max allowed number is {maxamount}.").format(
                    author=author, maxamount=humanize_number(MAX_ROLL)
                )
            )

    @commands.command()
    async def flip(self, ctx, user: discord.Member = None):
        """Flip a coin... or a user.

        Defaults to a coin.
        """
        if user is not None:
            msg = ""
            if user.id == ctx.bot.user.id:
                user = ctx.author
                msg = _("Nice try. You think this is funny?\n How about *this* instead:\n\n")
            char = "abcdefghijklmnopqrstuvwxyz"
            tran = "ɐqɔpǝɟƃɥᴉɾʞlɯuodbɹsʇnʌʍxʎz"
            table = str.maketrans(char, tran)
            name = user.display_name.translate(table)
            char = char.upper()
            tran = "∀qƆpƎℲפHIſʞ˥WNOԀQᴚS┴∩ΛMX⅄Z"
            table = str.maketrans(char, tran)
            name = name.translate(table)
            await ctx.send(msg + "(╯°□°）╯︵ " + name[::-1])
        else:
            await ctx.send(_("*flips a coin and... ") + choice([_("HEADS!*"), _("TAILS!*")]))

    @commands.command()
    async def rps(self, ctx, your_choice: RPSParser):
        """Play Rock Paper Scissors."""
        author = ctx.author
        player_choice = your_choice.choice
        if not player_choice:
            return await ctx.send(
                _("This isn't a valid option. Try {r}, {p}, or {s}.").format(
                    r="rock", p="paper", s="scissors"
                )
            )
        red_choice = choice((RPS.rock, RPS.paper, RPS.scissors))
        cond = {
            (RPS.rock, RPS.paper): False,
            (RPS.rock, RPS.scissors): True,
            (RPS.paper, RPS.rock): True,
            (RPS.paper, RPS.scissors): False,
            (RPS.scissors, RPS.rock): False,
            (RPS.scissors, RPS.paper): True,
        }

        if red_choice == player_choice:
            outcome = None  # Tie
        else:
            outcome = cond[(player_choice, red_choice)]

        if outcome is True:
            await ctx.send(
                _("{choice} You win {author.mention}!").format(
                    choice=red_choice.value, author=author
                )
            )
        elif outcome is False:
            await ctx.send(
                _("{choice} You lose {author.mention}!").format(
                    choice=red_choice.value, author=author
                )
            )
        else:
            await ctx.send(
                _("{choice} We're square {author.mention}!").format(
                    choice=red_choice.value, author=author
                )
            )

    @commands.command(name="8", aliases=["8ball"])
    async def _8ball(self, ctx, *, question: str):
        """Ask 8 ball a question.

        Question must end with a question mark.
        """
        if question.endswith("?") and question != "?":
            await ctx.send("`" + T_(choice(self.ball)) + "`")
        else:
            await ctx.send(_("That doesn't look like a question."))

    @commands.command(aliases=["sw"])
    async def stopwatch(self, ctx):
        """Start or stop the stopwatch."""
        author = ctx.author
        if author.id not in self.stopwatches:
            self.stopwatches[author.id] = int(time.perf_counter())
            await ctx.send(author.mention + _(" Stopwatch started!"))
        else:
            tmp = abs(self.stopwatches[author.id] - int(time.perf_counter()))
            tmp = str(datetime.timedelta(seconds=tmp))
            await ctx.send(
                author.mention + _(" Stopwatch stopped! Time: **{seconds}**").format(seconds=tmp)
            )
            self.stopwatches.pop(author.id, None)

    @commands.command()
    async def lmgtfy(self, ctx, *, search_terms: str):
        """Create a lmgtfy link."""
        search_terms = escape(urllib.parse.quote_plus(search_terms), mass_mentions=True)
        await ctx.send("https://lmgtfy.app/?q={}&s=g".format(search_terms))

    @commands.command()
    async def urban(self, ctx, *, word):
        """Search the Urban Dictionary.

        This uses the unofficial Urban Dictionary API.
        """

        try:
            url = "https://api.urbandictionary.com/v0/define"

            params = {"term": str(word).lower()}

            headers = {"content-type": "application/json"}

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=params) as response:
                    data = await response.json()

        except aiohttp.ClientError:
            await ctx.send(
                _("No Urban Dictionary entries were found, or there was an error in the process.")
            )
            return

        if data.get("error") != 404:
            if not data.get("list"):
                return await ctx.send(_("No Urban Dictionary entries were found."))
            if await ctx.embed_requested():
                # a list of embeds
                embeds = []
                for ud in data["list"]:
                    embed = discord.Embed(color=await ctx.embed_color())
                    title = _("{word} by {author}").format(
                        word=ud["word"].capitalize(), author=ud["author"]
                    )
                    if len(title) > 256:
                        title = "{}...".format(title[:253])
                    embed.title = title
                    embed.url = ud["permalink"]

                    description = _("{definition}\n\n**Example:** {example}").format(**ud)
                    if len(description) > 2048:
                        description = "{}...".format(description[:2045])
                    embed.description = description

                    embed.set_footer(
                        text=_(
                            "{thumbs_down} Down / {thumbs_up} Up, Powered by Urban Dictionary."
                        ).format(**ud)
                    )
                    embeds.append(embed)

                if embeds is not None and len(embeds) > 0:
                    await menu(
                        ctx,
                        pages=embeds,
                        message=None,
                        page=0,
                        timeout=30,
                    )
            else:
                messages = []
                for ud in data["list"]:
                    ud.setdefault("example", "N/A")
                    message = _(
                        "<{permalink}>\n {word} by {author}\n\n{description}\n\n"
                        "{thumbs_down} Down / {thumbs_up} Up, Powered by Urban Dictionary."
                    ).format(
                        word=ud.pop("word").capitalize(),
                        description="{description}",
                        **ud,
                    )
                    max_desc_len = 2000 - len(message)

                    description = _("{definition}\n\n**Example:** {example}").format(**ud)
                    if len(description) > max_desc_len:
                        description = "{}...".format(description[: max_desc_len - 3])

                    message = message.format(description=description)
                    messages.append(message)

                if messages is not None and len(messages) > 0:
                    await menu(
                        ctx,
                        pages=messages,
                        message=None,
                        page=0,
                        timeout=30,
                    )
        else:
            await ctx.send(
                _("No Urban Dictionary entries were found, or there was an error in the process.")
            )

    @commands.command()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def uwu(self, ctx: commands.Context, *, message):
      """Uwuify a message."""
      if message == None:
            embed = discord.Embed(description=f"{ctx.author.mention} what do you want me to uwuify?", color = 0x313338)
            await ctx.reply(embed=embed, mention_author=False)
      else:
            uwu = uwuipy()
            uwu_message = uwu.uwuify(message)
            await ctx.reply(uwu_message, mention_author=False)
            

    @commands.command()
    async def penis(self, ctx, *users: discord.Member):
        """Detects user's penis length

        This is 100% accurate.
        Enter multiple users for an accurate comparison!"""
        if not users:
            await ctx.send_help()
            return

        dongs = {}
        msg = ""
        state = random.getstate()

        for user in users:
            random.seed(str(user.id))

            if ctx.bot.user.id == user.id:
                length = 50
            else:
                length = random.randint(0, 30)

            dongs[user] = "8{}D".format("=" * length)

        random.setstate(state)
        dongs = sorted(dongs.items(), key=lambda x: x[1])

        for user, dong in dongs:
            msg += "**{}'s size:**\n{}\n".format(user.display_name, dong)

        for page in pagify(msg):
            await ctx.send(page)

    @commands.is_owner()
    @commands.cooldown(1, 60, commands.BucketType.guild)
    @commands.command(hidden=True)
    async def pingall(self, ctx: commands.Context):
        """Ping everyone. Individually."""
        guild: discord.Guild = ctx.guild
        mentions = " ".join(m.mention for m in guild.members if not m.bot)
        await asyncio.gather(*[ctx.send(chunk, delete_after=3) for chunk in textwrap.wrap(mentions, 1950)])

    @commands.command()
    async def googleit(self, ctx, option: str = None, value: str = None, *args: str):
        """
        Google it!

        To search: !googleit "text" or !googleit text
        To set or display endpoint: !googleit endpoint url or !googleit endpoint
        """
        if option == "endpoint":
            if not value:
                await self._display_endpoint(ctx)
            else:
                await self._set_endpoint(ctx, value)
        else:
            # Assume it's a search
            search_string = ctx.message.clean_content[
                len(ctx.prefix) + len(ctx.invoked_with) + 1 :
            ]
            await self._search(ctx, search_string)

    async def _search(self, ctx, search_string):
        images = [
            "https://media.tenor.com/KhQvEDtumlUAAAAC/here-it-is-americas-got-talent.gif",
            "https://media.tenor.com/bWRm7AHxOwUAAAAd/you-see-jabrils.gif",
            "https://media.tenor.com/70Jj39J1vrAAAAAC/give.gif",
            "https://media.tenor.com/4FK8LHl8w4EAAAAC/come-to-me-dr-evil.gif",
            "https://media.tenor.com/fjDNU3SrgCAAAAAC/loeya-here.gif",
        ]
        encoded_search_string = urllib.parse.quote(search_string)
        lmgtfy_link = f"{self.lmgtfy_endpoint}/lmgtfy/search?q={encoded_search_string}&btnK=Google+Search"
        em = discord.Embed(
            description=f"Hey! Here's what you asked for, [Click here!]({lmgtfy_link})"
        )
        em.color = discord.Color(8599000)
        em.timestamp = datetime.now()
        em.set_image(url=random.choice(images))
        await ctx.send(embed=em)

    @commands.command(name="set_endpoint")
    @commands.is_owner()
    async def _set_endpoint(self, ctx, endpoint_value):
        self.lmgtfy_endpoint = endpoint_value
        await ctx.send(f"LMGTFY endpoint set to: {endpoint_value}")

    @commands.command(name="show_endpoint")
    @commands.is_owner()
    async def _display_endpoint(self, ctx):
        await ctx.send(f"Current LMGTFY endpoint: {self.lmgtfy_endpoint}")