#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Hacky module to avoid cyclic imports, using a naive observer pattern.
This should die..."""

from collections.abc import Callable

cleanup_functions = set()


def register_cleanup(func: Callable[[], None]) -> None:
    cleanup_functions.add(func)


def unregister_cleanup(func: Callable[[], None]) -> None:
    cleanup_functions.remove(func)


# Reset some global variable to their original value. This is needed in
# keepalive mode. We could in fact do some positive caching in keepalive mode,
# e.g. the counters of the hosts could be saved in memory.
def cleanup_globals() -> None:
    for func in cleanup_functions:
        func()
