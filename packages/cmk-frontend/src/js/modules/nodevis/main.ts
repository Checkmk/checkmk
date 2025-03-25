/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import {select} from "d3";

import {BIForceConfig} from "./aggregations";
import {
    AggregationsDatasource,
    DatasourceManager,
    TopologyDatasource,
} from "./datasources";
import {LayoutStyleExampleGenerator} from "./example_generator";
import {ForceConfig} from "./force_utils";
import {layer_class_registry} from "./layer_utils";
import {layout_style_class_registry} from "./layout_utils";
import {link_type_class_registry} from "./link_utils";
import {get_custom_node_settings, node_type_class_registry} from "./node_utils";
import {SearchNodes} from "./search";
import type {TranslationKey} from "./texts";
import {get, set_translations} from "./texts";
import {TopologyForceConfig} from "./topology";
import type {
    BackendResponse,
    d3SelectionDiv,
    DatasourceType,
    OverlayConfig,
    TopologyBackendResponse,
    TopologyFrontendConfig,
} from "./type_defs";
import {NodevisWorld, OverlaysConfig} from "./type_defs";
import {LiveSearch, render_input_range, SearchFilters} from "./utils";
import {Viewport} from "./viewport";

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

    constructor(
        div_id: string,
        datasource: DatasourceType,
        translations: Record<TranslationKey, string> | null = null,
    ) {
        this._div_id = div_id;
        this._div_selection = select<HTMLDivElement, null>(
            "#" + this._div_id,
        ).append("div");

        if (translations) set_translations(translations);
        this._world = this._create_world(datasource);
        this._world.datasource_manager.schedule(true);
    }

    toggle_layout_designer(): boolean {
        return this._world.viewport.get_layout_manager().toggle_toolbar();
    }

    update_browser_url(): void {
        // The browser url can be used as bookmark
    }

    _get_force_config(): typeof ForceConfig {
        return ForceConfig;
    }

    _create_world(datasource: DatasourceType): NodevisWorld {
        this._div_selection
            .attr("id", "node_visualization_root_div")
            .attr("div_id", this._div_id)
            .classed("node_vis", true) // Main indicator for most NodeVisualization css styles
            .style("height", "100%");

        const viewport_selection = this._div_selection.append("div");
        const search_result_selection = this._div_selection.append("div");

        const datasource_manager = new DatasourceManager();
        const viewport = new Viewport(
            viewport_selection,
            datasource,
            this._get_force_config(),
            () => this.update_browser_url(),
        );

        const world = new NodevisWorld(
            this._div_selection,
            viewport,
            datasource,
            datasource_manager,
            () => this.update_data(),
            () => this.update_browser_url(),
            () => this.save_layout(),
            () => this.delete_layout(),
        );

        new SearchNodes(world, search_result_selection);

        viewport.create_layers(world);
        return world;
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
    constructor(div_id: string) {
        super(div_id, "bi_aggregations");
    }

    show_aggregations(list_of_aggregations: string[], use_layout_id: string) {
        const aggr_ds = this._world.datasource_manager.get_datasource(
            AggregationsDatasource.id(),
        ) as AggregationsDatasource;
        aggr_ds.enable();
        aggr_ds.subscribe_new_data(() =>
            this._show_aggregations(list_of_aggregations),
        );
        aggr_ds.fetch_aggregations(list_of_aggregations, use_layout_id);
    }

    override _get_force_config(): typeof ForceConfig {
        return BIForceConfig;
    }

    _show_aggregations(list_of_aggregations: string[]): void {
        if (list_of_aggregations.length > 0)
            select("table.header td.heading a").text(list_of_aggregations[0]);

        const aggr_ds = this._world.datasource_manager.get_datasource(
            AggregationsDatasource.id(),
        );
        const fetched_data = aggr_ds.get_data() as BackendResponse;
        this._world.viewport.feed_data(fetched_data);
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
        overlays_config: {[name: string]: any} = {},
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

function _parse_topology_settings(data: TopologySettings): TopologySettings {
    return new TopologySettings(
        data.growth_root_nodes,
        data.growth_forbidden_nodes,
        data.growth_continue_nodes,
        data.display_mode,
        data.max_nodes,
        data.mesh_depth,
    );
}

export class TopologyVisualization extends NodeVisualization {
    _custom_topology_fetch_parameters: {[name: string]: any} = {};
    _custom_node_settings_memory: Record<string, any> = {};
    _last_update_request: number;
    _update_request_timer_active = false;
    _topology_datasource: TopologyDatasource;
    _topology_type: string;
    _frontend_configuration: TopologyFrontendConfig | null = null;
    _livesearch: LiveSearch;

    constructor(
        div_id: string,
        topology_type: string,
        translations: Record<TranslationKey, string>,
    ) {
        super(div_id, "topology", translations);
        this._topology_type = topology_type;
        this._topology_datasource =
            this._world.datasource_manager.get_datasource(
                TopologyDatasource.id(),
            ) as TopologyDatasource;

        this._livesearch = new LiveSearch("form#form_filter", () =>
            this.update_data(),
        );
        this._custom_node_settings_memory = {};

        // Parameters used for throttling the GUI update
        this._last_update_request = 0;

        this._topology_datasource.enable();
        this._topology_datasource.subscribe_new_data(() =>
            this._fetched_topology_data(),
        );
    }

    frontend_configuration(): TopologyFrontendConfig {
        if (this._frontend_configuration == null)
            throw "Missing frontend configuration";
        return this._frontend_configuration;
    }

    override save_layout() {
        // TODO: move to layout.ts
        const fetch_params = new SearchFilters().get_filter_params();
        fetch_params["save_topology_configuration"] = "1";
        this._update_data(fetch_params);
    }

    override delete_layout() {
        // TODO: move to layout.ts
        const fetch_params = new SearchFilters().get_filter_params();
        fetch_params["delete_topology_configuration"] = "1";
        this._update_data(fetch_params);
    }

    update_filters(settings: TopologyFrontendConfig) {
        // Update filter form
        new SearchFilters().add_hosts_to_host_regex(
            new Set(settings.growth_root_nodes),
        );
    }

    _compute_frontend_config() {
        const frontend_config: TopologyFrontendConfig = {
            overlays_config: this._world.viewport.get_overlays_config(),
            growth_root_nodes: [],
            growth_forbidden_nodes: [],
            growth_continue_nodes: [],
            custom_node_settings: {},
            datasource_configuration:
                this.frontend_configuration().datasource_configuration,
        };

        this._world.viewport.get_all_nodes().forEach(node => {
            const growth_settings = node.data.growth_settings;
            if (growth_settings.growth_root)
                frontend_config.growth_root_nodes.push(node.data.id);
            if (growth_settings.growth_forbidden)
                frontend_config.growth_forbidden_nodes.push(node.data.id);
            if (growth_settings.growth_continue)
                frontend_config.growth_continue_nodes.push(node.data.id);
            const custom_node_settings = get_custom_node_settings(node);
            if (custom_node_settings) {
                frontend_config.custom_node_settings[node.data.id] =
                    custom_node_settings;
                this._custom_node_settings_memory[node.data.id] =
                    custom_node_settings;
            }
        });
        return frontend_config;
    }

    toggle_compare_history(): boolean {
        const div_compare = select(".suggestion.topology_compare_history");
        const icon = div_compare.select("img");
        const new_state = !icon.classed("on");
        icon.classed("on", new_state);

        const ds_config =
            this._frontend_configuration!.datasource_configuration;

        type SpanConfig = [string, string, [string, boolean][]];
        const reference_options: [string, boolean][] = [];
        const compare_to_options: [string, boolean][] = [];
        ds_config.available_datasources.forEach(datasource => {
            reference_options.push([
                datasource,
                datasource == ds_config.reference,
            ]);
            compare_to_options.push([
                datasource,
                datasource == ds_config.compare_to,
            ]);
        });
        const data: SpanConfig[] = [
            [get("reference"), "reference", reference_options],
            [get("compare_to"), "compare_to", compare_to_options],
        ];

        if (!new_state) {
            div_compare
                .selectAll("span.choice")
                .transition()
                .style("width", "0px")
                .remove();
            return new_state;
        }

        const inner_a = div_compare.select("a");
        const choices = inner_a
            .selectAll("span.choices")
            .data([null])
            .join("span")
            .classed("choices", true)
            .on("click", event => {
                event.stopPropagation();
            });
        const spans = choices
            .selectAll<HTMLSpanElement, SpanConfig[]>("span.choice")
            .data(data)
            .join("span")
            .style("width", "0px")
            .style("overflow", "hidden")
            .classed("choice", true);

        spans
            .selectAll<HTMLLabelElement, string>("label")
            .data(d => [d[0]])
            .join("label")
            .text(d => d)
            .on("click", event => {
                event.stopPropagation();
            });
        const selects = spans
            .selectAll<HTMLSelectElement, SpanConfig>("select")
            .data(d => [d])
            .join("select")
            .attr("class", d => d[1])
            .on("change", event => {
                this.frontend_configuration().datasource_configuration.reference =
                    choices.select("select.reference").property("value");
                this.frontend_configuration().datasource_configuration.compare_to =
                    choices.select("select.compare_to").property("value");
                this.update_data();
                event.stopPropagation();
            });

        selects
            .selectAll<HTMLOptionElement, SpanConfig>("option")
            .data(d => d[2])
            .join("option")
            .text(d => d[0])
            .property("selected", d => d[1])
            .on("click", event => {
                event.stopPropagation();
            });

        spans.transition().style("width", null);
        return new_state;
    }

    override update_browser_url(): void {
        return;
    }

    _fetched_topology_data() {
        this.show_topology(
            this._topology_datasource.get_data() as TopologyBackendResponse,
        );
    }

    show_topology(data: TopologyBackendResponse) {
        if (data.headline) select("div.titlebar a.title").text(data.headline);

        this._show_topology_errors(data.errors);
        this._frontend_configuration = data.frontend_configuration;
        this._world.viewport.finalize_status_message(
            "topology_fetch",
            "Topology: Received data",
        );

        const overlays_configs = OverlaysConfig.create_from_json(
            data.frontend_configuration.overlays_config,
        );
        this._world.viewport.set_overlays_config(overlays_configs);
        this._world.viewport.feed_data(data);
        this._apply_styles_to_previously_known_nodes();
        this._livesearch.update_finished();
        this._livesearch.enable();
    }

    _apply_styles_to_previously_known_nodes() {
        // Add in-browser memory of previous styles
        this._world.viewport.get_all_nodes().forEach(node => {
            const node_id = node.data.id;
            if (this._custom_node_settings_memory[node_id]) {
                for (const [key, value] of Object.entries(
                    //@ts-ignore
                    this._custom_node_settings_memory[node_id],
                )) {
                    //@ts-ignore
                    node.data[key] = value;
                }
                node.data.custom_node_settings =
                    this._custom_node_settings_memory[node_id];
                delete this._custom_node_settings_memory[node_id];
            }
        });
    }

    _show_topology_errors(errors: string): void {
        select("label#max_nodes_error_text").text(errors);
    }

    override _get_force_config(): typeof ForceConfig {
        return TopologyForceConfig;
    }

    override update_data() {
        if (this._throttle_update()) return;
        // Update browser url in case someone wants to bookmark the current settings
        this.update_browser_url();

        const frontend_config = this._compute_frontend_config();
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

    _update_data(
        fetch_params: Record<string, string>,
        frontend_config: TopologyFrontendConfig | null = null,
    ) {
        fetch_params["topology_type"] = this._topology_type;
        if (frontend_config)
            fetch_params["topology_frontend_configuration"] =
                JSON.stringify(frontend_config);
        else
            fetch_params["topology_frontend_configuration"] = JSON.stringify(
                this._compute_frontend_config(),
            );
        fetch_params["layout"] = JSON.stringify(
            this._world.viewport.get_layout_manager().get_layout().serialize(),
        );
        this._world.viewport.add_status_message(
            "topology_fetch",
            "Topology: Fetching data..",
        );
        this._topology_datasource.fetch_hosts(fetch_params);
    }

    _update_overlay_config(overlays_config: OverlayConfig[]) {
        for (const idx in overlays_config) {
            this._world.viewport.set_overlay_layer_config(
                idx,
                overlays_config[idx],
            );
        }
    }
}

export const example_generator = LayoutStyleExampleGenerator;

export const registries = {
    layout_style_class_registry: layout_style_class_registry,
    node_type_class_registry: node_type_class_registry,
    link_type_class_registry: link_type_class_registry,
    layer_class_registry: layer_class_registry,
};

export const utils = {
    render_input_range: render_input_range,
};
