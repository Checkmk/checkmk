#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import re
from collections.abc import Hashable, Iterator, Sequence
from typing import Any

from cmk.utils.exceptions import MKGeneralException
from cmk.utils.regex import escape_regex_chars

import cmk.gui.utils as utils
from cmk.gui.config import active_config
from cmk.gui.data_source import row_id
from cmk.gui.exporter import output_csv_headers
from cmk.gui.htmllib.html import html
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.painter.v0.base import Cell, EmptyCell
from cmk.gui.painter.v1.helpers import is_stale
from cmk.gui.painter_options import PainterOptions
from cmk.gui.table import init_rowselect, table_element
from cmk.gui.type_defs import GroupSpec, Row, Rows, ViewSpec
from cmk.gui.utils.theme import theme
from cmk.gui.visual_link import render_link_to_view

from .base import Layout
from .helpers import group_value
from .registry import LayoutRegistry


def register_layouts(registry: LayoutRegistry) -> None:
    registry.register(LayoutSingleDataset)
    registry.register(LayoutBalancedBoxes)
    registry.register(LayoutBalancedGraphBoxes)
    registry.register(LayoutTiled)
    registry.register(LayoutTable)
    registry.register(LayoutMatrix)


def render_checkbox(view: ViewSpec, row: Row, num_tds: int) -> None:
    # value contains the number of columns of this datarow. This is
    # needed for hiliting the correct number of TDs
    html.input(type_="checkbox", name=row_id(view["datasource"], row), value=str(num_tds + 1))
    html.label("", row_id(view["datasource"], row))


def render_checkbox_td(view: ViewSpec, row: Row, num_tds: int) -> None:
    html.open_td(class_="checkbox")
    render_checkbox(view, row, num_tds)
    html.close_td()


def render_group_checkbox_th() -> None:
    html.open_th()
    html.input(
        type_="button",
        class_="checkgroup",
        name="_toggle_group",
        onclick="cmk.selection.toggle_group_rows(this);",
        value="X",
    )
    html.close_th()


class LayoutSingleDataset(Layout):
    """Layout designed for showing one single dataset with the column
    headers left and the values on the right. It is able to handle
    more than on dataset however."""

    @property
    def ident(self) -> str:
        return "dataset"

    @property
    def title(self) -> str:
        return _("Single dataset")

    @property
    def can_display_checkboxes(self) -> bool:
        return False

    def render(
        self,
        rows: Rows,
        view: ViewSpec,
        group_cells: Sequence[Cell],
        cells: Sequence[Cell],
        num_columns: int,
        show_checkboxes: bool,
    ) -> None:
        html.open_table(class_="data single")
        rownum = 0
        odd = "odd"
        while rownum < len(rows):
            if rownum > 0:
                html.open_tr(class_="gap")
                html.td("", class_="gap", colspan=num_columns + 1)
                html.close_tr()
            thispart = rows[rownum : rownum + num_columns]
            for cell in cells:
                odd = "even" if odd == "odd" else "odd"
                html.open_tr(class_="data %s0" % odd)
                if view.get("column_headers") != "off":
                    html.td(cell.title(use_short=False), class_="left")

                for row in thispart:
                    cell.paint(row, render_link_to_view)

                if len(thispart) < num_columns:
                    html.td(
                        "",
                        class_="gap",
                        style="border-style: none;",
                        colspan=(1 + num_columns - len(thispart)),
                    )
                html.close_tr()
            rownum += num_columns
        html.close_table()


class GroupedBoxesLayout(Layout):
    @abc.abstractmethod
    def _css_class(self) -> str | None:
        raise NotImplementedError()

    def render(
        self,
        rows: Rows,
        view: ViewSpec,
        group_cells: Sequence[Cell],
        cells: Sequence[Cell],
        num_columns: int,
        show_checkboxes: bool,
    ) -> None:
        # N columns. Each should contain approx the same number of entries
        groups: list[tuple[Hashable, list[tuple[str, Row]]]] = []
        last_group = None
        for row in rows:
            this_group = group_value(row, group_cells)
            if this_group != last_group:
                last_group = this_group
                current_group: list[tuple[str, Row]] = []
                groups.append((this_group, current_group))
            current_group.append((row_id(view["datasource"], row), row))

        # Create empty columns
        columns: list[list[tuple[Hashable, list[tuple[str, Row]]]]] = []
        for _x in range(num_columns):
            columns.append([])

        # First put everything into the first column
        for group in groups:
            columns[0].append(group)

        # Shift from left to right as long as useful
        did_something = True
        while did_something:
            did_something = False
            for i in range(0, num_columns - 1):
                if self._balance(columns[i], columns[i + 1]):
                    did_something = True

        classes = ["boxlayout"]
        if box_class := self._css_class():
            classes.append(box_class)

        # render table
        html.open_table(class_=classes)
        html.open_tr()
        for column in columns:
            html.open_td(class_="boxcolumn")
            for _header, rows_with_ids in column:
                self._render_group(rows_with_ids, view, group_cells, cells, show_checkboxes)
            html.close_td()
        html.close_tr()
        html.close_table()

    def _render_group(  # pylint: disable=too-many-branches
        self,
        rows_with_ids: list[tuple[str, Row]],
        view: ViewSpec,
        group_cells: Sequence[Cell],
        cells: Sequence[Cell],
        show_checkboxes: bool,
    ) -> None:
        repeat_heading_every = 20  # in case column_headers is "repeat"

        if group_cells:
            self._show_group_header_table(group_cells, rows_with_ids[0][1])

        html.open_table(class_="data")
        odd = "odd"

        column_headers = view.get("column_headers")
        if column_headers != "off":
            self._show_header_line(cells, show_checkboxes)

        groups, rows_with_ids = calculate_view_grouping_of_services(
            rows_with_ids, row_group_cells=None
        )

        visible_row_number = 0
        group_hidden, num_grouped_rows = None, 0
        for index, row in rows_with_ids:
            if view.get("column_headers") == "repeat":
                if visible_row_number > 0 and visible_row_number % repeat_heading_every == 0:
                    self._show_header_line(cells, show_checkboxes)
            visible_row_number += 1

            odd = "even" if odd == "odd" else "odd"

            # state = row.get("service_state", row.get("aggr_state"))
            state = utils.saveint(row.get("service_state"))
            if state is None:
                state = utils.saveint(row.get("host_state", 0))
                if state > 0:
                    state += 1  # 1 is critical for hosts

            num_cells = len(cells)

            if index in groups:
                group_spec, num_grouped_rows = groups[index]
                group_hidden = grouped_row_title(
                    index, group_spec, num_grouped_rows, odd, num_cells
                )
                odd = "even" if odd == "odd" else "odd"

            css_classes = []

            if is_stale(row):
                css_classes.append("stale")

            hide = ""
            if num_grouped_rows > 0:
                num_grouped_rows -= 1
                if group_hidden:
                    hide = "display:none"

            if group_hidden is not None and num_grouped_rows == 0:
                # last row in group
                css_classes.append("group_end")
                group_hidden = None

            css_classes.append("%s%d" % (odd, state))

            html.open_tr(class_=["data"] + css_classes, style=hide)

            if show_checkboxes:
                render_checkbox_td(view, row, num_cells)

            for cell in cells:
                cell.paint(row, render_link_to_view)

            html.close_tr()

        html.close_table()
        # Don't make rows selectable when no commands can be fired
        # Ignore "C" display option here. Otherwise the rows will not be selectable
        # after view reload.
        if not user.may("general.act"):
            return

        init_rowselect(_get_view_name(view))

    def _show_group_header_table(self, group_cells: Sequence[Cell], first_row: Row) -> None:
        html.open_table(class_="groupheader", cellspacing="0", cellpadding="0", border="0")
        html.open_tr(class_="groupheader")
        painted = False
        for cell in group_cells:
            if painted:
                html.td(",&nbsp;")
            painted = cell.paint(first_row, render_link_to_view)
        html.close_tr()
        html.close_table()

    def _show_header_line(self, cells: Sequence[Cell], show_checkboxes: bool) -> None:
        html.open_tr()
        if show_checkboxes:
            render_group_checkbox_th()
        for cell in cells:
            cell.paint_as_header()
            html.write_text("\n")
        html.close_tr()

    def _balance(
        self,
        src: list[tuple[Hashable, list[tuple[str, Row]]]],
        dst: list[tuple[Hashable, list[tuple[str, Row]]]],
    ) -> bool:
        # shift from src to dst, if useful
        if len(src) == 0:
            return False
        hsrc = self._height_of(src)
        hdst = self._height_of(dst)
        shift = len(src[-1][1]) + 2
        if max(hsrc, hdst) > max(hsrc - shift, hdst + shift):
            dst[0:0] = [src[-1]]
            del src[-1]
            return True
        return False

    def _height_of(self, groups: list[tuple[Hashable, list[tuple[str, Row]]]]) -> int:
        # compute total space needed. I count the group header like two rows.
        return sum(len(rows_with_ids) for _header, rows_with_ids in groups) + 2 * len(groups)


def grouped_row_title(
    index: str, group_spec: GroupSpec, num_rows: int, trclass: str, num_cells: int
) -> bool:
    is_open = user.get_tree_state("grouped_rows", index, False)
    html.open_tr(
        class_=["data", "grouped_row_header", "closed" if not is_open else "", "%s0" % trclass]
    )
    html.open_td(
        colspan=num_cells,
        onclick="cmk.views.toggle_grouped_rows('grouped_rows', '%s', this, %d)" % (index, num_rows),
    )

    html.img(
        theme.url("images/tree_closed.svg"),
        align="absbottom",
        class_=["treeangle", "nform", "open" if is_open else "closed"],
    )
    html.write_text("%s (%d)" % (group_spec["title"], num_rows))

    html.close_td()
    html.close_tr()

    return not is_open


# Produces a dictionary where the row index of the first row is used as key
# and a tuple of the group_spec and the number of rows in this group is the value
#
# TODO: Be aware: We have a naming issue here. There are two things named "grouping"
#
# a) There is the view grouping (service grouping based on regex matching with folding of rows)
# b) Row grouping (Displaying header painters for each row)
#
# This is confusing and needs to be cleaned up!
def calculate_view_grouping_of_services(
    rows_with_ids: list[tuple[str, Row]], row_group_cells: Sequence[Cell] | None
) -> tuple[dict, list[tuple[str, Row]]]:
    if not active_config.service_view_grouping:
        return {}, rows_with_ids

    # First create dictionaries for each found group containing the
    # group spec and the row indizes of the grouped rows
    groups: dict[Hashable, tuple[GroupSpec, list[str]]] = {}
    current_group = None
    group_id: str | None = None
    last_row_group = None
    for index, (rid, row) in enumerate(rows_with_ids[:]):
        group_spec = try_to_match_group(row)
        if not group_spec:
            current_group = None
            continue

        # New row groups need to separate the view groups. There is no folding allowed
        # between row groups (e.g. services of different hosts when the host is a group cell)
        if row_group_cells:
            this_row_group = group_value(row, row_group_cells)
            if this_row_group != last_row_group:
                group_id = rid
                last_row_group = this_row_group

        if current_group is None:
            group_id = rid

        elif current_group != group_spec:
            group_id = rid

        groups.setdefault(group_id, (group_spec, []))

        # When the service is not OK and should not be grouped, move it's row
        # in front of the group.
        if row.get("service_state", -1) != 0 or is_stale(row):
            if current_group is None or current_group != group_spec:
                continue  # skip grouping first row

            if current_group == group_spec:
                row = rows_with_ids.pop(index)
                rows_with_ids.insert(index - len(groups[group_id][1]), row)
                continue

        current_group = group_spec
        groups[group_id][1].append(rid)

    # Now create the final structure as described above
    groupings = {}
    for _group_id, (group_spec, row_indizes) in groups.items():
        if len(row_indizes) >= group_spec.get("min_items", 2):
            groupings[row_indizes[0]] = group_spec, len(row_indizes)

    return groupings, rows_with_ids


def try_to_match_group(row: Row) -> GroupSpec | None:
    for group_spec in active_config.service_view_grouping:
        if row.get("service_description") and re.match(
            group_spec["pattern"], row["service_description"]
        ):
            if re.findall(r"(\([^)]*\))", group_spec["pattern"]):
                group_spec["title"] = re.sub(
                    group_spec["pattern"],
                    escape_regex_chars(group_spec["title"]),
                    row["service_description"],
                )
            return group_spec

    return None


class LayoutBalancedBoxes(GroupedBoxesLayout):
    """The boxed layout is useful in views with a width > 1, boxes are
    stacked in columns and can have different sizes."""

    @property
    def ident(self) -> str:
        return "boxed"

    @property
    def title(self) -> str:
        return _("Balanced boxes")

    @property
    def can_display_checkboxes(self) -> bool:
        return True

    def _css_class(self) -> str | None:
        return None

    @property
    def hide_entries_per_row(self) -> bool:
        return True


class LayoutBalancedGraphBoxes(GroupedBoxesLayout):
    """Same as balanced boxes layout but adds a CSS class graph to the box"""

    @property
    def ident(self) -> str:
        return "boxed_graph"

    @property
    def title(self) -> str:
        return _("Balanced graph boxes")

    @property
    def can_display_checkboxes(self) -> bool:
        return True

    def _css_class(self) -> str | None:
        return "graph"


class LayoutTiled(Layout):
    """The tiled layout puts each dataset into one box with a fixed size"""

    @property
    def ident(self) -> str:
        return "tiled"

    @property
    def title(self) -> str:
        return _("Tiles")

    @property
    def can_display_checkboxes(self) -> bool:
        return True

    def render(  # pylint: disable=too-many-branches
        self,
        rows: Rows,
        view: ViewSpec,
        group_cells: Sequence[Cell],
        cells: Sequence[Cell],
        num_columns: int,
        show_checkboxes: bool,
    ) -> None:
        html.open_table(class_="data tiled")

        last_group = None
        group_open = False
        for row in rows:
            # Show group header
            if group_cells:
                this_group = group_value(row, group_cells)
                if this_group != last_group:
                    # paint group header
                    if group_open:
                        html.close_td()
                        html.close_tr()
                    html.open_tr()
                    html.open_td()
                    html.open_table(class_="groupheader")
                    html.open_tr(class_="groupheader")

                    painted = False
                    for cell in group_cells:
                        if painted:
                            html.td(",&nbsp;")
                        painted = cell.paint(row, render_link_to_view)

                    html.close_tr()
                    html.close_table()

                    html.close_td()
                    html.close_tr()

                    html.open_tr()
                    html.open_td(class_="tiles")

                    group_open = True
                    last_group = this_group

            # background color of tile according to item state
            state = row.get("service_state", -1)
            if state == -1:
                hbc = row.get("host_has_been_checked", 1)
                if hbc:
                    state = row.get("host_state", 0)
                    sclass = "hhstate%d" % state
                else:
                    sclass = "hhstatep"
            else:
                hbc = row.get("service_has_been_checked", 1)
                if hbc:
                    sclass = "sstate%d" % state
                else:
                    sclass = "sstatep"

            if not group_open:
                html.open_tr()
                html.open_td(class_="tiles")
                group_open = True

            html.open_div(class_=["tile", sclass])
            html.open_table()

            # We need at least five cells
            render_cells = list(cells)
            if len(render_cells) < 5:
                render_cells += [EmptyCell(None, None)] * (5 - len(render_cells))

            rendered = [cell.render(row, render_link_to_view) for cell in render_cells]

            html.open_tr()
            html.open_td(class_=["tl", rendered[1][0]])
            if show_checkboxes:
                render_checkbox(view, row, len(render_cells) - 1)
            html.write_text(rendered[1][1])
            html.close_td()
            html.open_td(class_=["tr", rendered[2][0]])
            html.write_text(rendered[2][1])
            html.close_td()
            html.close_tr()

            html.open_tr()
            html.open_td(colspan=2, class_=["center", rendered[0][0]])
            html.write_text(rendered[0][1])
            html.close_td()
            html.close_tr()

            for css, cont in rendered[5:]:
                html.open_tr()
                html.open_td(colspan=2, class_=["cont", css])
                html.write_text(cont)
                html.close_td()
                html.close_tr()

            html.open_tr()
            html.open_td(class_=["bl", rendered[3][0]])
            html.write_text(rendered[3][1])
            html.close_td()
            html.open_td(class_=["br", rendered[4][0]])
            html.write_text(rendered[4][1])
            html.close_td()
            html.close_tr()

            html.close_table()
            html.close_div()

        if group_open:
            html.close_td()
            html.close_tr()

        html.close_table()
        if not user.may("general.act"):
            return

        init_rowselect(_get_view_name(view))


class LayoutTable(Layout):
    """Most common layout: render all datasets in one big table. Groups
    are shown in what seems to be separate tables but they share the
    width of the columns."""

    @property
    def ident(self) -> str:
        return "table"

    @property
    def title(self) -> str:
        return _("Table")

    @property
    def can_display_checkboxes(self) -> bool:
        return True

    def render(  # pylint: disable=too-many-branches
        self,
        rows: Rows,
        view: ViewSpec,
        group_cells: Sequence[Cell],
        cells: Sequence[Cell],
        num_columns: int,
        show_checkboxes: bool,
    ) -> None:
        repeat_heading_every = 20  # in case column_headers is "repeat"

        html.open_table(class_="data table")
        last_group = None
        odd = "odd"
        column = 1
        group_open = False
        num_cells = len(cells)
        if show_checkboxes:
            num_cells += 1

        if not group_cells and view.get("column_headers") != "off":
            self._show_header_line(cells, num_columns, show_checkboxes)

        rows_with_ids = [(row_id(view["datasource"], row), row) for row in rows]
        groups, rows_with_ids = calculate_view_grouping_of_services(
            rows_with_ids, row_group_cells=group_cells
        )

        visible_row_number = 0
        group_hidden, num_grouped_rows = None, 0
        for index, row in rows_with_ids:
            # Show group header, if a new group begins. But only if grouping
            # is activated
            if group_cells:
                this_group = group_value(row, group_cells)
                if this_group != last_group:
                    if column != 1:  # not a the beginning of a new line
                        for _i in range(column - 1, num_columns):
                            html.td("", class_="gap")
                            html.td("", class_="fillup", colspan=num_cells)
                        html.close_tr()
                        column = 1

                    group_open = True
                    visible_row_number = 0

                    # paint group header, but only if it is non-empty
                    header_is_empty = True
                    for cell in group_cells:
                        _tdclass, content = cell.render(row, render_link_to_view)
                        if content:
                            header_is_empty = False
                            break

                    if not header_is_empty:
                        html.open_tr(class_="groupheader")
                        html.open_td(
                            class_="groupheader",
                            colspan=(num_cells * (num_columns + 2) + (num_columns - 1)),
                        )
                        html.open_table(
                            class_="groupheader", cellspacing="0", cellpadding="0", border="0"
                        )
                        html.open_tr()
                        painted = False
                        for cell in group_cells:
                            if painted:
                                html.td(",&nbsp;")
                            painted = cell.paint(row, render_link_to_view)

                        html.close_tr()
                        html.close_table()
                        html.close_td()
                        html.close_tr()
                        odd = "odd"

                    # Table headers
                    if view.get("column_headers") != "off":
                        self._show_header_line(cells, num_columns, show_checkboxes)
                    last_group = this_group

            # Should we wrap over to a new line?
            if column >= num_columns + 1:
                html.close_tr()
                column = 1

            # At the beginning of the line? Beginn new line
            if column == 1:
                if view.get("column_headers") == "repeat":
                    if visible_row_number > 0 and visible_row_number % repeat_heading_every == 0:
                        self._show_header_line(cells, num_columns, show_checkboxes)
                visible_row_number += 1

                # In one-column layout we use the state of the service
                # or host - if available - to color the complete line
                if num_columns == 1:
                    # render state, if available through whole tr
                    if not row.get("service_description"):
                        state = row.get("host_state", 0)
                        if state > 0:
                            state += 1  # 1 is critical for hosts
                    else:
                        state = row.get("service_state", 0)
                else:
                    state = 0

                if index in groups:
                    group_spec, num_grouped_rows = groups[index]
                    group_hidden = grouped_row_title(
                        index, group_spec, num_grouped_rows, odd, num_cells
                    )
                    odd = "even" if odd == "odd" else "odd"

                css_classes = []

                hide = ""
                if num_grouped_rows > 0:
                    num_grouped_rows -= 1
                    if group_hidden:
                        hide = "display:none"

                if group_hidden is not None and num_grouped_rows == 0:
                    # last row in group
                    css_classes.append("group_end")
                    group_hidden = None

                odd = "even" if odd == "odd" else "odd"

                if num_columns > 1:
                    css_classes.append("multicolumn")
                css_classes += ["%s%d" % (odd, state)]

                html.open_tr(class_=["data"] + css_classes, style=hide)

            # Not first columns: Create one empty column as separator
            else:
                html.open_td(class_="gap")
                html.close_td()

            if show_checkboxes:
                render_checkbox_td(view, row, num_cells)

            for cell in cells:
                cell.paint(row, render_link_to_view)

            column += 1

        if group_open:
            for _i in range(column - 1, num_columns):
                html.td("", class_="gap")
                html.td("", class_="fillup", colspan=num_cells)
            html.close_tr()
        html.close_table()
        if not user.may("general.act"):
            return

        init_rowselect(_get_view_name(view))

    def _show_header_line(
        self, cells: Sequence[Cell], num_columns: int, show_checkboxes: bool
    ) -> None:
        html.open_tr()
        for n in range(1, num_columns + 1):
            if show_checkboxes:
                if n == 1:
                    render_group_checkbox_th()
                else:
                    html.th("")

            for cell in cells:
                cell.paint_as_header()

            if n < num_columns:
                html.td("", class_="gap")

        html.close_tr()


def _get_view_name(view: ViewSpec) -> str:
    return "view-%s" % view["name"]


class LayoutMatrix(Layout):
    """The Matrix is similar to what is called "Mine Map" in other GUIs.
    It create a matrix whose columns are single datasets and whole rows
    are entities with the same value in all those datasets. Typicall
    The columns are hosts and the rows are services."""

    @property
    def ident(self) -> str:
        return "matrix"

    @property
    def title(self) -> str:
        return _("Matrix")

    @property
    def can_display_checkboxes(self) -> bool:
        return False

    @property
    def has_individual_csv_export(self) -> bool:
        return True

    def csv_export(
        self, rows: Rows, view: ViewSpec, group_cells: Sequence[Cell], cells: Sequence[Cell]
    ) -> None:
        output_csv_headers(view)

        groups, unique_row_ids, matrix_cells = list(
            create_matrices(rows, group_cells, cells, num_columns=None)
        )[0]
        value_counts, _row_majorities = self._matrix_find_majorities(rows, cells)

        painter_options = PainterOptions.get_instance()
        with table_element(output_format="csv") as table:
            for cell_nr, cell in enumerate(group_cells):
                table.row()
                table.cell("", cell.title(use_short=False))
                for _group, group_row in groups:
                    _tdclass, content = cell.render(group_row, render_link_to_view)
                    table.cell("", content)

            for rid in unique_row_ids:
                # Omit rows where all cells have the same values
                if painter_options.get("matrix_omit_uniform"):
                    at_least_one_different = False
                    for counts in value_counts[rid].values():
                        if len(counts) > 1:
                            at_least_one_different = True
                            break
                    if not at_least_one_different:
                        continue

                table.row()
                _tdclass, content = cells[0].render(
                    list(matrix_cells[rid].values())[0], render_link_to_view
                )
                table.cell("", content)

                for group_id, group_row in groups:
                    table.cell("")
                    cell_row = matrix_cells[rid].get(group_id)
                    if cell_row is not None:
                        for cell_nr, cell in enumerate(cells[1:]):
                            _tdclass, content = cell.render(cell_row, render_link_to_view)
                            if cell_nr:
                                html.write_text(",")
                            html.write_text(content)

    def render(  # pylint: disable=too-many-branches
        self,
        rows: Rows,
        view: ViewSpec,
        group_cells: Sequence[Cell],
        cells: Sequence[Cell],
        num_columns: int,
        show_checkboxes: bool,
    ) -> None:
        header_majorities = self._matrix_find_majorities_for_header(rows, group_cells)
        value_counts, row_majorities = self._matrix_find_majorities(rows, cells)

        painter_options = PainterOptions.get_instance()
        for groups, unique_row_ids, matrix_cells in create_matrices(
            rows, group_cells, cells, num_columns
        ):
            # Paint the matrix. Begin with the group headers
            html.open_table(class_="data matrix")
            odd = "odd"
            for cell_nr, cell in enumerate(group_cells):
                odd = "even" if odd == "odd" else "odd"
                html.open_tr(class_="data %s0" % odd)
                html.open_td(class_="matrixhead")
                html.write_text(cell.title(use_short=False))
                html.close_td()
                for _group, group_row in groups:
                    tdclass, content = cell.render(group_row, render_link_to_view)
                    if cell_nr > 0:
                        gv = group_value(group_row, [cell])
                        majority_value = header_majorities.get(cell_nr - 1, None)
                        if majority_value is not None and majority_value != gv:
                            tdclass += " minority"
                    html.open_td(class_=["left", tdclass])
                    html.write_text(content)
                    html.close_td()
                html.close_tr()

            # Now for each unique service^H^H^H^H^H^H ID column paint one row
            for rid in unique_row_ids:
                # Omit rows where all cells have the same values
                if painter_options.get("matrix_omit_uniform"):
                    at_least_one_different = False
                    for counts in value_counts[rid].values():
                        if len(counts) > 1:
                            at_least_one_different = True
                            break
                    if not at_least_one_different:
                        continue

                odd = "even" if odd == "odd" else "odd"
                html.open_tr(class_="data %s0" % odd)
                tdclass, content = cells[0].render(
                    list(matrix_cells[rid].values())[0], render_link_to_view
                )
                html.open_td(class_=["left", tdclass])
                html.write_text(content)
                html.close_td()

                # Now go through the groups and paint the rest of the
                # columns
                for group_id, group_row in groups:
                    cell_row = matrix_cells[rid].get(group_id)
                    if cell_row is None:
                        html.td("")
                    else:
                        if len(cells) > 2:
                            html.open_td(class_="cell")
                            html.open_table()

                        for cell_nr, cell in enumerate(cells[1:]):
                            tdclass, content = cell.render(cell_row, render_link_to_view)

                            gv = group_value(cell_row, [cell])
                            majority_value = row_majorities[rid].get(cell_nr, None)
                            if majority_value is not None and majority_value != gv:
                                tdclass += " minority"

                            if len(cells) > 2:
                                html.open_tr()
                            html.td(content, class_=tdclass)
                            if len(cells) > 2:
                                html.close_tr()

                        if len(cells) > 2:
                            html.close_table()
                            html.close_td()
                html.close_tr()

            html.close_table()

    def _matrix_find_majorities_for_header(
        self, rows: Rows, group_cells: Sequence[Cell]
    ) -> dict[int, Hashable | None]:
        _counts, majorities = self._matrix_find_majorities(rows, group_cells, for_header=True)
        return majorities.get(None, {})

    def _matrix_find_majorities(
        self, rows: Rows, cells: Sequence[Cell], for_header: bool = False
    ) -> tuple[
        dict[Hashable | None, dict[int, dict[Hashable, int]]],
        dict[Hashable | None, dict[int, Hashable | None]],
    ]:
        # dict row_id -> cell_nr -> value -> count
        counts: dict[Hashable | None, dict[int, dict[Hashable, int]]] = {}

        for row in rows:
            if for_header:
                rid: Hashable | None = None
            else:
                rid = group_value(row, [cells[0]])

            for cell_nr, cell in enumerate(cells[1:]):
                value = group_value(row, [cell])
                row_entry = counts.setdefault(rid, {})
                cell_entry = row_entry.setdefault(cell_nr, {})
                cell_entry.setdefault(value, 0)
                cell_entry[value] += 1

        # Now find majorities for each row
        # row_id -> cell_nr -> majority value
        majorities: dict[Hashable, dict[int, Hashable | None]] = {}
        for rid, row_entry in counts.items():
            maj_entry = majorities.setdefault(rid, {})
            for cell_nr, cell_entry in row_entry.items():
                maj_value = None
                max_non_unique = 0  # maximum count, but maybe non unique
                for value, count in cell_entry.items():
                    if count > max_non_unique and count >= 2:
                        maj_value = value
                        max_non_unique = count
                    elif count == max_non_unique:
                        maj_value = None
                maj_entry[cell_nr] = maj_value

        return counts, majorities

    @property
    def painter_options(self) -> list[str]:
        return ["matrix_omit_uniform"]


def create_matrices(
    rows: Rows, group_cells: Sequence[Cell], cells: Sequence[Cell], num_columns: int | None
) -> Iterator[tuple[list[tuple[Any, Any]], list[Any], dict[Any, dict[Any, Any]]]]:
    """Create list of matrices to render for the view layout and for reports"""
    if len(cells) < 2:
        raise MKGeneralException(
            _("Cannot display this view in matrix layout. You need at least two columns!")
        )

    if not group_cells:
        raise MKGeneralException(
            _("Cannot display this view in matrix layout. You need at least one group column!")
        )

    # First find the groups - all rows that have the same values for
    # all group columns. Usually these should correspond with the hosts
    # in the matrix
    groups: list[tuple[Hashable, Any]] = []
    last_group_id: Hashable | None = None
    # not a set, but a list. Need to keep sort order!
    unique_row_ids: list[Hashable] = []
    # Dict from row_id -> group_id -> row
    matrix_cells: dict[Hashable, dict[Any, Any]] = {}
    col_num = 0

    for row in rows:
        group_id = group_value(row, group_cells)
        if group_id != last_group_id:
            col_num += 1
            if num_columns is not None and col_num > num_columns:
                yield (groups, unique_row_ids, matrix_cells)
                groups = []
                unique_row_ids = []  # not a set, but a list. Need to keep sort order!
                matrix_cells = {}  # Dict from row_id -> group_id -> row
                col_num = 1

            last_group_id = group_id
            groups.append((group_id, row))

        # Now the rule is that the *first* cell (usually the service
        # description) will define the left legend of the matrix. It defines
        # the set of possible rows.
        rid = group_value(row, [cells[0]])
        if rid not in matrix_cells:
            unique_row_ids.append(rid)
            matrix_cells[rid] = {}
        matrix_cells[rid][group_id] = row

    if col_num:
        yield (groups, unique_row_ids, matrix_cells)
