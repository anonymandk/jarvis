"""Compatibility facade for the JARVIS desktop UI package.

The original single-file implementation is kept behind a transparent module
proxy while its components move into responsibility-based modules. Existing
``import ui`` and ``patch.object(ui, ...)`` callers keep the same surface.
"""

from __future__ import annotations

import importlib
import sys
from types import ModuleType

_implementation = importlib.import_module("ui._legacy")
_implementation_names = frozenset(vars(_implementation))
__all__ = [name for name in dir(_implementation) if not name.startswith("_")]


class _UIFacade(ModuleType):
    def __getattr__(self, name: str):
        return getattr(_implementation, name)

    def __setattr__(self, name: str, value) -> None:
        if name.startswith("__") or name in {
            "_implementation", "_implementation_names", "_UIFacade", "__all__"
        }:
            super().__setattr__(name, value)
        elif name in _implementation_names or hasattr(_implementation, name):
            setattr(_implementation, name, value)
        else:
            super().__setattr__(name, value)

    def __delattr__(self, name: str) -> None:
        if name in _implementation_names and hasattr(_implementation, name):
            delattr(_implementation, name)
        else:
            super().__delattr__(name)

    def __dir__(self):
        return sorted(set(super().__dir__()) | set(dir(_implementation)))


sys.modules[__name__].__class__ = _UIFacade
