import contextlib
import importlib
import json
from pathlib import Path

from redbot.core import VersionInfo

from . import vexutils
from .anotherpingcog import setup

with open(Path(__file__).parent / "info.json") as fp:
    __red_end_user_data_statement__ = json.load(fp)["end_user_data_statement"]
