#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

import json
import time
from pathlib2 import Path

import cmk
import cmk.utils.store as store
from cmk.gui import sites
from cmk.gui.globals import html
from cmk.gui.i18n import _
import cmk.gui.watolib as watolib
import cmk.gui.bi as bi
import cmk.gui.config as config
from cmk.gui.pages import page_registry, AjaxPage


@cmk.gui.pages.register("parent_child_topology")
def _parent_child_topology():
    hostnames = json.loads(html.request.var("hostnames"))
    show_topology(hostnames, mode="parent_child")


def show_topology(hostnames, mode):
    html.header("")
    show_topology_content(hostnames, mode)


def show_topology_content(hostnames, mode):
    div_id = "node_visualization"
    html.div("", id=div_id)

    html.javascript(
        "topology_instance = new cmk.node_visualization.TopologyVisualization(%s, %s);" %
        (json.dumps(div_id), json.dumps(mode)))

    html.javascript("topology_instance.set_theme(%s)" % json.dumps(html.get_theme()))
    html.javascript("topology_instance.show_topology(%s)" % json.dumps(hostnames))


@cmk.gui.pages.register("bi_map")
def _bi_map():
    aggr_name = html.request.var("aggr_name")
    layout_id = html.request.var("layout_id")
    html.header("BI visualization")
    div_id = "node_visualization"
    html.div("", id=div_id)
    html.javascript("node_instance = new cmk.node_visualization.BIVisualization(%s);" %
                    json.dumps(div_id))

    html.javascript("node_instance.set_theme(%s)" % json.dumps(html.get_theme()))
    html.javascript("node_instance.show_aggregations(%s, %s)" %
                    (json.dumps([aggr_name]), json.dumps(layout_id)))


@page_registry.register_page("ajax_fetch_aggregation_data")
class AjaxFetchAggregationData(AjaxPage):
    def page(self):
        filter_names = json.loads(html.request.var("aggregations", "[]"))
        forced_layout_id = html.request.var("layout_id")
        if forced_layout_id not in BILayoutManagement.get_all_bi_template_layouts():
            forced_layout_id = None

        state_data = bi.api_get_aggregation_state(filter_names=filter_names)

        aggregation_info = {"aggregations": {}}

        aggregation_layouts = BILayoutManagement.get_all_bi_aggregation_layouts()

        for row in state_data["rows"]:
            aggr_name = row["tree"]["aggr_name"]
            if filter_names and aggr_name not in filter_names:
                continue
            visual_mapper = NodeVisualizationBIDataMapper()
            aggr_treestate = row["tree"]["aggr_treestate"]
            hierarchy = visual_mapper.consume(aggr_treestate)

            data = {}
            data["hierarchy"] = hierarchy
            data["groups"] = row["groups"]
            data["data_timestamp"] = int(time.time())

            aggr_settings = row["tree"]["aggr_tree"]["node_visualization"]
            layout = {"config": {}}
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
            aggregation_info["aggregations"][row["tree"]["aggr_name"]] = data

        html.set_output_format("json")
        return aggregation_info

    def _get_line_style_config(self, aggr_settings):
        line_style = aggr_settings.get("line_style", config.default_bi_layout["line_style"])
        if line_style == "default":
            line_style = config.default_bi_layout["line_style"]
        return {"style": line_style}

    def _get_template_based_layout_settings(self, aggr_settings):
        template_layout_id = aggr_settings.get("layout_id", "builtin_default")

        layout_settings = {}
        if template_layout_id in BILayoutManagement.get_all_bi_template_layouts():
            # FIXME: This feature is currently inactive
            layout_settings["origin_type"] = "template"
            layout_settings["origin_info"] = _("Template: %s" % template_layout_id)
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
            layout_settings["origin_info"] = _(
                "Fallback template (%s): Unknown ID %s" %
                (config.default_bi_layout["node_style"][8:].title(), template_layout_id))
            layout_settings["default_id"] = config.default_bi_layout["node_style"][8:]

        return layout_settings


# Creates are hierarchical dictionary which can be read by the NodeVisualization framework
class NodeVisualizationBIDataMapper(object):
    def consume(self, treestate, depth=1):
        subtrees = []
        node_data = {}
        if len(treestate) == 4:
            node_data["node_type"] = "bi_aggregator"
            state_info, _assumed_state, node, subtrees = treestate
            node_data["rule_id"] = {
                "pack": node["rule_id"][0],
                "rule": node["rule_id"][1],
                "function": node["rule_id"][2]
            }
            if "rule_layout_style" in node:
                node_data["rule_layout_style"] = node["rule_layout_style"]
            if "aggregation_id" in node:
                node_data["aggregation_id"] = node["aggregation_id"]
        else:
            state_info, _assumed_state, node = treestate
            node_data["node_type"] = "bi_leaf"
            node_data["hostname"] = node.get("host", ["", ""])[1]
            if "service" in node:
                node_data["service"] = node["service"]

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


class BILayoutManagement(object):
    _config_file = Path(watolib.multisite_dir()) / "bi_layouts.mk"

    @classmethod
    def save_layouts(cls):
        store.save_to_mk_file(str(BILayoutManagement._config_file),
                              "bi_layouts",
                              config.bi_layouts,
                              pprint_value=True)

    @classmethod
    def load_bi_template_layout(cls, template_id):
        return config.bi_layouts["templates"].get(template_id)

    @classmethod
    def load_bi_aggregation_layout(cls, aggregation_name):
        return config.bi_layouts["aggregations"].get(aggregation_name)

    @classmethod
    def get_all_bi_template_layouts(cls):
        return config.bi_layouts["templates"]

    @classmethod
    def get_all_bi_aggregation_layouts(cls):
        return config.bi_layouts["aggregations"]


# Explicit Aggregations
@page_registry.register_page("ajax_save_bi_aggregation_layout")
class AjaxSaveBIAggregationLayout(AjaxPage):
    def page(self):
        layout_config = json.loads(html.request.var("layout"))
        config.bi_layouts["aggregations"].update(layout_config)
        BILayoutManagement.save_layouts()


@page_registry.register_page("ajax_delete_bi_aggregation_layout")
class AjaxDeleteBIAggregationLayout(AjaxPage):
    def page(self):
        for_aggregation = html.request.var("aggregation_name")
        config.bi_layouts["aggregations"].pop(for_aggregation)
        BILayoutManagement.save_layouts()


@page_registry.register_page("ajax_load_bi_aggregation_layout")
class AjaxLoadBIAggregationLayout(AjaxPage):
    def page(self):
        aggregation_name = html.request.var("aggregation_name")
        return BILayoutManagement.load_bi_aggregation_layout(aggregation_name)


# Templates
@page_registry.register_page("ajax_save_bi_template_layout")
class AjaxSaveBITemplateLayout(AjaxPage):
    def page(self):
        layout_config = json.loads(html.request.var("layout"))
        config.bi_layouts["templates"].update(layout_config)
        BILayoutManagement.save_layouts()


@page_registry.register_page("ajax_delete_bi_template_layout")
class AjaxDeleteBITemplateLayout(AjaxPage):
    def page(self):
        layout_id = html.request.var("layout_id")
        config.bi_layouts["templates"].pop(layout_id)
        BILayoutManagement.save_layouts()


@page_registry.register_page("ajax_load_bi_template_layout")
class AjaxLoadBITemplateLayout(AjaxPage):
    def page(self):
        layout_id = html.request.var("layout_id")
        return BILayoutManagement.load_bi_template_layout(layout_id)


@page_registry.register_page("ajax_get_all_bi_template_layouts")
class AjaxGetAllBITemplateLayouts(AjaxPage):
    def page(self):
        return BILayoutManagement.get_all_bi_template_layouts()


@page_registry.register_page("ajax_fetch_topology")
class AjaxFetchTopology(AjaxPage):
    def page(self):
        # hostnames: a list of mandatory hostnames
        # mesh_depth: number of hops from growth root
        # growth_forbidden: block further traversal at the given nodes

        topo_config = json.loads(html.request.var("topology_config"))

        topology = self._get_topology_instance(topo_config)
        meshes = topology.compute()

        topology_info = {"topology_meshes": {}}

        def get_topology_info(hostname, mesh):
            return {
                "hostname": hostname,
                "icon": topology.get_host_icon_image(hostname),
                "node_type": "topology",
                "has_no_parents": topology.is_root_node(hostname),
                "growth_root": topology.is_growth_root(hostname),
                "growth_possible": topology.may_grow(hostname, mesh),
                "growth_forbidden": topology.growth_forbidden(hostname),
                "name": hostname,
                "state": 0,
            }

        topology_info = {
            "topology_chunks": {},
        }

        topology_info["headline"] = topology.title()

        for mesh in meshes:
            if not mesh:
                continue

            # Pick root host
            growth_roots = sorted(mesh.intersection(set(topo_config["growth_root_nodes"])))
            mesh_root = growth_roots[0]
            mesh_info = get_topology_info(mesh_root, mesh)

            mesh.remove(mesh_root)
            mesh = sorted(list(mesh))
            mesh.insert(0, mesh_root)

            if mesh:
                mesh_info["children"] = []
                mesh_info["children"].extend([get_topology_info(x, mesh) for x in mesh[1:]])

            mesh_links = set()
            # Incoming connections
            for idx, hostname in enumerate(mesh):
                for child in topology.get_host_incoming(hostname):
                    if child in mesh:
                        mesh_links.add((mesh.index(child), idx))
            # Outgoing connections
            for idx, hostname in enumerate(mesh):
                for parent in topology.get_host_outgoing(hostname):
                    if parent in mesh:
                        mesh_links.add((idx, mesh.index(parent)))

            topology_info["topology_chunks"][mesh_root] = {
                "layout": {
                    "config": {
                        "line_config": {
                            "style": "straight"
                        }
                    }
                },
                "hierarchy": mesh_info,
                "links": list(mesh_links)
            }

        html.set_output_format("json")
        return topology_info

    def _get_topology_instance(self, topo_config):
        topology_class = topology_registry.get(topo_config["mode"])
        return topology_class(topo_config)


class Topology(object):
    def __init__(self, topo_config):
        super(Topology, self).__init__()
        self._config = topo_config

        self._known_hosts = {}  # Hosts with complete data
        self._border_hosts = set()  # Child/parent hosts at the depth boundary
        self._actual_root_nodes = set()  # Nodes without a parent
        self._single_hosts = set()  # Nodes without child or parent

        self._depth_info = {}  # Node depth to next growth root

        self._current_iteration = 0

    def get_host_icon_image(self, hostname):
        if hostname not in self._known_hosts:
            return
        return self._known_hosts[hostname].get("icon_image")

    def get_host_incoming(self, hostname):
        if hostname not in self._known_hosts:
            return []
        return self._known_hosts[hostname]["incoming"]

    def get_host_outgoing(self, hostname):
        if hostname not in self._known_hosts:
            return []
        return self._known_hosts[hostname]["outgoing"]

    def is_growth_root(self, hostname):
        return hostname in self._config["growth_root_nodes"]

    def may_grow(self, hostname, mesh_hosts):
        known_host = self._known_hosts.get(hostname)
        if not known_host:
            return True

        unknown_hosts = set(known_host["incoming"] + known_host["outgoing"]) - set(mesh_hosts)
        return len(unknown_hosts) > 0

    def growth_forbidden(self, hostname):
        return hostname in self._config.get("growth_forbidden_nodes", set())

    def compute(self):
        if not self._config["growth_root_nodes"]:
            return []
        self._border_hosts = set(self._config["growth_root_nodes"])
        meshes = []
        while self._current_iteration < self._config["mesh_depth"]:
            self._current_iteration += 1
            meshes = self._compute_meshes(self._border_hosts)
            self._update_depth_information(meshes)

        meshes = self._compute_meshes(self._border_hosts)
        for mesh in meshes:
            mesh -= self._border_hosts
        self._update_depth_information(meshes)

        return meshes

    def _compute_meshes(self, hostnames):
        hostnames.update(self._known_hosts.keys())
        new_hosts = []
        for hostname, alias, icon_image, outgoing, incoming in self._fetch_data_for_hosts(
                hostnames):
            new_host = {
                "hostname": hostname,
                "icon_image": icon_image,
                "alias": alias,
                "outgoing": outgoing,
                "incoming": incoming
            }
            new_hosts.append(new_host)

        return self._generate_meshes(new_hosts)

    def _fetch_data_for_hosts(self, hostnames):
        raise NotImplementedError()

    def is_root_node(self, hostname):
        return hostname in self._actual_root_nodes

    def is_border_host(self, hostname):
        return hostname in self._border_hosts

    def _generate_meshes(self, new_hosts):
        # Data flow is child->parent
        # Incoming data comes from child
        # Outgoing data goes to parent
        incoming_nodes = {}
        outgoing_nodes = {}
        self._border_hosts = set()

        for new_host in new_hosts:
            hostname = new_host["hostname"]
            self._known_hosts[hostname] = new_host
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

        for hostname in list(self._border_hosts):
            if self.growth_forbidden(hostname):
                self._border_hosts.remove(hostname)

        meshes = []
        for hostname in self._known_hosts.iterkeys():
            meshes.append(set([hostname] + incoming_nodes[hostname] + outgoing_nodes[hostname]))
        self._combine_meshes_inplace(meshes)

        return meshes

    def _combine_meshes_inplace(self, meshes):
        """ Combines meshes with identical items to a bigger chunk """
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

    def _update_depth_information(self, meshes):
        for mesh_hosts in meshes:
            self._update_depth_of_mesh(mesh_hosts)

    def _update_depth_of_mesh(self, mesh_hosts):
        for hostname in list(mesh_hosts):
            if hostname in self._depth_info:
                continue
            self._depth_info[hostname] = self._current_iteration


class TopologyRegistry(cmk.utils.plugin_registry.ClassRegistry):
    def plugin_base_class(self):
        return Topology

    def plugin_name(self, plugin_class):
        return plugin_class.ident()


topology_registry = TopologyRegistry()


class ParentChildNetworkTopology(Topology):
    """ Generates parent/child topology view """
    @classmethod
    def ident(cls):
        return "parent_child"

    def title(self):
        return _("Parent / Child topology")

    def _fetch_data_for_hosts(self, hostnames):
        hostname_filters = []
        if hostnames:
            for hostname in hostnames:
                hostname_filters.append("Filter: host_name = %s" % hostname)
            hostname_filters.append("Or: %d" % len(hostnames))

        # Abstract parents/children to be more generic: children(incoming) / parents(outgoing)
        return sites.live().query("GET hosts\nColumns: name alias icon_image parents childs\n%s" %
                                  "\n".join(hostname_filters))


topology_registry.register(ParentChildNetworkTopology)
