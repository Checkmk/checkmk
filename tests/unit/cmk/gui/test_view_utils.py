#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.gui.utils.html import HTML
from cmk.gui.view_utils import format_plugin_output


@pytest.mark.parametrize(
    "args, expected",
    [
        pytest.param(
            '"http://127.0.0.1:5000/heute/che\'ck_mk"',
            HTML(
                """&quot;<a href="http://127.0.0.1:5000/heute/che&#x27;ck_mk" title="http://127.0.0.1:5000/heute/che&#x27;ck_mk" onfocus="if (this.blur) this.blur();" target=''><img src="themes/facelift/images/icon_link.png" class="icon iconbutton png" /></a>"""
            ),
            id="single quote in url",
        ),
        pytest.param(
            '"http://127.0.0.1:5000/heute/check_mk\'"',
            HTML(
                """&quot;<a href="http://127.0.0.1:5000/heute/check_mk&#x27;" title="http://127.0.0.1:5000/heute/check_mk&#x27;" onfocus="if (this.blur) this.blur();" target=''><img src="themes/facelift/images/icon_link.png" class="icon iconbutton png" /></a>"""
            ),
            id="trailing quote in url",
        ),
        pytest.param(
            "'http://127.0.0.1:5000/heute/check_mk'",
            HTML(
                """&#x27;<a href="http://127.0.0.1:5000/heute/check_mk" title="http://127.0.0.1:5000/heute/check_mk" onfocus="if (this.blur) this.blur();" target=''><img src="themes/facelift/images/icon_link.png" class="icon iconbutton png" /></a>"""
            ),
            id="enclosed in single quotes",
        ),
        pytest.param(
            """<A HREF="http://127.0.0.1:5000/heute/check_mk" target="_blank">""",
            HTML(
                """<a href="http://127.0.0.1:5000/heute/check_mk" title="http://127.0.0.1:5000/heute/check_mk" onfocus="if (this.blur) this.blur();" target=''><img src="themes/facelift/images/icon_link.png" class="icon iconbutton png" /></a>"""
            ),
            id="A HREF Replacement",
        ),
    ],
)
def test_button_url(args: str, expected: HTML) -> None:
    assert format_plugin_output(args) == expected
