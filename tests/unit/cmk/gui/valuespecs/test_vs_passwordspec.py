#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

import cmk.gui.valuespec as vs
from tests.unit.cmk.gui.compare_html import click_handling, inline_event_handlers

from .utils import render_input


class TestValueSpecPasswordSpec:
    def test_mask(self) -> None:
        assert vs.PasswordSpec().mask("eteer") == "******"


@pytest.mark.usefixtures("request_context", "patch_theme")
def test_password_spec_randomizes_the_password_by_click_action() -> None:
    code = render_input(vs.PasswordSpec(pwlen=12), "")

    assert click_handling(code, "a[title='Randomize password']") == (
        None,
        "valuespec_password_randomize",
        {"length": "12"},
    )


@pytest.mark.usefixtures("request_context", "patch_theme")
def test_password_spec_renders_without_inline_event_handlers() -> None:
    assert inline_event_handlers(render_input(vs.PasswordSpec(), "")) == []
