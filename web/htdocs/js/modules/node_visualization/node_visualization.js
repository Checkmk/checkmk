// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
// +------------------------------------------------------------------+
//
// This file is part of Check_MK.
// The official homepage is at http://mathias-kettner.de/check_mk.
//
// check_mk is free software;  you can redistribute it and/or modify it
// under the  terms of the  GNU General Public License  as published by
// the Free Software Foundation in version 2.  check_mk is  distributed
// in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
// out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
// PARTICULAR PURPOSE. See the  GNU General Public License for more de-
// tails.  You should have received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

import * as node_visualization_toolbar from "node_visualization_toolbar"
import * as node_visualization_datasources from "node_visualization_datasources"
import * as node_visualization_viewport from "node_visualization_viewport"
import * as node_visualization_infobox from "node_visualization_infobox"
import * as utils from "node_visualization_utils"
import * as d3 from "d3";

//
//  .--MainInstance--------------------------------------------------------.
//  |     __  __       _       ___           _                             |
//  |    |  \/  | __ _(_)_ __ |_ _|_ __  ___| |_ __ _ _ __   ___ ___       |
//  |    | |\/| |/ _` | | '_ \ | || '_ \/ __| __/ _` | '_ \ / __/ _ \      |
//  |    | |  | | (_| | | | | || || | | \__ \ || (_| | | | | (_|  __/      |
//  |    |_|  |_|\__,_|_|_| |_|___|_| |_|___/\__\__,_|_| |_|\___\___|      |
//  |                                                                      |
//  +----------------------------------------------------------------------+

class NodeVisualization {
    constructor(div_id) {
        this.div_id = div_id;

        this.gui_theme = "facelift"

        this.div_selection = null
        this.datasource_manager = null
        this.viewport = null
        this.infobox = null
        this.toolbar = null

        this._initialize_components()

        this.datasource_manager.schedule()
    }

    get_theme_prefix(new_theme) {
        return "themes/" + this.gui_theme
    }

    set_theme(new_theme) {
        this.gui_theme = new_theme
    }

    _initialize_components() {
        this.div_selection = d3.select("#" + this.div_id).append("div")
                                        .attr("id", "node_visualization_root_div")
                                        .attr("div_id", this.div_id)
                                        .classed("node_vis", true) // Main indicator for most NodeVisualization css styles

        this.datasource_manager = new node_visualization_datasources.DatasourceManager()
        this.viewport = new node_visualization_viewport.Viewport(this)
        this.infobox = new node_visualization_infobox.InfoBox(this)
        this.toolbar = new node_visualization_toolbar.Toolbar(this)
    }

    get_div_selection() {
        return this.div_selection;
    }
}


export class BIVisualization extends NodeVisualization {
    show_aggregations(list_of_aggregations, use_layout_id) {
        let aggr_ds = this.datasource_manager.get_datasource(node_visualization_datasources.AggregationsDatasource.id())
        aggr_ds.subscribe_new_data(d=>this._show_aggregations(list_of_aggregations))
        aggr_ds.fetch_aggregations(list_of_aggregations, use_layout_id)
    }

    _show_aggregations(list_of_aggregations) {
        if (list_of_aggregations.length > 0)
            d3.select("table.header td.heading a").text(list_of_aggregations[0])

        let aggr_ds = this.datasource_manager.get_datasource(node_visualization_datasources.AggregationsDatasource.id())
        let fetched_data = aggr_ds.get_data()

        let data_to_show = {chunks: []}
        for (let idx in fetched_data["aggregations"]) {
            data_to_show.chunks.push(fetched_data["aggregations"][idx])
        }

        if (fetched_data.use_layout)
            data_to_show.use_layout = fetched_data.use_layout

        this.viewport.show_data("bi_aggregations", data_to_show)
    }
}


export class TopologyVisualization extends NodeVisualization {
    constructor(div_id, mode) {
        super(div_id)
        this._mode = mode
    }
    show_topology(list_of_hosts) {
        let topo_ds = this.datasource_manager.get_datasource(node_visualization_datasources.TopologyDatasource.id())
        topo_ds.subscribe_new_data(d=>this._show_topology(list_of_hosts))
        this._default_depth = 0
        this.add_depth_slider()
        topo_ds.fetch_hosts({growth_root_nodes: list_of_hosts, mesh_depth: this._default_depth, mode: this._mode})
    }

    _show_topology(list_of_hosts) {
        let topo_ds = this.datasource_manager.get_datasource(node_visualization_datasources.TopologyDatasource.id())
        let ds_data = topo_ds.get_data()

        if (ds_data["headline"])
            d3.select("tbody tr td.heading a").text(ds_data["headline"])

        let topology_data = ds_data["topology_chunks"]

        let data_to_show = {chunks: []}
        for (let idx in topology_data) {
            data_to_show.chunks.push(topology_data[idx])
        }
        this.viewport.show_data("topology", data_to_show)
        this.viewport.current_viewport.layout_manager.enforce_node_drag()
    }

    add_depth_slider() {
        let slider = d3.select("#toolbar").selectAll(".depth_slider").data([null])
        let slider_enter = slider.enter().append("div")
                            .classed("depth_slider", true)
                            .style("position", "absolute")

        slider_enter.append("label")
                    .style("padding-left", "12px")
                    .text("Number of hops")
                    .classed("noselect", true)
        slider_enter.append("input")
                    .classed("depth_slider", true)
                    .style("pointer-events", "all")
                    .attr("type", "range")
                    .attr("step", 1)
                    .attr("min", d=>0)
                    .attr("max", d=>20)
                    .on("input", ()=>{
                        let new_range = d3.select("input.depth_slider").property("value")
                        d3.select("#depth_range_text").text(new_range)
                        this.update_data()
                    })
                    .property("value", this._default_depth)
        slider_enter.append("label").attr("id", "depth_range_text").text(this._default_depth)
    }

    update_data() {
        let growth_root_nodes = []
        let growth_forbidden_nodes = []

        this.viewport.current_viewport.get_all_nodes().forEach(node=>{
            if (node.data.growth_root)
                growth_root_nodes.push(node.data.hostname)
            if (node.data.growth_forbidden)
                growth_forbidden_nodes.push(node.data.hostname)
        })

        let current_depth = +d3.select("input.depth_slider").property("value")
        let ds = this.datasource_manager.get_datasource(node_visualization_datasources.TopologyDatasource.id())
        ds.fetch_hosts({growth_root_nodes: growth_root_nodes,
                        mesh_depth: current_depth,
                        growth_forbidden_nodes: growth_forbidden_nodes,
                        mode: this._mode});
    }
}
