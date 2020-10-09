// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

import * as node_visualization_toolbar from "node_visualization_toolbar";
import * as node_visualization_datasources from "node_visualization_datasources";
import * as node_visualization_viewport from "node_visualization_viewport";
import * as node_visualization_infobox from "node_visualization_infobox";
import * as node_visualization_utils from "node_visualization_utils";
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

        this.gui_theme = "facelift";

        this._div_selection = null;
        this.datasource_manager = null;
        this.viewport = null;
        this.infobox = null;
        this.toolbar = null;

        this._initialize_components();

        this.datasource_manager.schedule();
    }

    get_theme_prefix(new_theme) {
        return "themes/" + this.gui_theme;
    }

    set_theme(new_theme) {
        this.gui_theme = new_theme;
    }

    set_initial_overlays_config(overlay_config) {
        this._initial_overlay_config = overlay_config;
    }

    get_initial_overlays_config() {
        return this._initial_overlay_config;
    }

    _initialize_components() {
        this._div_selection = d3
            .select("#" + this.div_id)
            .append("div")
            .attr("id", "node_visualization_root_div")
            .attr("div_id", this.div_id)
            .classed("node_vis", true); // Main indicator for most NodeVisualization css styles

        let viewport_selection = this._div_selection.append("div");
        let toolbar_selection = this._div_selection.append("div");
        let infobox_selection = this._div_selection.append("div");

        this.datasource_manager = new node_visualization_datasources.DatasourceManager();
        this.toolbar = new node_visualization_toolbar.Toolbar(this, toolbar_selection);
        this.viewport = new node_visualization_viewport.Viewport(this, viewport_selection);
        this.infobox = new node_visualization_infobox.InfoBox(this, infobox_selection);
    }

    get_div_selection() {
        return this._div_selection;
    }
}

export class BIVisualization extends NodeVisualization {
    show_aggregations(list_of_aggregations, use_layout_id) {
        let aggr_ds = this.datasource_manager.get_datasource(
            node_visualization_datasources.AggregationsDatasource.id()
        );
        aggr_ds.enable();
        aggr_ds.subscribe_new_data(d => this._show_aggregations(list_of_aggregations));
        aggr_ds.fetch_aggregations(list_of_aggregations, use_layout_id);
    }

    _show_aggregations(list_of_aggregations) {
        if (list_of_aggregations.length > 0)
            d3.select("table.header td.heading a").text(list_of_aggregations[0]);

        let aggr_ds = this.datasource_manager.get_datasource(
            node_visualization_datasources.AggregationsDatasource.id()
        );
        let fetched_data = aggr_ds.get_data();

        let data_to_show = {chunks: []};
        for (let idx in fetched_data["aggregations"]) {
            data_to_show.chunks.push(fetched_data["aggregations"][idx]);
        }

        if (fetched_data.use_layout) data_to_show.use_layout = fetched_data.use_layout;

        this.viewport.show_data("bi_aggregations", data_to_show);
    }
}

export class TopologyVisualization extends NodeVisualization {
    constructor(div_id, mode) {
        super(div_id);
        this._mode = mode;
        this._mesh_depth = 0; // Number of hops from growth root
        this._max_nodes = 200; // Maximum allowed nodes
        this._growth_auto_max_nodes = null; // Automatically stop growth when this limit is reached (handled on server side)
        this.custom_topology_fetch_parameters = {}; // Custom parameter, added to each fetch request
    }
    show_topology(list_of_hosts) {
        let topo_ds = this.datasource_manager.get_datasource(
            node_visualization_datasources.TopologyDatasource.id()
        );
        topo_ds.enable();
        topo_ds.set_update_interval(30);
        //this.viewport.current_viewport.always_update_layout = true

        topo_ds.subscribe_new_data(d => this._show_topology(list_of_hosts));

        this.add_depth_slider();
        this.add_max_nodes_slider();

        this.update_sliders();
        topo_ds.fetch_hosts({
            growth_root_nodes: list_of_hosts,
            growth_auto_max_nodes: this._growth_auto_max_nodes,
            mesh_depth: this._mesh_depth,
            max_nodes: this._max_nodes,
            mode: this._mode,
        });
    }

    set_growth_auto_max_nodes(value) {
        this._growth_auto_max_nodes = value;
    }

    set_max_nodes(value) {
        this._max_nodes = value;
    }

    set_mesh_depth(value) {
        this._mesh_depth = value;
    }

    _show_topology(list_of_hosts) {
        let topo_ds = this.datasource_manager.get_datasource(
            node_visualization_datasources.TopologyDatasource.id()
        );
        let ds_data = topo_ds.get_data();

        if (ds_data["headline"]) d3.select("tbody tr td.heading a").text(ds_data["headline"]);

        let topology_data = ds_data["topology_chunks"];
        this._show_topology_errors(ds_data["errors"]);

        let data_to_show = {chunks: []};
        for (let idx in topology_data) {
            data_to_show.chunks.push(topology_data[idx]);
        }
        this.viewport.show_data("topology", data_to_show);
        this.viewport.current_viewport.layout_manager.enforce_node_drag();
    }

    _show_topology_errors(errors) {
        d3.select("label#max_nodes_error_text").text(errors);
    }

    add_depth_slider() {
        let slider = d3
            .select("div#toolbar_controls div#custom")
            .selectAll("div.mesh_depth_slider")
            .data([null]);
        let slider_enter = slider.enter().append("div").classed("topology_slider", true);

        slider_enter
            .append("label")
            .style("padding-left", "12px")
            .text("Number of hops")
            .classed("noselect", true);
        slider_enter
            .append("input")
            .classed("mesh_depth_slider", true)
            .style("pointer-events", "all")
            .attr("type", "range")
            .attr("step", 1)
            .attr("min", d => 0)
            .attr("max", d => 20)
            .on("input", () => {
                this._mesh_depth = d3.select("input.mesh_depth_slider").property("value");
                this.update_sliders();
                this.update_data();
            })
            .property("value", this._mesh_depth);
        slider_enter.append("label").attr("id", "mesh_depth_text");

        d3.select("form#form_filter input[name=topology_mesh_depth]").remove();
        d3.select("form#form_filter")
            .append("input")
            .attr("name", "topology_mesh_depth")
            .attr("type", "hidden")
            .property("value", this._mesh_depth);
    }

    add_max_nodes_slider() {
        let slider = d3
            .select("div#toolbar_controls div#custom")
            .selectAll("div.max_nodes_slider")
            .data([null]);
        let slider_enter = slider.enter().append("div").classed("topology_slider", true);

        slider_enter
            .append("label")
            .style("padding-left", "12px")
            .text("Maximum number of nodes")
            .classed("noselect", true);
        slider_enter
            .append("input")
            .classed("max_nodes_slider", true)
            .style("pointer-events", "all")
            .attr("type", "range")
            .attr("step", 10)
            .attr("min", d => 20)
            .attr("max", d => 2000)
            .on("input", () => {
                this._max_nodes = d3.select("input.max_nodes_slider").property("value");
                this.update_sliders();
                this.update_data();
            })
            .property("value", this._max_nodes);
        slider_enter.append("label").attr("id", "max_nodes_text").text(this._max_nodes);
        slider_enter
            .append("label")
            .attr("id", "max_nodes_error_text")
            .style("color", "red")
            .style("display", "block")
            .style("margin-left", "12px")
            .style("margin-top", "-5px");

        d3.select("form#form_filter input[name=topology_max_nodes]").remove();
        d3.select("form#form_filter")
            .append("input")
            .attr("name", "topology_max_nodes")
            .attr("type", "hidden")
            .property("value", this._max_nodes);
    }

    update_sliders() {
        d3.select("#max_nodes_slider").property("value", this._max_nodes);
        d3.select("#max_nodes_text").text(this._max_nodes);
        d3.select("form#form_filter input[name=topology_max_nodes]").property(
            "value",
            this._max_nodes
        );

        d3.select("#mesh_depth_slider").property("value", this._mesh_depth);
        d3.select("#mesh_depth_text").text(this._mesh_depth);
        d3.select("form#form_filter input[name=topology_mesh_depth]").property(
            "value",
            this._mesh_depth
        );
    }

    update_data() {
        let growth_root_nodes = [];
        let growth_forbidden_nodes = [];
        let growth_continue_nodes = [];

        this.viewport.current_viewport.get_all_nodes().forEach(node => {
            if (node.data.growth_root) growth_root_nodes.push(node.data.hostname);
            if (node.data.growth_forbidden) growth_forbidden_nodes.push(node.data.hostname);
            if (node.data.growth_continue) growth_continue_nodes.push(node.data.hostname);
        });

        let ds = this.datasource_manager.get_datasource(
            node_visualization_datasources.TopologyDatasource.id()
        );

        let config = {
            growth_root_nodes: growth_root_nodes,
            mesh_depth: this._mesh_depth,
            max_nodes: this._max_nodes,
            growth_forbidden_nodes: growth_forbidden_nodes,
            growth_continue_nodes: growth_continue_nodes,
            mode: this._mode,
        };

        for (let key in this.custom_topology_fetch_parameters) {
            config[key] = this.custom_topology_fetch_parameters[key];
        }
        ds.fetch_hosts(config);
    }
}
