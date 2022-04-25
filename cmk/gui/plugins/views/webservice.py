#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import time
from typing import Dict, List, TYPE_CHECKING, Union

import cmk.gui.utils.escaping as escaping
from cmk.gui.http import request, response
from cmk.gui.plugins.views.utils import (
    ExportCellContent,
    Exporter,
    exporter_registry,
    join_row,
    output_csv_headers,
)
from cmk.gui.type_defs import Rows

if TYPE_CHECKING:
    from cmk.gui.views import View


def _export_python_raw(view: "View", rows: Rows) -> None:
    response.set_data(repr(rows))


exporter_registry.register(
    Exporter(
        name="python-raw",
        handler=_export_python_raw,
    )
)


def _export_python(view: "View", rows: Rows) -> None:
    resp = []
    resp.append("[\n")
    resp.append(repr([cell.export_title() for cell in view.row_cells]))
    resp.append(",\n")
    for row in rows:
        resp.append("[")
        for cell in view.row_cells:
            joined_row = join_row(row, cell)
            content = cell.render_for_export(joined_row)

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


def _get_json_body(view: "View", rows: Rows) -> str:
    painted_rows: List[List] = []

    header_row = []
    for cell in view.row_cells:
        header_row.append(escaping.strip_tags(cell.export_title()))
    painted_rows.append(header_row)

    for row in rows:
        painted_row: List[Union[str, Dict]] = []
        for cell in view.row_cells:
            joined_row = join_row(row, cell)
            content = cell.render_for_export(joined_row)
            if isinstance(content, dict):
                # Allow painters to return lists and dicts, then json encode them
                # as such data structures without wrapping them into strings
                pass

            else:
                content = escaping.strip_tags(content.replace("<br>", "\n"))

            painted_row.append(content)

        painted_rows.append(painted_row)

    return json.dumps(painted_rows, indent=True)


def _export_json(view: "View", rows: Rows) -> None:
    response.set_data(_get_json_body(view, rows))


exporter_registry.register(
    Exporter(
        name="json",
        handler=_export_json,
    )
)


def _export_json_export(view: "View", rows: Rows) -> None:
    filename = "%s-%s.json" % (
        view.name,
        time.strftime("%Y-%m-%d_%H-%M-%S", time.localtime(time.time())),
    )
    response.headers["Content-Disposition"] = 'Attachment; filename="%s"' % filename

    response.set_data(_get_json_body(view, rows))


exporter_registry.register(
    Exporter(
        name="json_export",
        handler=_export_json_export,
    )
)


def _export_jsonp(view: "View", rows: Rows) -> None:
    response.set_data(
        "%s(\n%s);\n" % (request.var("jsonp", "myfunction"), _get_json_body(view, rows))
    )


exporter_registry.register(
    Exporter(
        name="jsonp",
        handler=_export_jsonp,
    )
)


class CSVRenderer:
    def show(self, view: "View", rows: Rows) -> None:
        csv_separator = request.get_str_input_mandatory("csv_separator", ";")
        first = True
        resp = []
        for cell in view.group_cells + view.row_cells:
            if first:
                first = False
            else:
                resp.append(csv_separator)
            title = cell.export_title()
            resp.append('"%s"' % self._format_for_csv(title))

        for row in rows:
            resp.append("\n")
            first = True
            for cell in view.group_cells + view.row_cells:
                if first:
                    first = False
                else:
                    resp.append(csv_separator)
                joined_row = join_row(row, cell)
                content = cell.render_for_export(joined_row)
                resp.append('"%s"' % self._format_for_csv(content))

        response.set_data("".join(resp))

    def _format_for_csv(self, raw_data: ExportCellContent) -> str:
        # raw_data can also be int, float, dict (labels)
        if isinstance(raw_data, dict):
            return ", ".join(["%s: %s" % (key, value) for key, value in raw_data.items()])

        return escaping.strip_tags(raw_data).replace("\n", "").replace('"', '""')


def _export_csv_export(view: "View", rows: Rows) -> None:
    output_csv_headers(view.spec)
    CSVRenderer().show(view, rows)


exporter_registry.register(
    Exporter(
        name="csv_export",
        handler=_export_csv_export,
    )
)


def _export_csv(view: "View", rows: Rows) -> None:
    CSVRenderer().show(view, rows)


exporter_registry.register(
    Exporter(
        name="csv",
        handler=_export_csv,
    )
)
