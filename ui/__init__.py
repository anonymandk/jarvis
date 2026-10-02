"""Compatibility facade for the JARVIS desktop UI package.

The original single-file implementation is kept behind a transparent module
proxy while its components move into responsibility-based modules. Existing
``import ui`` and ``patch.object(ui, ...)`` callers keep the same surface.
"""

from __future__ import annotations

import importlib
import sys
from types import ModuleType

_implementation = importlib.import_module("ui._runtime")
_implementation_names = frozenset(vars(_implementation))
_component_exports = {
    name: tuple(
        module for module_name, module in tuple(sys.modules.items())
        if module_name.startswith("ui.")
        and isinstance(module, ModuleType)
        and name in vars(module)
    )
    for name in _implementation_names
}
__all__ = [name for name in dir(_implementation) if not name.startswith("_")]


class _UIFacade(ModuleType):
    @staticmethod
    def _component_modules():
        return tuple(
            module for module_name, module in tuple(sys.modules.items())
            if module_name.startswith("ui.")
            and isinstance(module, ModuleType)
            and module is not _implementation
        )

    def __getattr__(self, name: str):
        return getattr(_implementation, name)

    def __setattr__(self, name: str, value) -> None:
        if name.startswith("__") or name in {
            "_implementation", "_implementation_names", "_UIFacade", "__all__"
        }:
            super().__setattr__(name, value)
        elif name in _implementation_names or hasattr(_implementation, name):
            setattr(_implementation, name, value)
            for module in _component_exports.get(name, ()):
                setattr(module, name, value)
        else:
            super().__setattr__(name, value)

    def __delattr__(self, name: str) -> None:
        if name in _implementation_names and hasattr(_implementation, name):
            delattr(_implementation, name)
            for module in _component_exports.get(name, ()):
                if hasattr(module, name):
                    delattr(module, name)
        else:
            super().__delattr__(name)

    def __dir__(self):
        return sorted(set(super().__dir__()) | set(dir(_implementation)))


sys.modules[__name__].__class__ = _UIFacade
