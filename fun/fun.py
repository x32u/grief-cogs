
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
from grief.core.bot import Red
from grief.core.i18n import Translator, cog_i18n
from grief.core.utils.menus import menu
from grief.core.utils.chat_formatting import (
    bold,
    escape,
    italics,
    humanize_number,
    humanize_timedelta,
)
from typing import Any, Dict, Optional
from . import constants as sub


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

    def __init__(self, bot: Red) -> None:
        super().__init__()
        self.bot = bot
        self.stopwatches = {}

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
    @commands.cooldown(1, 0.5, commands.BucketType.user)
    @commands.bot_has_permissions(embed_links=True)
    @commands.command()
    async def art(self, ctx: commands.Context):
        """Send art from random subreddits."""

        await self._send_reddit_msg(
            ctx, name=_("art image"), emoji="\N{ARTIST PALETTE}", sub=sub.ART, details=True
        )

    @commands.cooldown(1, 0.5, commands.BucketType.user)
    @commands.bot_has_permissions(embed_links=True)
    @commands.command()
    async def birb(self, ctx: commands.Context):
        """Send a random birb image from alexflipnote API."""

        await self._send_other_msg(
            ctx,
            name=_("birb"),
            emoji="\N{BIRD}",
            source="alexflipnote API",
            img_url="https://api.alexflipnote.dev/birb",
            img_arg="file",
            facts=False,
        )

    @commands.cooldown(1, 0.5, commands.BucketType.user)
    @commands.bot_has_permissions(embed_links=True)
    @commands.command(aliases=["cats"])
    async def cat(self, ctx: commands.Context):
        """Send a random cat image some-random-api.ml API."""

        await self._send_other_msg(
            ctx,
            name=_("cat"),
            emoji="\N{CAT FACE}",
            source="nekos.life",
            img_url="https://nekos.life/api/v2/img/meow",
            img_arg="url",
            facts=False,
        )

    @commands.cooldown(1, 0.5, commands.BucketType.user)
    @commands.bot_has_permissions(embed_links=True)
    @commands.command(aliases=["catsfact"])
    async def catfact(self, ctx: commands.Context):
        """Send a random cat fact with a random cat image from some-random-api.ml API."""

        await self._send_other_msg(
            ctx,
            name=_("a cat fact with a random cat image"),
            emoji="\N{CAT FACE}",
            source="nekos.life",
            img_url="https://nekos.life/api/v2/img/meow",
            img_arg="url",
            facts_url="https://some-random-api.ml/facts/cat",
            facts_arg="fact",
            facts=True,
        )

    @commands.cooldown(1, 0.5, commands.BucketType.user)
    @commands.bot_has_permissions(embed_links=True)
    @commands.command()
    async def coffee(self, ctx: commands.Context):
        """Send a random coffee image from alexflipnote API."""

        await self._send_other_msg(
            ctx,
            name=_("your coffee"),
            emoji="\N{HOT BEVERAGE}",
            source="alexflipnote API",
            img_url="https://coffee.alexflipnote.dev/random.json",
            img_arg="file",
            facts=False,
        )

    @commands.cooldown(1, 0.5, commands.BucketType.user)
    @commands.bot_has_permissions(embed_links=True)
    @commands.command(aliases=["cuteness"])
    async def cute(self, ctx: commands.Context):
        """Send a random cute images from random subreddits."""

        await self._send_reddit_msg(
            ctx, name=_("a cute image"), emoji="❤️", sub=sub.CUTE, details=False
        )

    @commands.cooldown(1, 0.5, commands.BucketType.user)
    @commands.bot_has_permissions(embed_links=True)
    @commands.command(aliases=["dogs"])
    async def dog(self, ctx: commands.Context):
        """Send a random dog image from random.dog API."""

        await self._send_other_msg(
            ctx,
            name=_("dog"),
            emoji="\N{DOG FACE}",
            source="random.dog",
            img_url="https://random.dog/woof.json",
            img_arg="url",
            facts=False,
        )

    @commands.cooldown(1, 0.5, commands.BucketType.user)
    @commands.bot_has_permissions(embed_links=True)
    @commands.command(aliases=["dogsfact"])
    async def dogfact(self, ctx: commands.Context):
        """Send a random dog fact with a random dog image from some-random-api.ml API."""

        await self._send_other_msg(
            ctx,
            name=_("a dog fact with a random dog image"),
            emoji="\N{DOG FACE}",
            source="random.dog",
            img_url="https://random.dog/woof.json",
            img_arg="url",
            facts_url="https://some-random-api.ml/facts/dog",
            facts_arg="fact",
            facts=True,
        )

    @commands.cooldown(1, 0.5, commands.BucketType.user)
    @commands.bot_has_permissions(embed_links=True)
    @commands.command()
    async def duck(self, ctx: commands.Context):
        """Send a random duck image from random subreddits."""

        await self._send_reddit_msg(
            ctx, name=_("a duck image"), emoji="\N{DUCK}", sub=sub.DUCKS, details=False
        )

    @commands.cooldown(1, 0.5, commands.BucketType.user)
    @commands.bot_has_permissions(embed_links=True)
    @commands.command(aliases=["ferrets"])
    async def ferret(self, ctx: commands.Context):
        """Send a random ferrets images from random subreddits."""

        await self._send_reddit_msg(
            ctx, name=_("a ferret image"), emoji="❤️", sub=sub.FERRETS, details=False
        )

    @commands.cooldown(1, 0.5, commands.BucketType.user)
    @commands.bot_has_permissions(embed_links=True)
    @commands.command(aliases=["foxes"])
    async def fox(self, ctx: commands.Context):
        """Send a random fox image from randomfox.ca API"""

        await self._send_other_msg(
            ctx,
            name=_("fox"),
            emoji="\N{FOX FACE}",
            source="randomfox.ca",
            img_url="https://randomfox.ca/floof",
            img_arg="image",
            facts=False,
        )

    @commands.cooldown(1, 0.5, commands.BucketType.user)
    @commands.bot_has_permissions(embed_links=True)
    @commands.command(aliases=["pandas"])
    async def panda(self, ctx: commands.Context):
        """Send a random panda image from some-random-api.ml API."""

        await self._send_other_msg(
            ctx,
            name=_("panda"),
            emoji="\N{PANDA FACE}",
            source="some-random-api.ml",
            img_url="https://some-random-api.ml/img/panda",
            img_arg="link",
            facts=False,
        )

    @commands.cooldown(1, 0.5, commands.BucketType.user)
    @commands.bot_has_permissions(embed_links=True)
    @commands.command()
    async def lizard(self, ctx: commands.Context):
        """Send a random lizard image from nekos.life API"""

        await self._send_other_msg(
            ctx,
            name=_("lizard"),
            emoji="\N{LIZARD}",
            source="nekos.life",
            img_url="https://nekos.life/api/lizard",
            img_arg="url",
            facts=False,
        )

    @commands.cooldown(1, 0.5, commands.BucketType.user)
    @commands.bot_has_permissions(embed_links=True)
    @commands.command(aliases=["memes"])
    async def meme(self, ctx: commands.Context):
        """Send a random dank meme from random subreddits."""

        await self._send_reddit_msg(
            ctx, name=_("meme image"), emoji="\N{OK HAND SIGN}", sub=sub.MEMES, details=False
        )

    @commands.cooldown(1, 0.5, commands.BucketType.user)
    @commands.bot_has_permissions(embed_links=True)
    @commands.command(aliases=["pandasfact"])
    async def pandafact(self, ctx: commands.Context):
        """Send a random panda fact with a random panda image from some-random-api.ml API."""

        await self._send_other_msg(
            ctx,
            name=_("a panda fact with a random panda image"),
            emoji="\N{PANDA FACE}",
            source="some-random-api.ml",
            img_url="https://some-random-api.ml/img/panda",
            img_arg="link",
            facts_url="https://some-random-api.ml/facts/panda",
            facts_arg="fact",
            facts=True,
        )

    @commands.cooldown(1, 0.5, commands.BucketType.user)
    @commands.bot_has_permissions(embed_links=True)
    @commands.command(aliases=["pikachu"])
    async def pika(self, ctx: commands.Context):
        """Send a random Pikachu image or GIF from some-random-api.ml API."""

        await self._send_other_msg(
            ctx,
            name=_("Pikachu"),
            emoji="❤️",
            source="some-random-api.ml",
            img_url="https://some-random-api.ml/img/pikachu",
            img_arg="link",
            facts=False,
        )

    @commands.cooldown(1, 0.5, commands.BucketType.user)
    @commands.bot_has_permissions(embed_links=True)
    @commands.command()
    async def shiba(self, ctx: commands.Context):
        """Send a random shiba image from shiba.online API."""

        await self._send_other_msg(
            ctx,
            name=_("shiba"),
            emoji="\N{DOG FACE}",
            source="shibe.online",
            img_url="http://shibe.online/api/shibes",
            img_arg=0,
            facts=False,
        )

    @commands.cooldown(1, 0.5, commands.BucketType.user)
    @commands.bot_has_permissions(embed_links=True)
    @commands.command(aliases=["photography"])
    async def photo(self, ctx: commands.Context):
        """Send a random photography from random subreddits."""

        await self._send_reddit_msg(
            ctx,
            name=_("a photography"),
            emoji="\N{CAMERA WITH FLASH}",
            sub=sub.PHOTOS,
            details=True,
        )

    @commands.cooldown(1, 0.5, commands.BucketType.user)
    @commands.bot_has_permissions(embed_links=True)
    @commands.command(aliases=["subr"])
    @commands.max_concurrency(1, commands.BucketType.user, wait=False)
    async def subreddit(self, ctx: commands.Context, *, subreddit: str):
        """Send a random image from a chosen subreddit."""
        if subreddit in ["friends", "mod"]:
            return await ctx.send("This isn't a valid subreddit.")

        await self._send_reddit_msg(
            ctx,
            name=_("random image"),
            emoji="\N{FRAME WITH PICTURE}",
            sub=[str(subreddit)],
            details=True,
        )

    @commands.cooldown(1, 0.5, commands.BucketType.user)
    @commands.bot_has_permissions(embed_links=True)
    @commands.command(aliases=["wallp"])
    async def wallpaper(self, ctx: commands.Context):
        """Send a random wallpaper image from random subreddits."""

        await self._send_reddit_msg(
            ctx,
            name=_("a wallpaper"),
            emoji="\N{FRAME WITH PICTURE}",
            sub=sub.WALLPAPERS,
            details=True,
        )
