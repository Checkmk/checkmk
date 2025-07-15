#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import time
from collections.abc import Callable, Sequence
from html import unescape
from typing import NamedTuple, override

from cmk.ccc.plugin_registry import Registry

from cmk.gui.http import ContentDispositionType, request, response
from cmk.gui.logged_in import user
from cmk.gui.painter.v0 import Cell, join_row
from cmk.gui.type_defs import Rows, ViewSpec
from cmk.gui.utils import escaping
from cmk.gui.utils.html import HTML


class Exporter(NamedTuple):
    name: str
    handler: Callable[[Sequence[Cell], Sequence[Cell], Rows, str, ViewSpec], None]


class ViewExporterRegistry(Registry[Exporter]):
    @override
    def plugin_name(self, instance: Exporter) -> str:
        return instance.name


def output_csv_headers(view: ViewSpec) -> None:
    filename = "{}-{}.csv".format(
        view["name"],
        time.strftime("%Y-%m-%d_%H-%M-%S", time.localtime(time.time())),
    )
    response.set_content_type("text/csv")
    response.set_content_disposition(ContentDispositionType.ATTACHMENT, filename)


exporter_registry = ViewExporterRegistry()


def _export_python_raw(
    row_cells: Sequence[Cell],
    group_cells: Sequence[Cell],
    rows: Rows,
    view_name: str,
    view_spec: ViewSpec,
) -> None:
    response.set_data(repr(rows))


exporter_registry.register(
    Exporter(
        name="python-raw",
        handler=_export_python_raw,
    )
)


def _export_python(
    row_cells: Sequence[Cell],
    group_cells: Sequence[Cell],
    rows: Rows,
    view_name: str,
    view_spec: ViewSpec,
) -> None:
    resp = []
    resp.append("[\n")
    resp.append(repr([cell.export_title() for cell in row_cells]))
    resp.append(",\n")
    for row in rows:
        resp.append("[")
        for cell in row_cells:
            content = cell.render_for_python_export(join_row(row, cell), user)

            # The aggr_treestate painters are returning a dictionary data structure (see
            # paint_aggregated_tree_state()) in case the output_format is not HTML. Only
            # remove the HTML tags from the top level strings produced by painters.
            if isinstance(content, str):
                content = escaping.strip_tags(content)

            resp.append(repr(content))
            resp.append(",")
        resp.append("],")
    resp.append("\n]\n")
    response.set_data("".join(resp))


exporter_registry.register(
    Exporter(
        name="python",
        handler=_export_python,
    )
)


def _get_json_body(
    row_cells: Sequence[Cell],
    group_cells: Sequence[Cell],
    rows: Rows,
    view_name: str,
    view_spec: ViewSpec,
) -> str:
    painted_rows: list[list] = []

    header_row = []
    for cell in row_cells:
        header_row.append(escaping.strip_tags(cell.export_title()))
    painted_rows.append(header_row)

    for row in rows:
        painted_row: list[object] = []
        for cell in row_cells:
            content = cell.render_for_json_export(join_row(row, cell), user)

            if isinstance(content, str):
                content = escaping.strip_tags(content.replace("<br>", "\n"))

            painted_row.append(content)

        painted_rows.append(painted_row)

    return json.dumps(painted_rows, indent=True)


def _export_json(
    row_cells: Sequence[Cell],
    group_cells: Sequence[Cell],
    rows: Rows,
    view_name: str,
    view_spec: ViewSpec,
) -> None:
    response.set_data(_get_json_body(row_cells, group_cells, rows, view_name, view_spec))


exporter_registry.register(
    Exporter(
        name="json",
        handler=_export_json,
    )
)


def _export_json_export(
    row_cells: Sequence[Cell],
    group_cells: Sequence[Cell],
    rows: Rows,
    view_name: str,
    view_spec: ViewSpec,
) -> None:
    filename = "{}-{}.json".format(
        view_name,
        time.strftime("%Y-%m-%d_%H-%M-%S", time.localtime(time.time())),
    )
    response.set_content_type("application/json")
    response.set_content_disposition(
        ContentDispositionType.ATTACHMENT,
        filename,
    )

    response.set_data(_get_json_body(row_cells, group_cells, rows, view_name, view_spec))


exporter_registry.register(
    Exporter(
        name="json_export",
        handler=_export_json_export,
    )
)


def _export_jsonp(
    row_cells: Sequence[Cell],
    group_cells: Sequence[Cell],
    rows: Rows,
    view_name: str,
    view_spec: ViewSpec,
) -> None:
    response.set_data(
        "{}(\n{});\n".format(
            request.var("jsonp", "myfunction"),
            _get_json_body(row_cells, group_cells, rows, view_name, view_spec),
        )
    )


exporter_registry.register(
    Exporter(
        name="jsonp",
        handler=_export_jsonp,
    )
)


def _export_csv_export(
    row_cells: Sequence[Cell],
    group_cells: Sequence[Cell],
    rows: Rows,
    view_name: str,
    view_spec: ViewSpec,
) -> None:
    output_csv_headers(view_spec)
    _export_csv(row_cells, group_cells, rows, view_name, view_spec)


exporter_registry.register(
    Exporter(
        name="csv_export",
        handler=_export_csv_export,
    )
)


def _export_csv(
    row_cells: Sequence[Cell],
    group_cells: Sequence[Cell],
    rows: Rows,
    view_name: str,
    view_spec: ViewSpec,
) -> None:
    csv_separator = request.get_str_input_mandatory("csv_separator", ";")
    cells = list(row_cells)
    cells.extend(group_cells)
    resp = []
    first = True
    for cell in cells:
        if first:
            first = False
        else:
            resp.append(csv_separator)
        resp.append(f'"{_format_for_csv(cell.export_title())}"')
    for row in rows:
        resp.append("\n")
        first = True
        for cell in cells:
            if first:
                first = False
            else:
                resp.append(csv_separator)
            resp.append(
                f'"{_format_for_csv(cell.render_for_csv_export(join_row(row, cell), user))}"'
            )
    response.set_data("".join(resp))


def _format_for_csv(raw_data: str | HTML) -> str:
    return escaping.strip_tags(unescape(str(raw_data))).replace("\n", "").replace('"', '""')


exporter_registry.register(
    Exporter(
        name="csv",
        handler=_export_csv,
    )
)
