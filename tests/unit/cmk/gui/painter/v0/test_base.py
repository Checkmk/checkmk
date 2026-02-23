#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.painter.v0.base import Cell
from cmk.gui.utils.html import HTML
from cmk.gui.utils.roles import UserPermissions


@pytest.mark.parametrize(
    "input_html,expected_output",
    [
        pytest.param(
            '<a href="https://example.com" class="cmk-url-icon-link">icon</a>',
            "https://example.com",
            id="icon_button_link_simple",
        ),
        pytest.param(
            'See <a href="https://example.com" class="cmk-url-icon-link" target="_blank">icon</a> for more',
            "See https://example.com for more",
            id="icon_button_link_with_surrounding_text",
        ),
        pytest.param(
            '<a href="https://example.com">regular link</a>',
            "regular link",
            id="regular_link_stripping",
        ),
        pytest.param(
            "Line 1<br>Line 2",
            "Line 1\nLine 2",
            id="single_line_break_conversion",
        ),
        pytest.param(
            "Line 1<br/>Line 2<br />Line 3",
            "Line 1\nLine 2\nLine 3",
            id="multiple_line_breaks_conversion",
        ),
        pytest.param(
            '<a href="https://first.com" class="cmk-url-icon-link">icon1</a><br>'
            '<a href="https://second.com" class="cmk-url-icon-link">icon2</a>',
            "https://first.com\nhttps://second.com",
            id="icon_button_links_with_line_breaks",
        ),
        pytest.param(
            "Some <b>bold</b> and <i>italic</i> text",
            "Some bold and italic text",
            id="html_tag_stripping",
        ),
        pytest.param(
            'URL to test: <a href="https://checkmk.com/" title="https://checkmk.com/" target="_blank" '
            'onfocus="if (this.blur) this.blur();" class="cmk-url-icon-link">'
            '<cmk-static-icon data="{&quot;icon&quot;: &quot;link&quot;}" class="iconbutton icon" data-v-app="">'
            '<img data-v-e04608b5="" data-v-02ca4a71="" class="cmk-icon cmk-icon--medium png cmk-icon-app__root iconbutton icon" '
            'src="http://localhost:3000/v260/check_mk/cmk-frontend-vue/assets/icon_www-DOG_jgjg.png" style="--v31288330: rotate(0deg);">'
            "</cmk-static-icon></a><br>"
            'Followed redirect to: <a href="https://www.checkmk.com/" title="https://www.checkmk.com/" target="_blank" '
            'onfocus="if (this.blur) this.blur();" class="cmk-url-icon-link">'
            '<cmk-static-icon data="{&quot;icon&quot;: &quot;link&quot;}" class="iconbutton icon" data-v-app="">'
            '<img data-v-e04608b5="" data-v-02ca4a71="" class="cmk-icon cmk-icon--medium png cmk-icon-app__root iconbutton icon" '
            'src="http://localhost:3000/v260/check_mk/cmk-frontend-vue/assets/icon_www-DOG_jgjg.png" style="--v31288330: rotate(0deg);">'
            "</cmk-static-icon></a><br>"
            "Method: GET<br>"
            "Version: HTTP/2.0<br>"
            "Status: 200 OK<br>"
            "Response time: 0.188 seconds<br>"
            "Page size: 17627 Bytes<br>"
            "User agent: checkmk-active-httpv2/2.6.0<br>",
            "URL to test: https://checkmk.com/\n"
            "Followed redirect to: https://www.checkmk.com/\n"
            "Method: GET\n"
            "Version: HTTP/2.0\n"
            "Status: 200 OK\n"
            "Response time: 0.188 seconds\n"
            "Page size: 17627 Bytes\n"
            "User agent: checkmk-active-httpv2/2.6.0\n",
            id="check_http_example",
        ),
    ],
)
def test_cell_render_html_content(input_html: str, expected_output: str) -> None:
    """Test Cell._render_html_content handles icon button links and line breaks correctly.

    This method is used during CSV/JSON/Python export to convert HTML content to plain text,
    with special handling for:
    - Icon button links (class="cmk-url-icon-link") - replaced with their URLs
    - Line breaks (<br>) - converted to newlines
    - Other HTML tags - stripped
    """
    # Create a minimal Cell instance (EmptyCell doesn't have _render_html_content)
    cell = Cell(
        column_spec=None,
        sort_url_parameter=None,
        registered_painters=None,
        user_permissions=UserPermissions({}, {}, {}, []),
    )

    # Test with string input
    result = cell._render_html_content(input_html)
    assert result == expected_output

    # Test with HTML object input
    result_html = cell._render_html_content(HTML.without_escaping(input_html))
    assert result_html == expected_output
