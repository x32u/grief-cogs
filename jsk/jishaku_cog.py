import jishaku
from jishaku.cog import OPTIONAL_FEATURES, STANDARD_FEATURES

jishaku.Flags.RETAIN = True
jishaku.Flags.NO_DM_TRACEBACK = True
jishaku.Flags.FORCE_PAGINATOR = True


class Jishaku(*STANDARD_FEATURES, *OPTIONAL_FEATURES):
    """Jishaku ported to Red"""

