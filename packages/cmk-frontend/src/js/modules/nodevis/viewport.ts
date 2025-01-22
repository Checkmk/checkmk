/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

// eslint-disable-next-line no-duplicate-imports -- Explicitly imported for side-effects
import "./layout";

import type {D3ZoomEvent, ScaleLinear, Selection, ZoomBehavior} from "d3";
import {scaleLinear, zoom, zoomIdentity} from "d3";

import {ForceSimulation} from "./force_simulation";
import type {ForceConfig} from "./force_utils";
import type {
    AbstractLayer,
    AbstractNodeVisConstructor,
    LayerSelections,
} from "./layer_utils";
import {
    DynamicToggleableLayer,
    FixLayer,
    layer_class_registry,
    ToggleableLayer,
} from "./layer_utils";
import {LayeredNodesLayer} from "./layers";
import type {LayoutManagerLayer} from "./layout";
import type {
    BackendResponse,
    Coords,
    d3SelectionDiv,
    d3SelectionG,
    d3SelectionSvg,
    NodevisLink,
    NodevisNode,
    NodevisWorld,
    OverlayConfig,
    Rectangle,
    RectangleWithCoords,
} from "./type_defs";
import {NodeConfig, OverlaysConfig} from "./type_defs";
import {DefaultTransition, get_bounding_rect} from "./utils";

export class Viewport {
    _world_for_layers: NodevisWorld | null = null;
    _div_selection: d3SelectionDiv;
    _div_content_selection: d3SelectionDiv;
    _svg_content_selection: d3SelectionSvg;
    _zoom_behaviour: ZoomBehavior<any, any>;
    last_zoom = zoomIdentity;
    scale_x: ScaleLinear<number, number>;
    scale_y: ScaleLinear<number, number>;
    always_update_layout = false;
    _node_config: NodeConfig;
    _margin = {top: 10, right: 10, bottom: 10, left: 10};
    _overlays_configs: OverlaysConfig;
    // Infos usable by layers
    _div_layers_selection: d3SelectionDiv;
    _status_table: Selection<HTMLTableElement, null, any, unknown>;
    _feeding_data = false;
    _show_debug_messages = true;

    //////////////////////////////////
    _svg_layers_selection: d3SelectionG;
    _layers: Record<string, AbstractLayer> = {};
    _selections_for_layers: Record<string, LayerSelections> = {};
    width = 0;
    height = 0;

    //////////////////////////////
    feed_data_timestamp = 0;

    _datasource: string;
    _force_simulation: ForceSimulation;
    _update_browser_url: () => void;

    constructor(
        into_selection: d3SelectionDiv,
        datasource: string,
        force_config: typeof ForceConfig,
        update_browser_url: () => void,
    ) {
        this._update_browser_url = update_browser_url;
        this._force_simulation = new ForceSimulation(this, force_config);

        this._datasource = datasource;
        into_selection.style("height", "100%");
        this._div_selection = into_selection
            .append("div")
            .attr("id", "main_window_layered");

        this._overlays_configs = new OverlaysConfig();
        // Each layer gets a svg and a div domain to render its content
        // Layer structure

        // div#main_window_layered
        //    svg#svg_content
        //       g#svg_layers
        //          layerA
        //          layerB
        //          layerC
        //    div#div_content
        //       div#div_layers
        //          layerA
        //          layerB
        //          layerC
        this._svg_content_selection = this._div_selection
            .append("svg")
            .attr("width", "100%")
            .attr("height", "100%")
            .attr("id", "svg_content")
            .style("cursor", "grab")
            .on("contextmenu", event => {
                event.preventDefault();
                event.stopPropagation();
                // TODO: identify nodes layer (svg/canvas)
                this._layers[
                    LayeredNodesLayer.prototype.id()
                ].render_context_menu(event, null);
            })
            .on("click.remove_context", event =>
                this._layers[
                    LayeredNodesLayer.prototype.id()
                ].hide_context_menu(event),
            );

        this._svg_layers_selection = this._svg_content_selection.append("g");
        this._svg_layers_selection.attr("id", "svg_layers");
        this._zoom_behaviour = zoom();
        this._zoom_behaviour
            .scaleExtent([0.2, 10])
            .on("zoom", event => this.zoomed(event))
            .on("end", () =>
                this._svg_content_selection.style("cursor", "grab"),
            )
            .filter(event => {
                // Disable left click zoom
                return event.button === 0 || event.button === 1;
            });
        this._svg_content_selection
            .call(this._zoom_behaviour)
            .on("dblclick.zoom", null);

        this._div_content_selection = this._div_selection
            .append("div")
            .style("position", "absolute")
            .style("width", "100%")
            .style("height", "100%")
            .style("top", "0px")
            .style("left", "0px")
            .style("pointer-events", "none")
            .style("overflow", "hidden")
            .attr("id", "div_content");

        this._div_layers_selection = this._div_content_selection
            .append("div")
            .attr("id", "div_layers");

        this._status_table = this._div_selection
            .append("div")
            .attr("id", "log_messages")
            .append("table")
            .style("table-layout", "fixed");

        // Initialize viewport size and scales before loading the layers
        this.scale_x = scaleLinear();
        this.scale_y = scaleLinear();

        this._node_config = NodeConfig.prototype.create_empty_config();
    }

    create_layers(world: NodevisWorld) {
        // TODO: check two times size changed
        this._world_for_layers = world;
        this.size_changed();
        this._load_layers([]);
        this.size_changed();
    }

    get_layers() {
        return this._layers;
    }
    get_layer_classes(): Record<
        string,
        AbstractNodeVisConstructor<AbstractLayer>
    > {
        const all_layers = Object.values(layer_class_registry.get_classes());
        const classes_by_id: Record<
            string,
            AbstractNodeVisConstructor<AbstractLayer>
        > = {};
        all_layers.forEach(layer_class => {
            const layer_prototype = layer_class.prototype;
            if (layer_prototype.supports_datasource(this._datasource))
                classes_by_id[layer_prototype.class_name()] = layer_class;
        });
        return classes_by_id;
    }

    restart_force_simulation(alpha: number) {
        this._force_simulation.restart_with_alpha(alpha);
    }

    _create_selections(layer_id: string): LayerSelections {
        this._selections_for_layers[layer_id] = {
            svg: this._svg_layers_selection.append("g").attr("id", layer_id),
            div: this._div_layers_selection.append("div").attr("id", layer_id),
        };
        return this._selections_for_layers[layer_id];
    }

    _load_layers(available_dynamic_layers: string[]): void {
        const layers_by_id = this.get_layer_classes();
        // Dynamic layers, created on demand
        available_dynamic_layers.forEach(layer_id => {
            if (this._layers[layer_id] || layer_id.indexOf("@") == -1) return;
            const [base_layer_id, dynamic_id] = layer_id.split("@", 2);
            const base_layer_class = layers_by_id[base_layer_id + "@"];
            if (base_layer_class.prototype instanceof DynamicToggleableLayer) {
                this._layers[layer_id] = new base_layer_class(
                    this._world_for_layers!,
                    this._create_selections(layer_id),
                    dynamic_id,
                    dynamic_id,
                );
            }
        });

        // Hardcoded layers
        for (const [layer_id, layer_class] of Object.entries(layers_by_id)) {
            const layer_prototype = layer_class.prototype;
            if (layer_prototype.is_dynamic_instance_template()) continue;
            if (this._layers[layer_id]) return;
            this._layers[layer_id] = new layer_class(
                this._world_for_layers!,
                this._create_selections(layer_id),
            );
        }

        // Enable FixLayer
        for (const idx in this._layers) {
            if (this._layers[idx] instanceof FixLayer)
                this._layers[idx].enable();
        }

        this._update_layer_order();
    }

    _update_layer_order(): void {
        // TODO: sort layer order
    }

    get_overlays_config(): OverlaysConfig {
        return this._overlays_configs;
    }

    get_overlay_layers_config(): Record<string, OverlayConfig> {
        return this._overlays_configs.overlays;
    }

    set_overlay_layer_config(
        overlay_id: string,
        new_config: OverlayConfig,
    ): void {
        this._overlays_configs.overlays[overlay_id] = new_config;
        this.update_active_overlays();
    }

    update_active_overlays(): void {
        // Enable/Disable overlays
        for (const idx in this._layers) {
            const layer = this._layers[idx];
            if (!(layer instanceof ToggleableLayer)) continue;

            const layer_id = layer.id();
            const layer_config = this.get_overlay_layers_config()[layer_id];
            if (!layer_config) continue;

            if (layer_config.active && !layer.is_enabled())
                this.enable_layer(layer_id);
            else if (!layer_config.active && layer.is_enabled())
                this.disable_layer(layer_id);
        }
        this._update_browser_url();
    }

    try_fetch_data() {
        if (this._feeding_data) {
            // Currently integrating data, switching layers, etc.  -> do nothing
            return;
        }
        this._world_for_layers!.update_data();
    }

    enable_layer(layer_id: string): void {
        this._layers[layer_id].enable();
    }

    disable_layer(layer_id: string): void {
        this._layers[layer_id].disable();
    }

    get_layer(layer_id: string): AbstractLayer {
        return this._layers[layer_id];
    }

    set_overlays_config(overlays_config: OverlaysConfig) {
        this._overlays_configs = overlays_config;
    }

    feed_data(data_to_show: BackendResponse): void {
        this._feeding_data = true;
        this.feed_data_timestamp = Math.floor(new Date().getTime() / 1000);

        const new_config = build_node_config(data_to_show, this._node_config);
        // This is an indicator whether its necessary to reapply all layouts
        // Applying layouts needlessly
        // - cost performance
        // - may cause the gui to flicker/move with certain layouts
        const nodes_changed =
            Object.keys(new_config.nodes_by_id) !=
            Object.keys(this._node_config.nodes_by_id);
        compute_missing_spawn_coords(new_config, {
            x: this.width / 2,
            y: this.height / 2,
        });
        this._node_config = new_config;
        this._load_layers(this._overlays_configs.available_layers);
        this.get_layout_manager().update_layout(data_to_show.layout);
        this.update_active_overlays();

        this.update_data_of_layers();
        this.get_layout_manager().apply_current_layout(
            nodes_changed || this.always_update_layout,
        );
        this.get_layout_manager().compute_node_positions();
        this.update_gui_of_layers(true);
        this._feeding_data = false;

        // this.zoom_fit();
    }

    _filter_root_cause(node: NodevisNode): void {
        if (!node._children) return;

        const critical_children: NodevisNode[] = [];
        node._children.forEach(child_node => {
            if (child_node.data.state != 0) {
                critical_children.push(child_node);
                this._filter_root_cause(child_node);
            }
        });
        node.data.user_interactions.bi = "root_cause";
        node.children = critical_children;
    }

    compute_spawn_coords(node: NodevisNode): {x: number; y: number} {
        return compute_spawn_coords(node, this._node_config, {
            x: this.width / 2,
            y: this.height / 2,
        });
    }

    get_nodes_layer(): LayeredNodesLayer {
        return this.get_layer("nodes") as LayeredNodesLayer;
    }
    get_layout_manager(): LayoutManagerLayer {
        return this.get_layer("layout_manager") as LayoutManagerLayer;
    }

    get_all_links(): NodevisLink[] {
        return this._node_config.link_info;
    }

    get_all_nodes(): NodevisNode[] {
        return this._node_config.hierarchy.descendants();
    }

    get_node_by_id(node_id: string) {
        return this._node_config.nodes_by_id[node_id];
    }

    get_size(): Rectangle {
        return {width: this.width, height: this.height};
    }

    _apply_user_interactions() {
        this.get_all_nodes().forEach(node => {
            const bi_setting = node.data.user_interactions.bi;
            if (bi_setting === undefined) return;

            switch (bi_setting) {
                case "collapsed":
                    // @ts-ignore
                    node.children = null;
                    break;
                case "root_cause":
                    this._filter_root_cause(node);
                    break;
            }
        });
        this.update_node_chunk_descendants_and_links();
    }

    update_node_chunk_descendants_and_links() {
        // This feature is only supported/useful for bi visualization
        if (this._datasource != "bi_aggregations") return;

        const chunk_links: NodevisLink[] = [];
        this.get_all_nodes().forEach(node => {
            if (!node.parent || node.data.invisible) return;
            chunk_links.push({
                source: node,
                target: node.parent,
                config: {type: "default"},
            });
        });
        this._node_config.link_info = chunk_links;
    }

    recompute_node_and_links() {
        this.update_node_chunk_descendants_and_links();
        const all_nodes = this.get_all_nodes();
        const all_links = this.get_all_links();
        this.update_layers();
        this._force_simulation.update_nodes_and_links(all_nodes, all_links);
        this._force_simulation.restart_with_alpha(0.5);
    }

    update_layers(force_gui_update = false) {
        this.update_data_of_layers();
        this.update_gui_of_layers(force_gui_update);
    }

    update_layer(layer_id: string) {
        this.update_data_of_layer(layer_id);
        this.update_gui_of_layer(layer_id);
    }

    update_data_of_layer(layer_id: string) {
        if (!this._layers[layer_id].is_enabled()) return;
        this._layers[layer_id].update_data();
    }

    update_gui_of_layer(layer_id: string) {
        if (!this._layers[layer_id].is_enabled()) return;
        this._layers[layer_id].update_gui();
    }

    update_data_of_layers() {
        for (const layer_id in this._layers) {
            this.update_data_of_layer(layer_id);
        }
    }

    update_gui_of_layers(force_gui_update = false) {
        for (const layer_id in this._layers) {
            if (!this._layers[layer_id].is_enabled()) continue;
            this._layers[layer_id].update_gui(force_gui_update);
        }
    }

    zoomed(event: D3ZoomEvent<any, any>) {
        this.last_zoom = event.transform;
        this.scale_x.range([0, this.width * event.transform.k]);
        this.scale_y.range([0, this.height * event.transform.k]);

        const transform_text =
            "translate(" + this.last_zoom.x + "," + this.last_zoom.y + ")";
        this._svg_layers_selection.attr("transform", transform_text);

        for (const layer_id in this._layers) {
            if (!this._layers[layer_id].is_enabled()) continue;
            this._layers[layer_id].zoomed();
            this._layers[layer_id].update_gui();
        }
        this._svg_content_selection.style("cursor", "grabbing");
    }

    // Applies scale and x/y translation
    translate_to_zoom(coords: Coords): Coords {
        const translated = this.scale_to_zoom(coords);
        if ("x" in translated) translated.x = this.last_zoom.x + translated.x;
        if ("y" in translated) translated.y = this.last_zoom.y + translated.y;
        return translated;
    }

    // Applies scale
    scale_to_zoom(
        coords: RectangleWithCoords | Coords,
    ): RectangleWithCoords | Coords {
        // TODO: be more specific, create distinct functions
        const translated: RectangleWithCoords = {
            x: 0,
            y: 0,
            width: 0,
            height: 0,
        };
        if ("x" in coords) translated.x = this.scale_x(coords.x);

        if ("y" in coords) translated.y = this.scale_y(coords.y);

        if ("width" in coords) translated.width = this.scale_x(coords.width);

        if ("height" in coords) translated.height = this.scale_y(coords.height);

        return translated;
    }

    size_changed() {
        const root_node = this._div_selection.node();
        if (root_node == null)
            // It can't be null. Just make typescript happy
            return;
        const rectangle = root_node.getBoundingClientRect();
        this.width = rectangle.width - this._margin.left - this._margin.right;
        this.height = rectangle.height - this._margin.top - this._margin.bottom;

        this.scale_x = scaleLinear()
            .domain([0, this.width])
            .range([0, this.width]);
        this.scale_y = scaleLinear()
            .domain([0, this.height])
            .range([0, this.height]);

        for (const layer_id in this._layers) {
            this._layers[layer_id].size_changed();
        }
    }

    get_div_selection(): d3SelectionDiv {
        return this._div_selection;
    }

    get_svg_content_selection(): d3SelectionSvg {
        return this._svg_content_selection;
    }

    zoom_to_coords(x: number, y: number, scale: number | null = null): void {
        const use_scale = scale ? scale : this.last_zoom.k;
        DefaultTransition.add_transition(this._svg_content_selection).call(
            this._zoom_behaviour.transform,
            () => {
                return zoomIdentity
                    .translate(this.width / 2, this.height / 2)
                    .scale(use_scale)
                    .translate(x, y);
            },
        );
    }

    zoom_reset() {
        this._svg_content_selection
            .transition()
            .duration(DefaultTransition.duration())
            .call(this._zoom_behaviour.transform, zoomIdentity);
    }

    zoom_fit() {
        const coords: Coords[] = [];
        this.get_all_nodes().forEach(node => {
            if (node.x != undefined && node.data.node_type != "topology_center")
                coords.push({x: node.x, y: node.y});
        });

        const rect = get_bounding_rect(coords);
        // Task: move rect x_min + width/2 into center
        const size = this.get_size();
        // TODO: leave some space on the right side because of the fi
        size.width -= 200;
        let new_scale = Math.min(
            size.width / rect.width,
            size.height / rect.height,
        );
        new_scale *= 0.8;
        this.zoom_to_coords(
            -(rect.x_min + rect.width / 2),
            -(rect.y_min + rect.height / 2),
            new_scale,
        );
    }

    set_zoom(to_percent: number) {
        const new_scale = to_percent / 100;
        const new_zoom = zoomIdentity
            .translate(
                (-this.width / 2) * new_scale + this.width / 2,
                (-this.height / 2) * new_scale + this.height / 2,
            )
            .scale(new_scale);
        DefaultTransition.add_transition(this._svg_content_selection).call(
            this._zoom_behaviour.transform,
            () => new_zoom,
        );
    }

    change_zoom(by_percent: number) {
        const new_scale =
            Math.floor((this.last_zoom.k * 100 + by_percent) / 10) / 10;
        const new_zoom = zoomIdentity
            .translate(
                (-this.width / 2) * new_scale + this.width / 2,
                (-this.height / 2) * new_scale + this.height / 2,
            )
            .scale(new_scale);
        this._svg_content_selection
            .transition()
            .duration(DefaultTransition.duration() / 3)
            .call(this._zoom_behaviour.transform, () => new_zoom);
    }

    add_status_message(message_id: string, message: string): void {
        if (!this._show_debug_messages) return;
        const now = new Date();
        const row = this._status_table
            .selectAll<HTMLTableRowElement, string>("tr")
            .data([message_id], d => d)
            .enter()
            .append("tr")
            .attr("update_time", now.getTime())
            .style("line-height", "10px");
        row.append("td").classed("time", true).text(this._format_time(now));
        row.append("td").classed("message", true).text(message);
        row.append("td")
            .classed("timedelta", true)
            .style("padding", "0px 5px 0px 5px")
            .style("text-align", "right")
            .text("");
    }

    finalize_status_message(message_id: string, message: string): void {
        if (!this._show_debug_messages) return;
        const now = new Date();
        const row = this._status_table
            .selectAll<HTMLTableRowElement, string>("tr")
            .data([message_id], d => d);
        if (row.empty()) return;
        row.select("td.time").text(this._format_time(now));
        row.select("td.message").text(message);
        row.select("td.timedelta").text(
            (now.getTime() - parseInt(row.attr("update_time")))
                .toFixed(2)
                .toString() + "ms",
        );
        row.datum(null);
        row.transition()
            .delay(10000)
            .duration(2000)
            .style("opacity", 0.0)
            .style("line-height", "0px")
            .remove();
    }

    _format_time(now: Date): string {
        return (
            now.toLocaleTimeString("de") +
            "." +
            Math.floor(now.getMilliseconds() / 10)
        );
    }

    update_nodes_and_links(all_nodes: NodevisNode[], all_links: NodevisLink[]) {
        this._force_simulation.update_nodes_and_links(all_nodes, all_links);
    }

    get_default_force_config() {
        return this._force_simulation.get_force_config().get_default_options();
    }

    get_force_alpha(): number {
        return this._force_simulation._simulation.alpha();
    }

    show_force_config() {
        return this._force_simulation.show_force_config();
    }

    get_viewport_percentage_of_node(node: NodevisNode): Coords {
        const coords = this.get_size();
        return {
            x: (100.0 * node.x) / coords.width,
            y: (100.0 * node.y) / coords.height,
        };
    }
}
function build_node_config(
    data: BackendResponse,
    old_node_config: NodeConfig,
): NodeConfig {
    const new_node_config = new NodeConfig(data.node_config);

    new_node_config.hierarchy.descendants().forEach(node => {
        const old_node_data = old_node_config.nodes_by_id[node.data.id];
        if (!old_node_data) return;
        _migrate_node_content(old_node_data, node);
    });
    return new_node_config;
}

function _migrate_node_content(old_node: NodevisNode, new_node: NodevisNode) {
    // Reuse computed coordinates from previous chunk data
    new_node.x = old_node.x;
    new_node.y = old_node.y;

    // Migrate user interactions
    new_node.data.user_interactions = old_node.data.user_interactions;
}

function linked_nodes_with_coords(
    node: NodevisNode,
    node_config: NodeConfig,
): NodevisNode[] {
    const linked_nodes: NodevisNode[] = [];
    node_config.link_info.forEach(link => {
        if (node == link.source && link.target.x)
            linked_nodes.push(link.target);
        else if (node == link.target && link.source.x)
            linked_nodes.push(link.source);
    });
    return linked_nodes;
}

function compute_spawn_coords(
    node: NodevisNode,
    node_config: NodeConfig,
    fallback_coords: Coords,
) {
    const linked_nodes = linked_nodes_with_coords(node, node_config);
    if (linked_nodes.length > 0)
        return {x: linked_nodes[0].x, y: linked_nodes[0].y};
    return fallback_coords;
}

function compute_missing_spawn_coords(
    node_config: NodeConfig,
    fallback_coords: Coords,
) {
    let rad = 0;
    const rad_delta = Math.PI / 8;
    node_config.hierarchy.descendants().forEach(node => {
        if (node.x)
            // This node already has coordinates
            return;
        const spawn_coords = compute_spawn_coords(
            node,
            node_config,
            fallback_coords,
        );
        // Do not spawn all nodes at the same location.
        // This will create a singularity which causes the force simulation to explode
        node.x = spawn_coords.x + Math.cos(rad) * (30 + rad * 4);
        node.y = spawn_coords.y + Math.sin(rad) * (30 + rad * 4);
        rad += rad_delta;
    });
}
