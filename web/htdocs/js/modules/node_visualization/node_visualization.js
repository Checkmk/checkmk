// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
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

        this._div_selection = null;
        this.datasource_manager = null;
        this.viewport = null;
        this.infobox = null;
        this.toolbar = null;

        this._initialize_components();

        this.datasource_manager.schedule();
    }

    update_browser_url() {
        // The browser url can be used as bookmark
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
        this.custom_topology_fetch_parameters = {}; // Custom parameter, added to each fetch request

        // Parameters used for throttling the GUI update
        this._last_update_request = 0;
        this._update_request_timer_active = false;
    }

    update_browser_url() {
        let current_url = new URL(window.location);

        this._topology_settings.overlays_config =
            this.viewport.current_viewport.get_overlay_configs();
        current_url.searchParams.set("topology_settings", JSON.stringify(this._topology_settings));
        window.history.replaceState({}, "", current_url.toString());
    }

    show_topology(topology_settings) {
        this._topology_settings = topology_settings;

        let topo_ds = this.datasource_manager.get_datasource(
            node_visualization_datasources.TopologyDatasource.id()
        );
        topo_ds.enable();
        topo_ds.set_update_interval(30);

        topo_ds.subscribe_new_data(d => this._show_topology());
        for (let idx in topology_settings.overlays_config) {
            this.viewport.current_viewport.set_overlay_config(
                idx,
                topology_settings.overlays_config[idx]
            );
        }

        this.add_depth_slider();
        this.add_max_nodes_slider();
        this.update_sliders();
        topo_ds.fetch_hosts(topology_settings);
    }

    _show_topology() {
        this.update_sliders();

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
                this._topology_settings.mesh_depth = parseInt(
                    d3.select("input.mesh_depth_slider").property("value")
                );
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
            .attr("min", 20)
            .attr("max", 2000)
            .on("input", () => {
                this._topology_settings.max_nodes = parseInt(
                    d3.select("input.max_nodes_slider").property("value")
                );
                this.update_sliders();
                this.update_data();
            });
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
            .attr("type", "hidden");
    }

    update_sliders() {
        d3.select("input.max_nodes_slider").property("value", this._topology_settings.max_nodes);
        d3.select("#max_nodes_text").text(this._topology_settings.max_nodes);
        d3.select("form#form_filter input[name=topology_max_nodes]").property(
            "value",
            this._topology_settings.max_nodes
        );

        d3.select("input.mesh_depth_slider").property("value", this._topology_settings.mesh_depth);
        d3.select("#mesh_depth_text").text(this._topology_settings.mesh_depth);
        d3.select("form#form_filter input[name=topology_mesh_depth]").property(
            "value",
            this._topology_settings.mesh_depth
        );
    }

    update_data() {
        if (this._throttle_update()) return;

        this._topology_settings.overlays_config =
            this.viewport.current_viewport.get_overlay_configs();
        this._topology_settings.growth_root_nodes = [];
        this._topology_settings.growth_forbidden_nodes = [];
        this._topology_settings.growth_continue_nodes = [];

        this.viewport.current_viewport.get_all_nodes().forEach(node => {
            if (node.data.growth_root)
                this._topology_settings.growth_root_nodes.push(node.data.hostname);
            if (node.data.growth_forbidden)
                this._topology_settings.growth_forbidden_nodes.push(node.data.hostname);
            if (node.data.growth_continue)
                this._topology_settings.growth_continue_nodes.push(node.data.hostname);
        });

        let ds = this.datasource_manager.get_datasource(
            node_visualization_datasources.TopologyDatasource.id()
        );

        for (let key in this.custom_topology_fetch_parameters) {
            this._topology_settings[key] = this.custom_topology_fetch_parameters[key];
        }

        this.update_browser_url();
        ds.fetch_hosts(this._topology_settings);
    }

    _throttle_update() {
        let now = new Date().getTime() / 1000;
        let min_delay = 0.2;
        if (now - self._last_update_request < min_delay) {
            if (!self._update_request_timer_active) {
                self._update_request_timer_active = true;
                setTimeout(() => this.update_data(), min_delay * 1000);
            }
            return true;
        }
        self._last_update_request = now;
        self._update_request_timer_active = false;
        return false;
    }
}
