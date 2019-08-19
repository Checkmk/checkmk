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

from contextlib import contextmanager
import re
import json

import cmk.gui.utils as utils
import cmk.gui.config as config
from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.htmllib import HTML


@contextmanager
def table_element(table_id=None, title=None, **kwargs):
    with html.plugged():
        table = Table(table_id, title, **kwargs)
        try:
            yield table
        finally:
            table._finish_previous()
            table._end()


#.
#   .--Table---------------------------------------------------------------.
#   |                       _____     _     _                              |
#   |                      |_   _|_ _| |__ | | ___                         |
#   |                        | |/ _` | '_ \| |/ _ \                        |
#   |                        | | (_| | |_) | |  __/                        |
#   |                        |_|\__,_|_.__/|_|\___|                        |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   | Usage:                                                               |
#   |                                                                      |
#   |        with table_element() as table:                                |
#   |            table.row()                                               |
#   |            table.cell("header", "content")                           |
#   |                                                                      |
#   '----------------------------------------------------------------------'


class Table(object):
    def __init__(self, table_id=None, title=None, **kwargs):
        super(Table, self).__init__()
        self.next_func = lambda: None
        self.next_header = None

        # Use our pagename as table id if none is specified
        table_id = table_id if table_id is not None else html.myfile

        # determine row limit
        try:
            limit = config.table_row_limit
        except:
            limit = None
        limit = kwargs.get('limit', limit)
        if html.request.var('limit') == 'none' or kwargs.get("output_format", "html") != "html":
            limit = None

        self.id = table_id
        self.title = title
        self.rows = []
        self.limit = limit
        self.headers = []
        self.options = {
            "collect_headers": False,  # also: True, "finished"
            "omit_if_empty": kwargs.get("omit_if_empty", False),
            "omit_empty_columns": kwargs.get("omit_empty_columns", False),
            "omit_headers": kwargs.get("omit_headers", False),
            "searchable": kwargs.get("searchable", True),
            "sortable": kwargs.get("sortable", True),
            "foldable": kwargs.get("foldable", False),
            "output_format": kwargs.get("output_format", "html"),  # possible: html, csv, fetch
        }

        self.empty_text = kwargs.get("empty_text", _("No entries."))
        self.help = kwargs.get("help", None)
        self.css = kwargs.get("css", None)
        self.mode = 'row'

    def row(self, *posargs, **kwargs):
        self._finish_previous()
        self.next_func = lambda: self._add_row(*posargs, **kwargs)

    def text_cell(self, *args, **kwargs):
        self.cell(*args, escape_text=True, **kwargs)

    def cell(self, *posargs, **kwargs):
        self._finish_previous()
        self.next_func = lambda: self._add_cell(*posargs, **kwargs)

    def _finish_previous(self):
        self.next_func()
        self.next_func = lambda: None

    def _add_row(self, css=None, state=0, collect_headers=True, fixed=False, **attrs):
        if self.next_header:
            self.rows.append((self.next_header, None, "header", True, attrs))
            self.next_header = None
        self.rows.append(([], css, state, fixed, attrs))
        if collect_headers:
            if self.options["collect_headers"] is False:
                self.options["collect_headers"] = True
            elif self.options["collect_headers"] is True:
                self.options["collect_headers"] = "finished"
        elif not collect_headers and self.options["collect_headers"] is True:
            self.options["collect_headers"] = False

    def _add_cell(self,
                  title="",
                  text="",
                  css=None,
                  help_txt=None,
                  colspan=None,
                  sortable=True,
                  escape_text=False):
        if escape_text:
            text = html.permissive_attrencode(text)
        else:
            if isinstance(text, HTML):
                text = "%s" % text
            if not isinstance(text, unicode):
                text = str(text)

        htmlcode = text + html.drain()

        if self.options["collect_headers"] is True:
            # small helper to make sorting introducion easier. Cells which contain
            # buttons are never sortable
            if css and 'buttons' in css and sortable:
                sortable = False
            self.headers.append((title, css, help_txt, sortable))

        self.rows[-1][0].append((htmlcode, css, colspan))

    # Intermediate title, shown as soon as there is a following row.
    # We store the group headers in the list of rows, with css None
    # and state set to "header"
    def groupheader(self, title):
        self.next_header = title

    def _end(self):
        if not self.rows and self.options["omit_if_empty"]:
            return

        if self.options["output_format"] == "csv":
            self._write_csv(csv_separator=html.request.var("csv_separator", ";"))
            return

        if self.title:
            if self.options["foldable"]:
                html.begin_foldable_container(treename="table",
                                              id_=self.id,
                                              isopen=True,
                                              indent=False,
                                              title=html.render_h3(self.title,
                                                                   class_=["treeangle", "title"]))
            else:
                html.open_h3()
                html.write(self.title)
                html.close_h3()

        if self.help:
            html.help(self.help)

        if not self.rows:
            html.div(self.empty_text, class_="info")
            return

        # Controls whether or not actions are available for a table
        rows, actions_enabled, actions_visible, search_term, user_opts = self._evaluate_user_opts()

        # Apply limit after search / sorting etc.
        num_rows_unlimited = len(rows)
        limit = self.limit
        if limit is not None:
            # only use rows up to the limit plus the fixed rows
            rows = [rows[i] for i in range(num_rows_unlimited) if i < limit or rows[i][3]]
            # Display corrected number of rows
            num_rows_unlimited -= len([r for r in rows if r[3]])

        # Render header
        self._write_table(rows, actions_enabled, actions_visible, search_term)

        if self.title and self.options["foldable"]:
            html.end_foldable_container()

        if limit is not None and num_rows_unlimited > limit:
            html.message(
                _('This table is limited to show only %d of %d rows. '
                  'Click <a href="%s">here</a> to disable the limitation.') %
                (limit, num_rows_unlimited, html.makeuri([('limit', 'none')])))

        if actions_enabled:
            config.user.save_file("tableoptions", user_opts)
        return

    def _evaluate_user_opts(self):
        table_id = self.id
        rows = self.rows

        search_term = None
        actions_enabled = (self.options["searchable"] or self.options["sortable"])

        if not actions_enabled:
            return rows, False, False, None, None

        user_opts = config.user.load_file("tableoptions", {})
        user_opts.setdefault(table_id, {})
        table_opts = user_opts[table_id]

        # Handle the initial visibility of the actions
        actions_visible = user_opts[table_id].get('actions_visible', False)
        if html.request.var('_%s_actions' % table_id):
            actions_visible = html.request.var('_%s_actions' % table_id) == '1'
            user_opts[table_id]['actions_visible'] = actions_visible

        if html.request.var('_%s_reset' % table_id):
            html.request.del_var('_%s_search' % table_id)
            if 'search' in table_opts:
                del table_opts['search']  # persist

        if self.options["searchable"]:
            # Search is always lower case -> case insensitive
            search_term = html.get_unicode_input('_%s_search' % table_id,
                                                 table_opts.get('search', '')).lower()
            if search_term:
                html.request.set_var('_%s_search' % table_id, search_term)
                table_opts['search'] = search_term  # persist
                rows = _filter_rows(rows, search_term)

        if html.request.var('_%s_reset_sorting' % table_id):
            html.request.del_var('_%s_sort' % table_id)
            if 'sort' in table_opts:
                del table_opts['sort']  # persist

        if self.options["sortable"]:
            # Now apply eventual sorting settings
            sort = html.request.var('_%s_sort' % table_id, table_opts.get('sort'))
            if sort is not None:
                html.request.set_var('_%s_sort' % table_id, sort)
                table_opts['sort'] = sort  # persist
                sort_col, sort_reverse = map(int, sort.split(',', 1))
                rows = _sort_rows(rows, sort_col, sort_reverse)

        return rows, actions_enabled, actions_visible, search_term, user_opts

    def _write_table(self, rows, actions_enabled, actions_visible, search_term):
        headinfo = _("1 row") if len(rows) == 1 else _("%d rows") % len(rows)
        html.javascript("cmk.utils.update_header_info(%s);" % json.dumps(headinfo))

        table_id = self.id

        num_cols = self._get_num_cols(rows)

        empty_columns = self._get_empty_columns(rows, num_cols)
        num_cols -= len([v for v in empty_columns if v])

        html.open_table(class_=["data", "oddeven", self.css])

        # If we have no group headers then paint the headers now
        if self.rows and self.rows[0][2] != "header":
            self._render_headers(
                actions_enabled,
                actions_visible,
                empty_columns,
            )

        if actions_enabled and actions_visible:
            html.open_tr(class_=["data", "even0", "actions"])
            html.open_td(colspan=num_cols)
            if not html.in_form():
                html.begin_form("%s_actions" % table_id)

            if self.options["searchable"]:
                html.open_div(class_="search")
                html.text_input("_%s_search" % table_id)
                html.button("_%s_submit" % table_id, _("Search"))
                html.button("_%s_reset" % table_id, _("Reset search"))
                html.set_focus("_%s_search" % table_id)
                html.close_div()

            if html.request.has_var('_%s_sort' % table_id):
                html.open_div(class_=["sort"])
                html.button("_%s_reset_sorting" % table_id, _("Reset sorting"))
                html.close_div()

            if not html.in_form():
                html.begin_form("%s_actions" % table_id)

            html.hidden_fields()
            html.end_form()
            html.close_tr()

        for nr, (row_spec, css, state, _fixed, attrs) in enumerate(rows):
            if not css and "class_" in attrs:
                css = attrs.pop("class_")
            if not css and "class" in attrs:
                css = attrs.pop("class")

            # Intermediate header
            if state == "header":
                # Show the header only, if at least one (non-header) row follows
                if nr < len(rows) - 1 and rows[nr + 1][2] != "header":
                    html.open_tr(class_="groupheader")
                    html.open_td(colspan=num_cols)
                    html.open_h3()
                    html.write(row_spec)
                    html.close_h3()
                    html.close_td()
                    html.close_tr()

                    self._render_headers(actions_enabled, actions_visible, empty_columns)
                continue

            oddeven_name = "even" if (nr - 1) % 2 == 0 else "odd"

            html.open_tr(class_=["data",
                                 "%s%d" % (oddeven_name, state), css if css else None],
                         **attrs)
            for col_index, (cell_content, css_classes, colspan) in enumerate(row_spec):
                if self.options["omit_empty_columns"] and empty_columns[col_index]:
                    continue

                html.open_td(class_=css_classes if css_classes else None,
                             colspan=colspan if colspan else None)
                html.write(cell_content)
                html.close_td()
            html.close_tr()

        if not rows and search_term:
            html.open_tr(class_=["data", "odd0", "no_match"])
            html.td(_('Found no matching rows. Please try another search term.'), colspan=num_cols)
            html.close_tr()

        html.close_table()

    def _get_num_cols(self, rows):
        if self.headers:
            return len(self.headers)
        elif self.rows:
            return len(self.rows[0])
        return 0

    def _get_empty_columns(self, rows, num_cols):
        if not num_cols:
            return []

        empty_columns = [True] * num_cols
        for row_spec, _css, state, _fixed, _attrs in rows:
            if state == "header":
                continue  # Don't care about group headers

            for col_index, (cell_content, _css_classes, _colspan) in enumerate(row_spec):
                empty_columns[col_index] &= not cell_content
        return empty_columns

    def _write_csv(self, csv_separator):
        rows = self.rows
        headers = self.headers
        limit = self.limit
        omit_headers = self.options["omit_headers"]

        # Apply limit after search / sorting etc.
        if limit is not None:
            rows = rows[:limit]

        # If we have no group headers then paint the headers now
        if not omit_headers and self.rows and self.rows[0][2] != "header":
            html.write(
                csv_separator.join(
                    [html.strip_tags(header) or ""
                     for (header, _css, _help, _sortable) in headers]) + "\n")

        for row_spec, _css, _state, _fixed, _attrs in rows:
            html.write(
                csv_separator.join([
                    html.strip_tags(cell_content)
                    for cell_content, _css_classes, _colspan in row_spec
                ]))
            html.write("\n")

    def _render_headers(self, actions_enabled, actions_visible, empty_columns):
        if self.options["omit_headers"]:
            return

        table_id = self.id

        html.open_tr()
        first_col = True
        for nr, (header, css, help_txt, sortable) in enumerate(self.headers):
            if self.options["omit_empty_columns"] and empty_columns[nr]:
                continue

            text = header

            if help_txt:
                header = '<span title="%s">%s</span>' % (html.attrencode(help_txt), header)

            css_class = "header_%s" % css if css else None

            if not self.options["sortable"] or not sortable:
                html.open_th(class_=css_class)
            else:
                reverse = 0
                sort = html.request.var('_%s_sort' % table_id)
                if sort:
                    sort_col, sort_reverse = map(int, sort.split(',', 1))
                    if sort_col == nr:
                        reverse = 1 if sort_reverse == 0 else 0

                action_uri = html.makeactionuri([('_%s_sort' % table_id, '%d,%d' % (nr, reverse))])
                html.open_th(class_=["sort", css_class],
                             title=_("Sort by %s") % text,
                             onclick="location.href='%s'" % action_uri)

            # Add the table action link
            if first_col:
                first_col = False
                if actions_enabled:
                    if not header:
                        header = "&nbsp;"  # Fixes layout problem with white triangle
                    if actions_visible:
                        state = '0'
                        help_txt = _('Hide table actions')
                        img = 'table_actions_on'
                    else:
                        state = '1'
                        help_txt = _('Display table actions')
                        img = 'table_actions_off'
                    html.open_div(class_=["toggle_actions"])
                    html.icon_button(html.makeuri([('_%s_actions' % table_id, state)]),
                                     help_txt,
                                     img,
                                     cssclass='toggle_actions')
                    html.open_span()
                    html.write(header)
                    html.close_span()
                    html.close_div()
                else:
                    html.write(header)
            else:
                html.write(header)

            html.close_th()
        html.close_tr()


def _filter_rows(rows, search_term):
    filtered_rows = []
    match_regex = re.compile(search_term, re.IGNORECASE)

    for row_spec, css, state, fixed, attrs in rows:
        if state == "header" or fixed:
            filtered_rows.append((row_spec, css, state, fixed, attrs))
            continue  # skip filtering of headers or fixed rows

        for cell_content, _css_classes, _colspan in row_spec:
            if match_regex.search(cell_content):
                filtered_rows.append((row_spec, css, state, fixed, attrs))
                break  # skip other cells when matched
    return filtered_rows


def _sort_rows(rows, sort_col, sort_reverse):
    # remove and remind fixed rows, add to separate list
    fixed_rows = []
    for index, row_spec in enumerate(rows[:]):
        if row_spec[3] is True:
            rows.remove(row_spec)
            fixed_rows.append((index, row_spec))

    # Then use natural sorting to sort the list. Note: due to a
    # change in the number of columns of a table in different software
    # versions the cmp-function might fail. This is because the sorting
    # column is persisted in a user file. So we ignore exceptions during
    # sorting. This gives the user the chance to change the sorting and
    # see the table in the first place.
    try:
        rows.sort(cmp=lambda a, b: utils.cmp_num_split(html.strip_tags(a[0][sort_col][0]),
                                                       html.strip_tags(b[0][sort_col][0])),
                  reverse=sort_reverse == 1)
    except IndexError:
        pass

    # Now re-add the removed "fixed" rows to the list again
    if fixed_rows:
        for index, row_spec in fixed_rows:
            rows.insert(index, row_spec)

    return rows
