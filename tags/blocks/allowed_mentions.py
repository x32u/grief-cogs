

from typing import Optional

from discord import AllowedMentions
from TagScriptEngine import Block, Context


class AllowedMentionsBlock(Block):
    """
    .. warning:: This block is incomplete and cannot be used yet.
    """

    def will_accept(self, ctx: Context) -> bool:
        dec = ctx.verb.declaration.lower()
        return dec == "allowedmentions"

    def process(self, ctx: Context) -> Optional[str]:
        if not (param := ctx.verb.parameter):
            return None
        param = param.strip().lower()
        allowed_mentions = ctx.response.actions.get(
            "allowed_mentions",
            AllowedMentions(everyone=False, users=True, roles=False, replied_user=True),
        )
