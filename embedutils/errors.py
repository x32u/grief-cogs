

__all__ = (
    "EmbedUtilsException",
    "EmbedNotFound",
    "EmbedFileError",
    "EmbedLimitReached",
    "EmbedConversionError",
)


class EmbedUtilsException(Exception):
    """Base class for EmbedUtils exceptions."""


class EmbedNotFound(EmbedUtilsException):
    """Raised when an embed isn't found on a message."""


class EmbedFileError(EmbedUtilsException):
    """Provides error messages when users supply invalid/no embed files."""


class EmbedLimitReached(EmbedUtilsException):
    """Raised when the limit for embeds that can be stored has been reached."""


class EmbedConversionError(EmbedUtilsException):
    def __init__(self, error_type: str, error: Exception):
        self.error_type = error_type
        self.error = error
        super().__init__(error)
