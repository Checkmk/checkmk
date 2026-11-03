#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
import json

import pytest

from cmk.gui.http import request, response
from cmk.gui.painter import Cell, InternalPainter
from cmk.gui.type_defs import ColumnSpec, Row
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.views.exporter import exporter_registry
from cmk.gui.views.store import multisite_builtin_views
from tests.unit.cmk.gui.helpers.painter_context_test_helper import make_painter_context

PAINTERS = {
    "host": InternalPainter(
        ident="host",
        title="Host",
        columns=["host_name"],
        render=lambda row, _cell, _user, _context: ("", f"<b>{row['host_name']}</b>"),
    ),
    "output": InternalPainter(
        ident="output",
        title="Output",
        columns=["service_plugin_output"],
        render=lambda row, _cell, _user, _context: ("", row["service_plugin_output"]),
    ),
}
ROWS: list[Row] = [
    {"host_name": "alpha", "service_plugin_output": 'said "hi"\nand left'},
    {"host_name": "beta", "service_plugin_output": "OK"},
]


def _export(exporter_name: str) -> str:
    context = make_painter_context(UserPermissions({}, {}, {}, []))
    context.request.set_var("output_format", exporter_name)
    cells = [
        Cell(ColumnSpec(name=name), None, PAINTERS, context, None) for name in ("host", "output")
    ]
    exporter_registry[exporter_name].handler(
        cells, [], ROWS, "allservices", multisite_builtin_views["allservices"]
    )
    return response.get_data(as_text=True)


@pytest.mark.usefixtures("request_context")
def test_the_csv_export_quotes_each_value_without_markup() -> None:
    assert _export("csv").splitlines() == [
        '"host";"output"',
        '"alpha";"said ""hi"" and left"',
        '"beta";"OK"',
    ]


@pytest.mark.usefixtures("request_context")
def test_the_csv_download_uses_the_requested_separator() -> None:
    request.set_var("csv_separator", ",")

    exported = _export("csv_export")

    assert exported.splitlines()[0] == '"host","output"'
    assert 'filename="allservices-' in response.headers["Content-Disposition"]


@pytest.mark.usefixtures("request_context")
def test_the_json_export_starts_with_the_column_titles() -> None:
    assert json.loads(_export("json")) == [
        ["host", "output"],
        ["alpha", 'said "hi"\nand left'],
        ["beta", "OK"],
    ]


@pytest.mark.usefixtures("request_context")
def test_the_json_download_is_an_attachment() -> None:
    exported = _export("json_export")

    assert json.loads(exported)[0] == ["host", "output"]
    assert response.headers["Content-Disposition"].endswith('.json"')


@pytest.mark.usefixtures("request_context")
def test_the_jsonp_export_wraps_the_data_into_the_given_callback() -> None:
    request.set_var("jsonp", "show")

    exported = _export("jsonp")

    assert exported.startswith("show(\n") and exported.endswith(");\n")
    assert json.loads(exported.removeprefix("show(\n").removesuffix(");\n"))[0] == [
        "host",
        "output",
    ]


@pytest.mark.usefixtures("request_context")
def test_the_python_export_is_a_python_literal_without_markup() -> None:
    assert ast.literal_eval(_export("python")) == [
        ["host", "output"],
        ["alpha", 'said "hi"\nand left'],
        ["beta", "OK"],
    ]


@pytest.mark.usefixtures("request_context")
def test_the_raw_python_export_returns_the_rows_unpainted() -> None:
    assert ast.literal_eval(_export("python-raw")) == ROWS
