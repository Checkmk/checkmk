#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.bakery.v2_alpha import Secret

_SECRET_VALUE = "t0ps3cr3t%$%!"

_SECRET = Secret(_SECRET_VALUE)


class TestSecret:
    @staticmethod
    def test_str_does_not_leak() -> None:
        assert _SECRET_VALUE not in str(_SECRET)

    @staticmethod
    def test_repr_does_not_leak() -> None:
        assert _SECRET_VALUE not in repr(_SECRET)

    @staticmethod
    def test_secret_value_is_accressible() -> None:
        assert _SECRET.revealed == _SECRET_VALUE

    @staticmethod
    def test_repr_changes_with_secret_value() -> None:
        assert repr(Secret("a")) != repr(Secret("b"))
