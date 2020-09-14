#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import time
from typing import List, Optional, Tuple, Dict, Any, Union, Set, Type
from pathlib import Path

import livestatus
import cmk.utils.store as store
from cmk.utils.type_defs import HostName

from cmk.gui import sites
from cmk.gui.globals import html
from cmk.gui.i18n import _
import cmk.gui.watolib as watolib
import cmk.gui.bi as bi
import cmk.gui.config as config
from cmk.gui.pages import (
    page_registry,
    Page,
    PageResult,
    AjaxPage,
    AjaxPageResult,
)

from cmk.gui.plugins.views.utils import (
    get_permitted_views,)
from cmk.gui.views import View

import cmk.gui.visuals
from cmk.gui.exceptions import MKGeneralException

from cmk.gui.plugins.visuals.utils import Filter
from cmk.gui.type_defs import FilterHeaders
from cmk.gui.breadcrumb import make_simple_page_breadcrumb
from cmk.gui.main_menu import mega_menu_registry

TopologyConfig = Dict[str, Any]
Mesh = Set[str]
Meshes = List[Mesh]


class MKGrowthExceeded(MKGeneralException):
    pass


class MKGrowthInterruption(MKGeneralException):
    pass


@page_registry.register_page("parent_child_topology")
class ParentChildTopologyPage(Page):
    def page(self) -> PageResult:
        """ Determines the hosts to be shown """
        growth_auto_max_nodes = None

        # Jump this number of hops from the root node(s)
        mesh_depth = html.request.get_integer_input_mandatory("topology_mesh_depth", 0)

        # Maximum number of nodes allowed to render
        max_nodes = html.request.get_integer_input_mandatory("topology_max_nodes", 400)

        if html.request.var("filled_in"):
            # Search in filter form
            hostnames = self._get_hostnames_from_filters()

        elif html.request.var("host_regex"):
            # Set by "Host Parent/Child topology" icon. One explicit host (ugly)
            host_regex_var = html.request.get_str_input_mandatory("host_regex")
            hostnames = [host_regex_var[1:-1]]

        else:
            # Initial page rendering of network topology
            growth_auto_max_nodes = 200
            mesh_depth = 5
            hostnames = self._get_default_view_hostnames(growth_auto_max_nodes)

        self.show_topology(hostnames,
                           mode="parent_child",
                           growth_auto_max_nodes=growth_auto_max_nodes,
                           mesh_depth=mesh_depth,
                           max_nodes=max_nodes)

    def _get_default_view_hostnames(self, growth_auto_max_nodes: int) -> List[HostName]:
        """ Returns all hosts without any parents """
        query = "GET hosts\nColumns: name\nFilter: parents ="
        sites.live().set_prepend_site(True)
        only_site = html.request.var("site")
        if only_site:
            sites.live().set_only_sites([only_site])
        hosts = [(x[0], x[1]) for x in sites.live().query(query)]
        sites.live().set_only_sites(None)
        sites.live().set_prepend_site(False)

        # If no explicit site is set and the number of initially displayed hosts
        # exceeds the auto growth range, only the hosts of the master site are shown
        if len(hosts) > growth_auto_max_nodes:
            hostnames = [x[1] for x in hosts if x[0] == config.omd_site()]
        else:
            hostnames = [x[1] for x in hosts]

        return hostnames

    def _get_hostnames_from_filters(self) -> List[str]:
        # Determine hosts from filters
        filter_headers = self._get_filter_headers()
        query = "GET hosts\nColumns: name"
        if filter_headers:
            query += "\n%s" % filter_headers
        only_site = html.request.var("site")
        try:
            if only_site:
                sites.live().set_only_sites([only_site])
            return [x[0] for x in sites.live().query(query)]
        finally:
            sites.live().set_only_sites(None)

    def show_topology(self,
                      hostnames: List[HostName],
                      mode: str,
                      growth_auto_max_nodes: Optional[int] = None,
                      mesh_depth: int = 0,
                      max_nodes: int = 400) -> None:
        breadcrumb = make_simple_page_breadcrumb(mega_menu_registry.menu_monitoring(), "")
        html.header("", breadcrumb)
        self.show_topology_content(hostnames,
                                   mode,
                                   growth_auto_max_nodes=growth_auto_max_nodes,
                                   mesh_depth=mesh_depth,
                                   max_nodes=max_nodes)

    def show_topology_content(self,
                              hostnames: List[HostName],
                              mode: str,
                              growth_auto_max_nodes: Optional[int] = None,
                              max_nodes: int = 400,
                              mesh_depth: int = 0) -> None:
        div_id = "node_visualization"
        html.div("", id=div_id)

        # Filters
        html.open_div(id="topology_filters")
        view, filters = self._get_topology_view_and_filters()
        html.request.set_var("topology_mesh_depth", str(mesh_depth))
        html.request.set_var("topology_max_nodes", str(max_nodes))
        cmk.gui.views.show_filter_form(view, filters)
        html.final_javascript("cmk.page_menu.open_popup('popup_filters');")
        html.close_div()

        html.javascript(
            "topology_instance = new cmk.node_visualization.TopologyVisualization(%s, %s);" %
            (json.dumps(div_id), json.dumps(mode)))

        if growth_auto_max_nodes:
            html.javascript("topology_instance.set_growth_auto_max_nodes(%d)" %
                            growth_auto_max_nodes)
        html.javascript("topology_instance.set_max_nodes(%d)" % max_nodes)
        html.javascript("topology_instance.set_mesh_depth(%d)" % mesh_depth)
        html.javascript("topology_instance.set_theme(%s)" % json.dumps(html.get_theme()))
        overlay_config = self._get_overlay_config()
        if overlay_config:
            html.javascript("topology_instance.set_initial_overlays_config(%s)" %
                            json.dumps(overlay_config))

        html.javascript("topology_instance.show_topology(%s)" % json.dumps(hostnames))

    def _get_overlay_config(self) -> List:
        return []

    def _get_filter_headers(self) -> FilterHeaders:
        view, filters = self._get_topology_view_and_filters()
        return cmk.gui.views.get_livestatus_filter_headers(view, filters)

    def _get_topology_view_and_filters(self) -> Tuple[View, List[Filter]]:
        view_spec = get_permitted_views()["topology_filters"]
        view_name = "topology_filters"
        view = View(view_name, view_spec, view_spec.get("context", {}))
        filters = cmk.gui.visuals.filters_of_visual(view.spec,
                                                    view.datasource.infos,
                                                    link_filters=view.datasource.link_filters)

        show_filters = cmk.gui.visuals.visible_filters_of_visual(view.spec, filters)
        return view, show_filters


@cmk.gui.pages.register("bi_map")
def _bi_map() -> None:
    aggr_name = html.request.var("aggr_name")
    layout_id = html.request.var("layout_id")
    title = _("BI visualization")
    breadcrumb = make_simple_page_breadcrumb(mega_menu_registry.menu_monitoring(), title)
    html.header(title, breadcrumb)
    div_id = "node_visualization"
    html.div("", id=div_id)
    html.javascript("node_instance = new cmk.node_visualization.BIVisualization(%s);" %
                    json.dumps(div_id))

    html.javascript("node_instance.set_theme(%s)" % json.dumps(html.get_theme()))
    html.javascript("node_instance.show_aggregations(%s, %s)" %
                    (json.dumps([aggr_name]), json.dumps(layout_id)))


@page_registry.register_page("ajax_fetch_aggregation_data")
class AjaxFetchAggregationData(AjaxPage):
    def page(self) -> AjaxPageResult:
        aggregations_var = html.request.get_str_input_mandatory("aggregations", "[]")
        filter_names = json.loads(aggregations_var)

        forced_layout_id = html.request.var("layout_id")
        if forced_layout_id not in BILayoutManagement.get_all_bi_template_layouts():
            forced_layout_id = None

        state_data = bi.api_get_aggregation_state(filter_names=filter_names)

        aggregation_info: Dict[str, Any] = {"aggregations": {}}

        aggregation_layouts = BILayoutManagement.get_all_bi_aggregation_layouts()

        for row in state_data["rows"]:
            row = row["tree"]
            aggr_name = row["aggr_name"]
            if filter_names and aggr_name not in filter_names:
                continue
            visual_mapper = NodeVisualizationBIDataMapper()
            aggr_treestate = row["aggr_treestate"]
            hierarchy = visual_mapper.consume(aggr_treestate)

            data: Dict[str, Any] = {}
            data["hierarchy"] = hierarchy
            data["aggr_type"] = row["aggr_tree"]["aggr_type"]
            data["groups"] = row["aggr_group"]
            data["data_timestamp"] = int(time.time())

            aggr_settings = row["aggr_tree"]["node_visualization"]
            layout: Dict[str, Any] = {"config": {}}
            if forced_layout_id:
                layout["enforced_id"] = aggr_name
                layout["origin_type"] = "globally_enforced"
                layout["origin_info"] = _("Globally enforced")
                layout["use_layout"] = BILayoutManagement.load_bi_template_layout(forced_layout_id)
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
                    "ignore_rule_styles", False)
            if "line_config" not in layout["config"]:
                layout["config"]["line_config"] = self._get_line_style_config(aggr_settings)

            data["layout"] = layout
            aggregation_info["aggregations"][row["aggr_name"]] = data

        html.set_output_format("json")
        return aggregation_info

    def _get_line_style_config(self, aggr_settings: Dict[str, Any]) -> Dict[str, Any]:
        line_style = aggr_settings.get("line_style", config.default_bi_layout["line_style"])
        if line_style == "default":
            line_style = config.default_bi_layout["line_style"]
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
                template_layout_id)
        elif template_layout_id.startswith("builtin_"):
            # FIXME: this mapping is currently copied from the bi configuration valuespec
            #        BI refactoring required...
            builtin_mapping = {
                "builtin_default": _("global"),
                "builtin_force": _("force"),
                "builtin_radial": _("radial"),
                "builtin_hierarchy": _("hierarchy")
            }
            layout_settings["origin_type"] = "default_template"
            layout_settings["origin_info"] = _("Default %s template") % builtin_mapping.get(
                template_layout_id, _("Unknown"))

            if template_layout_id == "builtin_default":
                template_layout_id = config.default_bi_layout["node_style"]
            layout_settings["default_id"] = template_layout_id[8:]
        else:
            # Any Unknown/Removed layout id gets the default template
            layout_settings["origin_type"] = "default_template"
            layout_settings["origin_info"] = _("Fallback template (%s): Unknown ID %s") % (
                config.default_bi_layout["node_style"][8:].title(), template_layout_id)
            layout_settings["default_id"] = config.default_bi_layout["node_style"][8:]

        return layout_settings


TreeState = Tuple[Dict[str, Any], Dict[str, Any], List]
BIAggrTreeState = Tuple[Dict[str, Any], Any, Dict[str, Any], List]
BILeafTreeState = Tuple[Dict[str, Any], Any, Dict[str, Any]]


# Creates are hierarchical dictionary which can be read by the NodeVisualization framework
class NodeVisualizationBIDataMapper:
    def consume(self,
                treestate: Union[BIAggrTreeState, BILeafTreeState],
                depth: int = 1) -> Dict[str, Any]:
        state_info, node, subtrees = self._normalize_treestate(treestate)
        if subtrees:
            node_data = self._get_node_data_of_bi_aggregator(node)
        else:
            node_data = self._get_node_data_of_bi_leaf(node)

        node_data["icon"] = node.get("icon")
        node_data["state"] = state_info["state"]
        node_data["name"] = node.get("title")

        # TODO: BI cleanup: in_downtime has two states 0, False
        node_data["in_downtime"] = not state_info.get("in_downtime", False) in [0, False]
        node_data["acknowledged"] = state_info.get("acknowledged", False)
        node_data["children"] = []
        for subtree in subtrees:
            node_data["children"].append(self.consume(subtree, depth=depth + 1))
        return node_data

    def _normalize_treestate(self, treestate):
        if isinstance(treestate, tuple):
            if len(treestate) == 4:
                return treestate[0], treestate[2], treestate[3]
            if len(treestate) == 3:
                return treestate[0], treestate[2], []
            raise ValueError("Invalid treestate tuple length")
        raise ValueError("Invalid treestate")

    def _get_node_data_of_bi_aggregator(self, node: Dict[str, Any]) -> Dict[str, Any]:
        node_data: Dict[str, Any] = {}
        node_data["node_type"] = "bi_aggregator"
        node_data["rule_id"] = {
            "pack": node["rule_id"][0],
            "rule": node["rule_id"][1],
            "function": node["rule_id"][2]
        }
        if "rule_layout_style" in node:
            node_data["rule_layout_style"] = node["rule_layout_style"]
        if "aggregation_id" in node:
            node_data["aggregation_id"] = node["aggregation_id"]
        return node_data

    def _get_node_data_of_bi_leaf(self, node: Dict[str, Any]) -> Dict[str, Any]:
        node_data: Dict[str, Any] = {}
        node_data["node_type"] = "bi_leaf"
        node_data["hostname"] = node.get("host", ["", ""])[1]
        if "service" in node:
            node_data["service"] = node["service"]
        return node_data


class BILayoutManagement:
    _config_file = Path(watolib.multisite_dir()) / "bi_layouts.mk"

    @classmethod
    def save_layouts(cls) -> None:
        store.save_to_mk_file(str(BILayoutManagement._config_file),
                              "bi_layouts",
                              config.bi_layouts,
                              pprint_value=True)

    @classmethod
    def load_bi_template_layout(cls, template_id: Optional[str]) -> Any:
        return config.bi_layouts["templates"].get(template_id)

    @classmethod
    def load_bi_aggregation_layout(cls, aggregation_name: Optional[str]) -> Any:
        return config.bi_layouts["aggregations"].get(aggregation_name)

    @classmethod
    def get_all_bi_template_layouts(cls) -> Any:
        return config.bi_layouts["templates"]

    @classmethod
    def get_all_bi_aggregation_layouts(cls) -> Any:
        return config.bi_layouts["aggregations"]


# Explicit Aggregations
@page_registry.register_page("ajax_save_bi_aggregation_layout")
class AjaxSaveBIAggregationLayout(AjaxPage):
    def page(self) -> AjaxPageResult:
        layout_var = html.request.get_str_input_mandatory("layout", "{}")
        layout_config = json.loads(layout_var)
        config.bi_layouts["aggregations"].update(layout_config)
        BILayoutManagement.save_layouts()
        return {}


@page_registry.register_page("ajax_delete_bi_aggregation_layout")
class AjaxDeleteBIAggregationLayout(AjaxPage):
    def page(self) -> AjaxPageResult:
        for_aggregation = html.request.var("aggregation_name")
        config.bi_layouts["aggregations"].pop(for_aggregation)
        BILayoutManagement.save_layouts()
        return {}


@page_registry.register_page("ajax_load_bi_aggregation_layout")
class AjaxLoadBIAggregationLayout(AjaxPage):
    def page(self) -> AjaxPageResult:
        aggregation_name = html.request.var("aggregation_name")
        return BILayoutManagement.load_bi_aggregation_layout(aggregation_name)


# Templates
@page_registry.register_page("ajax_save_bi_template_layout")
class AjaxSaveBITemplateLayout(AjaxPage):
    def page(self) -> AjaxPageResult:
        layout_var = html.request.get_str_input_mandatory("layout", "{}")
        layout_config = json.loads(layout_var)
        config.bi_layouts["templates"].update(layout_config)
        BILayoutManagement.save_layouts()
        return {}


@page_registry.register_page("ajax_delete_bi_template_layout")
class AjaxDeleteBITemplateLayout(AjaxPage):
    def page(self) -> AjaxPageResult:
        layout_id = html.request.var("layout_id")
        config.bi_layouts["templates"].pop(layout_id)
        BILayoutManagement.save_layouts()
        return {}


@page_registry.register_page("ajax_load_bi_template_layout")
class AjaxLoadBITemplateLayout(AjaxPage):
    def page(self) -> AjaxPageResult:
        layout_id = html.request.var("layout_id")
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

        topology_config_var = html.request.get_ascii_input_mandatory("topology_config")
        try:
            topology_config = json.loads(topology_config_var)
        except (TypeError, ValueError):
            raise MKGeneralException(_("Invalid topology_config %r") % topology_config_var)

        topology = self._get_topology_instance(topology_config)
        meshes = topology.compute()

        topology_info: Dict[str, Any] = {"topology_meshes": {}}
        topology_info = {
            "topology_chunks": {},
        }

        topology_info["headline"] = topology.title()
        topology_info["errors"] = topology.errors()
        topology_info["max_nodes"] = topology.max_nodes
        topology_info["mesh_depth"] = topology.mesh_depth

        for mesh in meshes:
            if not mesh:
                continue

            # Pick root host
            growth_roots = sorted(mesh.intersection(set(topology_config["growth_root_nodes"])))
            if growth_roots:
                mesh_root = growth_roots[0]
            else:
                mesh_root = list(mesh)[0]
            mesh_info = topology.get_info_for_host(mesh_root, mesh)

            mesh.remove(mesh_root)
            sorted_mesh = sorted(list(mesh))
            sorted_mesh.insert(0, mesh_root)

            if sorted_mesh:
                mesh_info["children"] = []
                mesh_info["children"].extend(
                    [topology.get_info_for_host(x, mesh) for x in sorted_mesh[1:]])

            mesh_links = set()
            # Incoming connections
            for idx, hostname in enumerate(sorted_mesh):
                for child in topology.get_host_incoming(hostname):
                    if child in sorted_mesh:
                        mesh_links.add((sorted_mesh.index(child), idx))
            # Outgoing connections
            for idx, hostname in enumerate(sorted_mesh):
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
                "hierarchy": mesh_info,
                "links": list(mesh_links)
            }

        return topology_info

    def _get_topology_instance(self, topology_config: TopologyConfig) -> 'Topology':
        topology_class = topology_registry.get(topology_config["mode"])
        if topology_class is None:
            raise Exception("unknown topology")
        return topology_class(topology_config)


class Topology:
    def __init__(self, topology_config: TopologyConfig) -> None:
        super(Topology, self).__init__()
        self._config = topology_config

        # Hosts with complete data
        self._known_hosts: Dict[str, Any] = {}

        # Child/parent hosts at the depth boundary
        self._border_hosts: Set[HostName] = set()

        # Nodes without a parent
        self._actual_root_nodes: Set[HostName] = set()

        # Nodes without child or parent
        self._single_hosts: Set[HostName] = set()
        self._errors: List[str] = []
        self._meshes: Meshes = []

        # Node depth to next growth root
        self._depth_info: Dict[str, int] = {}

        self._current_iteration = 0

    def title(self) -> str:
        raise NotImplementedError()

    def get_info_for_host(self, hostname: HostName, mesh: Mesh) -> Dict[str, Any]:
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

    def get_host_incoming(self, hostname: HostName) -> List[str]:
        if hostname not in self._known_hosts:
            return []
        return self._known_hosts[hostname]["incoming"]

    def get_host_outgoing(self, hostname: HostName) -> List[str]:
        if hostname not in self._known_hosts:
            return []
        return self._known_hosts[hostname]["outgoing"]

    def is_growth_root(self, hostname: HostName) -> bool:
        return hostname in self._config["growth_root_nodes"]

    def is_growth_continue(self, hostname: HostName) -> bool:
        return hostname in self._config.get("growth_continue_nodes", [])

    def may_grow(self, hostname: HostName, mesh_hosts: Mesh) -> bool:
        known_host = self._known_hosts.get(hostname)
        if not known_host:
            return True

        unknown_hosts = set(known_host["incoming"] + known_host["outgoing"]) - set(mesh_hosts)
        return len(unknown_hosts) > 0

    def growth_forbidden(self, hostname: HostName) -> bool:
        return hostname in self._config.get("growth_forbidden_nodes", set())

    def add_error(self, error: str) -> None:
        self._errors.append(error)

    def errors(self) -> List[str]:
        return self._errors

    def compute(self) -> Meshes:
        if not self._config["growth_root_nodes"]:
            return []
        self._border_hosts = set(self._config["growth_root_nodes"])

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
        self._growth_to_depth()
        self._growth_to_parents()
        self._growth_to_continue_nodes()

    def _check_mesh_size(self, meshes: Meshes) -> None:
        total_nodes = sum(map(len, meshes))
        if total_nodes > self.max_nodes:
            raise MKGrowthExceeded(
                _("Maximum number of nodes exceeded %d/%d") % (total_nodes, self.max_nodes))
        if total_nodes > self.growth_auto_max_nodes:
            raise MKGrowthInterruption(
                _("Growth interrupted %d/%d") % (total_nodes, self.growth_auto_max_nodes))

    @property
    def max_nodes(self) -> int:
        return int(self._config.get("max_nodes", 500))

    @property
    def growth_auto_max_nodes(self) -> int:
        return self._config.get("growth_auto_max_nodes") or 100000

    @property
    def mesh_depth(self) -> int:
        return int(self._config.get("mesh_depth", 0))

    def _growth_to_depth(self) -> None:
        while self._current_iteration <= self.mesh_depth:
            self._current_iteration += 1
            new_meshes = self._compute_meshes(self._border_hosts)
            self._check_mesh_size(new_meshes)
            self._meshes = new_meshes

    def _growth_to_parents(self) -> None:
        all_parents: Set[str] = set()
        while True:
            combined_mesh = set()
            for mesh in self._meshes:
                combined_mesh.update(mesh)

            combined_mesh -= self._border_hosts
            all_parents = set()
            for node_name in combined_mesh:
                all_parents.update(set(self._known_hosts[node_name]["outgoing"]))

            missing_parents = all_parents - combined_mesh
            if not missing_parents:
                break

            new_meshes = self._compute_meshes(missing_parents)
            self._check_mesh_size(new_meshes)
            self._meshes = new_meshes

    def _growth_to_continue_nodes(self) -> None:
        growth_continue_nodes = set(self._config.get("growth_continue_nodes", []))
        while growth_continue_nodes:
            growth_nodes = growth_continue_nodes.intersection(set(self._known_hosts.keys()))
            if not growth_nodes:
                break

            border_hosts = set()
            for node_name in growth_nodes:
                border_hosts.update(set(self._known_hosts[node_name]["incoming"]))
                border_hosts.update(set(self._known_hosts[node_name]["outgoing"]))

            new_meshes = self._compute_meshes(border_hosts)
            self._check_mesh_size(new_meshes)
            self._meshes = new_meshes
            growth_continue_nodes -= growth_nodes

    def _compute_meshes(self, hostnames: Set[HostName]) -> Meshes:
        hostnames.update(self._known_hosts.keys())  # pylint: disable=dict-keys-not-iterating

        new_hosts = []
        mandatory_keys = {"name", "outgoing", "incoming"}
        for host_data in self._fetch_data_for_hosts(hostnames):
            if len(mandatory_keys - set(host_data.keys())) > 0:
                raise MKGeneralException(
                    _("Missing mandatory topology keys: %r") %
                    (mandatory_keys - set(host_data.keys())))
            # Mandatory keys in host_data: name, outgoing, incoming
            new_hosts.append(host_data)

        meshes = self._generate_meshes(new_hosts)
        self._update_depth_information(meshes)
        return meshes

    def _postprocess_meshes(self, meshes: Meshes) -> Meshes:
        return meshes

    def _fetch_data_for_hosts(self, hostnames: Set[HostName]) -> List[Dict]:
        raise NotImplementedError()

    def is_root_node(self, hostname: HostName) -> bool:
        return hostname in self._actual_root_nodes

    def is_border_host(self, hostname: HostName) -> bool:
        return hostname in self._border_hosts

    def _generate_meshes(self, new_hosts: List[Dict[str, Any]]) -> Meshes:
        # Data flow is child->parent
        # Incoming data comes from child
        # Outgoing data goes to parent
        incoming_nodes = {}
        outgoing_nodes = {}
        self._border_hosts = set()

        for new_host in new_hosts:
            hostname = new_host["name"]
            self._known_hosts[hostname] = new_host

            if not self.growth_forbidden(hostname):
                outgoing = new_host["outgoing"]
                incoming = new_host["incoming"]
                for entry in outgoing + incoming:
                    self._border_hosts.add(entry)

            if not outgoing and not incoming:
                self._single_hosts.add(hostname)

            if not outgoing:
                self._actual_root_nodes.add(hostname)

            incoming_nodes[hostname] = incoming
            outgoing_nodes[hostname] = outgoing

        # Determine core and border hosts
        for hostname in self._known_hosts:
            if hostname in self._border_hosts:
                self._border_hosts.remove(hostname)

        meshes = []
        for hostname in self._known_hosts:
            meshes.append(set([hostname] + incoming_nodes[hostname] + outgoing_nodes[hostname]))
        self._combine_meshes_inplace(meshes)

        return meshes

    def _combine_meshes_inplace(self, meshes: Meshes) -> None:
        """ Combines meshes with identical items """
        while True:
            changed_meshes = False
            for idx in range(0, len(meshes) - 1):
                current_bundle = meshes[idx]
                for check_bundle in meshes[idx + 1:len(meshes)]:
                    if current_bundle.intersection(check_bundle):
                        new_bundle = current_bundle.union(check_bundle)
                        meshes[idx] = new_bundle
                        meshes.remove(check_bundle)
                        changed_meshes = True
                        break
                if changed_meshes:
                    break

            if not changed_meshes:
                break

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
    """ Generates parent/child topology view """
    @classmethod
    def ident(cls) -> str:
        return "parent_child"

    def title(self) -> str:
        return _("Parent / Child topology")

    def _fetch_data_for_hosts(self, hostnames: Set[HostName]) -> List[Dict]:
        hostname_filters = []
        if hostnames:
            for hostname in hostnames:
                hostname_filters.append("Filter: host_name = %s" % livestatus.lqencode(hostname))
            hostname_filters.append("Or: %d" % len(hostnames))

        try:
            sites.live().set_prepend_site(True)
            columns = [
                "name", "state", "alias", "icon_image", "parents", "childs", "has_been_checked"
            ]
            query_result = sites.live().query("GET hosts\nColumns: %s\n%s" %
                                              (" ".join(columns), "\n".join(hostname_filters)))
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
        """ Create a central node and add all monitoring sites as childs """

        central_node = {
            "name": "",
            "hostname": "Checkmk",
            "outgoing": [],
            "incoming": [],
            "node_type": "topology_center",
        }

        site_nodes: Dict[str, Any] = {}
        for mesh in meshes:
            for node_name in mesh:
                site = self._known_hosts[node_name]["site"]
                site_node_name = _("Site %s") % site
                site_nodes.setdefault(site_node_name, {
                    "node_type": "topology_site",
                    "outgoing": [central_node["name"]],
                    "incoming": []
                })
                outgoing_nodes = self._known_hosts.get(node_name, {"outgoing": []})["outgoing"]
                # Attach this node to the site not if it has no parents or if none of its parents are visible in the current mesh
                if not outgoing_nodes or len(set(outgoing_nodes) - mesh) == len(outgoing_nodes):
                    site_nodes[site_node_name]["incoming"].append(node_name)

        central_node["incoming"] = list(site_nodes.keys())
        self._known_hosts[str(central_node["name"])] = central_node

        combinator_mesh = set(central_node["name"])
        for node_name, settings in site_nodes.items():
            self._known_hosts[node_name] = settings
            combinator_mesh.add(node_name)
            combinator_mesh.update(set(settings["incoming"]))

        meshes.append(combinator_mesh)
        self._combine_meshes_inplace(meshes)

        return meshes

    def get_info_for_host(self, hostname: HostName, mesh: Mesh) -> Dict[str, Any]:
        info = super(ParentChildNetworkTopology, self).get_info_for_host(hostname, mesh)
        host_info = self._known_hosts[hostname]
        info.update(host_info)

        if "node_type" not in info:
            info["node_type"] = "topology"

        info["state"] = self._map_host_state_to_service_state(info, host_info)

        if info["node_type"] == "topology_center":
            info["explicit_force_options"] = {"repulsion": -3000, "center_force": 200}
        elif info["node_type"] == "topology_site":
            info["explicit_force_options"] = {"repulsion": -100, "link_distance": 50}

        return info

    def _map_host_state_to_service_state(self, info: Dict[str, Any], host_info: Dict[str,
                                                                                     Any]) -> int:
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
