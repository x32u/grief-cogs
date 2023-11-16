

from typing import Optional

from grief.core.commands import UserFeedbackCheckFailure
from grief.core.utils.chat_formatting import humanize_number as hn

__all__ = (
    "TagError",
    "MissingTagPermissions",
    "RequireCheckFailure",
    "WhitelistCheckFailure",
    "BlacklistCheckFailure",
    "TagFeedbackError",
    "TagAliasError",
)


class TagError(Exception):
    """Base exception class."""


class MissingTagPermissions(TagError):
    """Raised when a user doesn't have permissions to use a block in a tag."""


class RequireCheckFailure(TagError):
    """
    Raised during tag invocation if the user fails to fulfill
    blacklist or whitelist requirements.
    """

    def __init__(self, response: Optional[str] = None):
        self.response = response
        super().__init__(response)


class WhitelistCheckFailure(RequireCheckFailure):
    """Raised when a user is not in a whitelisted channel or has a whitelisted role."""


class BlacklistCheckFailure(RequireCheckFailure):
    """Raised when a user is in a blacklisted channel or has a blacklisted role."""


class TagFeedbackError(UserFeedbackCheckFailure, TagError):
    """Provides feedback to the user when running tag commands."""


class TagAliasError(TagFeedbackError):
    """Raised to provide feedback if an error occurs while adding/removing a tag alias."""


class BlockCompileError(TagError):
    """Raised when a block fails to compile."""


class TagCharacterLimitReached(TagError):
    """Raised when the TagScript character limit is reached."""

    def __init__(self, limit: int, length: int):
        super().__init__(f"TagScript cannot be longer than {hn(limit)} (**{hn(length)}**).")
