#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from ast import literal_eval

from cmk.bakery.v2_unstable import Secret

_SECRET_VALUE = "t0ps3cr3t%$%!"

_SECRET = Secret(_SECRET_VALUE, "src", "id")


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
        assert repr(Secret("a", "", "")) != repr(Secret("b", "", ""))

    @staticmethod
    def test_repr_is_evalable() -> None:
        assert literal_eval(repr(_SECRET))

    @staticmethod
    def test_repr_is_password_model_compatible() -> None:
        # this test is a little silly, but it should catch if someone changes the repr
        # in a way that breaks compatibility with the backend password model.
        ui_compatible_model = (
            "cmk_postprocessed",
            _SECRET.source,
            (_SECRET.id, str(_SECRET)),
        )
        assert repr(_SECRET) == repr(ui_compatible_model)
