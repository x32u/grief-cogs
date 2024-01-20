from __future__ import annotations

import random

import uwupy

import discord

from grief.core.bot import Grief
from grief.core.config import Config


async def is_allowed_by_hierarchy(
    bot: Grief, config: Config, guild: discord.Guild, mod: discord.Member, user: discord.Member
):
    if not await config.guild(guild).respect_hierarchy():
        return True
    is_special = mod == guild.owner or await bot.is_owner(mod)
    return mod.top_role > user.top_role or is_special


def uwuize_word(word: str):  # sourcery no-metrics
    # sourcery skip: low-code-quality
    word = word.lower()
    uwu = word.rstrip(".?!,")
    punctuations = word[len(uwu) :]
    final_punctuation = punctuations[-1] if punctuations else ""
    extra_punctuation = punctuations[:-1] if punctuations else ""

    if uwu in {"you're", "youre"}:
        uwu = "ur"
    elif uwu == "sin":
        uwu = "daddy"
    elif uwu == "fuck":
        uwu = "fwickk"
    elif uwu == "shit":
        uwu = "poopoo"
    elif uwu == "bitch":
        uwu = "meanie"
    elif uwu == "asshole":
        uwu = "b-butthole"
    elif uwu in {"dick", "penis"}:
        uwu = "peenie"
    elif uwu in {"cum", "semen"}:
        uwu = "cummies"
    elif uwu == "ass":
        uwu = "boi pussy"
    elif uwu in {"dad", "father"}:
        uwu = "daddy"
    else:
        protected = ""
        if uwu.endswith(("le", "ll", "er", "re")):
            protected = uwu[-2:]
            uwu = uwu[:-2]
        elif uwu.endswith(("les", "lls", "ers", "res")):
            protected = uwu[-3:]
            uwu = uwu[:-3]
        uwu = (
            uwu.replace("l", "w")
            .replace("r", "w")
            .replace("na", "nya")
            .replace("ne", "nye")
            .replace("ni", "nyi")
            .replace("no", "nyo")
            .replace("nu", "nyu")
            .replace("ove", "uv")
            + protected
        )
    uwu += extra_punctuation + final_punctuation
    if len(uwu) > 2 and uwu[0].isalpha() and "-" not in uwu and not random.randint(0, 6):
        uwu = f"{uwu[0]}-{uwu}"
    return uwu


def cap_change(message: str) -> str:
    result = ""
    for char in message:
        value = random.choice([True, False])
        result += char.upper() if value else char.lower()
    return result


def uwuize_string(string: str) -> str:
    """Uwuize and return a string."""
    converted = ""
    current_word = ""
    for letter in string:
        if letter.isprintable() and not letter.isspace():
            current_word += letter
        elif current_word:
            converted += uwuize_word(current_word) + letter
            current_word = ""
        else:
            converted += letter
    if current_word:
        converted += uwuize_word(current_word)
    if converted == string.lower():
        converted = uwupy.uwuify_str(string)
    return converted


def ghetto_word(word: str):  # sourcery no-metrics
    # sourcery skip: low-code-quality
    word = word.lower()
    uwu = word.rstrip(".?!,")
    punctuations = word[len(uwu) :]
    final_punctuation = punctuations[-1] if punctuations else ""
    extra_punctuation = punctuations[:-1] if punctuations else ""
    if uwu in {"you're", "youre"}:
        uwu = "ur"
    elif uwu == "monty":
        uwu = "daddy"
    elif uwu == "you":
        uwu = "chu"
    elif uwu == "lol":
        uwu = "ctfu"
    elif uwu == "lmfao":
        uwu = "ctfu"

    elif uwu == "no":
        uwu = "naur"

    elif uwu == "yes":
        uwu = "yas"
    elif uwu == "wtf":
        uwu = "da fuck"
    uwu += extra_punctuation + final_punctuation

    return uwu


def ghetto_string(string: str) -> str:
    """Make text GHETTO."""
    converted = ""
    current_word = ""
    for letter in string:
        if letter.isprintable() and not letter.isspace():
            current_word += letter
        elif current_word:
            converted += ghetto_word(current_word) + letter
            current_word = ""
        else:
            converted += letter
    if current_word:
        converted += ghetto_word(current_word)
    return converted