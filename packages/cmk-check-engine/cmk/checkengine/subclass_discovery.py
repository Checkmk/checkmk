#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

"""
Utility to discover subclass implementations
"""

import logging
from collections.abc import Callable, Mapping
from importlib import import_module
from inspect import isabstract
from pkgutil import iter_modules
from types import ModuleType
from typing import Any

_logger = logging.getLogger(__name__)


class DuplicateIdentifierError(Exception):
    """Raised when two distinct discovered classes claim the same identifier."""

    def __init__(self, identifier: object, existing: type, duplicate: type) -> None:
        super().__init__(
            f"Duplicate discovery identifier {identifier!r}: "
            f"{existing.__module__}.{existing.__qualname__} and "
            f"{duplicate.__module__}.{duplicate.__qualname__}"
        )


def get_default_identifier(cls: type) -> str:
    return cls.__name__


def discover[T, V](
    root_module: ModuleType,
    base_class: type[T] | type[Any],
    get_identifier: Callable[[type[T]], V],
) -> Mapping[V, type[T]]:
    """
    Find all subclasses of `base_class` in module.

    Note: Private submodules are skipped!
    """
    subclasses: dict[V, type[T]] = {}

    for mod_info in iter_modules(root_module.__path__):
        if mod_info.name.startswith("_"):
            # Private submodules are expected to not expose public objects!
            continue

        module_name = f"{root_module.__name__}.{mod_info.name}"
        try:
            module = import_module(module_name)
        except ImportError as exc:
            # A found module may legitimately fail to import because a feature/edition
            # gate withholds it or one of its dependencies. Such gating surfaces as a generic
            # ImportError so we only log it so a broken-but-ungated module leaves a diagnostic
            # trail instead of silently vanishing.
            _logger.debug(
                "Skipping module %(module)s during discovery: %(error)r",
                {"module": module_name, "error": exc},
            )
            continue

        for value in vars(module).values():
            if not (
                isinstance(value, type)
                and issubclass(value, base_class)
                and value is not base_class
                and not isabstract(value)
            ):
                continue

            # Only register classes *owned* by this module (defined here or in one of its
            # private submodules, e.g. re-exported through a package's ``__init__``). This
            # excludes classes merely imported into the module's namespace, which would
            # otherwise be re-registered under the wrong module -- with the winner depending
            # on ``iter_modules`` ordering.
            if not (
                value.__module__ == module.__name__
                or value.__module__.startswith(f"{module.__name__}.")
            ):
                continue

            identifier = get_identifier(value)
            if (existing := subclasses.get(identifier)) is not None and existing is not value:
                raise DuplicateIdentifierError(identifier, existing, value)
            subclasses[identifier] = value

    return subclasses
