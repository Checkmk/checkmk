#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]

from cmk.gui.utils.html import HTML
from cmk.gui.plugins.metrics import html_render


@pytest.mark.parametrize(
    "elements, plain_text, result",
    [([("first", None), ("second", "https://f.s")], True, "first / second"),
     ([("first", None),
       ("second", "https://f.s")], False, HTML("first / <a href=\"https://f.s\">second</a>")),
     ([("", None), ("second", "https://f.s")], True, "second")])
def test_render_title_elements(register_builtin_html, elements, plain_text, result):
    assert html_render.render_title_elements(elements, plain_text=plain_text) == result
