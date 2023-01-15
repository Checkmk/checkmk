#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import hashlib
import itertools
import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import livestatus

import cmk.utils.paths
import cmk.utils.plugin_registry
from cmk.utils import store
from cmk.utils.site import omd_site
from cmk.utils.type_defs import HostName, UserId

import cmk.gui.bi as bi
import cmk.gui.visuals
from cmk.gui import sites
from cmk.gui.breadcrumb import (
    make_current_page_breadcrumb_item,
    make_simple_page_breadcrumb,
    make_topic_breadcrumb,
)
from cmk.gui.config import active_config
from cmk.gui.dashboard import get_topology_context_and_filters
from cmk.gui.exceptions import MKGeneralException
from cmk.gui.htmllib.header import make_header
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _, _l
from cmk.gui.logged_in import user
from cmk.gui.main_menu import mega_menu_registry
from cmk.gui.node_vis_lib import BILayoutManagement
from cmk.gui.page_menu import (
    make_display_options_dropdown,
    PageMenu,
    PageMenuEntry,
    PageMenuSidePopup,
    PageMenuTopic,
)
from cmk.gui.pages import AjaxPage, Page, page_registry, PageResult
from cmk.gui.pagetypes import PagetypeTopics
from cmk.gui.plugins.visuals.node_vis import FilterTopologyMaxNodes, FilterTopologyMeshDepth
from cmk.gui.plugins.visuals.utils import get_livestatus_filter_headers
from cmk.gui.plugins.wato import bi_valuespecs
from cmk.gui.type_defs import ColumnSpec, PainterParameters, Visual, VisualLinkSpec
from cmk.gui.utils.csrf_token import check_csrf_token
from cmk.gui.utils.theme import theme
from cmk.gui.views.page_ajax_filters import ABCAjaxInitialFilters
from cmk.gui.views.store import multisite_builtin_views

from cmk.bi.aggregation_functions import BIAggregationFunctionSchema
from cmk.bi.computer import BIAggregationFilter
from cmk.bi.lib import NodeResultBundle
from cmk.bi.trees import BICompiledLeaf, BICompiledRule

Mesh = set[str]
Meshes = list[Mesh]


class MKGrowthExceeded(MKGeneralException):
    pass


class MKGrowthInterruption(MKGeneralException):
    pass


@dataclass(kw_only=True)
class TopologyDatasourceConfiguration:
    available_datasource: list[str] = field(default_factory=list)
    used_datasource: str = "default"


@dataclass
class TopologyFrontendConfiguration:
    growth_root_nodes: set[str] = field(default_factory=set)  # Extra Growth starts from here
    growth_forbidden_nodes: set[str] = field(default_factory=set)  # Growth stops here
    growth_continue_nodes: set[str] = field(default_factory=set)  # Growth continues here
    overlays_config: dict[str, dict[str, Any]] = field(default_factory=dict)
    node_style_config: dict[str, Any] = field(default_factory=dict)
    custom_node_settings: dict[str, dict[str, Any]] = field(default_factory=dict)
    datasource_configuration: TopologyDatasourceConfiguration = field(
        default_factory=TopologyDatasourceConfiguration
    )

    @classmethod
    def from_json(cls, serialized: str) -> "TopologyFrontendConfiguration":
        settings = json.loads(serialized)
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
        #        value["datasource_configuration"] = asdict
        return value


@dataclass
class TopologyFilterConfiguration:
    max_nodes: int = FilterTopologyMaxNodes().range_config.default
    mesh_depth: int = FilterTopologyMeshDepth().range_config.default
    growth_auto_max_nodes: int = 400
    query: str = "default_query"

    def ident(self):
        return "#".join(
            map(str, [self.max_nodes, self.mesh_depth, self.growth_auto_max_nodes, self.query])
        )


@dataclass
class TopologyConfiguration:
    type: str
    frontend: TopologyFrontendConfiguration
    filter: TopologyFilterConfiguration


def _get_topology_configuration(
    topology_type: str, default_overlays: dict[str, Any] | None = None
) -> TopologyConfiguration:
    topology_filters = _get_topology_settings_from_filters()
    mesh_depth = int(topology_filters["topology_mesh_depth"])
    max_nodes = int(topology_filters["topology_max_nodes"])
    filter_configuration = TopologyFilterConfiguration(
        mesh_depth=mesh_depth, max_nodes=max_nodes, query=_get_query_string()
    )

    if request.var("search_frontend_settings") and (
        value := _get_topology_frontend_configuration_for_filter(
            topology_type, filter_configuration
        )
    ):
        frontend_configuration = TopologyFrontendConfiguration.from_config(value)
    elif frontend_config := request.get_str_input("topology_frontend_configuration"):
        frontend_configuration = TopologyFrontendConfiguration.from_json(frontend_config)
    else:
        frontend_configuration = TopologyFrontendConfiguration()
        frontend_configuration.overlays_config = default_overlays or {}

    topology_configuration = TopologyConfiguration(
        topology_type, frontend_configuration, filter_configuration
    )
    return topology_configuration


def _get_hostnames_for_query(topology_configuration: TopologyConfiguration) -> set[HostName]:
    if topology_configuration.filter.query == "default_query":
        return _get_default_view_hostnames(topology_configuration)

    site_id = (
        livestatus.SiteId(request.get_str_input_mandatory("site"))
        if request.get_str_input("site")
        else None
    )
    with sites.only_sites(site_id):
        return {x[0] for x in sites.live().query(topology_configuration.filter.query)}


def _get_topology_settings_from_filters() -> dict[str, str]:
    topology_values: dict[str, str] = {}
    for filter_class in (FilterTopologyMaxNodes, FilterTopologyMeshDepth):
        filter_instance = filter_class()
        value = filter_instance.value()
        if not value[filter_instance.ident].isdigit():
            value = {filter_instance.ident: filter_instance.range_config.default}
        topology_values.update(value)
    return topology_values


def _get_query_string() -> str:
    if not request.has_var("filled_in"):
        return "default_query"

    # Determine hosts from filters
    filter_headers = "".join(get_livestatus_filter_headers(*get_topology_context_and_filters()))
    query = "GET hosts\nColumns: name"
    if filter_headers:
        query += "\n%s" % filter_headers
    return query


def _get_default_view_hostnames(topology_configuration: TopologyConfiguration) -> set[HostName]:
    """Returns all hosts without any parents"""
    query = "GET hosts\nColumns: name\nFilter: parents ="
    site_id = (
        livestatus.SiteId(request.get_str_input_mandatory("site"))
        if request.get_str_input("site")
        else None
    )
    with sites.prepend_site(), sites.only_sites(site_id):
        hosts = [(x[0], x[1]) for x in sites.live().query(query)]

    # If no explicit site is set and the number of initially displayed hosts
    # exceeds the auto growth range, only the hosts of the master site are shown
    if len(hosts) > topology_configuration.filter.growth_auto_max_nodes:
        hostnames = {x[1] for x in hosts if x[0] == omd_site()}
    else:
        hostnames = {x[1] for x in hosts}

    return hostnames


_topology_settings_file = Path(cmk.utils.paths.omd_root) / "etc" / "topology_settings.json"


def _delete_topology_configuration(topology_configuration: TopologyConfiguration) -> None:
    query_hash = _compute_topology_hash(topology_configuration)
    if not _topology_settings_file.exists():
        return

    try:
        data = json.loads(store.load_text_from_file(_topology_settings_file))
    except json.JSONDecodeError:
        data = {}

    data.pop(query_hash, None)
    store.save_text_to_file(_topology_settings_file, json.dumps(data))


def _save_topology_configuration(topology_configuration: TopologyConfiguration) -> None:
    query_hash = _compute_topology_hash(topology_configuration)
    if not _topology_settings_file.exists():
        _topology_settings_file.touch()

    try:
        data = json.loads(store.load_text_from_file(_topology_settings_file))
    except json.JSONDecodeError:
        data = {}

    data[query_hash] = asdict(topology_configuration.frontend)
    store.save_text_to_file(_topology_settings_file, json.dumps(data))


def _compute_topology_hash(topology_configuration: TopologyConfiguration) -> str:
    ident = "#".join([topology_configuration.type, topology_configuration.filter.ident()])
    return hashlib.md5(ident.encode("utf-8")).hexdigest()


def _get_topology_frontend_configuration_for_filter(
    topology_type: str, filter_configuration: TopologyFilterConfiguration
) -> dict[str, Any]:
    ident = "#".join([topology_type, filter_configuration.ident()])
    query_hash = hashlib.md5(ident.encode("utf-8")).hexdigest()
    if not _topology_settings_file.exists():
        return {}

    try:
        return json.loads(store.load_text_from_file(_topology_settings_file)).get(query_hash)
    except json.JSONDecodeError:
        return {}


class ABCTopologyPage(Page):
    @classmethod
    @abc.abstractmethod
    def visual_spec(cls):
        raise NotImplementedError

    def page(self) -> None:
        """Determines the hosts to be shown"""
        user.need_permission("general.parent_child_topology")
        self.show_topology()

    def show_topology(self) -> None:
        visual_spec = self.visual_spec()
        breadcrumb = make_topic_breadcrumb(
            mega_menu_registry.menu_monitoring(),
            PagetypeTopics.get_topic(visual_spec["topic"]).title(),
        )
        breadcrumb.append(make_current_page_breadcrumb_item(str(visual_spec["title"])))
        page_menu = PageMenu(breadcrumb=breadcrumb)
        self._extend_display_dropdown(page_menu, visual_spec["name"])
        make_header(html, str(visual_spec["title"]), breadcrumb, page_menu)
        self.show_topology_content()

    def show_topology_content(self) -> None:
        div_id = "node_visualization"
        html.div("", id_=div_id)

        search_frontend_settings = not request.has_var("topology_frontend_configuration")
        topology_configuration = _get_topology_configuration(
            self.visual_spec()["name"], self._get_overlays_config()
        )

        html.javascript(
            "topology_instance = new cmk.nodevis.TopologyVisualization(%s,%s);"
            % (json.dumps(div_id), json.dumps(topology_configuration.type))
        )

        html.javascript(
            "topology_instance.show_topology(%s,%s)"
            % (topology_configuration.frontend.to_json(), json.dumps(search_frontend_settings))
        )

    def _get_overlays_config(self) -> dict[str, Any]:
        return {}

    def _extend_display_dropdown(self, menu: PageMenu, page_name: str) -> None:
        _context, show_filters = get_topology_context_and_filters()
        display_dropdown = menu.get_dropdown_by_name("display", make_display_options_dropdown())
        display_dropdown.topics.insert(
            0,
            PageMenuTopic(
                title=_("Filter"),
                entries=[
                    PageMenuEntry(
                        title=_("Filter"),
                        icon_name="filters",
                        item=PageMenuSidePopup(
                            cmk.gui.visuals.render_filter_form(
                                info_list=["host", "service"],
                                context={f.ident: {} for f in show_filters if f.available()},
                                page_name=page_name,
                                reset_ajax_page="ajax_initial_topology_filters",
                            )
                        ),
                        name="filters",
                        is_shortcut=True,
                    ),
                ],
            ),
        )


@page_registry.register_page("parent_child_topology")
class ParentChildTopologyPage(ABCTopologyPage):
    @classmethod
    def visual_spec(cls) -> Visual:
        return {
            "owner": UserId.builtin(),
            "description": "",
            "hidebutton": False,
            "public": True,
            "topic": "overview",
            "title": _("Network topology"),
            "name": "parent_child_topology",
            "sort_index": 50,
            "is_show_more": False,
            "icon": "network_topology",
            "hidden": False,
            "single_infos": [],
            "context": {},
            "link_from": {},
            "add_context_to_title": True,
        }


@page_registry.register_page("ajax_initial_topology_filters")
class AjaxInitialTopologyFilters(ABCAjaxInitialFilters):
    def _get_context(self, page_name: str) -> dict:
        _view, show_filters = get_topology_context_and_filters()
        return {f.ident: {} for f in show_filters if f.available()}


@cmk.gui.pages.register("bi_map")
def _bi_map() -> None:
    aggr_name = request.var("aggr_name")
    layout_id = request.var("layout_id")
    title = _("BI visualization")
    breadcrumb = make_simple_page_breadcrumb(mega_menu_registry.menu_monitoring(), title)
    make_header(html, title, breadcrumb)
    div_id = "node_visualization"
    html.div("", id=div_id)
    html.javascript("node_instance = new cmk.nodevis.BIVisualization(%s);" % json.dumps(div_id))

    html.javascript(
        f"node_instance.show_aggregations({json.dumps([aggr_name])}, {json.dumps(layout_id)})"
    )


@page_registry.register_page("ajax_fetch_aggregation_data")
class AjaxFetchAggregationData(AjaxPage):
    def page(self) -> PageResult:
        aggregations_var = request.get_str_input_mandatory("aggregations", "[]")
        filter_names = json.loads(aggregations_var)

        forced_layout_id = request.var("layout_id")
        if forced_layout_id not in BILayoutManagement.get_all_bi_template_layouts():
            forced_layout_id = None

        bi_aggregation_filter = BIAggregationFilter([], [], [], filter_names, [], [])
        results = bi.BIManager().computer.compute_result_for_filter(bi_aggregation_filter)

        aggregation_info: dict[str, Any] = {"aggregations": {}}

        aggregation_layouts = BILayoutManagement.get_all_bi_aggregation_layouts()

        for bi_compiled_aggregation, node_result_bundles in results:
            for node_result_bundle in node_result_bundles:
                branch = node_result_bundle.instance
                aggr_name = branch.properties.title
                visual_mapper = NodeVisualizationBIDataMapper(
                    is_single_host_aggregation=len(branch.get_required_hosts()) == 1
                )
                hierarchy = visual_mapper.consume(node_result_bundle, 1, {})

                data: dict[str, Any] = {}
                data["type"] = "bi"
                data["hierarchy"] = hierarchy
                data["groups"] = bi_compiled_aggregation.groups.names
                data["data_timestamp"] = int(time.time())

                aggr_settings = bi_compiled_aggregation.aggregation_visualization
                layout: dict[str, Any] = {"config": {}}
                if forced_layout_id:
                    layout["enforced_id"] = aggr_name
                    layout["origin_type"] = "globally_enforced"
                    layout["origin_info"] = _("Globally enforced")
                    layout["use_layout"] = BILayoutManagement.load_bi_template_layout(
                        forced_layout_id
                    )
                else:
                    if aggr_name in aggregation_layouts:
                        layout["origin_type"] = "explicit"
                        layout["origin_info"] = _("Explicit set")
                        layout["explicit_id"] = aggr_name
                        layout["config"] = aggregation_layouts[aggr_name]
                        layout["config"]["ignore_rule_styles"] = True
                    else:
                        layout.update(self._get_template_based_layout_settings(aggr_settings))

                if "ignore_rule_styles" not in layout["config"]:
                    layout["config"]["ignore_rule_styles"] = aggr_settings.get(
                        "ignore_rule_styles", False
                    )
                if "line_config" not in layout["config"]:
                    layout["config"]["line_config"] = self._get_line_style_config(aggr_settings)

                data["layout"] = layout
                aggregation_info["aggregations"][aggr_name] = data

        return aggregation_info

    def _get_line_style_config(self, aggr_settings: dict[str, Any]) -> dict[str, Any]:
        line_style = aggr_settings.get("line_style", active_config.default_bi_layout["line_style"])
        if line_style == "default":
            line_style = active_config.default_bi_layout["line_style"]
        return {"style": line_style}

    def _get_template_based_layout_settings(self, aggr_settings: dict[str, Any]) -> dict[str, Any]:
        template_layout_id = aggr_settings.get("layout_id", "builtin_default")

        layout_settings: dict[str, Any] = {}
        if template_layout_id in BILayoutManagement.get_all_bi_template_layouts():
            # FIXME: This feature is currently inactive
            layout_settings["origin_type"] = "template"
            layout_settings["origin_info"] = _("Template: %s") % template_layout_id
            layout_settings["template_id"] = template_layout_id
            layout_settings["config"] = BILayoutManagement.load_bi_template_layout(
                template_layout_id
            )
        elif template_layout_id.startswith("builtin_"):
            # FIXME: this mapping is currently copied from the bi configuration valuespec
            #        BI refactoring required...
            builtin_mapping = {
                "builtin_default": _("global"),
                "builtin_force": _("force"),
                "builtin_radial": _("radial"),
                "builtin_hierarchy": _("hierarchy"),
            }
            layout_settings["origin_type"] = "default_template"
            layout_settings["origin_info"] = _("Default %s template") % builtin_mapping.get(
                template_layout_id, _("Unknown")
            )

            if template_layout_id == "builtin_default":
                template_layout_id = active_config.default_bi_layout["node_style"]
            layout_settings["default_id"] = template_layout_id[8:]
        else:
            # Any Unknown/Removed layout id gets the default template
            layout_settings["origin_type"] = "default_template"
            layout_settings["origin_info"] = _("Fallback template (%s): Unknown ID %s") % (
                active_config.default_bi_layout["node_style"][8:].title(),
                template_layout_id,
            )
            layout_settings["default_id"] = active_config.default_bi_layout["node_style"][8:]

        return layout_settings


TreeState = tuple[dict[str, Any], dict[str, Any], list]
BIAggrTreeState = tuple[dict[str, Any], Any, dict[str, Any], list]
BILeafTreeState = tuple[dict[str, Any], Any, dict[str, Any]]


# Creates are hierarchical dictionary which can be read by the NodeVisualization framework
class NodeVisualizationBIDataMapper:
    def __init__(self, is_single_host_aggregation=False):
        super().__init__()
        self._is_single_host_aggregation = is_single_host_aggregation
        self._siblings: dict[str, int] = {}

    def consume(
        self,
        node_result_bundle: NodeResultBundle,
        depth: int,
        parent_node: dict[str, Any],
    ) -> dict[str, Any]:
        instance = node_result_bundle.instance
        if isinstance(instance, BICompiledRule):
            node_data = self._get_node_data_for_rule(instance)
        else:
            node_data = self._get_node_data_for_leaf(instance)

        actual_result = node_result_bundle.actual_result
        if isinstance(instance, BICompiledRule) and instance.properties.icon:
            node_data["icon"] = theme.detect_icon_path(instance.properties.icon, prefix="icon_")

        node_id, aggr_path, aggr_name = self._compute_node_indices(node_data, parent_node)
        node_data["id"] = node_id
        node_data["aggr_path_id"] = aggr_path
        node_data["aggr_path_name"] = aggr_name

        node_data["state"] = actual_result.state

        node_data["in_downtime"] = actual_result.downtime_state > 0
        node_data["acknowledged"] = actual_result.acknowledged
        node_data["children"] = []
        for nested_bundle in node_result_bundle.nested_results:
            node_data["children"].append(self.consume(nested_bundle, depth + 1, node_data))
        return node_data

    def _compute_node_indices(
        self, node_data: dict[str, Any], parent_node: dict[str, Any]
    ) -> tuple[str, list[tuple[str, int]], list[tuple[str, int]]]:
        """Computes three unique identifiers for each node
        - one for the node itself
        - one for the aggregation path name (based on computed names)
        - one for the aggregation path id (based on aggr/rule ids)
        """
        aggr_path_id: list = []
        aggr_path_name: list = []

        if parent_node:
            p_aggr_path_id = parent_node.get("aggr_path_id")
            if isinstance(p_aggr_path_id, list):
                aggr_path_name.extend(p_aggr_path_id)
            p_aggr_path_name = parent_node.get("aggr_path_name")
            if isinstance(p_aggr_path_name, list):
                aggr_path_name.extend(p_aggr_path_name)

        parent_id = parent_node.get("id", "")
        if rule_id := node_data.get("rule_id"):
            rule_name = node_data["name"]
            rule_name_idx = self._get_sibling_index("rule_name", parent_id + rule_name)
            own_id = f"#{rule_name}#{rule_name_idx}"
            aggr_path_id.append(
                [rule_id["rule"], self._get_sibling_index("rule_id", parent_id + rule_id["rule"])]
            )
            aggr_path_name.append([rule_name, rule_name_idx])
        else:
            hostname = node_data["hostname"]
            if service := node_data.get("service"):
                own_id = f"{service}({self._get_sibling_index('service', parent_id + service)})"
            else:
                own_id = f"{hostname}({self._get_sibling_index('hostname', parent_id + hostname)})"
        node_id = parent_id + own_id

        return node_id, aggr_path_id, aggr_path_name

    def _get_sibling_index(self, domain: str, value: str) -> int:
        key = f"{domain}_{value}"
        self._siblings.setdefault(key, 0)
        self._siblings[key] += 1
        return self._siblings[key]

    def _get_node_data_for_rule(self, bi_compiled_rule: BICompiledRule) -> dict[str, Any]:
        node_data: dict[str, Any] = {
            "node_type": "bi_aggregator",
            "name": bi_compiled_rule.properties.title,
        }

        aggregation_function = bi_compiled_rule.aggregation_function
        function_data = BIAggregationFunctionSchema().dump(aggregation_function)
        aggr_func_gui = bi_valuespecs.bi_config_aggregation_function_registry[
            aggregation_function.kind()
        ]

        node_data["rule_id"] = {
            "pack": bi_compiled_rule.pack_id,
            "rule": bi_compiled_rule.id,
            "aggregation_function_description": str(aggr_func_gui(function_data)),
        }
        node_data["rule_layout_style"] = bi_compiled_rule.node_visualization
        return node_data

    def _get_node_data_for_leaf(self, bi_compiled_leaf: BICompiledLeaf) -> dict[str, Any]:
        node_data: dict[str, Any] = {"node_type": "bi_leaf", "hostname": bi_compiled_leaf.host_name}
        if not bi_compiled_leaf.service_description:
            node_data["name"] = bi_compiled_leaf.host_name
        else:
            node_data["service"] = bi_compiled_leaf.service_description
            if self._is_single_host_aggregation:
                node_data["name"] = bi_compiled_leaf.service_description
            else:
                node_data["name"] = " ".join(
                    [bi_compiled_leaf.host_name, bi_compiled_leaf.service_description]
                )
        return node_data


# Explicit Aggregations
@page_registry.register_page("ajax_save_bi_aggregation_layout")
class AjaxSaveBIAggregationLayout(AjaxPage):
    def page(self) -> PageResult:
        check_csrf_token()
        layout_var = request.get_str_input_mandatory("layout", "{}")
        layout_config = json.loads(layout_var)
        active_config.bi_layouts["aggregations"].update(layout_config)
        BILayoutManagement.save_layouts()
        return {}


@page_registry.register_page("ajax_delete_bi_aggregation_layout")
class AjaxDeleteBIAggregationLayout(AjaxPage):
    def page(self) -> PageResult:
        check_csrf_token()
        for_aggregation = request.var("aggregation_name")
        active_config.bi_layouts["aggregations"].pop(for_aggregation)
        BILayoutManagement.save_layouts()
        return {}


@page_registry.register_page("ajax_load_bi_aggregation_layout")
class AjaxLoadBIAggregationLayout(AjaxPage):
    def page(self) -> PageResult:
        aggregation_name = request.var("aggregation_name")
        return BILayoutManagement.load_bi_aggregation_layout(aggregation_name)


# Templates
@page_registry.register_page("ajax_save_bi_template_layout")
class AjaxSaveBITemplateLayout(AjaxPage):
    def page(self) -> PageResult:
        check_csrf_token()
        layout_var = request.get_str_input_mandatory("layout", "{}")
        layout_config = json.loads(layout_var)
        active_config.bi_layouts["templates"].update(layout_config)
        BILayoutManagement.save_layouts()
        return {}


@page_registry.register_page("ajax_delete_bi_template_layout")
class AjaxDeleteBITemplateLayout(AjaxPage):
    def page(self) -> PageResult:
        check_csrf_token()
        layout_id = request.var("layout_id")
        active_config.bi_layouts["templates"].pop(layout_id)
        BILayoutManagement.save_layouts()
        return {}


@page_registry.register_page("ajax_load_bi_template_layout")
class AjaxLoadBITemplateLayout(AjaxPage):
    def page(self) -> PageResult:
        layout_id = request.var("layout_id")
        return BILayoutManagement.load_bi_template_layout(layout_id)


@page_registry.register_page("ajax_get_all_bi_template_layouts")
class AjaxGetAllBITemplateLayouts(AjaxPage):
    def page(self) -> PageResult:
        return BILayoutManagement.get_all_bi_template_layouts()


@page_registry.register_page("ajax_fetch_topology")
class AjaxFetchTopology(AjaxPage):
    def page(self) -> PageResult:
        topology_configuration = _get_topology_configuration(
            request.get_str_input_mandatory("topology_type")
        )
        if request.has_var("delete_topology_configuration"):
            _delete_topology_configuration(topology_configuration)
            topology_configuration.frontend = TopologyFrontendConfiguration()
        if request.has_var("save_topology_configuration"):
            _save_topology_configuration(topology_configuration)
        topology = self._topology_instance_factory(topology_configuration)
        meshes = topology.compute()
        topology_info: dict[str, Any] = {
            "topology_meshes": {},
            "topology_chunks": {},
            "headline": topology.title(),
            "errors": topology.errors(),
            "frontend_configuration": topology_configuration.frontend.get_json_export_object(),
        }

        # Convert mesh information into a node visualization compatible format
        for mesh in meshes:
            if not mesh:
                continue
            topology_info["topology_chunks"][
                topology.get_mesh_root(mesh)
            ] = topology.generate_mesh_configuration(mesh)

        return topology_info

    def _topology_instance_factory(
        self, topology_configuration: TopologyConfiguration
    ) -> "Topology":
        topology_class = topology_registry.get(topology_configuration.type)
        if topology_class is None:
            raise MKGeneralException("Unknown topology %s" % topology_configuration.type)
        return topology_class(topology_configuration)


class Topology:
    def __init__(self, topology_settings: TopologyConfiguration) -> None:
        self._settings = topology_settings
        self._hostnames_from_filters = _get_hostnames_for_query(self._settings)

        # Hosts with complete data
        self._known_nodes: dict[str, Any] = {}

        # Child/parent hosts at the depth boundary
        self._border_hosts: set[HostName] = set()

        self._errors: list[str] = []
        self._meshes: Meshes = []

        # Node depth to next growth root
        self._depth_info: dict[str, int] = {}

        self._current_iteration = 0

    def title(self) -> str:
        raise NotImplementedError()

    def get_info_for_node(self, nodename: str, mesh: Mesh) -> dict[str, Any]:
        settings = {
            "name": nodename,  # Used as node text in GUI
            "id": nodename,
            "hostname": nodename,  # TODO: remove host reference
            "has_no_parents": self.is_root_node(nodename),
            "growth_root": self.is_growth_root(nodename),
            "growth_possible": self.may_grow(nodename, mesh),
            "growth_forbidden": self.growth_forbidden(nodename),
            "growth_continue": self.is_growth_continue(nodename),
            "data_timestamp": time.time(),
        }
        settings["custom_node_settings"] = self._settings.frontend.custom_node_settings.get(
            nodename
        )
        return settings

    def get_host_icon_image(self, hostname: HostName) -> str | None:
        if hostname not in self._known_nodes:
            return None
        return self._known_nodes[hostname].get("icon_image")

    def get_host_incoming(self, hostname: HostName) -> list[str]:
        if hostname not in self._known_nodes:
            return []
        return self._known_nodes[hostname]["incoming"]

    def get_host_outgoing(self, hostname: HostName) -> list[str]:
        if hostname not in self._known_nodes:
            return []
        return self._known_nodes[hostname]["outgoing"]

    def is_growth_root(self, hostname: HostName) -> bool:
        return hostname in self._settings.frontend.growth_root_nodes

    def is_growth_continue(self, hostname: HostName) -> bool:
        return hostname in self._settings.frontend.growth_continue_nodes

    def may_grow(self, hostname: HostName, mesh_hosts: Mesh) -> bool:
        known_host = self._known_nodes.get(hostname)
        if not known_host:
            return True

        unknown_hosts = set(known_host["incoming"] + known_host["outgoing"]) - set(mesh_hosts)
        return len(unknown_hosts) > 0

    def growth_forbidden(self, hostname: HostName) -> bool:
        return hostname in self._settings.frontend.growth_forbidden_nodes

    def add_error(self, error: str) -> None:
        self._errors.append(error)

    def errors(self) -> list[str]:
        return self._errors

    def compute(self) -> Meshes:
        if not self._settings.frontend.growth_root_nodes and not self._hostnames_from_filters:
            return []

        self._meshes = []
        try:
            self._grow()
        except MKGrowthExceeded as e:
            # Unexpected interuption, unable to display all nodes
            self.add_error(str(e))
        except MKGrowthInterruption:
            # Valid interruption, since the growth should stop when a given number of nodes is exceeded
            pass

        # Remove border hosts from meshes, since they do not provide complete data
        for mesh in self._meshes:
            mesh -= self._border_hosts

        meshes = self._postprocess_meshes(self._meshes)
        return meshes

    def _grow(self) -> None:
        self._fetch_root_nodes()
        self._growth_to_depth()
        self._growth_to_parents()
        self._growth_to_continue_nodes()

    def _check_mesh_size(self) -> None:
        total_nodes = sum(map(len, self._meshes))
        if total_nodes > self.max_nodes:
            raise MKGrowthExceeded(
                _("Maximum number of nodes exceeded %d/%d") % (total_nodes, self.max_nodes)
            )
        if total_nodes > self.growth_auto_max_nodes:
            raise MKGrowthInterruption(
                _("Growth interrupted %d/%d") % (total_nodes, self.growth_auto_max_nodes)
            )

    def get_mesh_root(self, mesh: set[str]) -> str:
        growth_roots = sorted(mesh.intersection(set(self._settings.frontend.growth_root_nodes)))
        if growth_roots:
            return growth_roots[0]
        return list(mesh)[0]

    def generate_mesh_configuration(self, mesh):
        # Pick root host
        mesh_root = self.get_mesh_root(mesh)
        mesh_info = self.get_info_for_node(mesh_root, mesh)

        sorted_children = sorted([x for x in mesh if x != mesh_root])
        mesh_info["children"] = list(self.get_info_for_node(x, mesh) for x in sorted_children)
        sorted_mesh = [mesh_root] + sorted_children

        mesh_links: list[dict[str, Any]] = []
        for hostname in sorted_mesh:
            # Incoming connections
            for child in self.get_host_incoming(hostname):
                if child in sorted_mesh:
                    mesh_links.append(
                        {"source": child, "target": hostname, "config": {"type": "default"}}
                    )

            # Outgoing connections
            for parent in self.get_host_outgoing(hostname):
                if parent in sorted_mesh:
                    mesh_links.append(
                        {"source": hostname, "target": parent, "config": {"type": "default"}}
                    )

        return {
            "layout": {
                "config": {
                    "line_config": {
                        "style": "straight",
                        "dashed": True,
                    }
                }
            },
            "type": "topology",
            "hierarchy": mesh_info,
            "links": mesh_links,
        }

    @property
    def max_nodes(self) -> int:
        return self._settings.filter.max_nodes

    @property
    def growth_auto_max_nodes(self) -> int:
        return self._settings.filter.growth_auto_max_nodes

    @property
    def mesh_depth(self) -> int:
        return self._settings.filter.mesh_depth

    def _fetch_root_nodes(self):
        self._compute_meshes(
            self._settings.frontend.growth_root_nodes | self._hostnames_from_filters
        )

    def _growth_to_depth(self) -> None:
        while self._current_iteration < self.mesh_depth:
            self._current_iteration += 1
            self._compute_meshes(self._border_hosts)

    def _growth_to_parents(self) -> None:
        while True:
            combined_mesh = set()
            for mesh in self._meshes:
                combined_mesh.update(mesh)

            combined_mesh -= self._border_hosts
            all_parents: set[str] = set()
            for node_name in combined_mesh:
                all_parents.update(set(self._known_nodes[node_name]["outgoing"]))

            missing_parents = all_parents - combined_mesh
            if not missing_parents:
                break

            self._compute_meshes(missing_parents)

    def _growth_to_continue_nodes(self) -> None:
        growth_continue_nodes = set(self._settings.frontend.growth_continue_nodes)
        while growth_continue_nodes:
            growth_nodes = growth_continue_nodes.intersection(set(self._known_nodes.keys()))
            if not growth_nodes:
                break

            border_hosts = set()
            for node_name in growth_nodes:
                border_hosts.update(set(self._known_nodes[node_name]["incoming"]))
                border_hosts.update(set(self._known_nodes[node_name]["outgoing"]))

            self._compute_meshes(border_hosts)
            growth_continue_nodes -= growth_nodes

    def _compute_meshes(self, hostnames: set[HostName]) -> None:
        new_hosts = self._query_data(hostnames)
        self._update_meshes(new_hosts)
        self._check_mesh_size()

    def _query_data(self, hostnames: set[HostName]) -> list[dict[str, Any]]:
        if not hostnames:
            return []

        new_hosts: list[dict[str, Any]] = []
        mandatory_keys = {"name", "outgoing", "incoming"}
        for host_data in self._fetch_data_for_hosts(hostnames):
            if len(mandatory_keys - set(host_data.keys())) > 0:
                raise MKGeneralException(
                    _("Missing mandatory topology keys: %r")
                    % (mandatory_keys - set(host_data.keys()))
                )
            # Mandatory keys in host_data: name, outgoing, incoming
            new_hosts.append(host_data)
        return new_hosts

    def _postprocess_meshes(self, meshes: Meshes) -> Meshes:
        return meshes

    def _fetch_data_for_hosts(self, hostnames: set[HostName]) -> list[dict]:
        raise NotImplementedError()

    def is_root_node(self, hostname: HostName) -> bool:
        return len(self._known_nodes[hostname]["outgoing"]) == 0

    def is_border_host(self, hostname: HostName) -> bool:
        return hostname in self._border_hosts

    def _update_meshes(self, new_hosts: list[dict[HostName, Any]]) -> None:
        # Data flow is child->parent
        # Incoming data comes from child
        # Outgoing data goes to parent
        self._border_hosts = set()

        # Update known hosts
        for new_host in new_hosts:
            new_host["mesh_depth"] = self._current_iteration
            hostname = new_host["name"]
            self._known_nodes[hostname] = new_host

        # Update meshes and border hosts
        new_meshes = []
        for new_host in new_hosts:
            hostname = new_host["name"]
            known_mesh_hosts = {hostname}

            adjacent_hosts = new_host["outgoing"] + new_host["incoming"]
            known_mesh_hosts.update(x for x in adjacent_hosts if x in self._known_nodes)
            if not self.growth_forbidden(hostname):
                self._border_hosts.update(x for x in adjacent_hosts if x not in self._known_nodes)
            new_meshes.append(known_mesh_hosts)

        self._integrate_new_meshes(new_meshes)

    def _integrate_new_meshes(self, new_meshes: list[set[HostName]]) -> None:
        """Combines meshes with identical items"""
        self._meshes.extend(new_meshes)
        all_hosts = set(itertools.chain.from_iterable(self._meshes))
        for hostname in all_hosts:
            common_meshes = [x for x in self._meshes if hostname in x]
            for mesh in common_meshes:
                self._meshes.remove(mesh)

            self._meshes.append(set(itertools.chain.from_iterable(common_meshes)))

    def _update_depth_information(self, meshes: Meshes) -> None:
        for mesh_hosts in meshes:
            self._update_depth_of_mesh(mesh_hosts)

    def _update_depth_of_mesh(self, mesh_hosts: Mesh) -> None:
        for hostname in list(mesh_hosts):
            if hostname in self._depth_info:
                continue
            self._depth_info[hostname] = self._current_iteration


class TopologyRegistry(cmk.utils.plugin_registry.Registry[type[Topology]]):
    def plugin_name(self, instance):
        return instance.ident()


topology_registry = TopologyRegistry()


class ParentChildNetworkTopology(Topology):
    _topology_site_node_type = "topology_site"
    """ Generates parent/child topology view """

    @classmethod
    def ident(cls) -> str:
        return "parent_child_topology"

    def title(self) -> str:
        return _("Parent / Child topology")

    def get_mesh_root(self, mesh: set[str]) -> str:
        # The root of each parent/child chunk is the topology_site node
        for nodename in mesh:
            if self._known_nodes[nodename].get("node_type") == self._topology_site_node_type:
                return nodename
        return "unknown_root"

    def _fetch_data_for_hosts(self, hostnames: set[HostName]) -> list[dict]:
        hostname_filters = []
        if hostnames:
            for hostname in hostnames:
                hostname_filters.append("Filter: host_name = %s" % livestatus.lqencode(hostname))
            hostname_filters.append("Or: %d" % len(hostnames))

        try:
            sites.live().set_prepend_site(True)
            columns = [
                "name",
                "state",
                "alias",
                "icon_image",
                "parents",
                "childs",
                "has_been_checked",
            ]
            query_result = sites.live().query(
                "GET hosts\nColumns: %s\n%s" % (" ".join(columns), "\n".join(hostname_filters))
            )
        finally:
            sites.live().set_prepend_site(False)

        headers = ["site"] + columns
        response = [dict(zip(headers, x)) for x in query_result]
        # Postprocess data
        for entry in response:
            # Abstract parents/children relationship to children(incoming) / parents(outgoing)
            entry["outgoing"] = entry["parents"]
            entry["incoming"] = entry["childs"]

        return response

    def _postprocess_meshes(self, meshes: Meshes) -> Meshes:
        """Create a central node and add all monitoring sites as children"""

        central_node = {
            "name": "",
            "hostname": "Checkmk",
            "outgoing": [],
            "incoming": [],
            "node_type": "topology_center",
        }

        site_nodes: dict[str, Any] = {}
        for mesh in meshes:
            for node_name in mesh:
                site = self._known_nodes[node_name]["site"]
                site_node_name = _("Site %s") % site
                site_nodes.setdefault(
                    site_node_name,
                    {
                        "node_type": self._topology_site_node_type,
                        "outgoing": [central_node["name"]],
                        "incoming": [],
                    },
                )
                outgoing_nodes = self._known_nodes.get(node_name, {"outgoing": []})["outgoing"]
                # Attach this node to the site not if it has no parents or if none of its parents are visible in the current mesh
                if not outgoing_nodes or len(set(outgoing_nodes) - mesh) == len(outgoing_nodes):
                    site_nodes[site_node_name]["incoming"].append(node_name)

        central_node["incoming"] = list(site_nodes.keys())
        self._known_nodes[str(central_node["name"])] = central_node

        combinator_mesh = set(central_node["name"])
        for node_name, settings in site_nodes.items():
            self._known_nodes[node_name] = settings
            combinator_mesh.add(node_name)
            combinator_mesh.update(set(settings["incoming"]))

        meshes.append(combinator_mesh)
        self._integrate_new_meshes(meshes)

        return meshes

    def get_info_for_node(self, nodename: str, mesh: Mesh) -> dict[str, Any]:
        info = super().get_info_for_node(nodename, mesh)
        host_info = self._known_nodes[nodename]
        info.update(host_info)
        for key in ["childs", "parents"]:
            try:
                del info[key]
            except KeyError:
                pass

        if "node_type" not in info:
            info["node_type"] = "topology"

        info["state"] = self._map_host_state_to_service_state(info, host_info)

        if info["node_type"] == "topology_center":
            info["explicit_force_options"] = {"repulsion": -3000, "center_force": 200}
        elif info["node_type"] == "topology_site":
            info["explicit_force_options"] = {"repulsion": -100, "link_distance": 50}

        return info

    def _map_host_state_to_service_state(
        self, info: dict[str, Any], host_info: dict[str, Any]
    ) -> int:
        if info["node_type"] in ["topology_center", "topology_site"]:
            return 0
        if not host_info["has_been_checked"]:
            return -1
        if host_info["state"] == 0:
            return 0
        if host_info["state"] == 2:
            return 3
        return 2


topology_registry.register(ParentChildNetworkTopology)


multisite_builtin_views.update(
    {
        "topology_filters": {
            "browser_reload": 30,
            "column_headers": "pergroup",
            "datasource": "hosts",
            "description": _l(
                "Configures the number of available filters in the network topology view."
            ),
            "group_painters": [],
            "hidden": True,
            "hidebutton": True,
            "layout": "table",
            "mustsearch": False,
            "name": "topology_filters",
            "num_columns": 3,
            "owner": UserId.builtin(),
            "painters": [ColumnSpec(name="host_state")],
            "play_sounds": False,
            "public": True,
            "sorters": [],
            "title": _l("Topology filters"),
            "topic": "Topology",
            "user_sortable": True,
            "single_infos": [],
            "context": {
                "topology_max_nodes": {},
                "topology_mesh_depth": {},
                "hoststate": {},
                "hostalias": {},
                "siteopt": {},
                "hostregex": {},
                "hostgroups": {},
                "host_labels": {},
                "opthost_contactgroup": {},
                "host_tags": {},
            },
            "link_from": {},
            "icon": None,
            "add_context_to_title": True,
            "sort_index": 99,
            "is_show_more": False,
        },
        "bi_map_hover_host": {
            "browser_reload": 0,
            "column_headers": "pergroup",
            "datasource": "hosts",
            "description": _l("Host hover menu shown in BI visualization"),
            "hidden": True,
            "hidebutton": True,
            "group_painters": [],
            "icon": None,
            "layout": "dataset",
            "mobile": False,
            "mustsearch": False,
            "name": "bi_map_hover_host",
            "num_columns": 1,
            "owner": UserId.builtin(),
            "painters": [
                ColumnSpec(
                    name="host",
                    parameters=PainterParameters(color_choices=[]),
                    link_spec=VisualLinkSpec(type_name="views", name="hoststatus"),
                ),
                ColumnSpec(name="host_state"),
                ColumnSpec(name="host_plugin_output"),
            ],
            "play_sounds": False,
            "public": True,
            "single_infos": ["host"],
            "sorters": [],
            "title": _l("BI host details"),
            "user_sortable": True,
            "context": {},
            "link_from": {},
            "topic": "",
            "add_context_to_title": True,
            "sort_index": 99,
            "is_show_more": False,
        },
        "bi_map_hover_service": {
            "browser_reload": 0,
            "column_headers": "pergroup",
            "datasource": "services",
            "description": _l("Service hover menu shown in BI visualization"),
            "hidden": True,
            "hidebutton": True,
            "group_painters": [],
            "icon": None,
            "layout": "dataset",
            "mobile": False,
            "mustsearch": False,
            "name": "bi_map_hover_service",
            "num_columns": 1,
            "painters": [
                ColumnSpec(
                    name="host",
                    parameters=PainterParameters(color_choices=[]),
                    link_spec=VisualLinkSpec(type_name="views", name="hoststatus"),
                ),
                ColumnSpec(
                    name="service_description",
                    link_spec=VisualLinkSpec(type_name="views", name="service"),
                ),
                ColumnSpec(name="service_state"),
                ColumnSpec(name="host_check_age"),
                ColumnSpec(name="svc_acknowledged"),
                ColumnSpec(name="svc_in_downtime"),
            ],
            "play_sounds": False,
            "public": True,
            "single_infos": ["service", "host"],
            "sorters": [],
            "title": _l("BI service details"),
            "owner": UserId.builtin(),
            "user_sortable": True,
            "context": {},
            "link_from": {},
            "topic": "",
            "add_context_to_title": True,
            "sort_index": 99,
            "is_show_more": False,
        },
        "topology_hover_host": {
            "browser_reload": 0,
            "column_headers": "pergroup",
            "datasource": "hosts",
            "description": _l("Host hover menu shown in topolgoy visualization"),
            "hidden": True,
            "hidebutton": True,
            "group_painters": [],
            "icon": None,
            "layout": "dataset",
            "mobile": False,
            "mustsearch": False,
            "name": "topology_hover_host",
            "num_columns": 1,
            "owner": UserId.builtin(),
            "painters": [
                ColumnSpec(
                    name="host",
                    parameters=PainterParameters(color_choices=[]),
                    link_spec=VisualLinkSpec(type_name="views", name="hoststatus"),
                ),
                ColumnSpec(name="host_state"),
                ColumnSpec(name="host_plugin_output"),
                ColumnSpec(name="host_parents"),
                ColumnSpec(name="host_childs"),
            ],
            "play_sounds": False,
            "public": True,
            "single_infos": ["host"],
            "sorters": [],
            "title": _l("Toplogy host details"),
            "user_sortable": True,
            "context": {},
            "link_from": {},
            "topic": "",
            "add_context_to_title": True,
            "sort_index": 99,
            "is_show_more": False,
        },
    }
)
