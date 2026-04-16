#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time

from cmk.gui import availability
from cmk.gui.availability import (
    AVData,
    AVEntry,
    AVMode,
    AVObjectCells,
    AVObjectType,
    AVOptions,
    AVRowCells,
)
from cmk.gui.config import active_config
from cmk.gui.http import ContentDispositionType, response
from cmk.gui.i18n import _
from cmk.gui.table import Table, table_element


def _output_csv(what: AVObjectType, av_mode: AVMode, av_data: AVData, avoptions: AVOptions) -> None:
    if av_mode == "availability":
        _output_availability_csv(what, av_data, avoptions)
    elif av_mode == "timeline":
        _output_availability_timelines_csv(what, av_data, avoptions)
    else:
        raise NotImplementedError("Unhandled availability mode: %r" % av_mode)


def _output_availability_timelines_csv(
    what: AVObjectType, av_data: AVData, avoptions: AVOptions
) -> None:
    _av_output_set_content_disposition("Checkmk-Availability-Timeline")

    with table_element(
        "av_timeline",
        "",
        output_format="csv",
        limit=active_config.table_row_limit,
    ) as table:
        for av_entry in av_data:
            _output_availability_timeline_csv(table, what, av_entry, avoptions)


def _output_availability_timeline_csv(
    table: Table, what: AVObjectType, av_entry: AVEntry, avoptions: AVOptions
) -> None:
    timeline_layout = availability.layout_timeline(
        what,
        av_entry["timeline"],
        av_entry["considered_duration"],
        avoptions,
        "standalone",
    )

    object_cells = availability.get_object_cells(what, av_entry, avoptions["labelling"])
    for row in timeline_layout["table"]:
        table.row()

        table.cell("object_type", what)
        for cell_index, objectcell in enumerate(object_cells):
            table.cell("object_name_%d" % cell_index, objectcell[0])

        table.cell("object_title", availability.object_title(what, av_entry))
        table.cell("from", row["from"])
        table.cell("from_text", row["from_text"])
        table.cell("until", row["until"])
        table.cell("until_text", row["until_text"])
        table.cell("state", row["state"])
        table.cell("state_name", row["state_name"])
        table.cell("duration_text", row["duration_text"])

        if "omit_timeline_plugin_output" not in avoptions["labelling"]:
            table.cell("log_output", row.get("log_output", ""))

        if "timeline_long_output" in avoptions["labelling"]:
            table.cell("long_log_output", row.get("long_log_output", ""))


def _output_availability_csv(what: AVObjectType, av_data: AVData, avoptions: AVOptions) -> None:
    def cells_from_row(
        table: Table,
        group_titles: list[str],
        group_cells: list[str],
        object_titles: list[str],
        cell_titles: list[tuple[str, str]],
        row_object: AVObjectCells,
        row_cells: AVRowCells,
    ) -> None:
        for column_title, group_title in zip(group_titles, group_cells):
            table.cell(column_title, group_title)

        for title, (name, _url) in zip(object_titles, row_object):
            table.cell(title, name)

        for (title, _help), (text, _css) in zip(cell_titles, row_cells):
            table.cell(title, text)

    _av_output_set_content_disposition("Checkmk-Availability")
    availability_tables = availability.compute_availability_groups(what, av_data, avoptions)
    with table_element(
        "av_items", output_format="csv", limit=active_config.table_row_limit
    ) as table:
        for group_title, availability_table in availability_tables:
            av_table = availability.layout_availability_table(
                what, group_title, availability_table, avoptions
            )
            pad = 0

            if group_title:
                group_titles, group_cells = [_("Group")], [group_title]
            else:
                group_titles, group_cells = [], []

            for row in av_table["rows"]:
                table.row()
                cells_from_row(
                    table,
                    group_titles,
                    group_cells,
                    av_table["object_titles"],
                    av_table["cell_titles"],
                    row["object"],
                    row["cells"],
                )
                # presumably all rows have the same width
                pad = len(row["object"]) - 1
            table.row()

            if "summary" in av_table:
                row_object: AVObjectCells = [(_("Summary"), "")]
                row_object += [("", "")] * pad
                cells_from_row(
                    table,
                    group_titles,
                    group_cells,
                    av_table["object_titles"],
                    av_table["cell_titles"],
                    row_object,
                    av_table["summary"],
                )


def _av_output_set_content_disposition(title: str) -> None:
    filename = "{}-{}.csv".format(
        title,
        time.strftime("%Y-%m-%d_%H-%M-%S", time.localtime(time.time())),
    )
    response.set_content_type("text/csv")
    response.set_content_disposition(ContentDispositionType.ATTACHMENT, filename)
