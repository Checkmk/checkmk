#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import time
import six

import cmk.gui.escaping as escaping
from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.htmllib import HTML
from cmk.gui.plugins.views import (
    layout_registry,
    Layout,
    join_row,
    output_csv_headers,
)


@layout_registry.register
class LayoutPythonRaw(Layout):
    @property
    def ident(self):
        return "python-raw"

    @property
    def title(self):
        return _("Python raw data output")

    @property
    def can_display_checkboxes(self):
        return False

    @property
    def is_hidden(self):
        return True

    def render(self, rows, view, group_cells, cells, num_columns, show_checkboxes):
        html.write(repr(rows))


@layout_registry.register
class LayoutPython(Layout):
    @property
    def ident(self):
        return "python"

    @property
    def title(self):
        return _("Python data output")

    @property
    def can_display_checkboxes(self):
        return False

    @property
    def is_hidden(self):
        return True

    def render(self, rows, view, group_cells, cells, num_columns, show_checkboxes):
        html.write_text("[\n")
        html.write(repr([cell.export_title() for cell in cells]))
        html.write_text(",\n")
        for row in rows:
            html.write_text("[")
            for cell in cells:
                joined_row = join_row(row, cell)
                content = cell.render_for_export(joined_row)

                # The aggr_treestate painters are returning a dictionary data structure (see
                # paint_aggregated_tree_state()) in case the output_format is not HTML. Only
                # remove the HTML tags from the top level strings produced by painters.
                if isinstance(content, (HTML, six.string_types)):
                    content = escaping.strip_tags(content)

                html.write(repr(content))
                html.write_text(",")
            html.write_text("],")
        html.write_text("\n]\n")


class JSONLayout(Layout):
    def render(self, rows, view, group_cells, cells, num_columns, show_checkboxes):
        painted_rows = []

        header_row = []
        for cell in cells:
            header_row.append(escaping.strip_tags(cell.export_title()))
        painted_rows.append(header_row)

        for row in rows:
            painted_row = []
            for cell in cells:
                joined_row = join_row(row, cell)
                content = cell.render_for_export(joined_row)
                if isinstance(content, (list, dict)):
                    # Allow painters to return lists and dicts, then json encode them
                    # as such data structures without wrapping them into strings
                    pass

                else:
                    content = "%s" % content
                    content = escaping.strip_tags(content.replace("<br>", "\n"))

                painted_row.append(content)

            painted_rows.append(painted_row)

        html.write(json.dumps(painted_rows, indent=True))


@layout_registry.register
class LayoutJSONExport(JSONLayout):
    @property
    def ident(self):
        return "json_export"

    @property
    def title(self):
        return _("JSON data export")

    @property
    def can_display_checkboxes(self):
        return False

    @property
    def is_hidden(self):
        return True

    def render(self, rows, view, group_cells, cells, num_columns, show_checkboxes):
        filename = '%s-%s.json' % (view['name'],
                                   time.strftime('%Y-%m-%d_%H-%M-%S', time.localtime(time.time())))
        html.response.headers[
            "Content-Disposition"] = "Attachment; filename=\"%s\"" % six.ensure_str(filename)

        super(LayoutJSONExport, self).render(rows, view, group_cells, cells, num_columns,
                                             show_checkboxes)


@layout_registry.register
class LayoutJSON(JSONLayout):
    @property
    def ident(self):
        return "json"

    @property
    def title(self):
        return _("JSON data output")

    @property
    def can_display_checkboxes(self):
        return False

    @property
    def is_hidden(self):
        return True


@layout_registry.register
class LayoutJSONP(JSONLayout):
    @property
    def ident(self):
        return "jsonp"

    @property
    def title(self):
        return _("JSONP data output")

    @property
    def can_display_checkboxes(self):
        return False

    @property
    def is_hidden(self):
        return True

    def render(self, rows, view, group_cells, cells, num_columns, show_checkboxes):
        html.write("%s(\n" % html.request.var('jsonp', 'myfunction'))
        super(LayoutJSONP, self).render(rows, view, group_cells, cells, num_columns,
                                        show_checkboxes)
        html.write_text(");\n")


class CSVLayout(Layout):
    def render(self, rows, view, group_cells, cells, num_columns, show_checkboxes):
        csv_separator = html.request.get_str_input_mandatory("csv_separator", ";")
        first = True
        for cell in group_cells + cells:
            if first:
                first = False
            else:
                html.write(csv_separator)
            content = cell.export_title()
            html.write('"%s"' % self._format_for_csv(content))

        for row in rows:
            html.write_text("\n")
            first = True
            for cell in group_cells + cells:
                if first:
                    first = False
                else:
                    html.write(csv_separator)
                joined_row = join_row(row, cell)
                content = cell.render_for_export(joined_row)
                html.write('"%s"' % self._format_for_csv(content))

    def _format_for_csv(self, raw_data):
        # raw_data can also be int, float
        content = "%s" % raw_data
        stripped = escaping.strip_tags(content).replace('\n', '').replace('"', '""')
        return stripped.encode("utf-8")


@layout_registry.register
class LayoutCSVExport(CSVLayout):
    @property
    def ident(self):
        return "csv_export"

    @property
    def title(self):
        return _("CSV data export")

    @property
    def can_display_checkboxes(self):
        return False

    @property
    def is_hidden(self):
        return True

    def render(self, rows, view, group_cells, cells, num_columns, show_checkboxes):
        output_csv_headers(view)

        super(LayoutCSVExport, self).render(rows, view, group_cells, cells, num_columns,
                                            show_checkboxes)


@layout_registry.register
class LayoutCSV(CSVLayout):
    @property
    def ident(self):
        return "csv"

    @property
    def title(self):
        return _("CSV data output")

    @property
    def can_display_checkboxes(self):
        return False

    @property
    def is_hidden(self):
        return True
