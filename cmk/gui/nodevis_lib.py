#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import cmk.utils
from cmk.utils import store
from cmk.utils.exceptions import MKGeneralException

from cmk.gui.config import active_config
from cmk.gui.htmllib.html import html
from cmk.gui.i18n import _l
from cmk.gui.type_defs import FilterHTTPVariables, Row
from cmk.gui.utils.html import HTML
from cmk.gui.utils.speaklater import LazyString
from cmk.gui.visuals.filter import Filter
from cmk.gui.watolib.utils import multisite_dir

topology_dir = Path(cmk.utils.paths.var_dir) / "topology"
topology_settings_lookup = topology_dir / "topology_settings"
topology_configs_dir = topology_dir / "configs"


class MKGrowthExceeded(MKGeneralException):
    pass


class MKGrowthInterruption(MKGeneralException):
    pass


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


class FilterTopologyMeshDepth(FilterRange):
    def __init__(self) -> None:
        super().__init__(
            _FilterRangeConfig(
                column="topology_mesh_depth",
                title=_l("Topology mesh depth"),
                step=1,
                default=2,
                min=0,
                max=10,
            )
        )


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


@dataclass(kw_only=True)
class TopologyDatasourceConfiguration:
    available_datasources: list[str] = field(default_factory=list)
    reference: str = "default"
    compare_to: str = "default"


@dataclass
class TopologyFrontendConfiguration:
    growth_root_nodes: set[str] = field(default_factory=set)  # Extra Growth starts from here
    growth_forbidden_nodes: set[str] = field(default_factory=set)  # Growth stops here
    growth_continue_nodes: set[str] = field(default_factory=set)  # Growth continues here
    overlays_config: dict[str, dict[str, Any]] = field(default_factory=dict)
    custom_node_settings: dict[str, dict[str, Any]] = field(default_factory=dict)
    datasource_configuration: TopologyDatasourceConfiguration = field(
        default_factory=TopologyDatasourceConfiguration
    )
    reference_size: list[int] = field(default_factory=lambda: [1024, 768])
    style_configs: list[dict[str, Any]] = field(default_factory=list)
    line_config: dict[str, Any] = field(default_factory=dict)
    force_options: dict[str, int | bool] = field(default_factory=dict)

    @classmethod
    def from_json_str(cls, serialized: str) -> "TopologyFrontendConfiguration":
        return cls.from_json_object(json.loads(serialized))

    @classmethod
    def from_json_object(cls, settings: dict[str, Any]) -> "TopologyFrontendConfiguration":
        for key in ["growth_root_nodes", "growth_forbidden_nodes", "growth_continue_nodes"]:
            settings[key] = set(settings[key])
        settings["datasource_configuration"] = TopologyDatasourceConfiguration(
            **settings.get("datasource_configuration", {})
        )
        return cls(**settings)

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> "TopologyFrontendConfiguration":
        ds_config = TopologyDatasourceConfiguration(**config.pop("datasource_configuration", {}))
        return cls(datasource_configuration=ds_config, **config)

    def to_json(self) -> str:
        return json.dumps(self.get_json_export_object())

    def get_json_export_object(self) -> dict[str, Any]:
        value = asdict(self)
        for key in ["growth_root_nodes", "growth_forbidden_nodes", "growth_continue_nodes"]:
            value[key] = list(value[key])
        return value


@dataclass
class TopologyFilterConfiguration:
    max_nodes: int = FilterTopologyMaxNodes().range_config.default
    mesh_depth: int = FilterTopologyMeshDepth().range_config.default
    growth_auto_max_nodes: int = 400
    query: str = ""

    @property
    def ident(self) -> tuple[str, ...]:
        return tuple(
            map(str, [self.max_nodes, self.mesh_depth, self.growth_auto_max_nodes, self.query])
        )


@dataclass
class TopologyConfiguration:
    type: str
    frontend: TopologyFrontendConfiguration
    filter: TopologyFilterConfiguration


class TopologyQueryIdentifier:
    """Describes the query parameters which were used to generate the result"""

    def __init__(
        self, topology_type: str, topology_filter_configuration: TopologyFilterConfiguration
    ):
        self._identifier: tuple[str, ...] = (
            topology_type,
            *topology_filter_configuration.ident,
        )

    @property
    def identifier(self) -> tuple[str, ...]:
        return self._identifier

    def __hash__(self) -> int:
        hash_object = hashlib.sha256("#".join(self._identifier).encode("utf-8"))
        return int(hash_object.hexdigest(), 16)


class BILayoutManagement:
    _config_file = Path(multisite_dir()) / "bi_layouts.mk"

    @classmethod
    def save_layouts(cls) -> None:
        store.save_to_mk_file(
            str(BILayoutManagement._config_file),
            "bi_layouts",
            active_config.bi_layouts,
            pprint_value=True,
        )

    @classmethod
    def load_bi_template_layout(cls, template_id: str | None) -> Any:
        return active_config.bi_layouts["templates"].get(template_id)

    @classmethod
    def load_bi_aggregation_layout(cls, aggregation_name: str | None) -> Any:
        return active_config.bi_layouts["aggregations"].get(aggregation_name)

    @classmethod
    def get_all_bi_template_layouts(cls) -> Any:
        return active_config.bi_layouts["templates"]

    @classmethod
    def get_all_bi_aggregation_layouts(cls) -> Any:
        return active_config.bi_layouts["aggregations"]
