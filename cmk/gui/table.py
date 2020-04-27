#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from contextlib import contextmanager
import re
import json
from typing import NamedTuple, Union, cast, Dict, Tuple, List, Optional, Text, Any, Iterator  # pylint: disable=unused-import
import six

import cmk.gui.utils as utils
import cmk.gui.config as config
import cmk.gui.escaping as escaping
from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.htmllib import CSSSpec, HTML, HTMLContent, HTMLTagAttributes  # pylint: disable=unused-import

TableHeader = NamedTuple(
    "TableHeader",
    [
        ("title", Union[int, HTML, str, Text]),  # basically HTMLContent without None
        ("css", CSSSpec),
        ("help_txt", Optional[Text]),
        ("sortable", bool),
    ])

CellSpec = NamedTuple("CellSpec", [
    ("content", Text),
    ("css", CSSSpec),
    ("colspan", Optional[int]),
])

TableRow = NamedTuple("TableRow", [
    ("cells", List[CellSpec]),
    ("css", Optional[str]),
    ("state", int),
    ("fixed", bool),
    ("row_attributes", HTMLTagAttributes),
])

GroupHeader = NamedTuple("GroupHeader", [
    ("title", Text),
    ("fixed", bool),
    ("row_attributes", HTMLTagAttributes),
])

TableRows = List[Union[TableRow, GroupHeader]]


@contextmanager
def table_element(
    table_id=None,  # type: Optional[str]
    title=None,  # type: HTMLContent
    searchable=True,  # type: bool
    sortable=True,  # type: bool
    foldable=False,  # type: bool
    limit=None,  # type: Optional[int]
    output_format="html",  # type: str
    omit_if_empty=False,  # type: bool
    omit_empty_columns=False,  # type: bool
    omit_headers=False,  # type: bool
    empty_text=None,  # type: Optional[Text]
    help=None,  # type: Optional[Text] # pylint: disable=redefined-builtin
    css=None,  # type: Optional[str]
):
    # type: (...) -> Iterator[Table]
    with html.plugged():
        table = Table(table_id=table_id,
                      title=title,
                      searchable=searchable,
                      sortable=sortable,
                      foldable=foldable,
                      limit=limit,
                      output_format=output_format,
                      omit_if_empty=omit_if_empty,
                      omit_empty_columns=omit_empty_columns,
                      omit_headers=omit_headers,
                      empty_text=empty_text,
                      help=help,
                      css=css)
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
    def __init__(
        self,
        table_id=None,  # type: Optional[str]
        title=None,  # type: HTMLContent
        searchable=True,  # type: bool
        sortable=True,  # type: bool
        foldable=False,  # type: bool
        limit=None,  # type: Optional[int]
        output_format="html",  # type: str
        omit_if_empty=False,  # type: bool
        omit_empty_columns=False,  # type: bool
        omit_headers=False,  # type: bool
        empty_text=None,  # type: Optional[Text]
        help=None,  # type: Optional[Text] # pylint: disable=redefined-builtin
        css=None,  # type: Optional[str]
    ):
        super(Table, self).__init__()
        self.next_func = lambda: None
        self.next_header = None  # type: Optional[Text]

        # Use our pagename as table id if none is specified
        table_id = table_id if table_id is not None else html.myfile
        assert table_id is not None

        # determine row limit
        if limit is None:
            limit = config.table_row_limit
        if html.request.get_ascii_input('limit') == 'none' or output_format != "html":
            limit = None

        self.id = table_id
        self.title = title
        self.rows = []  # type: TableRows
        self.limit = limit
        self.headers = []  # type: List[TableHeader]
        self.options = {
            "collect_headers": False,  # also: True, "finished"
            "omit_if_empty": omit_if_empty,
            "omit_empty_columns": omit_empty_columns,
            "omit_headers": omit_headers,
            "searchable": searchable,
            "sortable": sortable,
            "foldable": foldable,
            "output_format": output_format,  # possible: html, csv, fetch
        }

        self.empty_text = empty_text if empty_text is not None else _("No entries.")
        self.help = help
        self.css = css
        self.mode = 'row'

    def row(self, *posargs, **kwargs):
        self._finish_previous()
        self.next_func = lambda: self._add_row(*posargs, **kwargs)

    def text_cell(
        self,
        title="",  # type: HTMLContent
        text="",  # type: HTMLContent
        css=None,  # type: CSSSpec
        help_txt=None,  # type: Optional[Text]
        colspan=None,  # type: Optional[int]
        sortable=True,  # type: bool
    ):
        self.cell(title=title,
                  text=text,
                  css=css,
                  help_txt=help_txt,
                  colspan=colspan,
                  escape_text=True)

    def cell(
        self,
        title="",  # type: HTMLContent
        text="",  # type: HTMLContent
        css=None,  # type: CSSSpec
        help_txt=None,  # type: Optional[Text]
        colspan=None,  # type: Optional[int]
        sortable=True,  # type: bool
        escape_text=False,  # type: bool
    ):
        self._finish_previous()
        self.next_func = lambda: self._add_cell(title=title,
                                                text=text,
                                                css=css,
                                                help_txt=help_txt,
                                                colspan=colspan,
                                                sortable=sortable,
                                                escape_text=escape_text)

    def _finish_previous(self):
        # type: () -> None
        self.next_func()
        self.next_func = lambda: None

    def _add_row(self, css=None, state=0, collect_headers=True, fixed=False, **attrs):
        # type: (Optional[str], int, bool, bool, **Any) -> None
        if self.next_header:
            self.rows.append(GroupHeader(title=self.next_header, fixed=True, row_attributes=attrs))
            self.next_header = None
        self.rows.append(TableRow([], css, state, fixed, attrs))
        if collect_headers:
            if self.options["collect_headers"] is False:
                self.options["collect_headers"] = True
            elif self.options["collect_headers"] is True:
                self.options["collect_headers"] = "finished"
        elif not collect_headers and self.options["collect_headers"] is True:
            self.options["collect_headers"] = False

    def _add_cell(
        self,
        title="",  # type: HTMLContent
        text="",  # type: HTMLContent
        css=None,  # type: CSSSpec
        help_txt=None,  # type: Optional[Text]
        colspan=None,  # type: Optional[int]
        sortable=True,  # type: bool
        escape_text=False,  # type: bool
    ):
        if escape_text:
            cell_text = escaping.escape_text(text)
        else:
            if isinstance(text, HTML):
                cell_text = "%s" % text
            elif not isinstance(text, six.text_type):
                cell_text = str(text)
            else:
                cell_text = text

        htmlcode = cell_text + html.drain()  # type: Text

        if title is None:
            title = ""

        if self.options["collect_headers"] is True:
            # small helper to make sorting introducion easier. Cells which contain
            # buttons are never sortable
            if css and 'buttons' in css and sortable:
                sortable = False
            self.headers.append(
                TableHeader(title=title, css=css, help_txt=help_txt, sortable=sortable))

        current_row = self.rows[-1]
        assert isinstance(current_row, TableRow)
        current_row.cells.append(CellSpec(htmlcode, css, colspan))

    def groupheader(self, title):
        # type: (Text) -> None
        """Intermediate title, shown as soon as there is a following row.
        We store the group headers in the list of rows, with css None and state set to "header"
        """
        self.next_header = title

    def _end(self):
        # type: () -> None
        if not self.rows and self.options["omit_if_empty"]:
            return

        if self.options["output_format"] == "csv":
            self._write_csv(
                csv_separator=html.request.get_str_input_mandatory("csv_separator", ";"))
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
        rows, actions_visible, search_term = self._evaluate_user_opts()

        # Apply limit after search / sorting etc.
        num_rows_unlimited = len(rows)
        limit = self.limit
        if limit is not None:
            # only use rows up to the limit plus the fixed rows
            limited_rows = []
            for index in range(num_rows_unlimited):
                row = rows[index]
                if index < limit or isinstance(row, GroupHeader) or row.fixed:
                    limited_rows.append(row)
            # Display corrected number of rows
            num_rows_unlimited -= len(
                [r for r in limited_rows if isinstance(row, GroupHeader) or r.fixed])
            rows = limited_rows

        # Render header
        self._write_table(rows, self._show_action_row(), actions_visible, search_term)

        if self.title and self.options["foldable"]:
            html.end_foldable_container()

        if limit is not None and num_rows_unlimited > limit:
            html.show_message(
                _('This table is limited to show only %d of %d rows. '
                  'Click <a href="%s">here</a> to disable the limitation.') %
                (limit, num_rows_unlimited, html.makeuri([('limit', 'none')])))

        return

    def _show_action_row(self):
        # type: () -> bool
        if self.options["searchable"]:
            return True

        if self.options["sortable"] and self._get_sort_column(config.user.tableoptions[self.id]):
            return True

        return False

    def _evaluate_user_opts(self):
        # type: () -> Tuple[TableRows, bool, Optional[Text]]
        assert self.id is not None
        table_id = six.ensure_str(self.id)
        rows = self.rows

        search_term = None
        actions_enabled = (self.options["searchable"] or self.options["sortable"])

        if not actions_enabled:
            return rows, False, None

        table_opts = config.user.tableoptions.setdefault(table_id, {})

        # Handle the initial visibility of the actions
        actions_visible = table_opts.get('actions_visible', False)
        if html.request.get_ascii_input('_%s_actions' % table_id):
            actions_visible = html.request.get_ascii_input('_%s_actions' % table_id) == '1'
            table_opts['actions_visible'] = actions_visible

        if html.request.get_ascii_input('_%s_reset' % table_id):
            html.request.del_var('_%s_search' % table_id)
            if 'search' in table_opts:
                del table_opts['search']  # persist

        if self.options["searchable"]:
            # Search is always lower case -> case insensitive
            search_term = html.request.get_unicode_input_mandatory('_%s_search' % table_id,
                                                                   table_opts.get('search', ''))
            search_term = search_term.lower()
            if search_term:
                html.request.set_var('_%s_search' % table_id, search_term)
                table_opts['search'] = search_term  # persist
                rows = _filter_rows(rows, search_term)

        if html.request.get_ascii_input('_%s_reset_sorting' % table_id):
            html.request.del_var('_%s_sort' % table_id)
            if 'sort' in table_opts:
                del table_opts['sort']  # persist

        if self.options["sortable"]:
            # Now apply eventual sorting settings
            sort = self._get_sort_column(table_opts)
            if sort is not None:
                html.request.set_var('_%s_sort' % table_id, sort)
                table_opts['sort'] = sort  # persist
                sort_col, sort_reverse = map(int, sort.split(',', 1))
                rows = _sort_rows(rows, sort_col, sort_reverse)

        if actions_enabled:
            config.user.save_tableoptions()

        return rows, actions_visible, search_term

    def _get_sort_column(self, table_opts):
        # type: (Dict[str, Any]) -> Optional[str]
        return html.request.get_ascii_input('_%s_sort' % self.id, table_opts.get('sort'))

    def _write_table(self, rows, actions_enabled, actions_visible, search_term):
        # type: (TableRows, bool, bool, Optional[Text]) -> None
        headinfo = _("1 row") if len(rows) == 1 else _("%d rows") % len(rows)
        html.javascript("cmk.utils.update_header_info(%s);" % json.dumps(headinfo))

        table_id = self.id

        num_cols = self._get_num_cols(rows)

        empty_columns = self._get_empty_columns(rows, num_cols)
        if self.options["omit_empty_columns"]:
            num_cols -= len([v for v in empty_columns if v])

        html.open_table(class_=["data", "oddeven", self.css])

        # If we have no group headers then paint the headers now
        if self.rows and not isinstance(self.rows[0], GroupHeader):
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

        for nr, row in enumerate(rows):
            # Intermediate header
            if isinstance(row, GroupHeader):
                # Show the header only, if at least one (non-header) row follows
                if nr < len(rows) - 1 and not isinstance(rows[nr + 1], GroupHeader):
                    html.open_tr(class_="groupheader")
                    html.open_td(colspan=num_cols)
                    html.open_h3()
                    html.write(row.title)
                    html.close_h3()
                    html.close_td()
                    html.close_tr()

                    self._render_headers(actions_enabled, actions_visible, empty_columns)
                continue

            oddeven_name = "even" if (nr - 1) % 2 == 0 else "odd"
            class_ = ["data", "%s%d" % (oddeven_name, row.state)]
            if row.css:
                class_.append(row.css)
            else:
                for k in ["class_", "class"]:
                    if k in row.row_attributes:
                        cls_spec = cast(CSSSpec, row.row_attributes.pop(k))
                        if isinstance(cls_spec, list):
                            class_.extend([c for c in cls_spec if c is not None])
                        elif cls_spec is not None:
                            class_.append(cls_spec)

            html.open_tr(class_=class_, **row.row_attributes)
            for col_index, cell in enumerate(row.cells):
                if self.options["omit_empty_columns"] and empty_columns[col_index]:
                    continue

                html.open_td(class_=cell.css, colspan=cell.colspan)
                html.write(cell.content)
                html.close_td()
            html.close_tr()

        if not rows and search_term:
            html.open_tr(class_=["data", "odd0", "no_match"])
            html.td(_('Found no matching rows. Please try another search term.'), colspan=num_cols)
            html.close_tr()

        html.close_table()

    def _get_num_cols(self, rows):
        # type: (TableRows) -> int
        if self.headers:
            return len(self.headers)
        elif self.rows:
            return len(self.rows[0])
        return 0

    def _get_empty_columns(self, rows, num_cols):
        # type: (TableRows, int) -> List[bool]
        if not num_cols:
            return []

        empty_columns = [True] * num_cols
        for row in rows:
            if isinstance(row, GroupHeader):
                continue  # Don't care about group headers

            for col_index, cell in enumerate(row.cells):
                empty_columns[col_index] &= not cell.content
        return empty_columns

    def _write_csv(self, csv_separator):
        # type: (str) -> None
        rows = self.rows
        limit = self.limit
        omit_headers = self.options["omit_headers"]

        # Apply limit after search / sorting etc.
        if limit is not None:
            rows = rows[:limit]

        # If we have no group headers then paint the headers now
        if not omit_headers and self.rows and not isinstance(self.rows[0], GroupHeader):
            html.write(
                csv_separator.join(
                    [escaping.strip_tags(header.title) or "" for header in self.headers]) + "\n")

        for row in rows:
            if isinstance(row, GroupHeader):
                continue

            html.write(csv_separator.join([escaping.strip_tags(cell.content) for cell in row.cells
                                          ]))
            html.write("\n")

    def _render_headers(self, actions_enabled, actions_visible, empty_columns):
        # type: (bool, bool, List[bool]) -> None
        if self.options["omit_headers"]:
            return

        table_id = self.id

        html.open_tr()
        first_col = True
        for nr, header in enumerate(self.headers):
            if self.options["omit_empty_columns"] and empty_columns[nr]:
                continue

            if header.help_txt:
                header_title = html.render_span(
                    header.title, title=header.help_txt)  # type: Union[int, HTML, Text]
            else:
                header_title = header.title

            if not isinstance(header.css, list):
                css_class = [header.css]  # type: CSSSpec
            else:
                css_class = header.css

            assert isinstance(css_class, list)
            css_class = [("header_%s" % c) for c in css_class if c is not None]

            if not self.options["sortable"] or not header.sortable:
                html.open_th(class_=css_class)
            else:
                css_class.insert(0, "sort")
                reverse = 0
                sort = html.request.get_ascii_input('_%s_sort' % table_id)
                if sort:
                    sort_col, sort_reverse = map(int, sort.split(',', 1))
                    if sort_col == nr:
                        reverse = 1 if sort_reverse == 0 else 0

                action_uri = html.makeactionuri([('_%s_sort' % table_id, '%d,%d' % (nr, reverse))])
                html.open_th(class_=css_class,
                             title=_("Sort by %s") % header.title,
                             onclick="location.href='%s'" % action_uri)

            # Add the table action link
            if first_col:
                first_col = False
                if actions_enabled:
                    if not header_title:
                        header_title = "&nbsp;"  # Fixes layout problem with white triangle

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
                    html.write(header_title)
                    html.close_span()
                    html.close_div()
                else:
                    html.write(header_title)
            else:
                html.write(header_title)

            html.close_th()
        html.close_tr()


def _filter_rows(rows, search_term):
    # type: (TableRows, Text) -> TableRows
    filtered_rows = []  # type: TableRows
    match_regex = re.compile(search_term, re.IGNORECASE)

    for row in rows:
        if isinstance(row, GroupHeader) or row.fixed:
            filtered_rows.append(row)
            continue  # skip filtering of headers or fixed rows

        for cell in row.cells:
            if match_regex.search(cell.content):
                filtered_rows.append(row)
                break  # skip other cells when matched
    return filtered_rows


def _sort_rows(rows, sort_col, sort_reverse):
    # type: (TableRows, int, int) -> TableRows
    # remove and remind fixed rows, add to separate list
    fixed_rows = []
    for index, row in enumerate(rows[:]):
        if row.fixed:
            rows.remove(row)
            fixed_rows.append((index, row))

    # Then use natural sorting to sort the list. Note: due to a
    # change in the number of columns of a table in different software
    # versions the cmp-function might fail. This is because the sorting
    # column is persisted in a user file. So we ignore exceptions during
    # sorting. This gives the user the chance to change the sorting and
    # see the table in the first place.
    try:
        rows.sort(key=lambda x: utils.key_num_split(escaping.strip_tags(x[0][sort_col][0])),
                  reverse=sort_reverse == 1)
    except IndexError:
        pass

    # Now re-add the removed "fixed" rows to the list again
    if fixed_rows:
        for index, cells in fixed_rows:
            rows.insert(index, cells)

    return rows
