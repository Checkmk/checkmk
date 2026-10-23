#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import importlib
import inspect
import pkgutil
from collections.abc import Iterator, Mapping, Sequence
from typing import Final

from cmk.astrein import checkers
from cmk.astrein.engine import ENGINE_SUMMARIES
from cmk.astrein.framework import ASTVisitorChecker


def _discover_checkers() -> Iterator[type[ASTVisitorChecker]]:
    for module_info in pkgutil.walk_packages(checkers.__path__, f"{checkers.__name__}."):
        module = importlib.import_module(module_info.name)
        for _, member in inspect.getmembers(module, inspect.isclass):
            if issubclass(member, ASTVisitorChecker) and member.__module__ == module.__name__:
                yield member


ALL_CHECKERS: Final[Sequence[type[ASTVisitorChecker]]] = tuple(_discover_checkers())


def all_checkers() -> dict[str, type[ASTVisitorChecker]]:
    return {checker.checker_id: checker for checker in ALL_CHECKERS}


def all_summaries() -> Mapping[str, str]:
    return {
        **{checker.checker_id: checker.summary for checker in ALL_CHECKERS},
        **ENGINE_SUMMARIES,
    }
