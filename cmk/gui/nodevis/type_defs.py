#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import hashlib
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Literal

from cmk.utils.exceptions import MKGeneralException

from cmk.gui.nodevis.filters import FilterTopologyMaxNodes, FilterTopologyMeshDepth


class MKGrowthExceeded(MKGeneralException):
    pass


class MKGrowthInterruption(MKGeneralException):
    pass


@dataclass
class TopologyFilterConfiguration:
    max_nodes: int = FilterTopologyMaxNodes().range_config.default
    mesh_depth: int = FilterTopologyMeshDepth().range_config.default
    growth_auto_max_nodes: int = 400
    query: str = ""

    @property
    def ident(self) -> tuple:
        return self.max_nodes, self.mesh_depth, self.growth_auto_max_nodes, self.query


@dataclass(kw_only=True)
class TopologyDatasourceConfiguration:
    available_datasources: list[str] = field(default_factory=list)
    reference: str = "default"
    compare_to: str = "default"


@dataclass(kw_only=True)
class ComputationOptions:
    merge_nodes: bool = True
    show_services: Literal["none", "all", "only_problems"] = "all"


@dataclass(kw_only=True)
class OverlayConfig:
    active: bool = True


@dataclass(kw_only=True)
class OverlaysConfig:
    available_layers: list[str] = field(default_factory=list)
    overlays: dict[str, Any] = field(default_factory=dict)
    computation_options: ComputationOptions = field(default_factory=ComputationOptions)

    def __init__(
        self,
        available_layers: list[str] | None = None,
        overlays: dict[str, OverlayConfig] | None = None,
        computation_options: ComputationOptions | None = None,
    ):
        self.available_layers = available_layers or []
        self.overlays = overlays or {}
        self.computation_options = computation_options or ComputationOptions()

    @classmethod
    def deserialize(cls, config: dict[str, Any]) -> "OverlaysConfig":
        return OverlaysConfig(
            config["available_layers"],
            {
                x: OverlayConfig(active=y.get("active"))
                for x, y in config.get("overlays", {}).items()
            },
            ComputationOptions(**config.get("computation_options", {})),
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
class FrontendTopologyConfiguration:
    overlays_config: OverlaysConfig = field(default_factory=OverlaysConfig)
    growth_root_nodes: set[str] = field(default_factory=set)  # Extra Growth starts from here
    growth_forbidden_nodes: set[str] = field(default_factory=set)  # Growth stops here
    growth_continue_nodes: set[str] = field(default_factory=set)  # Growth continues here
    datasource_configuration: TopologyDatasourceConfiguration = field(
        default_factory=TopologyDatasourceConfiguration
    )
    custom_node_settings: dict[str, dict[str, Any]] = field(default_factory=dict)

    @classmethod
    def deserialize(cls, settings: dict[str, Any]) -> "FrontendTopologyConfiguration":
        for key in ["growth_root_nodes", "growth_forbidden_nodes", "growth_continue_nodes"]:
            settings[key] = set(settings[key])
        settings["datasource_configuration"] = TopologyDatasourceConfiguration(
            **settings.get("datasource_configuration", {})
        )
        settings["overlays_config"] = OverlaysConfig.deserialize(
            settings.get("overlays_config", {})
        )
        return cls(**settings)

    @classmethod
    def _convert_overlays_config(cls, overlays_config: dict[str, Any]) -> dict[str, Any]:
        if "available_layers" in overlays_config:
            return overlays_config
        return {
            "available_layers": [],
            "overlays": overlays_config,
            "computation_options": ComputationOptions(),
        }

    def serialize(self):
        value = asdict(self)
        for key in ["growth_root_nodes", "growth_forbidden_nodes", "growth_continue_nodes"]:
            value[key] = list(value[key])
        return value


@dataclass
class TopologyConfiguration:
    type: str
    frontend: FrontendTopologyConfiguration
    filter: TopologyFilterConfiguration
    layout: Layout = field(default_factory=Layout)
    version = 1

    def serialize(self):
        return {
            "type": self.type,
            "frontend": self.frontend.serialize(),
            "filter": self.filter.ident,
            "layout": asdict(self.layout),
            "version": self.version,
        }

    @classmethod
    def deserialize(cls, data: dict[str, Any]) -> "TopologyConfiguration":
        if "version" not in data:
            data = cls._migrate_legacy_data(data)
        return TopologyConfiguration(
            data.get("type", ""),
            FrontendTopologyConfiguration.deserialize(data.get("frontend", {})),
            TopologyFilterConfiguration(*data.get("filter", [])),
            Layout(**data.get("layout", {})),
        )

    @classmethod
    def _migrate_legacy_data(cls, data: dict[str, Any]) -> dict[str, Any]:
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
            "type": "parent_child_topology",
            "frontend": data,
            "filter": TopologyFilterConfiguration().ident,
            "layout": migrated_layout,
        }


@dataclass(kw_only=True)
class GrowthSettings:
    growth_root: bool = False  # growth should start here
    growth_continue: bool = False  # growth may continue here, ignores mesh depth
    growth_forbidden: bool = False  # growth should stop here
    indicator_growth_possible: bool = False  # indicator, growth possible
    indicator_growth_root: bool = False  # indicator, growth started here


class FrontendNodeType(Enum):
    TOPOLOGY_SITE = "topology_site"
    TOPOLOGY_CENTER = "topology_center"
    TOPOLOGY = "topology"
    TOPOLOGY_HOST = "topology_host"
    TOPOLOGY_SERVICE = "topology_service"
    TOPOLOGY_UNKNOWN = "topology_unknown"


class TopologyLinkType(Enum):
    DEFAULT = "default"
    HOST2HOST = "host2host"
    SERVICE2SERVICE = "service2service"
    HOST2SERVICE = "host2service"


@dataclass
class TopologyFrontendLink:
    source: str
    target: str
    config: dict[str, Any]

    def __hash__(self):
        tokens = tuple(sorted([self.source, self.target]))
        return ("%s_%s" % tokens).__hash__()

    def id(self) -> tuple[str, ...]:
        return tuple(sorted([self.source, self.target]))


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
class TopologyNode:
    id: str
    name: str
    incoming: set[str] = field(default_factory=set)
    outgoing: set[str] = field(default_factory=set)
    mesh_depth: int = 1
    type: FrontendNodeType = FrontendNodeType.TOPOLOGY
    metadata: dict[str, Any] = field(default_factory=dict)


TopologyNodes = dict[str, TopologyNode]

#### FRONTEND DATACLASSES


@dataclass(kw_only=True)
class TopologyFrontendNode:
    id: str
    name: str
    node_type: str
    children: list["TopologyFrontendNode"]
    growth_settings: GrowthSettings = field(default_factory=GrowthSettings)
    type_specific: dict[str, Any] = field(default_factory=dict)


@dataclass
class FrontendNodeConfig:
    hierarchy: TopologyFrontendNode
    links: list[TopologyFrontendLink]


@dataclass
class TopologyResponse:
    """Response send to the frontend"""

    node_config: FrontendNodeConfig
    frontend_configuration: FrontendTopologyConfiguration
    layout: Layout = field(default_factory=Layout)
    headline: str | None = None
    errors: list[str] = field(default_factory=list)
