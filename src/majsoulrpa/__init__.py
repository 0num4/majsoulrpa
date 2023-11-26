# ruff: noqa: F401
from logging import NullHandler, getLogger

from . import presentation
from ._version import __version__
from .rpa import RPA

getLogger(__name__).addHandler(NullHandler())
