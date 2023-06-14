#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.gui.utils.html import HTML
from cmk.gui.view_utils import format_plugin_output


@pytest.mark.parametrize(
    "args, expected",
    [
        pytest.param(
            "https://example.com A simple example",
            HTML(
                """<a href="https://example.com" title="https://example.com" target="_blank" onfocus="if (this.blur) this.blur();"><img src="themes/facelift/images/icon_link.png" class="icon iconbutton png" /></a> A simple example"""
            ),
            id="nothing fancy",
        ),
        pytest.param(
            '"http://127.0.0.1:5000/heute/che\'ck_mk"',
            HTML(
                """<a href="http://127.0.0.1:5000/heute/che&#x27;ck_mk" title="http://127.0.0.1:5000/heute/che&#x27;ck_mk" target="_blank" onfocus="if (this.blur) this.blur();"><img src="themes/facelift/images/icon_link.png" class="icon iconbutton png" /></a>"""
            ),
            id="single quote in url",
        ),
        pytest.param(
            '"http://127.0.0.1:5000/heute/check_mk\'"',
            HTML(
                """<a href="http://127.0.0.1:5000/heute/check_mk&#x27;" title="http://127.0.0.1:5000/heute/check_mk&#x27;" target="_blank" onfocus="if (this.blur) this.blur();"><img src="themes/facelift/images/icon_link.png" class="icon iconbutton png" /></a>"""
            ),
            id="trailing quote in url",
        ),
        pytest.param(
            "'http://127.0.0.1:5000/heute/check_mk'",
            HTML(
                """<a href="http://127.0.0.1:5000/heute/check_mk" title="http://127.0.0.1:5000/heute/check_mk" target="_blank" onfocus="if (this.blur) this.blur();"><img src="themes/facelift/images/icon_link.png" class="icon iconbutton png" /></a>"""
            ),
            id="enclosed in single quotes",
        ),
        pytest.param(
            """<A HREF="http://127.0.0.1:5000/heute/check_mk" target="_blank">Some text </A>""",
            HTML(
                """<a href="http://127.0.0.1:5000/heute/check_mk" title="http://127.0.0.1:5000/heute/check_mk" target="_blank" onfocus="if (this.blur) this.blur();"><img src="themes/facelift/images/icon_link.png" class="icon iconbutton png" /></a> Some text"""
            ),
            id="A HREF Replacement",
        ),
        pytest.param(
            "Don't look at this: https://bitly.com/98K8eH, This is another summary",
            HTML(
                """Don&#x27;t look at this: <a href="https://bitly.com/98K8eH" title="https://bitly.com/98K8eH" target="_blank" onfocus="if (this.blur) this.blur();"><img src="themes/facelift/images/icon_link.png" class="icon iconbutton png" /></a>, This is another summary"""
            ),
            id="The comma is not part of the URL",
        ),
        pytest.param(
            "Link with a state marker: https://bitly.com/98K8eH(!), This is another summary(!!), Another summary with a link https://bitly.com/98K8eH(.)",
            HTML(
                """Link with a state marker: <a href="https://bitly.com/98K8eH" title="https://bitly.com/98K8eH" target="_blank" onfocus="if (this.blur) this.blur();"><img src="themes/facelift/images/icon_link.png" class="icon iconbutton png" /></a><b class="stmark state1">WARN</b>, This is another summary<b class="stmark state2">CRIT</b>, Another summary with a link <a href="https://bitly.com/98K8eH" title="https://bitly.com/98K8eH" target="_blank" onfocus="if (this.blur) this.blur();"><img src="themes/facelift/images/icon_link.png" class="icon iconbutton png" /></a><b class="stmark state0">OK</b>"""
            ),
            id="The link has appended state marker",
        ),
    ],
)
def test_button_url(args: str, expected: HTML) -> None:
    assert format_plugin_output(args) == expected
