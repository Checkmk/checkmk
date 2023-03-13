// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

import * as d3 from "d3";
import {ZoomTransform} from "d3";
import {
    BackendChunkResponse,
    Coords,
    d3SelectionDiv,
    d3SelectionG,
    d3SelectionSvg,
    NodeChunk,
    NodeData,
    NodevisLink,
    NodevisNode,
    NodevisWorld,
    RectangleWithCoords,
    SerializedNodeChunk,
} from "nodevis/type_defs";
import {
    AbstractLayer,
    FixLayer,
    layer_class_registry,
    LayerSelections,
    OverlayConfig,
    ToggleableLayer,
} from "nodevis/layer_utils";
import {DefaultTransition} from "nodevis/utils";
import "nodevis/layout";
import {LayeredNodesLayer} from "nodevis/layers";

//#.
//#   .-Layered Viewport---------------------------------------------------.
//#   |                _                                  _                |
//#   |               | |    __ _ _   _  ___ _ __ ___  __| |               |
//#   |               | |   / _` | | | |/ _ \ '__/ _ \/ _` |               |
//#   |               | |__| (_| | |_| |  __/ | |  __/ (_| |               |
//#   |               |_____\__,_|\__, |\___|_|  \___|\__,_|               |
//#   |                           |___/                                    |
//#   |           __     ___                                _              |
//#   |           \ \   / (_) _____      ___ __   ___  _ __| |_            |
//#   |            \ \ / /| |/ _ \ \ /\ / / '_ \ / _ \| '__| __|           |
//#   |             \ V / | |  __/\ V  V /| |_) | (_) | |  | |_            |
//#   |              \_/  |_|\___| \_/\_/ | .__/ \___/|_|   \__|           |
//#   |                                   |_|                              |
//#   +--------------------------------------------------------------------+

export class LayeredViewport {
    _world: NodevisWorld;
    _div_selection: d3SelectionDiv;
    _div_content_selection: d3SelectionDiv;
    _svg_content_selection: d3SelectionSvg;
    _zoom_behaviour: d3.ZoomBehavior<any, any>;
    last_zoom = d3.zoomIdentity;
    scale_x: d3.ScaleLinear<number, number>;
    scale_y: d3.ScaleLinear<number, number>;
    always_update_layout = false;
    _node_chunk_list: NodeChunk[] = []; // Node data
    _chunks_changed = false;
    _margin = {top: 10, right: 10, bottom: 10, left: 10};
    _overlay_configs: {[name: string]: OverlayConfig} = {};
    // Infos usable by layers
    _div_layers_selection: d3SelectionDiv;
    _status_table: d3.Selection<HTMLTableElement, unknown, any, unknown>;
    _show_debug_messages = false;

    //////////////////////////////////
    _svg_layers_selection: d3SelectionG;
    _layers: {[name: string]: AbstractLayer} = {};
    _selections_for_layers: {[name: string]: LayerSelections} = {};
    width = 0;
    height = 0;

    //////////////////////////////
    feed_data_timestamp = 0;

    //////////////////////////////
    data_to_show: BackendChunkResponse = {chunks: []};

    constructor(world: NodevisWorld, into_selection: d3SelectionDiv) {
        this._world = world;
        into_selection.style("height", "100%");
        this._div_selection = into_selection
            .append("div")
            .attr("id", "main_window_layered");

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
                ].hide_context_menu(event)
            );

        this._svg_layers_selection = this._svg_content_selection.append("g");
        this._svg_layers_selection.attr("id", "svg_layers");
        this._zoom_behaviour = d3.zoom();
        this._zoom_behaviour
            .scaleExtent([0.2, 10])
            .on("zoom", event => this.zoomed(event))
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
            .style("position", "absolute")
            .style("width", "40%")
            .style("height", "150px")
            .style("top", "60px")
            .style("left", "30%")
            .style("pointer-events", "none")
            .style("overflow", "hidden")
            .append("table")
            .style("background", "#1c2228")
            .style("table-layout", "fixed");

        // Initialize viewport size and scales before loading the layers
        this.scale_x = d3.scaleLinear();
        this.scale_y = d3.scaleLinear();
    }

    static id(): string {
        return "layered_viewport";
    }

    setup_world_components() {
        // TODO: check two times size changed
        this.size_changed();
        this._load_layers();
        this.size_changed();
    }

    _load_layers(): void {
        for (const [layer_id, layer_class] of Object.entries(
            layer_class_registry.get_classes()
        )) {
            this._selections_for_layers[layer_id] = {
                svg: this._svg_layers_selection
                    .append("g")
                    .attr("id", layer_id),
                div: this._div_layers_selection
                    .append("div")
                    .attr("id", layer_id),
            };
            const layer_instance = new layer_class(
                this._world,
                this._selections_for_layers[layer_id]
            );
            this._layers[layer_id] = layer_instance;
        }

        // Enable enabled FixLayer
        for (const idx in this._layers) {
            if (this._layers[idx] instanceof FixLayer)
                this._layers[idx].enable();
        }

        this._update_layer_order();
    }

    _update_layer_order(): void {
        // TODO: sort layer order
    }

    get_overlay_configs(): {[name: string]: OverlayConfig} {
        return this._overlay_configs;
    }

    set_overlay_config(overlay_id: string, new_config: OverlayConfig): void {
        this._overlay_configs[overlay_id] = new_config;
        this.update_active_overlays();
    }

    update_active_overlays(): void {
        // Enable/Disable overlays
        for (const idx in this._layers) {
            const layer = this._layers[idx];
            if (!(layer instanceof ToggleableLayer)) continue;

            const layer_id = layer.id();
            const layer_config = this.get_overlay_configs()[layer_id];
            if (!layer_config) continue;

            if (layer_config.active && !layer.is_enabled())
                this.enable_layer(layer_id);
            else if (!layer_config.active && layer.is_enabled())
                this.disable_layer(layer_id);
        }
        this.update_overlay_toggleboxes();
        this._world.update_browser_url();
    }

    enable_layer(layer_id): void {
        this._layers[layer_id].enable();
    }

    disable_layer(layer_id): void {
        this._layers[layer_id].disable();
    }

    get_layers(): {[name: string]: AbstractLayer} {
        return this._layers;
    }

    get_layer(layer_id): AbstractLayer {
        return this._layers[layer_id];
    }

    update_overlay_toggleboxes(): void {
        if (!this._world.layout_manager.layout_applier.current_layout_group)
            return;
        type OverlayType = {layer: AbstractLayer; config: OverlayConfig};
        const configurable_overlays: OverlayType[] = [];
        for (const idx in this._layers) {
            const layer = this._layers[idx];
            const layer_id = layer.id();
            if (layer instanceof ToggleableLayer) {
                if (!this._overlay_configs[layer_id]) continue;
                if (this._overlay_configs[layer_id].configurable != true)
                    continue;
                configurable_overlays.push({
                    layer: layer,
                    config: this._overlay_configs[layer_id],
                });
            }
        }

        // Update toggleboxes
        const toggleboxes = d3
            .select("div#togglebuttons")
            .selectAll<HTMLDivElement, OverlayType>("div.togglebox")
            .data<OverlayType>(configurable_overlays, d => d.layer.id())
            .join(enter =>
                enter
                    .append("div")
                    .classed("togglebox_wrap", true)
                    .append("div")
                    .text(d => d.layer.name())
                    .attr("layer_id", d => d.layer.id())
                    .classed("noselect", true)
                    .classed("togglebox", true)
                    .style("pointer-events", "all")
                    .on("click", event => this.toggle_overlay_click(event))
            );
        toggleboxes.classed("enabled", d => d.config.active);
    }

    toggle_overlay_click(event): void {
        event.stopPropagation();
        const target = d3.select(event.target);
        const layer_id = target.attr("layer_id");
        target.classed("enabled", !this._layers[layer_id].is_enabled());
        const overlay_config = this.get_overlay_configs()[layer_id] || {};
        overlay_config.active = !overlay_config.active;
        this.set_overlay_config(layer_id, overlay_config);
        this.update_active_overlays();
    }

    feed_data(data_to_show: BackendChunkResponse): void {
        this.feed_data_timestamp = Math.floor(new Date().getTime() / 1000);
        this.data_to_show = data_to_show;

        // TODO: fix marked obsolete handling
        this._node_chunk_list.forEach(
            node_chunk => (node_chunk.marked_obsolete = true)
        );

        // This is an indicator whether its necessary to reapply all layouts
        // Applying layouts needlessly
        // - cost performance
        // - may cause the gui to flicker/move with certain layouts
        this._chunks_changed = false;

        this.data_to_show.chunks.forEach(serialized_node_chunk => {
            this._consume_chunk_rawdata(serialized_node_chunk);
        });

        this._remove_obsolete_chunks();
        this._arrange_multiple_node_chunks();

        this._world.force_simulation.restart_with_alpha(0.3);

        this.update_layers();
        this._world.layout_manager.layout_applier.apply_multiple_layouts(
            this.get_hierarchy_list(),
            this._chunks_changed || this.always_update_layout
        );
        this._world.layout_manager.compute_node_positions();

        this.update_active_overlays();
    }

    _consume_chunk_rawdata(serialized_node_chunk: SerializedNodeChunk): void {
        // Generates a chunk object which includes the following data
        // {
        //   id:                 ID to identify this chunk
        //   type:               bi / topology
        //   tree:               hierarchy tree
        //   nodes:              visible nodes as list
        //   nodes_by_id:        all nodes by id
        //   links:              links between nodes
        //                       These are either provided in the rawdata or
        //                       automatically computed out of the hierarchy layout
        //   layout_settings:    layout configuration
        // }

        const hierarchy = d3.hierarchy<NodeData>(
            serialized_node_chunk.hierarchy
        );

        // Initialize default info of each node
        hierarchy.descendants().forEach(node => {
            node._children = node.children;
            node.data.node_positioning = {};
            node.data.transition_info = {};
            // User interactions, e.g. collapsing node, root cause analysis
            node.data.user_interactions = {};
        });

        const new_chunk = new NodeChunk(
            serialized_node_chunk.type,
            hierarchy,
            serialized_node_chunk.links,
            // @ts-ignore
            serialized_node_chunk.layout
        );

        // TODO: remove some bi hack
        if (serialized_node_chunk["aggr_type"])
            new_chunk["aggr_type"] = serialized_node_chunk["aggr_type"];

        this.update_node_chunk_list(new_chunk);
    }

    _remove_obsolete_chunks(): void {
        const new_chunk_list: NodeChunk[] = [];
        this._node_chunk_list.forEach(node_chunk => {
            if (!node_chunk.marked_obsolete) new_chunk_list.push(node_chunk);
            else this._chunks_changed = true;
        });
        this._node_chunk_list = new_chunk_list;
    }

    _filter_root_cause(node): void {
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

    _arrange_multiple_node_chunks(): void {
        if (this._node_chunk_list.length == 0) return;

        type hierarchy_overview_type = {
            name: "root";
            count: number;
            children: {name: string; count: number}[];
        };
        const partition_hierarchy: hierarchy_overview_type = {
            name: "root",
            children: [],
            count: 0,
        };
        this._node_chunk_list.forEach(chunk => {
            partition_hierarchy.children.push({
                name: chunk.id,
                count: chunk.nodes.length,
            });
        });

        const treemap_root = d3.hierarchy(partition_hierarchy);
        treemap_root.sum(d => d.count);

        d3.treemap().size([this.width, this.height])(treemap_root);
        for (const idx in treemap_root.children) {
            const child = treemap_root.children[idx];
            const node_chunk = this._node_chunk_list[idx];
            node_chunk.coords = {
                x: child.x0,
                y: child.y0,
                width: child.x1 - child.x0,
                height: child.y1 - child.y0,
            };

            let rad = 0;
            const rad_delta = Math.PI / 8;

            node_chunk.nodes.forEach(node => {
                if (node["x"])
                    // This node already has some coordinates
                    return;

                const spawn_coords = this._compute_spawn_coords(
                    node_chunk,
                    node
                );
                node.x = spawn_coords.x + Math.cos(rad) * (30 + rad * 4);
                node.y = spawn_coords.y + Math.sin(rad) * (30 + rad * 4);
                rad += rad_delta;
            });
        }
    }

    _compute_spawn_coords(
        node_chunk: NodeChunk,
        node: NodevisNode
    ): {x: number; y: number} {
        const linked_nodes: NodevisNode[] = this._find_linked_nodes(
            node_chunk,
            node
        );
        // Try to use the coordinates of active linked nodes
        for (const idx in linked_nodes) {
            const linked_node = linked_nodes[idx];
            if (linked_node.x) return {x: linked_node.x, y: linked_node.y};
        }

        // Try to use the coordinates of the parent node
        if (node.parent && node.parent.x) {
            return {x: node.parent.x, y: node.parent.y};
        }

        // Fallback. Spawn at center
        return {
            x: node_chunk.coords.width / 2,
            y: node_chunk.coords.height / 2,
        };
    }

    _find_linked_nodes(
        node_chunk: NodeChunk,
        node: NodevisNode
    ): NodevisNode[] {
        const linked_nodes: NodevisNode[] = [];
        node_chunk.links.forEach(link => {
            if (node == link.source) linked_nodes.push(link.target);
            else if (node == link.target) linked_nodes.push(link.source);
        });
        return linked_nodes;
    }

    get_all_links(): NodevisLink[] {
        let all_links: NodevisLink[] = [];
        this._node_chunk_list.forEach(chunk => {
            all_links = all_links.concat(chunk.links);
        });
        return all_links;
    }

    get_all_nodes(): NodevisNode[] {
        let all_nodes: NodevisNode[] = [];
        this._node_chunk_list.forEach(hierarchy => {
            all_nodes = all_nodes.concat(hierarchy.nodes);
        });
        return all_nodes;
    }

    get_hierarchy_list(): NodeChunk[] {
        return this._node_chunk_list;
    }

    get_chunk_of_node(node_in_chunk): NodeChunk | null {
        const root_node = this._get_chunk_root(node_in_chunk);
        for (const idx in this._node_chunk_list) {
            if (this._node_chunk_list[idx].tree == root_node)
                return this._node_chunk_list[idx];
        }
        return null;
    }

    _get_chunk_root(node): NodevisNode {
        if (!node.parent) return node;
        return this._get_chunk_root(node.parent);
    }

    update_node_chunk_list(new_chunk) {
        const chunk_id = new_chunk.tree.data.id;
        for (const idx in this._node_chunk_list) {
            const existing_chunk = this._node_chunk_list[idx];
            if (existing_chunk.tree.data.id == chunk_id) {
                new_chunk.layout_instance = existing_chunk.layout_instance;
                new_chunk.coords = existing_chunk.coords;
                new_chunk.nodes.forEach(node => {
                    const existing_node =
                        existing_chunk.nodes_by_id[node.data.id];
                    if (existing_node !== undefined)
                        this._migrate_node_content(existing_node, node);
                    else this._chunks_changed = true;
                });
                this._node_chunk_list[idx] = new_chunk;
                this._apply_user_interactions_to_chunk(new_chunk);
                if (existing_chunk.nodes.length != new_chunk.nodes.length)
                    this._chunks_changed = true;
                return;
            }
        }

        this._node_chunk_list.push(new_chunk);
    }

    _migrate_node_content(old_node, new_node) {
        // Reuse computed coordinates from previous chunk data
        new_node.x = old_node.x;
        new_node.y = old_node.y;

        // Migrate user interactions
        new_node.data.user_interactions = old_node.data.user_interactions;
    }

    _apply_user_interactions_to_chunk(chunk) {
        chunk.nodes.forEach(node => {
            const bi_setting = node.data.user_interactions.bi;
            if (bi_setting === undefined) return;

            switch (bi_setting) {
                case "collapsed":
                    node.children = null;
                    break;
                case "root_cause":
                    this._filter_root_cause(node);
                    break;
            }
        });
        this.update_node_chunk_descendants_and_links(chunk);
    }

    update_node_chunk_descendants_and_links(node_chunk) {
        // This feature is only supported/useful for bi visualization
        if (node_chunk.type != "bi") return;

        node_chunk.nodes = node_chunk.tree.descendants();
        const chunk_links: NodevisLink[] = [];
        node_chunk.nodes.forEach(node => {
            if (!node.parent || node.data.invisible) return;
            chunk_links.push({
                source: node,
                target: node.parent,
                config: {type: "default"},
            });
        });
        node_chunk.links = chunk_links;
    }

    recompute_node_chunk_descendants_and_links(node_chunk) {
        this.update_node_chunk_descendants_and_links(node_chunk);
        const all_nodes = this.get_all_nodes();
        const all_links = this.get_all_links();
        this.update_layers();
        this._world.force_simulation.update_nodes_and_links(
            all_nodes,
            all_links
        );
        this._world.force_simulation.restart_with_alpha(0.5);
    }

    update_layers() {
        this.update_data_of_layers();
        this.update_gui_of_layers();
    }

    update_data_of_layers() {
        for (const layer_id in this._layers) {
            if (!this._layers[layer_id].is_enabled()) continue;
            this._layers[layer_id].update_data();
        }
    }

    update_gui_of_layers() {
        for (const layer_id in this._layers) {
            if (!this._layers[layer_id].is_enabled()) continue;
            this._layers[layer_id].update_gui();
        }
    }

    zoomed(event) {
        if (!this.data_to_show) return;

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
    }

    // Applies scale and x/y translation
    translate_to_zoom(coords): Coords {
        const translated = this.scale_to_zoom(coords);
        if ("x" in translated) translated.x = this.last_zoom.x + translated.x;
        if ("y" in translated) translated.y = this.last_zoom.y + translated.y;
        return translated;
    }

    // Applies scale
    scale_to_zoom(
        coords: RectangleWithCoords | Coords
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

        this.scale_x = d3
            .scaleLinear()
            .domain([0, this.width])
            .range([0, this.width]);
        this.scale_y = d3
            .scaleLinear()
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

    zoom_to_coords(x: number, y: number): void {
        DefaultTransition.add_transition(this._svg_content_selection).call(
            this._zoom_behaviour.transform,
            () => this._zoom_coords(x, y)
        );
    }

    // TODO: integrate in zoom_to_coords
    _zoom_coords(x: number, y: number) {
        return d3.zoomIdentity
            .translate(this.width / 2, this.height / 2)
            .scale(this.last_zoom.k)
            .translate(x, y);
    }

    get_last_zoom(): ZoomTransform {
        return this.last_zoom;
    }

    reset_zoom() {
        this._svg_content_selection
            .transition()
            .duration(DefaultTransition.duration())
            .call(this._zoom_behaviour.transform, d3.zoomIdentity);
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
                .toString() + "ms"
        );
        row.datum(null);
        row.transition()
            .delay(10000)
            .duration(2000)
            .style("opacity", 0.0)
            .style("line-height", "0px")
            .remove();
    }

    _format_time(now): string {
        return (
            now.toLocaleTimeString("de") +
            "." +
            Math.floor(now.getMilliseconds() / 10)
        );
    }
}
