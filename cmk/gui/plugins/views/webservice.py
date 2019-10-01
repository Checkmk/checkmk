#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

import json
import time
import six

from cmk.gui.i18n import _
from cmk.gui.globals import html
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
                _tdclass, content = cell.render_content(joined_row)
                html.write(repr(html.strip_tags(content)))
                html.write_text(",")
            html.write_text("],")
        html.write_text("\n]\n")


class JSONLayout(Layout):
    def render(self, rows, view, group_cells, cells, num_columns, show_checkboxes):
        painted_rows = []

        header_row = []
        for cell in cells:
            header_row.append(html.strip_tags(cell.export_title()))
        painted_rows.append(header_row)

        for row in rows:
            painted_row = []
            for cell in cells:
                joined_row = join_row(row, cell)
                content = cell.render_content(joined_row)[1]
                if isinstance(content, (list, dict)):
                    # Allow painters to return lists and dicts, then json encode them
                    # as such data structures without wrapping them into strings
                    pass

                else:
                    if isinstance(content, six.text_type):
                        content = content.encode("utf-8")
                    else:
                        content = "%s" % content
                    content = html.strip_tags(content.replace("<br>", "\n"))

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
        if isinstance(filename, six.text_type):
            filename = filename.encode("utf-8")
        html.response.headers["Content-Disposition"] = "Attachment; filename=\"%s\"" % filename

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
        csv_separator = html.request.var("csv_separator", ";")
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
                _tdclass, content = cell.render_content(joined_row)
                html.write('"%s"' % self._format_for_csv(content))

    def _format_for_csv(self, raw_data):
        # raw_data can also be int, float
        content = "%s" % raw_data
        stripped = html.strip_tags(content).replace('\n', '').replace('"', '""')
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
