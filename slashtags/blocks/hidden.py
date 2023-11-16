

from typing import Optional

from TagScriptEngine import Block, Context, helper_parse_if


class HideBlock(Block):
    """
    Hide blocks will send a hidden response if the given parameter is true.
    If there is no parameter i.e. ``{hide}`` it will default to true.

    **Usage:** ``{hide([bool])``

    **Aliases:** ``hidden``

    **Payload:** None

    **Parameter:** bool, None

    **Examples:** ::

        {hide}
        {hide({args(1)}==hide)}
    """

    def will_accept(self, ctx: Context) -> bool:
        dec = ctx.verb.declaration.lower()
        return dec in ("hide", "hidden")

    def process(self, ctx: Context) -> Optional[str]:
        if "hide" in ctx.response.actions.keys():
            return None
        if ctx.verb.parameter is None:
            value = True
        else:
            value = helper_parse_if(ctx.verb.parameter)
        ctx.response.actions["hide"] = value
        return ""
