"""
MIT License

Copyright (c) 2020-2023 PhenoM4n4n
Copyright (c) 2023-present japandotorg

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import asyncio
import logging
from typing import Any, List, Optional, Union

import discord
from grief.core import commands
from grief.core.utils.chat_formatting import pagify
from grief.core.utils.menus import DEFAULT_CONTROLS, menu, start_adding_reactions
from grief.core.utils.predicates import MessagePredicate, ReactionPredicate

from .abc import CompositeMetaClass, MixinMeta
from .converters import EmojiRole, ObjectConverter, RealEmojiConverter, StrictRole
from .utils import delete_quietly, my_role_heirarchy

log = logging.getLogger("red.seina.roleutils.reactroles")


class ReactRules:
    NORMAL = "NORMAL"
    UNIQUE = "UNIQUE"
    VERIFY = "VERIFY"
    DROP = "DROP"


class ReactRoles(MixinMeta, metaclass=CompositeMetaClass):
    """
    Reaction Roles.
    """