from grief.core import commands, checks


@checks.is_owner()
@commands.group(name="dashboard")
async def dashboard(self, ctx: commands.Context):
    """Group command for controlling the web dashboard for Red."""
    pass


class DBMixin:
    """ This is mostly here to easily mess with things... """

    c = dashboard
