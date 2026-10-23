#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from unittest.mock import Mock

import pytest

from cmk.gui.config import Config, RequestCacheConfig
from cmk.gui.display_options import DisplayOptions
from cmk.gui.logged_in import LoggedInUser
from cmk.gui.painter.base import (
    Cell,
    CellDrilldown,
    columns_of_cells,
    InternalPainter,
    JoinCell,
    PainterContext,
)
from cmk.gui.type_defs import ColumnSpec, Row, VisualLinkSpec
from cmk.gui.utils.roles import UserPermissions
from cmk.web.utils.html import HTML
from cmk.web.utils.request_cache import RequestCache
from tests.unit.cmk.gui.helpers.painter_context_test_helper import make_painter_context

_ROW: Row = {"host_name": "heute"}


def _painter(*, use_painter_link: bool = True) -> InternalPainter:
    painter = Mock(spec=InternalPainter)
    painter.columns = ["host_alias"]
    painter.render.return_value = ("", "heute")
    painter.use_painter_link = use_painter_link
    return painter


def _painter_context() -> PainterContext:
    painter_context = make_painter_context(UserPermissions({}, {}, {}, []))
    # A page sets its display options from the request; all of them on allows links.
    painter_context.url_renderer.display_options.options = DisplayOptions.all_on()
    return painter_context


def _request_cache() -> RequestCache[RequestCacheConfig]:
    return RequestCache(Config())


def _cell(
    column_spec: ColumnSpec, drilldown: CellDrilldown, *, use_painter_link: bool = True
) -> Cell:
    return Cell(
        column_spec,
        None,
        {column_spec.name: _painter(use_painter_link=use_painter_link)},
        _painter_context(),
        _request_cache(),
        drilldown=drilldown,
    )


def _join_cell(drilldown: CellDrilldown) -> JoinCell:
    return JoinCell(
        ColumnSpec("alias", join_value="CPU load"),
        None,
        {"alias": _painter()},
        _painter_context(),
        _request_cache(),
        drilldown=drilldown,
    )


def _link_to_view(content: str | HTML, _row: Row, link_spec: VisualLinkSpec) -> str | HTML:
    return f"view:{link_spec.name}:{content}"


def _drilldown_to(url: str) -> CellDrilldown:
    return CellDrilldown(columns=[], url=lambda row: f"{url}?host={row['host_name']}")


def test_cell_render_links_the_content_to_its_drilldown() -> None:
    cell = _cell(ColumnSpec("alias"), _drilldown_to("dashboard.py"))

    _tdclass, content = cell.render(_ROW, _link_to_view, Mock(spec=LoggedInUser))

    assert str(content) == '<a href="dashboard.py?host=heute">heute</a>'


def test_cell_render_follows_the_link_spec_over_the_drilldown() -> None:
    cell = _cell(
        ColumnSpec("alias", link_spec=VisualLinkSpec("views", "host")),
        _drilldown_to("dashboard.py"),
    )

    _tdclass, content = cell.render(_ROW, _link_to_view, Mock(spec=LoggedInUser))

    assert content == "view:host:heute"


def test_cell_render_leaves_a_painter_without_links_unlinked() -> None:
    cell = _cell(ColumnSpec("alias"), _drilldown_to("dashboard.py"), use_painter_link=False)

    _tdclass, content = cell.render(_ROW, _link_to_view, Mock(spec=LoggedInUser))

    assert content == "heute"


def test_cell_render_leaves_a_row_without_a_drilldown_url_unlinked() -> None:
    cell = _cell(ColumnSpec("alias"), CellDrilldown(columns=[], url=lambda _row: None))

    _tdclass, content = cell.render(_ROW, _link_to_view, Mock(spec=LoggedInUser))

    assert content == "heute"


def test_cell_needed_columns_include_the_columns_of_its_drilldown() -> None:
    cell = _cell(ColumnSpec("alias"), CellDrilldown(columns=["host_name"], url=lambda _row: ""))

    assert cell.needed_columns({}) == {"host_alias", "host_name"}


def test_join_cell_render_links_the_view_row_to_its_drilldown() -> None:
    cell = _join_cell(_drilldown_to("dashboard.py"))
    row: Row = {"host_name": "heute", "JOIN": {"CPU load": {"CPU load": 42}}}

    _tdclass, content = cell.render(row, _link_to_view, Mock(spec=LoggedInUser))

    assert str(content) == '<a href="dashboard.py?host=heute">heute</a>'


def test_columns_of_cells_include_the_columns_of_a_join_cells_drilldown() -> None:
    cell = _join_cell(CellDrilldown(columns=["host_name"], url=lambda _row: ""))

    assert columns_of_cells([cell], {}) == {"host_alias", "host_name"}


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
            'class="cmk-url-icon-link">'
            '<cmk-static-icon data="{&quot;icon&quot;: &quot;link&quot;}" class="iconbutton icon" data-v-app="">'
            '<img data-v-e04608b5="" data-v-02ca4a71="" class="cmk-icon cmk-icon--medium png cmk-icon-app__root iconbutton icon" '
            'src="http://localhost:3000/v260/check_mk/cmk-frontend-vue/assets/icon_www-DOG_jgjg.png" style="--v31288330: rotate(0deg);">'
            "</cmk-static-icon></a><br>"
            'Followed redirect to: <a href="https://www.checkmk.com/" title="https://www.checkmk.com/" target="_blank" '
            'class="cmk-url-icon-link">'
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
        painter_context=make_painter_context(UserPermissions({}, {}, {}, [])),
        request_cache=None,
    )

    # Test with string input
    result = cell._render_html_content(input_html)  # noqa: SLF001
    assert result == expected_output

    # Test with HTML object input
    result_html = cell._render_html_content(HTML.without_escaping(input_html))  # noqa: SLF001
    assert result_html == expected_output
