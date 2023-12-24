

import discord
from datetime import datetime

TITLE_TEXT = "Defender update"
FOOTER_TEXT = "\n\n*- Twentysix, creator of Defender*"
REPO_LINK = "https://github.com/Twentysix26/x26-Cogs"
WARDEN_URL = "https://github.com/Twentysix26/x26-Cogs/wiki/Warden"
SOCIALS = "\n\n[`x26.it`](https://x26.it) - [`Support me!`](https://www.patreon.com/Twentysix26)"
TAG = FOOTER_TEXT + SOCIALS
WARDEN_ANNOUNCEMENT = ("Hello. There is a new auto-module available: **Warden**.\nThis auto-module allows you to define "
                       "complex rules to better monitor, manage and moderate your community.\nIt is now the most "
                       f"versatile module that Defender features and by following the [guide]({WARDEN_URL}) "
                       "you will learn how to leverage its full potential in no time. For any suggestion feel free to "
                       f"open an issue in my [repository]({REPO_LINK}).\n\n"
                       "Also, as a small quality of life improvement, the `[p]defender` command has been aliased to "
                       "`[p]def` (using the standard alias cog would cause some issues).\n\n"
                       "I hope you're enjoying Defender as much as I enjoyed creating it.")
CA_ANNOUNCEMENT = ("Hello, a new auto-module is available: **Comment analysis**.\nThis auto-module leverages Google's "
                   "[Perspective API](https://www.perspectiveapi.com/) to detect all kinds of abusive messages, turning Defender "
                   "in an even smarter tool for monitoring and prevention.\n\nThis update also brings you some new "
                   "debugging tools for Warden (check `[p]def warden`) and more consistent notifications for every module.\n"
                   "To finish up there is now the possibility to assign a *punishing role* through the automodules: "
                   "this is convenient if you want to prevent an offending user from sending messages instead of just expelling "
                   "them. As usual, `[p]def status` will guide you through the setup.\nEnjoy!")

ANNOUNCEMENTS = {
    1601078400: WARDEN_ANNOUNCEMENT,
    1625135507: CA_ANNOUNCEMENT,
}

def _make_announcement_embed(content):
    return discord.Embed(color=discord.Colour.red(), title=TITLE_TEXT, description=content)

def get_announcements_text(*, only_recent=True):
    to_send = {}
    now = datetime.utcnow()

    for k, v in ANNOUNCEMENTS.items():
        ts = datetime.utcfromtimestamp(k)
        if only_recent is True and now > ts: # The announcement is old
            continue
        to_send[k] = {"title": TITLE_TEXT, "description": v + TAG}

    return to_send

def get_announcements_embed(*, only_recent=True):
    to_send = {}
    now = datetime.utcnow()

    for k, v in ANNOUNCEMENTS.items():
        ts = datetime.utcfromtimestamp(k)
        if only_recent is True and now > ts: # The announcement is old
            continue
        to_send[k] = _make_announcement_embed(v + TAG)

    return to_send