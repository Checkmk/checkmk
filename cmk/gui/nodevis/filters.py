#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from dataclasses import dataclass

from cmk.gui.htmllib.html import html
from cmk.gui.i18n import _l
from cmk.gui.type_defs import FilterHTTPVariables, Row
from cmk.gui.utils.speaklater import LazyString
from cmk.gui.visuals.filter import Filter


@dataclass
class _FilterRangeConfig:
    column: str
    title: LazyString
    step: int
    default: int
    min: int
    max: int


class FilterRange(Filter):
    def __init__(self, filter_range_config: _FilterRangeConfig) -> None:
        super().__init__(
            ident=filter_range_config.column,
            title=filter_range_config.title,
            sort_index=92,
            info="host",
            htmlvars=[filter_range_config.column],
            link_columns=[filter_range_config.column],
        )
        self._filter_range_config = filter_range_config

    @property
    def range_config(self):
        return self._filter_range_config

    def request_vars_from_row(self, row: Row) -> dict[str, str]:
        return {self._filter_range_config.column: row[self._filter_range_config.column]}

    def display(self, value: FilterHTTPVariables) -> None:
        filter_value = str(value.get(self._filter_range_config.column))
        actual_value = (
            filter_value if filter_value.isnumeric() else self._filter_range_config.default
        )
        html.add_form_var(self._filter_range_config.column)
        html.open_table()
        html.tr("", id_=self._filter_range_config.column, css=["range_input"])
        html.close_table()
        html.javascript(
            "cmk.nodevis.utils.render_input_range(cmk.d3.select(%s), %s, %s)"
            % (
                json.dumps(f"#{self._filter_range_config.column}"),
                json.dumps(
                    {
                        "id": self._filter_range_config.column,
                        "title": "",
                        "step": self._filter_range_config.step,
                        "min": self._filter_range_config.min,
                        "max": self._filter_range_config.max,
                        "default_value": self._filter_range_config.default,
                    },
                ),
                json.dumps(actual_value),
            ),
            data_cmk_execute_after_replace="",
        )

    def _update_label(self) -> str:
        return f"cmk.d3.select('label#{self._filter_range_config.column}_label').text(event.target.value);"


class FilterTopologyMeshDepth(FilterRange):
    def __init__(self) -> None:
        super().__init__(
            _FilterRangeConfig(
                column="topology_mesh_depth",
                title=_l("Topology mesh depth"),
                step=1,
                default=2,
                min=0,
                max=20,
            )
        )


class FilterTopologyMaxNodes(FilterRange):
    def __init__(self) -> None:
        super().__init__(
            _FilterRangeConfig(
                column="topology_max_nodes",
                title=_l("Topology max nodes"),
                step=5,
                default=2000,
                min=5,
                max=10000,
            )
        )
