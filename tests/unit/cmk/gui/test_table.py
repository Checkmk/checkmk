#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from typing import Literal

import pytest
from bs4 import BeautifulSoup as bs
from pytest import MonkeyPatch

from tests.unit.cmk.gui.compare_html import compare_html

from cmk.gui.htmllib.html import html
from cmk.gui.http import request, response
from cmk.gui.logged_in import LoggedInNobody
from cmk.gui.table import table_element
from cmk.gui.utils.html import HTML
from cmk.gui.utils.output_funnel import output_funnel


def read_out_simple_table(text):
    assert isinstance(text, str)
    # Get the contents of the table as a list of lists
    data = []
    for row in bs(text, "lxml").findAll("tr"):
        columns = row.findAll("th")
        if not columns:
            columns = row.findAll("td")
        row_data = []
        for cell in columns:
            cell = re.sub(r"\s", "", re.sub(r"<[^<]*>", "", cell.text))
            row_data.append(cell)
        data.append(row_data)
    return data


def read_out_csv(text, separator):
    # Get the contents of the table as a list of lists
    data = []
    for row in text.split("\n"):
        columns = row.split(separator)
        data.append([re.sub(r"\s", "", re.sub(r"<[^<]*>", "", cell)) for cell in columns])
    data = [row for row in data if not all(cell == "" for cell in row)]
    return data


@pytest.mark.usefixtures("request_context")
def test_basic() -> None:
    table_id = 0
    title = " TEST "

    with output_funnel.plugged():
        with table_element("%d" % table_id, title, searchable=False, sortable=False) as table:
            table.row()
            table.cell("A", "1")
            table.cell("B", "2")
            table.row()
            table.cell("A", "1")
            table.cell("C", "4")

        written_text = "".join(output_funnel.drain())
    assert read_out_simple_table(written_text) == [["A", "B"], ["1", "2"], ["1", "4"]]


@pytest.mark.usefixtures("request_context")
def test_cell_content_escaping() -> None:
    with output_funnel.plugged():
        with table_element("ding", "TITLE", searchable=False, sortable=False) as table:
            table.row()
            table.cell("A", "<script>alert('A')</script>")
            table.cell("B", HTML.without_escaping("<script>alert('B')</script>"))
            table.cell("C", "<b>C</b>")

        written_text = output_funnel.drain()

    assert "&lt;script&gt;alert(&#x27;A&#x27;)&lt;/script&gt;" in written_text
    assert "<script>alert('B')</script>" in written_text
    assert "<b>C</b>" in written_text


@pytest.mark.usefixtures("request_context")
def test_cell_title_escaping() -> None:
    with output_funnel.plugged():
        with table_element("ding", "TITLE", searchable=False, sortable=False) as table:
            table.row()
            table.cell("<script>alert('A')</script>")
            table.cell(HTML.without_escaping("<script>alert('B')</script>"))
            table.cell("<b>C</b>")

        written_text = output_funnel.drain()

    assert "&lt;script&gt;alert(&#x27;A&#x27;)&lt;/script&gt;" in written_text
    assert "<script>alert('B')</script>" in written_text
    assert "<b>C</b>" in written_text


@pytest.mark.usefixtures("request_context")
def test_plug() -> None:
    table_id = 0
    title = " TEST "

    with output_funnel.plugged():
        with table_element("%d" % table_id, title, searchable=False, sortable=False) as table:
            table.row()
            table.cell("A", "1")
            html.write_text_permissive("a")
            table.cell("B", "2")
            html.write_text_permissive("b")
            table.row()
            table.cell("A", "1")
            html.write_text_permissive("a")
            table.cell("C", "4")
            html.write_text_permissive("c")

        written_text = "".join(output_funnel.drain())
    assert read_out_simple_table(written_text) == [["A", "B"], ["1a", "2b"], ["1a", "4c"]]


@pytest.mark.usefixtures("request_context")
def test_context() -> None:
    table_id = 0
    rows = [(i, i**3) for i in range(10)]
    header = ["Number", "Cubical"]
    with output_funnel.plugged():
        with table_element(table_id="%d" % table_id, searchable=False, sortable=False) as table:
            for row in rows:
                table.row()
                for h, r in zip(header, row):
                    table.cell(h, r)

        written_text = "".join(output_funnel.drain())
    data = read_out_simple_table(written_text)
    assert data.pop(0) == header
    data = [tuple(map(int, row)) for row in data if row and row[0]]
    assert data == rows


@pytest.mark.usefixtures("request_context")
def test_nesting() -> None:
    table_id = 0
    title = " TEST "

    with output_funnel.plugged():
        with table_element("%d" % table_id, title, searchable=False, sortable=False) as table1:
            table1.row()
            table1.cell("A", "1")
            table1.cell("B", "")
            with table_element(
                "%d" % (table_id + 1), title + "2", searchable=False, sortable=False
            ) as table2:
                table2.row()
                table2.cell("_", "+")
                table2.cell("|", "-")

        written_text = "".join(output_funnel.drain())
    assert compare_html(
        written_text,
        """<h3 class="table">  TEST </h3>
                            <script type="text/javascript">\ncmk.utils.update_row_info(\'1 row\');\n</script>
                            <table class="data oddeven">
                            <tr>  <th>   A  </th>  <th>   B  </th> </tr>
                            <tr class="data even0">  <td>   1  </td>  <td>
                                <h3 class="table"> TEST 2</h3>
                                <script type="text/javascript">\ncmk.utils.update_row_info(\'1 row\');\n</script>
                                <table class="data oddeven">
                                <tr><th>_</th><th>|</th></tr>
                                <tr class="data even0"><td>+</td><td>-</td></tr>
                                </table>  </td>
                            </tr>
                            </table>""",
    ), written_text


@pytest.mark.usefixtures("request_context")
def test_nesting_context() -> None:
    table_id = 0
    title = " TEST "

    with output_funnel.plugged():
        with table_element(
            table_id="%d" % table_id, title=title, searchable=False, sortable=False
        ) as table1:
            table1.row()
            table1.cell("A", "1")
            table1.cell("B", "")
            with table_element(
                "%d" % (table_id + 1), title + "2", searchable=False, sortable=False
            ) as table2:
                table2.row()
                table2.cell("_", "+")
                table2.cell("|", "-")

        written_text = "".join(output_funnel.drain())
    assert compare_html(
        written_text,
        """<h3 class="table">  TEST </h3>
                            <script type="text/javascript">\ncmk.utils.update_row_info(\'1 row\');\n</script>
                            <table class="data oddeven">
                            <tr>  <th>   A  </th>  <th>   B  </th> </tr>
                            <tr class="data even0">  <td>   1  </td>  <td>
                                <h3 class="table"> TEST 2</h3>
                                <script type="text/javascript">\ncmk.utils.update_row_info(\'1 row\');\n</script>
                                <table class="data oddeven">
                                <tr><th>_</th><th>|</th></tr>
                                <tr class="data even0"><td>+</td><td>-</td></tr>
                                </table>  </td>
                            </tr>
                            </table>""",
    ), written_text


@pytest.mark.usefixtures("request_context", "patch_theme")
@pytest.mark.parametrize("sortable", [True, False])
@pytest.mark.parametrize("searchable", [True, False])
@pytest.mark.parametrize("limit", [None, 2])
@pytest.mark.parametrize("output_format", ["html", "csv"])
def test_table_cubical(
    monkeypatch: MonkeyPatch,
    sortable: bool,
    searchable: bool,
    limit: int | Literal[False] | None,
    output_format: str,
) -> None:
    monkeypatch.setattr(LoggedInNobody, "save_tableoptions", lambda s: None)

    # Test data
    rows = [(i, i**3) for i in range(10)]
    header = ["Number", "Cubical"]

    # Table options
    table_id = 0
    title = " TEST "
    separator = ";"
    request.set_var("_%s_sort" % table_id, "1,0")
    request.set_var("_%s_actions" % table_id, "1")

    def _render_table() -> None:
        with table_element(
            table_id="%d" % table_id,
            title=title,
            sortable=sortable,
            searchable=searchable,
            limit=limit,
            output_format=output_format,
        ) as table:
            for row in rows:
                table.row()
                for h, r in zip(header, row):
                    table.cell(h, r)

    # Data assertions
    assert output_format in ["html", "csv"], "Fetch is not yet implemented"
    if output_format == "html":
        with output_funnel.plugged():
            _render_table()
            written_text = "".join(output_funnel.drain())

        data = read_out_simple_table(written_text)
        assert data.pop(0) == header, "Wrong header"
    elif output_format == "csv":
        _render_table()
        data = read_out_csv(response.get_data(as_text=True), separator)
        limit = len(data)
        assert data.pop(0) == header, "Wrong header"
    else:
        raise Exception("Not yet implemented")

    # Reconstruct table data
    data = [tuple(map(int, row)) for row in data if row and row[0]]
    if limit is None:
        limit = len(rows)

    # Assert data correctness
    assert len(data) <= limit, f"Wrong number of rows: Got {len(data)}, should be <= {limit}"
    assert data == rows[:limit], f"Incorrect data: {data}\n\nVS\n{rows[:limit]}"
