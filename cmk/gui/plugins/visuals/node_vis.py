#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from dataclasses import dataclass
from typing import Dict

from cmk.gui.htmllib.html import html
from cmk.gui.i18n import _l
from cmk.gui.plugins.visuals.utils import Filter, filter_registry
from cmk.gui.type_defs import FilterHTTPVariables, Row
from cmk.gui.utils.html import HTML
from cmk.gui.utils.speaklater import LazyString


@dataclass
class _FilterRangeConfig:
    column: str
    title: LazyString
    step: int
    default: int
    min: int
    max: int


class FilterRange(Filter):
    def __init__(self, filter_range_config: _FilterRangeConfig):
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

    def request_vars_from_row(self, row: Row) -> Dict[str, str]:
        return {self._filter_range_config.column: row[self._filter_range_config.column]}

    def display(self, value: FilterHTTPVariables) -> None:
        actual_value = value.get(
            self._filter_range_config.column, self._filter_range_config.default
        )
        html.add_form_var(self._filter_range_config.column)
        html.write_html(
            HTML(
                f"""
            <input
                id={self._filter_range_config.column}
                name={self._filter_range_config.column}
                style="pointer-events: all; width: 80%%;"
                oninput="{self._update_label()}" type="range"
                step="{self._filter_range_config.step}"
                min="{self._filter_range_config.min}"
                max="{self._filter_range_config.max}"
                value="{actual_value}">
            <label id={self._filter_range_config.column}_label>{actual_value}</>
            """
            )
        )

    def _update_label(self) -> str:
        return (
            f"d3.select('label#{self._filter_range_config.column}_label').text(event.target.value);"
        )


@filter_registry.register_instance
class FilterTopologyMeshDepth(FilterRange):
    def __init__(self) -> None:
        super().__init__(
            _FilterRangeConfig(
                column="topology_mesh_depth",
                title=_l("Topology mesh depth"),
                step=1,
                default=0,
                min=0,
                max=10,
            )
        )


@filter_registry.register_instance
class FilterTopologyMaxNodes(FilterRange):
    def __init__(self) -> None:
        super().__init__(
            _FilterRangeConfig(
                column="topology_max_nodes",
                title=_l("Topology max nodes"),
                step=100,
                default=2000,
                min=200,
                max=10000,
            )
        )
