#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

import cmk.gui.valuespec as vs
from tests.unit.cmk.gui.compare_html import click_handling

from .utils import render_input


@pytest.mark.usefixtures("request_context", "patch_theme")
def test_rule_comment_is_prefixed_by_click_action() -> None:
    onclick, action, _arguments = click_handling(render_input(vs.RuleComment(), ""), "a")

    assert (onclick, action) == (None, "valuespec_rule_comment_prefix")
