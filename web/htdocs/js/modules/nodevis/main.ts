/**
 * Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import * as d3 from "d3";
import {
    AggregationsDatasource,
    DatasourceManager,
    TopologyDatasource,
} from "nodevis/datasources";
import {LayoutStyleExampleGenerator} from "nodevis/example_generator";
import {
    BIForceConfig,
    ForceConfig,
    ForceOptions,
    ForceSimulation,
} from "nodevis/force_simulation";
import {InfoBox} from "nodevis/infobox";
import {layer_class_registry, OverlayConfig} from "nodevis/layer_utils";
import {LayeredNodesLayer} from "nodevis/layers";
import {LayoutManagerLayer} from "nodevis/layout";
import {
    layout_style_class_registry,
    LineConfig,
    StyleConfig,
} from "nodevis/layout_utils";
import {node_type_class_registry} from "nodevis/node_utils";
import {Toolbar} from "nodevis/toolbar";
import {
    BackendChunkResponse,
    d3SelectionDiv,
    NodevisWorld,
    Rectangle,
} from "nodevis/type_defs";
import {LiveSearch, SearchFilters} from "nodevis/utils";
import {LayeredViewport} from "nodevis/viewport";

//
//  .--MainInstance--------------------------------------------------------.
//  |     __  __       _       ___           _                             |
//  |    |  \/  | __ _(_)_ __ |_ _|_ __  ___| |_ __ _ _ __   ___ ___       |
//  |    | |\/| |/ _` | | '_ \ | || '_ \/ __| __/ _` | '_ \ / __/ _ \      |
//  |    | |  | | (_| | | | | || || | | \__ \ || (_| | | | | (_|  __/      |
//  |    |_|  |_|\__,_|_|_| |_|___|_| |_|___/\__\__,_|_| |_|\___\___|      |
//  |                                                                      |
//  +----------------------------------------------------------------------+

export class NodeVisualization {
    _div_id: string;
    _div_selection: d3SelectionDiv;
    _world: NodevisWorld;
    static _nodevis_type = "nodevis";

    constructor(div_id: string) {
        this._div_id = div_id;
        this._div_selection = d3.select("#" + this._div_id).append("div");
        this._world = this._create_world();
        this._world.datasource_manager.schedule();
    }

    update_browser_url(): void {
        // The browser url can be used as bookmark
    }

    _get_force_config(): typeof ForceConfig {
        return ForceConfig;
    }

    _create_world(): NodevisWorld {
        // Horrible startup..
        // This block is the biggest challenge in the upcoming refactoring
        // At least, once we through this block everything is initialized correctly..
        this._div_selection
            .attr("id", "node_visualization_root_div")
            .attr("div_id", this._div_id)
            .classed("node_vis", true) // Main indicator for most NodeVisualization css styles
            .style("height", "100%");

        const viewport_selection = this._div_selection.append("div");
        const toolbar_selection = this._div_selection.append("div");
        const infobox_selection = this._div_selection.append("div");

        // TODO: super ugly, couldn't find a better solution
        const fake_world = this._create_fake_world();

        // @ts-ignore
        fake_world.current_datasource = this.constructor._nodevis_type;
        const datasource_manager = new DatasourceManager();
        const toolbar = new Toolbar(fake_world, toolbar_selection);
        const viewport = new LayeredViewport(fake_world, viewport_selection);
        const infobox = new InfoBox(fake_world, infobox_selection);
        const force_simulation = new ForceSimulation(
            fake_world,
            this._get_force_config()
        );

        // Setup components which require a real world
        toolbar.setup_world_components();
        fake_world.root_div = this._div_selection;
        fake_world.datasource_manager = datasource_manager;
        fake_world.toolbar = toolbar;
        fake_world.viewport = viewport;
        fake_world.infobox = infobox;
        fake_world.force_simulation = force_simulation;
        fake_world.main_instance = this; // TODO: get rid of this
        fake_world.update_data = () => this.update_data();
        fake_world.update_browser_url = () => this.update_browser_url();
        fake_world.save_layout = () => this.save_layout();
        fake_world.delete_layout = () => this.delete_layout();

        viewport.setup_world_components();
        fake_world.nodes_layer = viewport.get_layer(
            "nodes"
        ) as LayeredNodesLayer;
        fake_world.layout_manager = viewport.get_layer(
            "layout_manager"
        ) as LayoutManagerLayer;
        fake_world.toolbar.update_toolbar_plugins();

        return fake_world;
    }

    _create_fake_world(): NodevisWorld {
        // This world is only used on startup
        // Couldn't find better a way to make some globals available to all instances
        return {} as NodevisWorld;
    }

    get_div_selection(): d3SelectionDiv {
        return this._div_selection;
    }

    update_data(): void {
        return;
    }

    save_layout() {
        return;
    }

    delete_layout() {
        return;
    }
}

export class BIVisualization extends NodeVisualization {
    static _nodevis_type = "bi_aggregations";
    constructor(div_id) {
        super(div_id);
    }

    show_aggregations(list_of_aggregations, use_layout_id) {
        const aggr_ds = this._world.datasource_manager.get_datasource(
            AggregationsDatasource.id()
        ) as AggregationsDatasource;
        aggr_ds.enable();
        aggr_ds.subscribe_new_data(() =>
            this._show_aggregations(list_of_aggregations)
        );
        aggr_ds.fetch_aggregations(list_of_aggregations, use_layout_id);
    }

    _get_force_config(): typeof ForceConfig {
        return BIForceConfig;
    }

    _show_aggregations(list_of_aggregations): void {
        if (list_of_aggregations.length > 0)
            d3.select("table.header td.heading a").text(
                list_of_aggregations[0]
            );

        const aggr_ds = this._world.datasource_manager.get_datasource(
            AggregationsDatasource.id()
        );
        const fetched_data = aggr_ds.get_data();

        const data_to_show: BackendChunkResponse = {chunks: []};
        for (const idx in fetched_data["aggregations"]) {
            const data: any = fetched_data["aggregations"][idx];
            data_to_show.chunks.push(data);
        }
        if (fetched_data.use_layout)
            data_to_show.use_layout = fetched_data.use_layout;

        this._world.viewport.feed_data(data_to_show);
    }
}

class TopologySettings {
    growth_root_nodes: string[];
    growth_forbidden_nodes: string[];
    growth_continue_nodes: string[];
    display_mode: string;
    max_nodes: number;
    mesh_depth: number;
    overlays_config: {[name: string]: any};

    constructor(
        growth_root_nodes: string[] = [],
        growth_forbidden_nodes: string[] = [],
        growth_continue_nodes: string[] = [],
        display_mode = "parent_child",
        max_nodes = 2000,
        mesh_depth = 2,
        overlays_config: {[name: string]: any} = {}
    ) {
        this.growth_root_nodes = growth_root_nodes;
        this.growth_forbidden_nodes = growth_forbidden_nodes;
        this.growth_continue_nodes = growth_continue_nodes;
        this.display_mode = display_mode;
        this.max_nodes = max_nodes;
        this.mesh_depth = mesh_depth;
        this.overlays_config = overlays_config;
    }
}

function _parse_topology_settings(data): TopologySettings {
    return new TopologySettings(
        data.growth_root_nodes,
        data.growth_forbidden_nodes,
        data.growth_continue_nodes,
        data.display_mode,
        data.max_nodes,
        data.mesh_depth
    );
}

interface TopologyFrontendConfig {
    overlays_config: {[name: string]: OverlayConfig};
    growth_root_nodes: string[];
    growth_forbidden_nodes: string[];
    growth_continue_nodes: string[];
    custom_node_settings: {[name: string]: any};
    datasource_configuration: {
        available_datasources: string[];
        reference: string;
        compare_to: string;
    };
    reference_size: Rectangle;
    style_configs: StyleConfig[];
    line_config: LineConfig;
    force_options: ForceOptions;
}

export class TopologyVisualization extends NodeVisualization {
    static _nodevis_type = "topology";
    _custom_topology_fetch_parameters: {[name: string]: any} = {};
    _custom_node_settings_memory = {};
    _last_update_request: number;
    _update_request_timer_active = false;
    _topology_datasource: TopologyDatasource;
    _topology_type: string;
    _frontend_configuration: TopologyFrontendConfig | null = null;
    _livesearch: LiveSearch;

    constructor(div_id, topology_type) {
        super(div_id);
        this._topology_type = topology_type;
        this._topology_datasource =
            this._world.datasource_manager.get_datasource(
                TopologyDatasource.id()
            ) as TopologyDatasource;

        this._livesearch = new LiveSearch("form#form_filter", () =>
            this.update_data()
        );
        this._custom_node_settings_memory = {};

        // Parameters used for throttling the GUI update
        this._last_update_request = 0;
    }

    frontend_configuration(): TopologyFrontendConfig {
        if (this._frontend_configuration == null)
            throw "Missing frontend confiuguration";
        return this._frontend_configuration;
    }

    save_layout() {
        // TODO: move to layout.ts
        const fetch_params = new SearchFilters().get_filter_params();
        fetch_params["topology_frontend_configuration"] = JSON.stringify(
            this._compute_frontend_config()
        );
        fetch_params["save_topology_configuration"] = "1";
        this._update_data(fetch_params);
    }

    delete_layout() {
        // TODO: move to layout.ts
        const fetch_params = new SearchFilters().get_filter_params();
        fetch_params["topology_frontend_configuration"] = JSON.stringify(
            this._compute_frontend_config()
        );
        fetch_params["delete_topology_configuration"] = "1";
        this._update_data(fetch_params);
    }

    update_filters(settings) {
        // Update filter form
        new SearchFilters().add_hosts_to_host_regex(
            new Set(settings.growth_root_nodes)
        );
    }

    _compute_frontend_config() {
        const current_layout =
            this._world.layout_manager.layout_applier.get_current_layout();

        const frontend_config: TopologyFrontendConfig = {
            overlays_config: this._world.viewport.get_overlay_configs(),
            growth_root_nodes: [],
            growth_forbidden_nodes: [],
            growth_continue_nodes: [],
            custom_node_settings: {},
            datasource_configuration:
                this.frontend_configuration().datasource_configuration,
            reference_size: current_layout.reference_size,
            style_configs: current_layout.style_configs,
            line_config: current_layout.line_config,
            force_options: current_layout.force_options,
        };

        this._world.viewport.get_all_nodes().forEach(node => {
            if (node.data.growth_root)
                frontend_config.growth_root_nodes.push(node.data.hostname);
            if (node.data.growth_forbidden)
                frontend_config.growth_forbidden_nodes.push(node.data.hostname);
            if (node.data.growth_continue)
                frontend_config.growth_continue_nodes.push(node.data.hostname);
            if (node.data.custom_node_settings) {
                frontend_config.custom_node_settings[node.data.id] =
                    node.data.custom_node_settings;
                this._custom_node_settings_memory[node.data.id] =
                    node.data.custom_node_settings;
            }
        });
        return frontend_config;
    }

    update_browser_url(): void {
        return;
    }

    show_topology(frontend_configuration, search_frontend_settings) {
        this._topology_datasource.enable();
        this._topology_datasource.set_update_interval(30);

        this._topology_datasource.subscribe_new_data(() =>
            this._show_topology()
        );
        this._world.layout_manager.layout_applier._align_layouts = false;

        const fetch_params = new SearchFilters().get_filter_params();
        if (search_frontend_settings)
            fetch_params["search_frontend_settings"] = true;
        fetch_params["topology_frontend_configuration"] = JSON.stringify(
            frontend_configuration
        );
        this._update_data(fetch_params);
    }

    _show_topology() {
        const ds_data = this._topology_datasource.get_data();
        if (ds_data["headline"])
            d3.select("div.titlebar a.title").text(ds_data["headline"]);

        const topology_data: {[name: string]: any} = ds_data["topology_chunks"];
        this._show_topology_errors(ds_data["errors"]);
        this._update_overlay_config(
            ds_data.frontend_configuration.overlays_config
        );
        if (ds_data["query_hash"])
            d3.select("input[name=topology_query_hash_hint]").property(
                "value",
                ds_data["query_hash"]
            );

        this._frontend_configuration = ds_data.frontend_configuration;
        const data_to_show: BackendChunkResponse = {chunks: []};
        for (const idx in topology_data) {
            data_to_show.chunks.push(topology_data[idx]);
        }
        this._world.viewport.finalize_status_message(
            "topology_fetch",
            "Topology: Received data"
        );
        this._world.viewport.feed_data(data_to_show);
        this._apply_styles_to_previously_known_nodes();
        //this._livesearch.update_finished();
        //this._livesearch.enable();
    }

    _apply_styles_to_previously_known_nodes() {
        // Add in-browser memory of previous styles
        this._world.viewport.get_all_nodes().forEach(node => {
            const node_id = node.data.id;
            if (this._custom_node_settings_memory[node_id]) {
                for (const [key, value] of Object.entries(
                    this._custom_node_settings_memory[node_id]
                )) {
                    node.data[key] = value;
                }
                node.data.custom_node_settings =
                    this._custom_node_settings_memory[node_id];
                delete this._custom_node_settings_memory[node_id];
            }
        });
    }

    _show_topology_errors(errors): void {
        d3.select("label#max_nodes_error_text").text(errors);
    }

    update_data() {
        if (this._throttle_update()) return;
        // Update browser url in case someone wants to bookmark the current settings
        this.update_browser_url();

        const frontend_config = this._compute_frontend_config();
        this.update_filters(frontend_config);

        const fetch_params = new SearchFilters().get_filter_params();
        fetch_params["topology_frontend_configuration"] =
            JSON.stringify(frontend_config);
        this._update_data(fetch_params);
    }

    _throttle_update(): boolean {
        const now = new Date().getTime() / 1000;
        const min_delay = 0.2;
        if (now - this._last_update_request < min_delay) {
            if (!this._update_request_timer_active) {
                this._update_request_timer_active = true;
                setTimeout(() => this.update_data(), min_delay * 1000);
            }
            return true;
        }
        this._last_update_request = now;
        this._update_request_timer_active = false;
        return false;
    }

    _update_data(fetch_params) {
        fetch_params["topology_type"] = this._topology_type;
        this._world.viewport.add_status_message(
            "topology_fetch",
            "Topology: Fetching data.."
        );
        this._topology_datasource.fetch_hosts(
            new URLSearchParams(fetch_params).toString()
        );
    }

    _update_overlay_config(overlays_config) {
        for (const idx in overlays_config) {
            this._world.viewport.set_overlay_config(idx, overlays_config[idx]);
        }
    }
}

export const example_generator = LayoutStyleExampleGenerator;

export const registries = {
    layout_style_class_registry: layout_style_class_registry,
    node_type_class_registry: node_type_class_registry,
    layer_class_registry: layer_class_registry,
};
