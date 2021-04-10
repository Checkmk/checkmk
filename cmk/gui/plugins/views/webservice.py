#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import time
from typing import TYPE_CHECKING

from six import ensure_str

import cmk.gui.escaping as escaping
from cmk.gui.globals import html
from cmk.gui.htmllib import HTML
from cmk.gui.type_defs import Rows
from cmk.gui.plugins.views import (
    exporter_registry,
    Exporter,
    join_row,
    output_csv_headers,
)

if TYPE_CHECKING:
    from cmk.gui.views import View


def _export_python_raw(view: "View", rows: Rows) -> None:
    html.write(repr(rows))


exporter_registry.register(Exporter(
    name="python-raw",
    handler=_export_python_raw,
))


def _export_python(view: "View", rows: Rows) -> None:
    html.write_text("[\n")
    html.write(repr([cell.export_title() for cell in view.row_cells]))
    html.write_text(",\n")
    for row in rows:
        html.write_text("[")
        for cell in view.row_cells:
            joined_row = join_row(row, cell)
            content = cell.render_for_export(joined_row)

            # The aggr_treestate painters are returning a dictionary data structure (see
            # paint_aggregated_tree_state()) in case the output_format is not HTML. Only
            # remove the HTML tags from the top level strings produced by painters.
            if isinstance(content, (HTML, str)):
                content = escaping.strip_tags(content)

            html.write(repr(content))
            html.write_text(",")
        html.write_text("],")
    html.write_text("\n]\n")


exporter_registry.register(Exporter(
    name="python",
    handler=_export_python,
))


def _show_json(view: "View", rows: Rows) -> None:
    painted_rows = []

    header_row = []
    for cell in view.row_cells:
        header_row.append(escaping.strip_tags(cell.export_title()))
    painted_rows.append(header_row)

    for row in rows:
        painted_row = []
        for cell in view.row_cells:
            joined_row = join_row(row, cell)
            content = cell.render_for_export(joined_row)
            if isinstance(content, (list, dict)):
                # Allow painters to return lists and dicts, then json encode them
                # as such data structures without wrapping them into strings
                pass

            else:
                content = escaping.strip_tags(str(content).replace("<br>", "\n"))

            painted_row.append(content)

        painted_rows.append(painted_row)

    html.write(json.dumps(painted_rows, indent=True))


def _export_json(view: "View", rows: Rows) -> None:
    _show_json(view, rows)


exporter_registry.register(Exporter(
    name="json",
    handler=_export_json,
))


def _export_json_export(view: "View", rows: Rows) -> None:
    filename = '%s-%s.json' % (view.name,
                               time.strftime('%Y-%m-%d_%H-%M-%S', time.localtime(time.time())))
    html.response.headers["Content-Disposition"] = "Attachment; filename=\"%s\"" % ensure_str(
        filename)

    _show_json(view, rows)


exporter_registry.register(Exporter(
    name="json_export",
    handler=_export_json_export,
))


def _export_jsonp(view: "View", rows: Rows) -> None:
    html.write("%s(\n" % html.request.var('jsonp', 'myfunction'))
    _show_json(view, rows)
    html.write_text(");\n")


exporter_registry.register(Exporter(
    name="jsonp",
    handler=_export_jsonp,
))


class CSVRenderer:
    def show(self, view: "View", rows: Rows) -> None:
        csv_separator = html.request.get_str_input_mandatory("csv_separator", ";")
        first = True
        for cell in view.group_cells + view.row_cells:
            if first:
                first = False
            else:
                html.write(csv_separator)
            content = cell.export_title()
            html.write('"%s"' % self._format_for_csv(content))

        for row in rows:
            html.write_text("\n")
            first = True
            for cell in view.group_cells + view.row_cells:
                if first:
                    first = False
                else:
                    html.write(csv_separator)
                joined_row = join_row(row, cell)
                content = cell.render_for_export(joined_row)
                html.write('"%s"' % self._format_for_csv(content))

    def _format_for_csv(self, raw_data):
        # raw_data can also be int, float, dict (labels)
        if isinstance(raw_data, dict):
            return ', '.join(["%s: %s" % (key, value) for key, value in raw_data.items()])

        return escaping.strip_tags(str(raw_data)).replace('\n', '').replace('"', '""')


def _export_csv_export(view: "View", rows: Rows) -> None:
    output_csv_headers(view.spec)
    CSVRenderer().show(view, rows)


exporter_registry.register(Exporter(
    name="csv_export",
    handler=_export_csv_export,
))


def _export_csv(view: "View", rows: Rows) -> None:
    CSVRenderer().show(view, rows)


exporter_registry.register(Exporter(
    name="csv",
    handler=_export_csv,
))
