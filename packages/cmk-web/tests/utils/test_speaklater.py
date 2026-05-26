#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.web.utils.speaklater import LazyString, LazyText


def test_lazy_string_mod_returns_self_and_stores_args() -> None:
    lazy = LazyString(str, "Hello %s")
    result = lazy % "World"
    assert result is lazy
    assert str(result) == "Hello World"


def test_lazy_string_mod_with_tuple() -> None:
    lazy = LazyString(str, "%s %s")
    assert str(lazy % ("Hello", "World")) == "Hello World"


def test_lazy_string_rmod_formats_with_self() -> None:
    lazy = LazyString(str, "World")
    assert "Hello %s" % lazy == "Hello World"


def test_lazy_string_rmod_uses_translation_func() -> None:
    lazy = LazyString(lambda text: text.upper(), "world")
    assert "Hello %s" % lazy == "Hello WORLD"


def test_lazy_text_rmod_formats_with_self() -> None:
    lazy = LazyText(lambda: "World")
    assert "Hello %s" % lazy == "Hello World"


def test_lazy_text_rmod_reflects_current_state() -> None:
    state = {"value": "first"}
    lazy = LazyText(lambda: state["value"])
    assert "Hello %s" % lazy == "Hello first"
    state["value"] = "second"
    assert "Hello %s" % lazy == "Hello second"


def test_lazy_text_mod_formats_self_with_other() -> None:
    lazy = LazyText(lambda: "Hello %s")
    assert lazy % "World" == "Hello World"
