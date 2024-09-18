#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import glob
import hashlib
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Literal

from cmk.ccc.exceptions import MKGeneralException

from cmk.gui.nodevis.filters import FilterTopologyMaxNodes, FilterTopologyMeshDepth
from cmk.gui.nodevis.utils import topology_data_dir


class MKGrowthExceeded(MKGeneralException):
    pass


class MKGrowthInterruption(MKGeneralException):
    pass


class TopologyLinkType(Enum):
    DEFAULT = "default"
    HOST2HOST = "host2host"
    SERVICE2SERVICE = "service2service"
    HOST2SERVICE = "host2service"


class NodeType(Enum):
    TOPOLOGY_SITE = "topology_site"
    TOPOLOGY_CENTER = "topology_center"
    TOPOLOGY = "topology"
    TOPOLOGY_HOST = "topology_host"
    TOPOLOGY_SERVICE = "topology_service"
    TOPOLOGY_UNKNOWN_HOST = "topology_unknown_host"
    TOPOLOGY_UNKNOWN_SERVICE = "topology_unknown_service"
    TOPOLOGY_UNKNOWN = "topology_unknown"


@dataclass(kw_only=True)
class TopologyFilterConfiguration:
    max_nodes: int = FilterTopologyMaxNodes().range_config.default
    mesh_depth: int = FilterTopologyMeshDepth().range_config.default
    growth_auto_max_nodes: int = 400
    query: str = ""

    @classmethod
    def parse(cls, serialized_config: dict[str, Any]) -> "TopologyFilterConfiguration":
        return cls(
            max_nodes=serialized_config.get(
                "max_nodes", FilterTopologyMaxNodes().range_config.default
            ),
            mesh_depth=serialized_config.get(
                "mesh_depth", FilterTopologyMeshDepth().range_config.default
            ),
            growth_auto_max_nodes=serialized_config.get("growth_auto_max_nodes", 400),
            query=serialized_config.get("query", ""),
        )

    @property
    def ident(self) -> tuple:
        return self.max_nodes, self.mesh_depth, self.growth_auto_max_nodes, self.query


@dataclass(kw_only=True)
class TopologyDatasourceConfiguration:
    available_datasources: list[str] = field(default_factory=list)
    reference: str = "default"
    compare_to: str = "default"

    def __post_init__(self):
        if not self.available_datasources:
            sorted_list = sorted(glob.glob("*", root_dir=topology_data_dir))
            try:
                sorted_list.remove("default")
            except ValueError:
                pass
            self.available_datasources = ["default"] + sorted_list


@dataclass(kw_only=True)
class ComputationOptions:
    merge_nodes: bool = True
    show_services: Literal["none", "all", "only_problems"] = "all"
    hierarchy: Literal["full", "flat"] = "full"
    enforce_hierarchy_update: bool = False

    @classmethod
    def parse(cls, serialized_config: dict[str, Any]) -> "ComputationOptions":
        show_services: Literal["none", "all", "only_problems"] = "all"
        show_services = serialized_config.get("show_services", show_services)
        hierarchy: Literal["flat", "full"] = "full"
        hierarchy = serialized_config.get("hierarchy", hierarchy)

        return cls(
            merge_nodes=serialized_config.get("merge_nodes", True),
            show_services=show_services,
            hierarchy=hierarchy,
            enforce_hierarchy_update=serialized_config.get("enforce_hierarchy_update", False),
        )


@dataclass(kw_only=True)
class OverlaysConfig:
    available_layers: list[str] = field(default_factory=list)
    overlays: dict[str, dict[str, Any]] = field(default_factory=dict)
    computation_options: ComputationOptions = field(default_factory=ComputationOptions)

    @classmethod
    def parse(cls, serialized_config: dict[str, Any]) -> "OverlaysConfig":
        return cls(
            available_layers=serialized_config.get("available_layers") or [],
            overlays=serialized_config.get("overlays", {}),
            computation_options=ComputationOptions.parse(
                serialized_config.get("computation_options", {})
            ),
        )


@dataclass(kw_only=True)
class Layout:
    line_config: dict[str, Any] = field(default_factory=dict)
    force_config: dict[str, Any] = field(default_factory=dict)
    reference_size: list[int] = field(default_factory=lambda: [1024, 768])
    style_configs: list[dict[str, Any]] = field(default_factory=list)
    origin_info: str = ""
    origin_type: str = ""


@dataclass
class FrontendConfiguration:
    overlays_config: OverlaysConfig = field(default_factory=OverlaysConfig)
    growth_root_nodes: list[str] = field(default_factory=list)  # Extra Growth starts from here
    growth_forbidden_nodes: list[str] = field(default_factory=list)  # Growth stops here
    growth_continue_nodes: list[str] = field(default_factory=list)  # Growth continues here
    datasource_configuration: TopologyDatasourceConfiguration = field(
        default_factory=TopologyDatasourceConfiguration
    )
    custom_node_settings: dict[str, dict[str, Any]] = field(default_factory=dict)

    def __post_init__(self):
        # Used as faster lookup, not serialized
        self._growth_root_nodes_set = set(self.growth_root_nodes)
        self._growth_forbidden_nodes_set = set(self.growth_forbidden_nodes)
        self._growth_continue_nodes_set = set(self.growth_continue_nodes)

    @classmethod
    def parse(cls, serialized_config: dict[str, Any]) -> "FrontendConfiguration":
        return cls(
            overlays_config=OverlaysConfig.parse(serialized_config.get("overlays_config", {})),
            growth_root_nodes=serialized_config.get("growth_root_nodes", []),
            growth_forbidden_nodes=serialized_config.get("growth_forbidden_nodes", []),
            growth_continue_nodes=serialized_config.get("growth_continue_nodes", []),
            datasource_configuration=TopologyDatasourceConfiguration(
                **serialized_config.get("datasource_configuration", {})
            ),
            custom_node_settings=(serialized_config.get("custom_node_settings", {})),
        )

    @property
    def growth_root_nodes_set(self) -> set[str]:
        return self._growth_root_nodes_set

    @property
    def growth_forbidden_nodes_set(self) -> set[str]:
        return self._growth_root_nodes_set

    @property
    def growth_continue_nodes_set(self) -> set[str]:
        return self._growth_continue_nodes_set

    @classmethod
    def _convert_overlays_config(cls, overlays_config: dict[str, Any]) -> dict[str, Any]:
        if "available_layers" in overlays_config:
            return overlays_config
        return {
            "available_layers": [],
            "overlays": overlays_config,
            "computation_options": ComputationOptions(),
        }


class TopologyQueryIdentifier:
    """Describes the query parameters which were used to generate the result"""

    def __init__(
        self, topology_type: str, topology_filter_configuration: TopologyFilterConfiguration
    ):
        self._identifier: tuple[str, ...] = (
            topology_type,
            *map(str, topology_filter_configuration.ident),
        )

    @property
    def identifier(self) -> tuple[str, ...]:
        return self._identifier

    def __hash__(self) -> int:
        hash_object = hashlib.sha256("#".join(self._identifier).encode("utf-8"))
        return int(hash_object.hexdigest(), 16)


@dataclass(kw_only=True)
class TopologyConfiguration:
    version: int = 1
    type: str = ""
    frontend: FrontendConfiguration = field(default_factory=FrontendConfiguration)
    filter: TopologyFilterConfiguration = field(default_factory=TopologyFilterConfiguration)
    layout: Layout = field(default_factory=Layout)

    @classmethod
    def parse(
        cls, serialized_config: dict[str, Any], query_identifier: TopologyQueryIdentifier
    ) -> "TopologyConfiguration":
        if serialized_config.get("version") is None:
            serialized_config = cls._migrate_legacy_data(serialized_config, query_identifier)

        return cls(
            version=int(serialized_config.get("version", 1)),
            type=serialized_config.get("type", "parent_child_topology"),
            frontend=FrontendConfiguration.parse(serialized_config.get("frontend", {})),
            filter=TopologyFilterConfiguration.parse(serialized_config.get("filter", {})),
            layout=Layout(**serialized_config.get("layout", {})),
        )

    @classmethod
    def _migrate_legacy_data(
        cls, data: dict[str, Any], query_identifier: TopologyQueryIdentifier
    ) -> dict[str, Any]:
        force_options = data.pop("force_options", {})
        line_config = data.pop("line_config", {})
        ref_size = data.pop("reference_size", {"height": 1024, "width": 768})
        style_configs = data.pop("style_configs", None)
        migrated_layout = {
            "force_config": force_options,
            "line_config": line_config,
            "reference_size": [ref_size["width"], ref_size["height"]],
            "style_configs": style_configs,
        }
        # NOTE: legacy format only had parent_child_topology
        return {
            "version": 1,
            "type": "parent_child_topology",
            "frontend": data,
            "filter": asdict(
                TopologyFilterConfiguration(
                    max_nodes=int(query_identifier.identifier[1]),
                    mesh_depth=int(query_identifier.identifier[2]),
                    growth_auto_max_nodes=int(query_identifier.identifier[3]),
                    query=query_identifier.identifier[4],
                )
            ),
            "layout": migrated_layout,
        }


@dataclass(kw_only=True)
class GrowthSettings:
    growth_root: bool = False  # growth should start here
    growth_continue: bool = False  # growth may continue here, ignores mesh depth
    growth_forbidden: bool = False  # growth should stop here
    indicator_growth_possible: bool = False  # indicator, growth possible
    indicator_growth_root: bool = False  # indicator, growth started here


@dataclass(kw_only=True)
class TopologyNode:
    id: str
    name: str
    incoming: set[str] = field(default_factory=set)
    outgoing: set[str] = field(default_factory=set)
    mesh_depth: int = 1
    type: NodeType = NodeType.TOPOLOGY
    metadata: dict[str, Any] = field(default_factory=dict)


TopologyNodes = dict[str, TopologyNode]


# FRONTEND DATACLASSES ##


@dataclass
class TopologyLink:
    source: str
    target: str
    config: dict[str, Any] = field(default_factory=dict)

    def __hash__(self) -> int:
        tokens = tuple(sorted([self.source, self.target]))
        return ("%s_%s" % tokens).__hash__()

    def __eq__(self, other: object) -> bool:
        return hash(self) == hash(other)


@dataclass(kw_only=True)
class HierarchyNode:
    id: str
    name: str
    node_type: str
    children: list["HierarchyNode"]
    growth_settings: GrowthSettings = field(default_factory=GrowthSettings)
    type_specific: dict[str, Any] = field(default_factory=dict)


@dataclass
class NodeConfig:
    hierarchy: HierarchyNode
    links: list[TopologyLink]


@dataclass
class TopologyResponse:
    node_config: NodeConfig
    frontend_configuration: FrontendConfiguration
    layout: Layout = field(default_factory=Layout)
    headline: str | None = None
    errors: list[str] = field(default_factory=list)
    query_hash: str | None = None
