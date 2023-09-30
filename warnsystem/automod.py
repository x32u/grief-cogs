import discord
import asyncio

from redbot.core import commands
from redbot.core import checks
from redbot.core.i18n import Translator
from redbot.core.utils import menus
from redbot.core.utils.predicates import MessagePredicate, ReactionPredicate
from redbot.core.utils.chat_formatting import pagify, box
from redbot.core.commands.converter import TimedeltaConverter

from typing import Optional
from datetime import timedelta

from .abc import MixinMeta
from .converters import ValidRegex

_ = Translator("WarnSystem", __file__)


class AutomodMixin(MixinMeta):
    """
    Automod configuration.
    """