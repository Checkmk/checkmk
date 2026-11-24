#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.ccc.cleanup import cleanup_globals, register_cleanup, unregister_cleanup


def test_cleanup_globals_calls_the_registered_functions() -> None:
    calls = []

    def cleanup() -> None:
        calls.append("cleanup")

    register_cleanup(cleanup)
    try:
        cleanup_globals()
    finally:
        unregister_cleanup(cleanup)

    assert calls == ["cleanup"]


def test_cleanup_globals_leaves_out_unregistered_functions() -> None:
    calls = []

    def cleanup() -> None:
        calls.append("cleanup")

    register_cleanup(cleanup)
    unregister_cleanup(cleanup)

    cleanup_globals()

    assert not calls


def test_unregistering_an_unknown_function_raises_key_error() -> None:
    with pytest.raises(KeyError):
        unregister_cleanup(lambda: None)
