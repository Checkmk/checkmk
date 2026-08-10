#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.livestatus_client import (
    Command,
)


def _all_command_names() -> list[str]:
    """Recursively collect the name() of every concrete (non-abstract) Command subclass."""
    names: list[str] = []
    stack = list(Command.__subclasses__())
    while stack:
        cls = stack.pop()
        stack.extend(cls.__subclasses__())
        if not cls.__abstractmethods__:
            # cls is known concrete here, but mypy can't see that from __abstractmethods__.
            names.append(object.__new__(cls).name())  # type: ignore[type-abstract]
    return names


def test_all_command_names_are_unique() -> None:
    # Regression test: every concrete Command subclass hardcodes its wire name() as a string
    # literal, so it's easy to copy-paste one command's name() into another.
    # Checking uniqueness across *all* commands catches that whole class of bug.
    names = _all_command_names()
    assert len(names) == len(set(names))
