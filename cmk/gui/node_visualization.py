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


@cmk.gui.pages.register("bi_map")
def _bi_map():
    aggr_name = html.request.var("aggr_name")
    layout_id = html.request.var("layout_id")
    html.header("BI visualization")
    div_id = "node_visualization"
    html.div("", id=div_id)
    html.javascript(
        "node_instance = new cmk.node_visualization.BIVisualization(%s);" % json.dumps(div_id))

    html.javascript("node_instance.set_theme(%s)" % json.dumps(html.get_theme()))
    html.javascript("node_instance.show_aggregations(%s, %s)" % (json.dumps([aggr_name]),
                                                                 json.dumps(layout_id)))


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

            if not forced_layout_id:
                if aggr_name in aggregation_layouts:
                    data["use_layout_id"] = aggr_name
                    data["use_layout"] = aggregation_layouts[aggr_name]
                    data["layout_origin"] = _("Explicit set")
                else:
                    template_layout_id = row["tree"]["aggr_tree"]["use_layout_id"]
                    if template_layout_id and template_layout_id in BILayoutManagement.get_all_bi_template_layouts(
                    ):
                        data["use_layout"] = BILayoutManagement.load_bi_template_layout(
                            template_layout_id)
                        data["layout_origin"] = _("Template: %s" % template_layout_id)
                    else:
                        data["use_default_layout"] = config.default_bi_layout
                        data["layout_origin"] = _(
                            "Default layout: %s" % config.default_bi_layout.title())

            aggregation_info["aggregations"][row["tree"]["aggr_name"]] = data

        if forced_layout_id:
            aggregation_info["use_layout"] = BILayoutManagement.load_bi_template_layout(
                forced_layout_id)

        html.set_output_format("json")
        return aggregation_info


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
        store.save_to_mk_file(
            str(BILayoutManagement._config_file),
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


# Feature currently under the radar (unavailable)
@page_registry.register_page("ajax_fetch_network_topology")
class AjaxFetchNetworkTopology(AjaxPage):
    def page(self):
        filtered_nodes = html.request.var("hostnames")
        if filtered_nodes:
            filtered_nodes = json.loads(filtered_nodes)

        child_nodes = {}
        root_nodes = set()
        single_hosts = set()
        chunks = []

        topology_info = {"nodes": [], "links": []}
        for hostname, parents, childs in sites.live().query(
                "GET hosts\nColumns: name parents childs"):
            if filtered_nodes:
                for node in filtered_nodes:
                    if hostname == node or node in parents or node in childs:
                        break
                else:
                    continue
            if not parents and not childs:
                single_hosts.add(hostname)
                continue
            if not parents:
                root_nodes.add(hostname)
            if childs:
                child_nodes[hostname] = childs

        for hostname, childs in child_nodes.iteritems():
            chunks.append(set([hostname] + childs))

        while True:
            changed_chunks = False
            for idx in range(0, len(chunks) - 1):
                current_bundle = chunks[idx]
                for check_bundle in chunks[idx + 1:len(chunks)]:
                    if current_bundle.intersection(check_bundle):
                        new_bundle = current_bundle.union(check_bundle)
                        chunks[idx] = new_bundle
                        chunks.remove(check_bundle)
                        changed_chunks = True
                        break
                if changed_chunks:
                    break

            if not changed_chunks:
                break

        topology_info = {"topology_chunks": {}}

        def get_topology_info(hostname):
            return {
                "hostname": hostname,
                "in_downtime": False,
                "acknowledged": False,
                "icon": "",
                "node_type": "topology",
                "topology_root": hostname in root_nodes,
                "rule_id": "no_rule",
                "name": hostname,
                "id": hostname,
                "state": 0,
            }

        for chunk in chunks:
            # Pick root host
            chunk = list(chunk)
            root_host = chunk[0]
            chunk_info = get_topology_info(root_host)
            if len(chunk) > 1:
                chunk_info["children"] = []
                chunk_info["children"].extend([get_topology_info(x) for x in chunk[1:]])

            chunk_links = []
            for idx, hostname in enumerate(chunk):
                for child in child_nodes.get(hostname, []):
                    chunk_links.append([chunk.index(child), idx])

            topology_info["topology_chunks"][root_host] = {
                "hierarchy": chunk_info,
                "links": chunk_links
            }

        html.set_output_format("json")
        return topology_info
