#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import itertools
import json
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Literal, Optional, Set, Tuple, Type, TypedDict

import livestatus
from livestatus import SiteId

from cmk.utils.bi.bi_aggregation_functions import BIAggregationFunctionSchema
from cmk.utils.bi.bi_computer import BIAggregationFilter
from cmk.utils.bi.bi_lib import NodeResultBundle
from cmk.utils.bi.bi_trees import BICompiledLeaf, BICompiledRule
from cmk.utils.site import omd_site
from cmk.utils.type_defs import HostName

import cmk.gui.bi as bi
import cmk.gui.visuals
from cmk.gui import sites
from cmk.gui.breadcrumb import (
    make_current_page_breadcrumb_item,
    make_simple_page_breadcrumb,
    make_topic_breadcrumb,
)
from cmk.gui.config import active_config
from cmk.gui.exceptions import MKGeneralException
from cmk.gui.htmllib.header import make_header
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _
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
from cmk.gui.pages import AjaxPage, AjaxPageResult, Page, page_registry, PageResult
from cmk.gui.pagetypes import PagetypeTopics
from cmk.gui.plugins.views.utils import get_permitted_views
from cmk.gui.plugins.visuals.node_vis import FilterTopologyMaxNodes, FilterTopologyMeshDepth
from cmk.gui.plugins.visuals.utils import Filter, get_livestatus_filter_headers
from cmk.gui.plugins.wato import bi_valuespecs
from cmk.gui.type_defs import VisualContext
from cmk.gui.utils.csrf_token import check_csrf_token
from cmk.gui.utils.theme import theme
from cmk.gui.views import ABCAjaxInitialFilters, View

Mesh = Set[HostName]
Meshes = List[Mesh]


class MKGrowthExceeded(MKGeneralException):
    pass


class MKGrowthInterruption(MKGeneralException):
    pass


@dataclass
class TopologySettings:
    growth_root_nodes: Set[HostName] = field(default_factory=set)  # Growth starts from here
    growth_forbidden_nodes: Set[HostName] = field(default_factory=set)  # Growth stops here
    growth_continue_nodes: Set[HostName] = field(default_factory=set)  # Growth continues here
    display_mode: str = "parent_child"
    max_nodes: int = FilterTopologyMaxNodes().range_config.default
    mesh_depth: int = FilterTopologyMeshDepth().range_config.default
    growth_auto_max_nodes: int = 400
    overlays_config: Dict[str, Dict[str, Any]] = field(default_factory=dict)


class TopologySettingsJSON(TopologySettings):
    @classmethod
    def from_json(cls, serialized: Dict[str, Any]) -> "TopologySettingsJSON":
        for key in ["growth_root_nodes", "growth_forbidden_nodes", "growth_continue_nodes"]:
            serialized[key] = {HostName(hn) for hn in serialized[key]}
        return cls(**serialized)

    def to_json(self) -> Dict[str, Any]:
        value = asdict(self)
        for key in ["growth_root_nodes", "growth_forbidden_nodes", "growth_continue_nodes"]:
            value[key] = list(map(str, value[key]))
        return value


@page_registry.register_page("parent_child_topology")
class ParentChildTopologyPage(Page):
    @classmethod
    def visual_spec(cls):
        return {
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

    def page(self) -> PageResult:
        """Determines the hosts to be shown"""
        user.need_permission("general.parent_child_topology")

        topology_settings = TopologySettings()
        if request.var("filled_in"):
            # Parameters from the check_mk filters
            self._update_topology_settings_with_context(topology_settings)
        elif request.var("host_name"):
            # Explicit host_name. Used by icon linking to Topology
            topology_settings.growth_root_nodes = {
                HostName(html.request.get_str_input_mandatory("host_name"))
            }
        else:
            # Default page without further context
            topology_settings.growth_root_nodes = self._get_default_view_hostnames(
                topology_settings.growth_auto_max_nodes
            )

        if request.has_var("topology_settings"):
            # These parameters are usually generated within javascript through user interactions
            try:
                settings_from_var = json.loads(request.get_str_input_mandatory("topology_settings"))
                for key, value in settings_from_var.items():
                    setattr(topology_settings, key, value)
            except (TypeError, ValueError):
                raise MKGeneralException(_("Invalid topology_settings %r") % topology_settings)

        self.show_topology(topology_settings)

    def _get_default_view_hostnames(self, max_nodes: int) -> Set[HostName]:
        """Returns all hosts without any parents"""
        query = "GET hosts\nColumns: name\nFilter: parents ="
        site = request.var("site")
        with sites.prepend_site(), sites.only_sites(None if site is None else SiteId(site)):
            hosts = [(x[0], x[1]) for x in sites.live().query(query)]

        # If no explicit site is set and the number of initially displayed hosts
        # exceeds the auto growth range, only the hosts of the master site are shown
        if len(hosts) > max_nodes:
            hostnames = {HostName(x[1]) for x in hosts if x[0] == omd_site()}
        else:
            hostnames = {HostName(x[1]) for x in hosts}

        return hostnames

    def _update_topology_settings_with_context(self, topology_settings: TopologySettings) -> None:
        view, filters = get_topology_view_and_filters()
        context = cmk.gui.visuals.active_context_from_request(
            view.datasource.infos, view.spec["context"]
        )
        topology_settings.growth_root_nodes = self._get_hostnames_from_filters(context, filters)

        max_nodes_range_config = FilterTopologyMaxNodes().range_config
        if value := context.get(max_nodes_range_config.column, {}).get(
            max_nodes_range_config.column
        ):
            topology_settings.max_nodes = int(value)

        mesh_depth_range_config = FilterTopologyMeshDepth().range_config
        if value := context.get(mesh_depth_range_config.column, {}).get(
            mesh_depth_range_config.column
        ):
            topology_settings.mesh_depth = int(value)

    def _get_hostnames_from_filters(
        self, context: VisualContext, filters: List[Filter]
    ) -> Set[HostName]:
        filter_headers = "".join(get_livestatus_filter_headers(context, filters))

        query = "GET hosts\nColumns: name"
        if filter_headers:
            query += "\n%s" % filter_headers

        site = request.var("site")
        with sites.only_sites(None if site is None else SiteId(site)):
            return {HostName(x) for x in sites.live().query_column_unique(query)}

    def show_topology(self, topology_settings: TopologySettings) -> None:
        visual_spec = ParentChildTopologyPage.visual_spec()
        breadcrumb = make_topic_breadcrumb(
            mega_menu_registry.menu_monitoring(),
            PagetypeTopics.get_topic(visual_spec["topic"]).title(),
        )
        breadcrumb.append(make_current_page_breadcrumb_item(visual_spec["title"]))
        page_menu = PageMenu(breadcrumb=breadcrumb)
        self._extend_display_dropdown(page_menu, visual_spec["name"])
        make_header(html, visual_spec["title"], breadcrumb, page_menu)
        self.show_topology_content(topology_settings=topology_settings)

    def show_topology_content(self, topology_settings: TopologySettings) -> None:
        div_id = "node_visualization"
        html.div("", id_=div_id)
        html.javascript(
            "topology_instance = new cmk.node_visualization.TopologyVisualization(%s);"
            % json.dumps(div_id)
        )

        html.javascript(
            "topology_instance.show_topology(%s)"
            % json.dumps(TopologySettingsJSON(**asdict(topology_settings)).to_json())
        )

    def _get_overlays_config(self) -> List:
        return []

    def _extend_display_dropdown(self, menu: PageMenu, page_name: str) -> None:
        _view, show_filters = get_topology_view_and_filters()
        display_dropdown = menu.get_dropdown_by_name("display", make_display_options_dropdown())
        display_dropdown.topics.insert(
            0,
            PageMenuTopic(
                title=_("Filter"),
                entries=[
                    PageMenuEntry(
                        title=_("Filter"),
                        icon_name="filter",
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


def get_topology_view_and_filters() -> Tuple[View, List[Filter]]:
    view_name = "topology_filters"

    view_spec = get_permitted_views()[view_name]
    view = View(view_name, view_spec, view_spec.get("context", {}))
    filters = cmk.gui.visuals.filters_of_visual(
        view.spec, view.datasource.infos, link_filters=view.datasource.link_filters
    )
    show_filters = cmk.gui.visuals.visible_filters_of_visual(view.spec, filters)
    return view, show_filters


@page_registry.register_page("ajax_initial_topology_filters")
class AjaxInitialTopologyFilters(ABCAjaxInitialFilters):
    def _get_context(self, page_name: str) -> Dict:
        _view, show_filters = get_topology_view_and_filters()
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
    html.javascript(
        "node_instance = new cmk.node_visualization.BIVisualization(%s);" % json.dumps(div_id)
    )

    html.javascript(
        "node_instance.show_aggregations(%s, %s)" % (json.dumps([aggr_name]), json.dumps(layout_id))
    )


@page_registry.register_page("ajax_fetch_aggregation_data")
class AjaxFetchAggregationData(AjaxPage):
    def page(self) -> AjaxPageResult:
        aggregations_var = request.get_str_input_mandatory("aggregations", "[]")
        filter_names = json.loads(aggregations_var)

        forced_layout_id = request.var("layout_id")
        if forced_layout_id not in BILayoutManagement.get_all_bi_template_layouts():
            forced_layout_id = None

        bi_aggregation_filter = BIAggregationFilter([], [], [], filter_names, [], [])
        results = bi.get_cached_bi_manager().computer.compute_result_for_filter(
            bi_aggregation_filter
        )

        aggregation_info: Dict[str, Any] = {"aggregations": {}}

        aggregation_layouts = BILayoutManagement.get_all_bi_aggregation_layouts()

        for bi_compiled_aggregation, node_result_bundles in results:
            for node_result_bundle in node_result_bundles:
                branch = node_result_bundle.instance
                aggr_name = branch.properties.title
                visual_mapper = NodeVisualizationBIDataMapper(
                    is_single_host_aggregation=len(branch.get_required_hosts()) == 1
                )
                hierarchy = visual_mapper.consume(node_result_bundle)

                data: Dict[str, Any] = {}
                data["type"] = "bi"
                data["hierarchy"] = hierarchy
                data["groups"] = bi_compiled_aggregation.groups.names
                data["data_timestamp"] = int(time.time())

                aggr_settings = bi_compiled_aggregation.aggregation_visualization
                layout: Dict[str, Any] = {"config": {}}
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

    def _get_line_style_config(self, aggr_settings: Dict[str, Any]) -> Dict[str, Any]:
        line_style = aggr_settings.get("line_style", active_config.default_bi_layout["line_style"])
        if line_style == "default":
            line_style = active_config.default_bi_layout["line_style"]
        return {"style": line_style}

    def _get_template_based_layout_settings(self, aggr_settings: Dict[str, Any]) -> Dict[str, Any]:
        template_layout_id = aggr_settings.get("layout_id", "builtin_default")

        layout_settings: Dict[str, Any] = {}
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


TreeState = Tuple[Dict[str, Any], Dict[str, Any], List]
BIAggrTreeState = Tuple[Dict[str, Any], Any, Dict[str, Any], List]
BILeafTreeState = Tuple[Dict[str, Any], Any, Dict[str, Any]]


# Creates are hierarchical dictionary which can be read by the NodeVisualization framework
class NodeVisualizationBIDataMapper:
    def __init__(self, is_single_host_aggregation=False):
        super().__init__()
        self._is_single_host_aggregation = is_single_host_aggregation

    def consume(self, node_result_bundle: NodeResultBundle, depth: int = 1) -> Dict[str, Any]:
        instance = node_result_bundle.instance
        if isinstance(instance, BICompiledRule):
            node_data = self._get_node_data_for_rule(instance)
        else:
            node_data = self._get_node_data_for_leaf(instance)

        actual_result = node_result_bundle.actual_result
        if isinstance(instance, BICompiledRule) and instance.properties.icon:
            node_data["icon"] = theme.detect_icon_path(instance.properties.icon, prefix="icon_")

        node_data["state"] = actual_result.state

        node_data["in_downtime"] = actual_result.downtime_state > 0
        node_data["acknowledged"] = actual_result.acknowledged
        node_data["children"] = []
        for nested_bundle in node_result_bundle.nested_results:
            node_data["children"].append(self.consume(nested_bundle, depth=depth + 1))
        return node_data

    def _get_node_data_for_rule(self, bi_compiled_rule: BICompiledRule) -> Dict[str, Any]:
        node_data: Dict[str, Any] = {
            "node_type": "bi_aggregator",
            "name": bi_compiled_rule.properties.title,
        }

        aggregation_function = bi_compiled_rule.aggregation_function
        function_data = BIAggregationFunctionSchema().dump(aggregation_function)
        aggr_func_gui = bi_valuespecs.bi_config_aggregation_function_registry[
            aggregation_function.type()
        ]

        node_data["rule_id"] = {
            "pack": bi_compiled_rule.pack_id,
            "rule": bi_compiled_rule.id,
            "aggregation_function_description": str(aggr_func_gui(function_data)),
        }
        node_data["rule_layout_style"] = bi_compiled_rule.node_visualization
        return node_data

    def _get_node_data_for_leaf(self, bi_compiled_leaf: BICompiledLeaf) -> Dict[str, Any]:
        node_data: Dict[str, Any] = {"node_type": "bi_leaf", "hostname": bi_compiled_leaf.host_name}
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
    def page(self) -> AjaxPageResult:
        check_csrf_token()
        layout_var = request.get_str_input_mandatory("layout", "{}")
        layout_config = json.loads(layout_var)
        active_config.bi_layouts["aggregations"].update(layout_config)
        BILayoutManagement.save_layouts()
        return {}


@page_registry.register_page("ajax_delete_bi_aggregation_layout")
class AjaxDeleteBIAggregationLayout(AjaxPage):
    def page(self) -> AjaxPageResult:
        check_csrf_token()
        for_aggregation = request.var("aggregation_name")
        active_config.bi_layouts["aggregations"].pop(for_aggregation)
        BILayoutManagement.save_layouts()
        return {}


@page_registry.register_page("ajax_load_bi_aggregation_layout")
class AjaxLoadBIAggregationLayout(AjaxPage):
    def page(self) -> AjaxPageResult:
        aggregation_name = request.var("aggregation_name")
        return BILayoutManagement.load_bi_aggregation_layout(aggregation_name)


# Templates
@page_registry.register_page("ajax_save_bi_template_layout")
class AjaxSaveBITemplateLayout(AjaxPage):
    def page(self) -> AjaxPageResult:
        check_csrf_token()
        layout_var = request.get_str_input_mandatory("layout", "{}")
        layout_config = json.loads(layout_var)
        active_config.bi_layouts["templates"].update(layout_config)
        BILayoutManagement.save_layouts()
        return {}


@page_registry.register_page("ajax_delete_bi_template_layout")
class AjaxDeleteBITemplateLayout(AjaxPage):
    def page(self) -> AjaxPageResult:
        check_csrf_token()
        layout_id = request.var("layout_id")
        active_config.bi_layouts["templates"].pop(layout_id)
        BILayoutManagement.save_layouts()
        return {}


@page_registry.register_page("ajax_load_bi_template_layout")
class AjaxLoadBITemplateLayout(AjaxPage):
    def page(self) -> AjaxPageResult:
        layout_id = request.var("layout_id")
        return BILayoutManagement.load_bi_template_layout(layout_id)


@page_registry.register_page("ajax_get_all_bi_template_layouts")
class AjaxGetAllBITemplateLayouts(AjaxPage):
    def page(self) -> AjaxPageResult:
        return BILayoutManagement.get_all_bi_template_layouts()


@page_registry.register_page("ajax_fetch_topology")
class AjaxFetchTopology(AjaxPage):
    def page(self) -> AjaxPageResult:
        # growth_root_nodes: a list of mandatory hostnames
        # mesh_depth: number of hops from growth root
        # growth_forbidden: block further traversal at the given nodes
        # growth_continue_nodes: expand these nodes, event if the depth has been reached

        topology_config_var = request.get_str_input_mandatory("topology_settings")
        try:
            topology_settings = TopologySettingsJSON.from_json(json.loads(topology_config_var))
        except (TypeError, ValueError):
            raise MKGeneralException(_("Invalid topology_config %r") % topology_config_var)

        topology = self._topology_instance_factory(topology_settings)
        meshes = topology.compute()
        topology_info: Dict[str, Any] = {
            "topology_meshes": {},
            "topology_chunks": {},
            "headline": topology.title(),
            "errors": topology.errors(),
            "max_nodes": topology.max_nodes,
            "mesh_depth": topology.mesh_depth,
        }

        # Convert mesh information into a node visualization compatible format
        for mesh in meshes:
            if not mesh:
                continue

            # Pick root host
            growth_roots = sorted(mesh.intersection(set(topology_settings.growth_root_nodes)))
            if growth_roots:
                mesh_root = growth_roots[0]
            else:
                mesh_root = list(mesh)[0]
            mesh_info = topology.get_info_for_host(mesh_root, mesh)

            sorted_children = sorted([x for x in mesh if x != mesh_root])
            mesh_info["children"] = list(
                topology.get_info_for_host(x, mesh) for x in sorted_children
            )
            sorted_mesh = [mesh_root] + sorted_children

            mesh_links = set()
            for idx, hostname in enumerate(sorted_mesh):
                # Incoming connections
                for child in topology.get_host_incoming(hostname):
                    if child in sorted_mesh:
                        mesh_links.add((sorted_mesh.index(child), idx))

                # Outgoing connections
                for parent in topology.get_host_outgoing(hostname):
                    if parent in sorted_mesh:
                        mesh_links.add((idx, sorted_mesh.index(parent)))

            topology_info["topology_chunks"][mesh_root] = {
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
                "links": list(mesh_links),
            }

        return topology_info

    def _topology_instance_factory(self, topology_settings: TopologySettings) -> "Topology":
        topology_class = topology_registry.get(topology_settings.display_mode)
        if topology_class is None:
            raise Exception("unknown topology")
        return topology_class(topology_settings)


class _MeshNode(TypedDict, total=False):
    name: HostName
    alias: str
    site: str
    hostname: HostName
    outgoing: List[HostName]
    incoming: List[HostName]
    # 2021-08-03: Not entirely sure, so if mypy complains,
    #             feel free to change it back to str
    node_type: Literal["topology", "topology_center", "topology_site"]
    mesh_depth: int
    icon_image: str
    state: int
    has_been_checked: bool

    has_no_parents: bool
    growth_root: bool
    growth_possible: bool
    growth_forbidden: bool
    growth_continue: bool
    children: List  # List["_MeshNode"]
    explicit_force_options: Dict[str, int]


class Topology:
    def __init__(self, topology_settings: TopologySettings) -> None:
        super().__init__()
        self._settings = topology_settings

        # Hosts with complete data
        self._known_hosts: Dict[HostName, _MeshNode] = {}

        # Child/parent hosts at the depth boundary
        self._border_hosts: Set[HostName] = set()

        self._errors: List[str] = []
        self._meshes: Meshes = []

        # Node depth to next growth root
        self._depth_info: Dict[str, int] = {}

        self._current_iteration = 0

    def title(self) -> str:
        raise NotImplementedError()

    def get_info_for_host(self, hostname: HostName, mesh: Mesh) -> _MeshNode:
        return {
            "name": hostname,  # Used as node text in GUI
            "hostname": hostname,
            "has_no_parents": self.is_root_node(hostname),
            "growth_root": self.is_growth_root(hostname),
            "growth_possible": self.may_grow(hostname, mesh),
            "growth_forbidden": self.growth_forbidden(hostname),
            "growth_continue": self.is_growth_continue(hostname),
        }

    def get_host_icon_image(self, hostname: HostName) -> Optional[str]:
        if hostname not in self._known_hosts:
            return None
        return self._known_hosts[hostname].get("icon_image")

    def get_host_incoming(self, hostname: HostName) -> List[HostName]:
        if hostname not in self._known_hosts:
            return []
        return self._known_hosts[hostname]["incoming"]

    def get_host_outgoing(self, hostname: HostName) -> List[HostName]:
        if hostname not in self._known_hosts:
            return []
        return self._known_hosts[hostname]["outgoing"]

    def is_growth_root(self, hostname: HostName) -> bool:
        return hostname in self._settings.growth_root_nodes

    def is_growth_continue(self, hostname: HostName) -> bool:
        return hostname in self._settings.growth_continue_nodes

    def may_grow(self, hostname: HostName, mesh_hosts: Mesh) -> bool:
        known_host = self._known_hosts.get(hostname)
        if not known_host:
            return True

        unknown_hosts = set(known_host["incoming"] + known_host["outgoing"]) - set(mesh_hosts)
        return len(unknown_hosts) > 0

    def growth_forbidden(self, hostname: HostName) -> bool:
        return hostname in self._settings.growth_forbidden_nodes

    def add_error(self, error: str) -> None:
        self._errors.append(error)

    def errors(self) -> List[str]:
        return self._errors

    def compute(self) -> Meshes:
        if not self._settings.growth_root_nodes:
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

    @property
    def max_nodes(self) -> int:
        return self._settings.max_nodes

    @property
    def growth_auto_max_nodes(self) -> int:
        return self._settings.growth_auto_max_nodes

    @property
    def mesh_depth(self) -> int:
        return self._settings.mesh_depth

    def _fetch_root_nodes(self):
        self._compute_meshes(self._settings.growth_root_nodes)

    def _growth_to_depth(self) -> None:
        while self._current_iteration < self.mesh_depth:
            self._current_iteration += 1
            self._compute_meshes(self._border_hosts)

    def _growth_to_parents(self) -> None:
        while True:
            combined_mesh: Set[HostName] = set()
            for mesh in self._meshes:
                combined_mesh.update(mesh)

            combined_mesh -= self._border_hosts
            all_parents: Set[HostName] = set()
            for node_name in combined_mesh:
                all_parents.update(set(self._known_hosts[node_name]["outgoing"]))

            missing_parents: Set[HostName] = all_parents - combined_mesh
            if not missing_parents:
                break

            self._compute_meshes(missing_parents)

    def _growth_to_continue_nodes(self) -> None:
        growth_continue_nodes = set(self._settings.growth_continue_nodes)
        while growth_continue_nodes:
            growth_nodes = growth_continue_nodes.intersection(set(self._known_hosts.keys()))
            if not growth_nodes:
                break

            border_hosts: Set[HostName] = set()
            for node_name in growth_nodes:
                border_hosts.update(set(self._known_hosts[node_name]["incoming"]))
                border_hosts.update(set(self._known_hosts[node_name]["outgoing"]))

            self._compute_meshes(border_hosts)
            growth_continue_nodes -= growth_nodes

    def _compute_meshes(self, hostnames: Set[HostName]) -> None:
        new_hosts = self._query_data(hostnames)
        self._update_meshes(new_hosts)
        self._check_mesh_size()

    def _query_data(self, hostnames: Set[HostName]) -> List[_MeshNode]:
        if not hostnames:
            return []

        new_hosts = []
        mandatory_keys = {"name", "outgoing", "incoming"}
        for host_data in self._fetch_data_for_hosts(hostnames):
            missing_keys = mandatory_keys - set(host_data)
            if missing_keys:
                raise MKGeneralException(_("Missing mandatory topology keys: %r") % missing_keys)
            new_hosts.append(host_data)
        return new_hosts

    def _postprocess_meshes(self, meshes: Meshes) -> Meshes:
        return meshes

    def _fetch_data_for_hosts(self, hostnames: Set[HostName]) -> List[_MeshNode]:
        raise NotImplementedError()

    def is_root_node(self, hostname: HostName) -> bool:
        return len(self._known_hosts[hostname]["outgoing"]) == 0

    def is_border_host(self, hostname: HostName) -> bool:
        return hostname in self._border_hosts

    def _update_meshes(self, new_hosts: List[_MeshNode]):
        # Data flow is child->parent
        # Incoming data comes from child
        # Outgoing data goes to parent
        self._border_hosts = set()

        # Update known hosts
        for new_host in new_hosts:
            new_host["mesh_depth"] = self._current_iteration
            hostname = new_host["name"]
            self._known_hosts[hostname] = new_host

        # Update meshes and border hosts
        new_meshes = []
        for new_host in new_hosts:
            hostname = new_host["name"]
            known_mesh_hosts = set([hostname])

            adjacent_hosts = new_host["outgoing"] + new_host["incoming"]
            known_mesh_hosts.update(x for x in adjacent_hosts if x in self._known_hosts)
            if not self.growth_forbidden(hostname):
                self._border_hosts.update(x for x in adjacent_hosts if x not in self._known_hosts)
            new_meshes.append(known_mesh_hosts)

        self._integrate_new_meshes(new_meshes)

    def _integrate_new_meshes(self, new_meshes: List[Set[HostName]]) -> None:
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


class TopologyRegistry(cmk.utils.plugin_registry.Registry[Type[Topology]]):
    def plugin_name(self, instance):
        return instance.ident()


topology_registry = TopologyRegistry()


class ParentChildNetworkTopology(Topology):
    """Generates parent/child topology view"""

    @classmethod
    def ident(cls) -> str:
        return "parent_child"

    def title(self) -> str:
        return _("Parent / Child topology")

    def _fetch_data_for_hosts(self, hostnames: Set[HostName]) -> List[_MeshNode]:
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

        return [
            {
                "site": str(x[0]),
                "name": HostName(str(x[1])),
                "state": int(x[2]),
                "alias": str(x[3]),
                "icon_image": str(x[4]),
                "outgoing": [HostName(str(i)) for i in x[5]],
                "incoming": [HostName(str(i)) for i in x[6]],
                "has_been_checked": bool(x[7]),
            }
            for x in query_result
        ]

    def _postprocess_meshes(self, meshes: Meshes) -> Meshes:
        """Create a central node and add all monitoring sites as childs"""

        central_node: _MeshNode = {
            "name": HostName(""),
            "hostname": HostName("Checkmk"),
            "outgoing": [],
            "incoming": [],
            "node_type": "topology_center",
        }

        site_nodes: Dict[HostName, _MeshNode] = {}
        for mesh in meshes:
            for node_name in mesh:
                site = self._known_hosts[node_name]["site"]
                site_node_name = HostName(_("Site %s") % site)
                site_nodes.setdefault(
                    site_node_name,
                    {
                        "node_type": "topology_site",
                        "outgoing": [central_node["name"]],
                        "incoming": [],
                    },
                )
                outgoing_nodes = self._known_hosts.get(node_name, {"outgoing": []})["outgoing"]
                # Only attach this node to the site if it has no parents that are visible
                # in the current mesh
                if not mesh.intersection(outgoing_nodes):
                    site_nodes[site_node_name]["incoming"].append(node_name)

        central_node["incoming"] = list(site_nodes.keys())
        self._known_hosts[central_node["name"]] = central_node

        combinator_mesh: Set[HostName] = set()
        for node_name, settings in site_nodes.items():
            self._known_hosts[node_name] = settings
            combinator_mesh.add(node_name)
            combinator_mesh.update(set(settings["incoming"]))

        meshes.append(combinator_mesh)
        self._integrate_new_meshes(meshes)

        return meshes

    def get_info_for_host(self, hostname: HostName, mesh: Mesh) -> _MeshNode:
        info = super().get_info_for_host(hostname, mesh)
        host_info = self._known_hosts[hostname]
        info.update(host_info)

        if "node_type" not in info:
            info["node_type"] = "topology"

        info["state"] = self._map_host_state_to_service_state(info)

        if info["node_type"] == "topology_center":
            info["explicit_force_options"] = {"repulsion": -3000, "center_force": 200}
        elif info["node_type"] == "topology_site":
            info["explicit_force_options"] = {"repulsion": -100, "link_distance": 50}

        return info

    def _map_host_state_to_service_state(self, info: _MeshNode) -> int:
        if info["node_type"] in ["topology_center", "topology_site"]:
            return 0
        if not info["has_been_checked"]:
            return -1
        if info["state"] == 0:
            return 0
        if info["state"] == 2:
            return 3
        return 2


topology_registry.register(ParentChildNetworkTopology)
