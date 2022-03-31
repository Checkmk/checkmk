#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import re
from contextlib import contextmanager, nullcontext
from enum import auto, Enum
from typing import (
    Any,
    ContextManager,
    Dict,
    Final,
    Iterator,
    List,
    Literal,
    NamedTuple,
    Optional,
    Tuple,
    TYPE_CHECKING,
    Union,
)

import cmk.gui.utils as utils
import cmk.gui.utils.escaping as escaping
import cmk.gui.weblib as weblib
from cmk.gui.globals import config, html, output_funnel, request, response, transactions
from cmk.gui.htmllib import foldable_container, HTML
from cmk.gui.i18n import _
from cmk.gui.utils.escaping import escape_to_html_permissive
from cmk.gui.utils.logged_in import user
from cmk.gui.utils.urls import makeactionuri, makeuri, requested_file_name

if TYPE_CHECKING:
    from cmk.gui.htmllib import HTMLContent
    from cmk.gui.type_defs import CSSSpec


class TableHeader(NamedTuple):
    title: HTML
    css: "CSSSpec"
    help_txt: Optional[str]
    sortable: bool


class CellSpec(NamedTuple):
    content: HTML
    css: "CSSSpec"
    colspan: Optional[int]


class TableRow(NamedTuple):
    cells: List[CellSpec]
    css: "CSSSpec"
    state: int
    fixed: bool
    id_: Optional[str]
    onmouseover: Optional[str]
    onmouseout: Optional[str]


class GroupHeader(NamedTuple):
    title: str
    fixed: bool
    id_: Optional[str]
    onmouseover: Optional[str]
    onmouseout: Optional[str]


TableRows = List[Union[TableRow, GroupHeader]]


class Foldable(Enum):
    NOT_FOLDABLE = auto()
    FOLDABLE_SAVE_STATE = auto()
    FOLDABLE_STATELESS = auto()


@contextmanager
def table_element(
    table_id: Optional[str] = None,
    title: Optional["HTMLContent"] = None,
    searchable: bool = True,
    sortable: bool = True,
    foldable: Foldable = Foldable.NOT_FOLDABLE,
    limit: Union[None, int, Literal[False]] = None,
    output_format: str = "html",
    omit_if_empty: bool = False,
    omit_empty_columns: bool = False,
    omit_headers: bool = False,
    omit_update_header: bool = False,
    empty_text: Optional[str] = None,
    help: Optional[str] = None,  # pylint: disable=redefined-builtin
    css: Optional[str] = None,
    isopen: bool = True,
) -> Iterator["Table"]:
    with output_funnel.plugged():
        table = Table(
            table_id=table_id,
            title=title,
            searchable=searchable,
            sortable=sortable,
            foldable=foldable,
            limit=limit,
            output_format=output_format,
            omit_if_empty=omit_if_empty,
            omit_empty_columns=omit_empty_columns,
            omit_headers=omit_headers,
            omit_update_header=omit_update_header,
            empty_text=empty_text,
            help=help,
            css=css,
            isopen=isopen,
        )
        try:
            yield table
        finally:
            table._finish_previous()
            table._end()


# .
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


class Table:
    def __init__(
        self,
        table_id: Optional[str] = None,
        title: Optional["HTMLContent"] = None,
        searchable: bool = True,
        sortable: bool = True,
        foldable: Foldable = Foldable.NOT_FOLDABLE,
        limit: Union[None, int, Literal[False]] = None,
        output_format: str = "html",
        omit_if_empty: bool = False,
        omit_empty_columns: bool = False,
        omit_headers: bool = False,
        omit_update_header: bool = False,
        empty_text: Optional[str] = None,
        help: Optional[str] = None,  # pylint: disable=redefined-builtin
        css: Optional[str] = None,
        isopen: bool = True,
    ):
        super().__init__()
        self.next_func = lambda: None
        self.next_header: Optional[str] = None

        # Use our pagename as table id if none is specified
        table_id = table_id if table_id is not None else requested_file_name(request)
        assert table_id is not None

        # determine row limit
        if limit is None:
            limit = config.table_row_limit
        if request.get_ascii_input("limit") == "none" or output_format != "html":
            limit = None

        self.id = table_id
        self.title = title
        self.rows: TableRows = []
        self.limit = limit
        self.limit_reached = False
        self.limit_hint: Optional[int] = None
        self.headers: List[TableHeader] = []
        self.options = {
            "collect_headers": False,  # also: True, "finished"
            "omit_if_empty": omit_if_empty,
            "omit_empty_columns": omit_empty_columns,
            "omit_headers": omit_headers,
            "omit_update_header": omit_update_header,
            "searchable": searchable,
            "sortable": sortable,
            "foldable": foldable,
            "output_format": output_format,  # possible: html, csv, fetch
        }

        self.empty_text = empty_text if empty_text is not None else _("No entries.")
        self.help = help
        self.css = css
        self.mode = "row"
        self.isopen: Final = isopen

    def row(
        self,
        css: Optional["CSSSpec"] = None,
        state: int = 0,
        collect_headers: bool = True,
        fixed: bool = False,
        id_: Optional[str] = None,
        onmouseover: Optional[str] = None,
        onmouseout: Optional[str] = None,
    ) -> None:
        self._finish_previous()
        self.next_func = lambda: self._add_row(
            css, state, collect_headers, fixed, id_, onmouseover, onmouseout
        )

    def cell(
        self,
        title: "HTMLContent" = "",
        text: "HTMLContent" = "",
        css: Optional["CSSSpec"] = None,
        help_txt: Optional[str] = None,
        colspan: Optional[int] = None,
        sortable: bool = True,
    ):
        self._finish_previous()
        self.next_func = lambda: self._add_cell(
            title=title,
            text=text,
            css=css,
            help_txt=help_txt,
            colspan=colspan,
            sortable=sortable,
        )

    def _finish_previous(self) -> None:
        self.next_func()
        self.next_func = lambda: None

    def _add_row(
        self,
        css: Optional["CSSSpec"] = None,
        state: int = 0,
        collect_headers: bool = True,
        fixed: bool = False,
        id_: Optional[str] = None,
        onmouseover: Optional[str] = None,
        onmouseout: Optional[str] = None,
    ) -> None:
        if self.next_header:
            self.rows.append(
                GroupHeader(
                    title=self.next_header,
                    fixed=True,
                    id_=id_,
                    onmouseover=onmouseover,
                    onmouseout=onmouseout,
                )
            )
            self.next_header = None
        self.rows.append(TableRow([], css, state, fixed, id_, onmouseover, onmouseout))
        if collect_headers:
            if self.options["collect_headers"] is False:
                self.options["collect_headers"] = True
            elif self.options["collect_headers"] is True:
                self.options["collect_headers"] = "finished"
        elif not collect_headers and self.options["collect_headers"] is True:
            self.options["collect_headers"] = False

        self.limit_reached = False if self.limit is None else len(self.rows) > self.limit

    def _add_cell(
        self,
        title: "HTMLContent" = "",
        text: "HTMLContent" = "",
        css: Optional["CSSSpec"] = None,
        help_txt: Optional[str] = None,
        colspan: Optional[int] = None,
        sortable: bool = True,
    ):
        if isinstance(text, HTML):
            content = text
        else:
            content = escape_to_html_permissive(
                str(text) if not isinstance(text, str) else text, escape_links=False
            )

        htmlcode: HTML = content + HTML(output_funnel.drain())

        if isinstance(title, HTML):
            header_title = title
        else:
            if title is None:
                title = ""
            header_title = escape_to_html_permissive(
                str(title) if not isinstance(title, str) else title, escape_links=False
            )

        if self.options["collect_headers"] is True:
            # small helper to make sorting introducion easier. Cells which contain
            # buttons are never sortable
            if css and "buttons" in css and sortable:
                sortable = False
            self.headers.append(
                TableHeader(title=header_title, css=css, help_txt=help_txt, sortable=sortable)
            )

        current_row = self.rows[-1]
        assert isinstance(current_row, TableRow)
        current_row.cells.append(CellSpec(htmlcode, css, colspan))

    def groupheader(self, title: str) -> None:
        """Intermediate title, shown as soon as there is a following row.
        We store the group headers in the list of rows, with css None and state set to "header"
        """
        self.next_header = title

    def _end(self) -> None:
        if not self.rows and self.options["omit_if_empty"]:
            return

        if self.options["output_format"] == "csv":
            self._write_csv(csv_separator=request.get_str_input_mandatory("csv_separator", ";"))
            return

        container: ContextManager[bool] = nullcontext(False)
        if self.title:
            if self.options["foldable"] in [
                Foldable.FOLDABLE_SAVE_STATE,
                Foldable.FOLDABLE_STATELESS,
            ]:
                html.open_div(class_="foldable_wrapper")
                container = foldable_container(
                    treename="table",
                    id_=self.id,
                    isopen=self.isopen,
                    indent=False,
                    title=html.render_h3(self.title, class_=["treeangle", "title"]),
                    save_state=self.options["foldable"] == Foldable.FOLDABLE_SAVE_STATE,
                )
            else:
                html.h3(self.title, class_="table")

        with container:
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
            if limit:
                # only use rows up to the limit plus the fixed rows
                limited_rows = []
                for index in range(num_rows_unlimited):
                    row = rows[index]
                    if index < limit or isinstance(row, GroupHeader) or row.fixed:
                        limited_rows.append(row)
                # Display corrected number of rows
                num_rows_unlimited -= len(
                    [r for r in limited_rows if isinstance(row, GroupHeader) or r.fixed]
                )
                rows = limited_rows

            # Render header
            if self.limit_hint is not None:
                num_rows_unlimited = self.limit_hint

            if limit and num_rows_unlimited > limit:

                html.show_message(
                    _(
                        "This table is limited to show only %d of %d rows. "
                        'Click <a href="%s">here</a> to disable the limitation.'
                    )
                    % (limit, num_rows_unlimited, makeuri(request, [("limit", "none")]))
                )

            self._write_table(
                rows, num_rows_unlimited, self._show_action_row(), actions_visible, search_term
            )

        if self.title and self.options["foldable"] in [
            Foldable.FOLDABLE_SAVE_STATE,
            Foldable.FOLDABLE_STATELESS,
        ]:
            html.close_div()

        return

    def _show_action_row(self) -> bool:
        if self.options["sortable"] and self._get_sort_column(user.tableoptions[self.id]):
            return True

        return False

    def _evaluate_user_opts(self) -> Tuple[TableRows, bool, Optional[str]]:
        assert self.id is not None
        table_id = self.id
        rows = self.rows

        search_term = None
        actions_enabled = self.options["searchable"] or self.options["sortable"]

        if not actions_enabled:
            return rows, False, None

        table_opts = user.tableoptions.setdefault(table_id, {})

        # Handle the initial visibility of the actions
        actions_visible = table_opts.get("actions_visible", False)
        if request.get_ascii_input("_%s_actions" % table_id):
            actions_visible = request.get_ascii_input("_%s_actions" % table_id) == "1"
            table_opts["actions_visible"] = actions_visible

        if self.options["searchable"]:
            search_term = request.get_str_input_mandatory("search", "")
            # Search is always lower case -> case insensitive
            search_term = search_term.lower()
            if search_term:
                request.set_var("search", search_term)
                rows = _filter_rows(rows, search_term)

        if request.get_ascii_input("_%s_reset_sorting" % table_id):
            request.del_var("_%s_sort" % table_id)
            if "sort" in table_opts:
                del table_opts["sort"]  # persist

        if self.options["sortable"]:
            # Now apply eventual sorting settings
            sort = self._get_sort_column(table_opts)
            if sort is not None:
                request.set_var("_%s_sort" % table_id, sort)
                table_opts["sort"] = sort  # persist
                sort_col, sort_reverse = map(int, sort.split(",", 1))
                rows = _sort_rows(rows, sort_col, sort_reverse)

        if actions_enabled:
            user.save_tableoptions()

        return rows, actions_visible, search_term

    def _get_sort_column(self, table_opts: Dict[str, Any]) -> Optional[str]:
        return request.get_ascii_input("_%s_sort" % self.id, table_opts.get("sort"))

    def _write_table(
        self,
        rows: TableRows,
        num_rows_unlimited: int,
        actions_enabled: bool,
        actions_visible: bool,
        search_term: Optional[str],
    ) -> None:
        if not self.options["omit_update_header"]:
            row_info = _("1 row") if len(rows) == 1 else _("%d rows") % num_rows_unlimited
            html.javascript("cmk.utils.update_row_info(%s);" % json.dumps(row_info))

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

            if request.has_var("_%s_sort" % table_id):
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
                    html.h3(row.title)
                    html.close_td()
                    html.close_tr()

                    self._render_headers(actions_enabled, actions_visible, empty_columns)
                continue

            oddeven_name = "even" if nr % 2 == 0 else "odd"
            class_ = ["data", "%s%d" % (oddeven_name, row.state)]

            if isinstance(row.css, list):
                class_.extend([c for c in row.css if c is not None])
            elif row.css is not None:
                class_.append(row.css)

            html.open_tr(
                class_=class_, id_=row.id_, onmouseover=row.onmouseover, onmouseout=row.onmouseout
            )
            for col_index, cell in enumerate(row.cells):
                if self.options["omit_empty_columns"] and empty_columns[col_index]:
                    continue

                html.td(cell.content, class_=cell.css, colspan=cell.colspan)
            html.close_tr()

        if not rows and search_term:
            html.open_tr(class_=["data", "odd0", "no_match"])
            html.td(_("Found no matching rows. Please try another search term."), colspan=num_cols)
            html.close_tr()

        html.close_table()

    def _get_num_cols(self, rows: TableRows) -> int:
        if self.headers:
            return len(self.headers)
        if self.rows:
            return len(self.rows[0])
        return 0

    def _get_empty_columns(self, rows: TableRows, num_cols: int) -> List[bool]:
        if not num_cols:
            return []

        empty_columns = [True] * num_cols
        for row in rows:
            if isinstance(row, GroupHeader):
                continue  # Don't care about group headers

            for col_index, cell in enumerate(row.cells):
                empty_columns[col_index] &= not cell.content
        return empty_columns

    def _write_csv(self, csv_separator: str) -> None:
        rows = self.rows
        limit = self.limit
        omit_headers = self.options["omit_headers"]

        # Apply limit after search / sorting etc.
        if limit is not None:
            rows = rows[:limit]

        resp = []

        # If we have no group headers then paint the headers now
        if not omit_headers and self.rows and not isinstance(self.rows[0], GroupHeader):
            resp.append(
                csv_separator.join(
                    [escaping.strip_tags(header.title) or "" for header in self.headers]
                )
                + "\n"
            )

        for row in rows:
            if isinstance(row, GroupHeader):
                continue

            resp.append(
                csv_separator.join([escaping.strip_tags(cell.content) for cell in row.cells])
            )
            resp.append("\n")

        response.set_data("".join(resp))

    def _render_headers(
        self, actions_enabled: bool, actions_visible: bool, empty_columns: List[bool]
    ) -> None:
        if self.options["omit_headers"]:
            return

        table_id = self.id

        html.open_tr()
        first_col = True
        for nr, header in enumerate(self.headers):
            if self.options["omit_empty_columns"] and empty_columns[nr]:
                continue

            if header.help_txt:
                header_title: HTML = html.render_span(header.title, title=header.help_txt)
            else:
                header_title = header.title

            if not isinstance(header.css, list):
                css_class: "CSSSpec" = [header.css]
            else:
                css_class = header.css

            assert isinstance(css_class, list)
            css_class = [("header_%s" % c) for c in css_class if c is not None]

            if not self.options["sortable"] or not header.sortable:
                html.open_th(class_=css_class)
            else:
                css_class.insert(0, "sort")
                reverse = 0
                sort = request.get_ascii_input("_%s_sort" % table_id)
                if sort:
                    sort_col, sort_reverse = map(int, sort.split(",", 1))
                    if sort_col == nr:
                        reverse = 1 if sort_reverse == 0 else 0

                action_uri = makeactionuri(
                    request, transactions, [("_%s_sort" % table_id, "%d,%d" % (nr, reverse))]
                )
                html.open_th(
                    class_=css_class,
                    title=_("Sort by %s") % header.title,
                    onclick="location.href='%s'" % action_uri,
                )

            # Add the table action link
            if first_col:
                first_col = False
                if actions_enabled:
                    if not header_title:
                        header_title = HTML("&nbsp;")  # Fixes layout problem with white triangle

                    if actions_visible:
                        state = "0"
                        help_txt = _("Hide table actions")
                        img = "table_actions_on"
                    else:
                        state = "1"
                        help_txt = _("Display table actions")
                        img = "table_actions_off"

                    html.open_div(class_=["toggle_actions"])
                    html.icon_button(
                        makeuri(request, [("_%s_actions" % table_id, state)]),
                        help_txt,
                        img,
                        cssclass="toggle_actions",
                    )
                    html.span(header_title)
                    html.close_div()
                else:
                    html.write_text(header_title)
            else:
                html.write_text(header_title)

            html.close_th()
        html.close_tr()


def _filter_rows(rows: TableRows, search_term: str) -> TableRows:
    filtered_rows: TableRows = []
    match_regex = re.compile(search_term, re.IGNORECASE)

    for row in rows:
        if isinstance(row, GroupHeader) or row.fixed:
            filtered_rows.append(row)
            continue  # skip filtering of headers or fixed rows

        for cell in row.cells:
            # Filter out buttons
            if cell.css is not None and "buttons" in cell.css:
                continue
            if match_regex.search(str(cell.content)):
                filtered_rows.append(row)
                break  # skip other cells when matched
    return filtered_rows


def _sort_rows(rows: TableRows, sort_col: int, sort_reverse: int) -> TableRows:
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
        rows.sort(
            key=lambda x: utils.key_num_split(escaping.strip_tags(x[0][sort_col][0])),
            reverse=sort_reverse == 1,
        )
    except IndexError:
        pass

    # Now re-add the removed "fixed" rows to the list again
    if fixed_rows:
        for index, cells in fixed_rows:
            rows.insert(index, cells)

    return rows


def init_rowselect(selection_key: str) -> None:
    selected = user.get_rowselection(weblib.selection_id(), selection_key)
    selection_properties = {
        "page_id": selection_key,
        "selection_id": weblib.selection_id(),
        "selected_rows": selected,
    }
    html.javascript("cmk.selection.init_rowselect(%s);" % (json.dumps(selection_properties)))
