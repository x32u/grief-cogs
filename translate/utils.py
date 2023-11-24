

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Union

from grief.core import commands
from translatepy import Translator
from translatepy.exceptions import UnknownLanguage
from translatepy.language import Language
from translatepy.translators import *


class NotFlag(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> str:
        argument = argument.replace("—", "--")  # For iOS' weird smart punctuation
        if argument.startswith("--"):
            raise commands.BadArgument("Text should not start with flag.")
        return argument


class LanguageConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> Language:
        try:
            return Language(argument, threshold=63)
        except UnknownLanguage as e:
            raise commands.BadArgument(str(e))


TRANSLATORS = {
    "auto": Translator(),
    # "bing": BingTranslate(), -> Bad translator tbh, often returning errors
    "deepl": DeeplTranslate(),
    "google": GoogleTranslate(),
    "libre": LibreTranslate(),
    # "microsoft": MicrosoftTranslate(), -> Same as Bing, don't ask me why
    "mymemory": MyMemoryTranslate(),
    "reverso": ReversoTranslate(),
    "translatecom": TranslateComTranslate(),
    "translate.com": TranslateComTranslate(),  # Just in case :p
    "yandex": YandexTranslate(),
}


class TranslatorConverter(commands.Converter):
    async def convert(
        self, ctx: commands.Context, argument: str
    ) -> Union[BaseTranslator, Translator]:
        if argument.lower() in TRANSLATORS.keys():
            return TRANSLATORS[argument.lower()]
        raise commands.BadArgument(f"Invalid translator: `{argument}`")


class TranslateFlags(commands.FlagConverter, case_insensitive=True, prefix="--", delimiter=" "):
    from_lang: str = commands.flag(
        name="from",
        default=Language("auto"),
        converter=LanguageConverter,
        description="The language to translate from.",
    )
    to_lang: str = commands.flag(
        name="to",
        default=Language("eng"),
        converter=LanguageConverter,
        description="The language to translate to.",
    )
    translator: str = commands.flag(
        name="translator",
        aliases=["service", "with"],
        default=Translator(),
        converter=TranslatorConverter,
        description="The translator to use.",
    )

    async def convert(self, ctx: commands.Context, argument: str) -> TranslateFlags:
        argument = argument.replace("—", "--")  # For iOS' weird smart punctuation
        return await super().convert(ctx, argument)


def get_language_from_flag(flag: str) -> Optional[str]:
    with open(Path(__file__).parent / "flags.json", "r") as f:
        flags = json.load(f)
    if flag not in flags:
        return
    if not flags[flag]["country"]:
        return
    return flags[flag]["name"]