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
import * as node_visualization_utils from "node_visualization_utils"
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
        this._mesh_depth = 0 // Number of hops from growth root
        this._max_nodes = 200 // Maximum allowed nodes
        this._growth_auto_max_nodes = null // Automatically stop growth when this limit is reached (handled on server side)
    }
    show_topology(list_of_hosts) {
        let topo_ds = this.datasource_manager.get_datasource(node_visualization_datasources.TopologyDatasource.id())
        topo_ds.subscribe_new_data(d=>this._show_topology(list_of_hosts))


        this.add_search_togglebutton()
        this.add_depth_slider()
        this.add_max_nodes_slider()
        this.viewport.current_viewport.always_update_layout = true

        this.update_sliders()
        topo_ds.fetch_hosts({growth_root_nodes: list_of_hosts,
                        growth_auto_max_nodes: this._growth_auto_max_nodes,
                        mesh_depth: this._mesh_depth,
                        max_nodes: this._max_nodes,
                        mode: this._mode});
    }

    set_growth_auto_max_nodes(value) {
        this._growth_auto_max_nodes = value
    }

    set_max_nodes(value) {
        this._max_nodes = value
    }

    set_mesh_depth(value) {
        this._mesh_depth = value
    }

    _show_topology(list_of_hosts) {
        let topo_ds = this.datasource_manager.get_datasource(node_visualization_datasources.TopologyDatasource.id())
        let ds_data = topo_ds.get_data()

        if (ds_data["headline"])
            d3.select("tbody tr td.heading a").text(ds_data["headline"])

        let topology_data = ds_data["topology_chunks"]
        this._show_topology_errors(ds_data["errors"])

        let data_to_show = {chunks: []}
        for (let idx in topology_data) {
            data_to_show.chunks.push(topology_data[idx])
        }
        this.viewport.show_data("topology", data_to_show)
        this.viewport.current_viewport.layout_manager.enforce_node_drag()
    }

    _show_topology_errors(errors) {
        d3.select("label#max_nodes_error_text").text(errors)
    }

    add_search_togglebutton() {
        let togglebuttons = d3.select("div#togglebuttons")
        let search = togglebuttons.selectAll("div#search").data([null])
        search.enter().append("div")
            .attr("id", "search")
            .classed("box", true)
            .classed("togglebutton", true)
            .classed("filters", true)
            .style("cursor", "pointer")
            .classed("noselect", true)
            .classed("box", true)
            .classed("on", true)
            .classed("up", true)
            .on("click", ()=>this._toggle_search())
            .append("img")
            .attr("src", this.get_theme_prefix() + "/images/icon_filter.png")
            .attr("title", "Search")
            .style("opacity", 1)

        d3.select("#topology_filters").style("height", "0px")
    }

    _toggle_search() {
        let search = d3.select("div#togglebuttons div#search");
        let is_up = search.classed("up")
        if (is_up) {
            search.classed("up", false)
            search.classed("down", true)
            node_visualization_utils.DefaultTransition.add_transition(d3.select("#topology_filters")).style("height", null)
        } else {
            search.classed("up", true)
            search.classed("down", false)
            node_visualization_utils.DefaultTransition.add_transition(d3.select("#topology_filters")).style("height", "0px")
        }
    }

    add_depth_slider() {
        let slider = d3.select("#togglebuttons").selectAll("div.mesh_depth_slider").data([null])
        let slider_enter = slider.enter().append("div")
                    .classed("topology_slider", true)

        slider_enter.append("label")
                    .style("padding-left", "12px")
                    .text("Number of hops")
                    .classed("noselect", true)
        slider_enter.append("input")
                    .classed("mesh_depth_slider", true)
                    .style("pointer-events", "all")
                    .attr("type", "range")
                    .attr("step", 1)
                    .attr("min", d=>0)
                    .attr("max", d=>20)
                    .on("input", ()=>{
                        this._mesh_depth = d3.select("input.mesh_depth_slider").property("value");
                        this.update_sliders();
                        this.update_data();
                    })
                    .property("value", this._mesh_depth)
        slider_enter.append("label").attr("id", "mesh_depth_text")
    }

    add_max_nodes_slider() {
        let slider = d3.select("#togglebuttons").selectAll("div.max_nodes_slider").data([null])
        let slider_enter = slider.enter().append("div")
                    .classed("topology_slider", true)

        slider_enter.append("label")
                    .style("padding-left", "12px")
                    .text("Maximum number of nodes")
                    .classed("noselect", true)
        slider_enter.append("input")
                    .classed("max_nodes_slider", true)
                    .style("pointer-events", "all")
                    .attr("type", "range")
                    .attr("step", 10)
                    .attr("min", d=>20)
                    .attr("max", d=>2000)
                    .on("input", ()=>{
                        this._max_nodes = d3.select("input.max_nodes_slider").property("value");
                        this.update_sliders();
                        this.update_data();
                    })
                    .property("value", this._max_nodes)
        slider_enter.append("label").attr("id", "max_nodes_text").text(this._max_nodes)
        slider_enter.append("label").attr("id", "max_nodes_error_text")
                    .style("color", "red")
                    .style("display", "block")
                    .style("margin-left", "12px")
                    .style("margin-top", "-5px")
    }

    update_sliders() {
        d3.select("#max_nodes_slider").property("value", this._max_nodes)
        d3.select("#max_nodes_text").text(this._max_nodes)
        d3.select("div#topology_filters input[name=topology_max_nodes]").property("value", this._max_nodes)

        d3.select("#mesh_depth_slider").property("value", this._mesh_depth)
        d3.select("#mesh_depth_text").text(this._mesh_depth)
        d3.select("div#topology_filters input[name=topology_mesh_depth]").property("value", this._mesh_depth)
    }

    update_data() {
        let growth_root_nodes = []
        let growth_forbidden_nodes = []
        let growth_continue_nodes = []

        this.viewport.current_viewport.get_all_nodes().forEach(node=>{
            if (node.data.growth_root)
                growth_root_nodes.push(node.data.hostname)
            if (node.data.growth_forbidden)
                growth_forbidden_nodes.push(node.data.hostname)
            if (node.data.growth_continue)
                growth_continue_nodes.push(node.data.hostname)
        })

        let ds = this.datasource_manager.get_datasource(node_visualization_datasources.TopologyDatasource.id())
        ds.fetch_hosts({growth_root_nodes: growth_root_nodes,
                        mesh_depth: this._mesh_depth,
                        max_nodes: this._max_nodes,
                        growth_forbidden_nodes: growth_forbidden_nodes,
                        growth_continue_nodes: growth_continue_nodes,
                        mode: this._mode});
    }
}
