/**
 * Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import "nodevis/node_types";
import "nodevis/link_types";

import * as d3 from "d3";
import {
    FixLayer,
    layer_class_registry,
    LayerSelections,
    ToggleableLayer,
} from "nodevis/layer_utils";
import {
    AbstractLink,
    compute_link_id,
    link_type_class_registry,
} from "nodevis/link_utils";
import {AbstractGUINode, node_type_class_registry} from "nodevis/node_utils";
import {
    ContextMenuElement,
    Coords,
    d3SelectionDiv,
    d3SelectionG,
    NodevisLink,
    NodevisNode,
    NodevisWorld,
    RectangleWithCoords,
} from "nodevis/type_defs";
import {DefaultTransition} from "nodevis/utils";

export class LayeredDebugLayer extends ToggleableLayer {
    static class_name = "debug_layer";
    _anchor_info?: d3SelectionG;

    id() {
        return "debug_layer";
    }

    z_index(): number {
        return 20;
    }

    name() {
        return "Debug Layer";
    }

    setup() {
        this.overlay_active = false;
    }

    update_gui() {
        this._div_selection
            .selectAll("td#Simulation")
            .text(
                "Alpha: " +
                    this._world.force_simulation._simulation.alpha().toFixed(3)
            );
        if (this.overlay_active == this._world.layout_manager.edit_layout)
            return;

        if (this._world.layout_manager.edit_layout) this.enable_overlay();
        else this.disable_overlay();
    }

    _update_chunk_boundaries() {
        if (!this._world.layout_manager.edit_layout) {
            this._svg_selection.selectAll("rect.boundary").remove();
            return;
        }

        type RectangleWithId = {id: string} & RectangleWithCoords;
        const boundary_list: RectangleWithId[] = [];
        this._world.viewport.get_hierarchy_list().forEach(node_chunk => {
            const coords = this._world.viewport.translate_to_zoom(
                node_chunk.coords
            ) as unknown as RectangleWithId;
            coords.id = node_chunk.id;
            boundary_list.push(coords);
        });

        let boundaries = this._svg_selection
            .selectAll<SVGRectElement, RectangleWithId>("rect.boundary")
            .data(boundary_list, d => d.id);
        boundaries.exit().remove();
        boundaries = boundaries
            .enter()
            .append("rect")
            .classed("boundary", true)
            .attr("fill", "none")
            .attr("stroke", "black")
            .attr("stroke-width", 1)
            .merge(boundaries);

        boundaries
            .attr("x", d => d.x)
            .attr("y", d => d.y)
            .attr("width", d => d.width)
            .attr("height", d => d.height);
    }

    enable_overlay() {
        this.overlay_active = true;
        this._anchor_info = this._svg_selection
            .append("g")
            .attr("transform", "translate(-50,-50)");

        this._div_selection
            .append("input")
            .style("pointer-events", "all")
            .attr("id", "reset_pan_and_zoom")
            .attr("type", "button")
            .classed("button", true)
            .attr("value", "Reset panning and zoom")
            .on("click", () => this.reset_pan_and_zoom())
            .style("opacity", 0)
            .transition()
            .duration(DefaultTransition.duration())
            .style("opacity", 1);

        this._world.viewport
            .get_div_selection()
            .on("mousemove.translation_info", event => this.mousemove(event));
        const rows = this._div_selection
            .append("table")
            .attr("id", "translation_infobox")
            .selectAll("tr")
            .data(["Zoom", "Panning", "Mouse"]);

        const rows_enter = rows.enter().append("tr");
        rows_enter
            .append("td")
            .text(d => d)
            .classed("noselect", true);
        rows_enter
            .append("td")
            .attr("id", d => d)
            .classed("noselect", true);
        this.size_changed();
        this.zoomed();
    }

    disable_overlay() {
        this.overlay_active = false;
        this._svg_selection
            .selectAll("*")
            .transition()
            .duration(DefaultTransition.duration())
            .attr("opacity", 0)
            .remove();
        this._div_selection
            .selectAll("*")
            .transition()
            .duration(DefaultTransition.duration())
            .style("opacity", 0)
            .remove();
        this._world.viewport
            .get_div_selection()
            .on("mousemove.translation_info", null);
    }

    size_changed() {
        if (!this.overlay_active) return;
    }

    reset_pan_and_zoom() {
        this._world.viewport.reset_zoom();
    }

    zoomed() {
        if (!this.overlay_active || !this._anchor_info) return;
        // TODO: check if toString is working
        this._anchor_info.attr(
            "transform",
            this._world.viewport.get_last_zoom().toString()
        );
        const last_zoom = this._world.viewport.get_last_zoom();
        this._div_selection.selectAll("td#Zoom").text(last_zoom.k.toFixed(2));
        this._div_selection
            .selectAll("td#Panning")
            .text("X: " + last_zoom.x + " / Y:" + last_zoom.y);
    }

    mousemove(event) {
        const coords = d3.pointer(event);
        this._div_selection
            .selectAll("td#Mouse")
            .text("X:" + coords[0] + " / Y:" + coords[1]);
    }
}

export class LayeredIconOverlay extends ToggleableLayer {
    static class_name = "node_icon_overlay";

    id() {
        return "node_icon_overlay";
    }

    z_index(): number {
        return 10;
    }

    name() {
        return "Node icons";
    }

    update_gui() {
        const nodes: NodevisNode[] = [];
        this._world.viewport.get_all_nodes().forEach(node => {
            if (!node.data.icon_image) return;
            nodes.push(node);
        });

        let icons = this._div_selection
            .selectAll<HTMLImageElement, NodevisNode>("img")
            .data(nodes, d => d.data.id);
        icons.exit().remove();
        icons = icons
            .enter()
            .append("img")
            .attr(
                "src",
                d => "themes/facelift/images/icon_" + d.data.icon_image + ".svg"
            )
            .classed("node_icon", true)
            .style("position", "absolute")
            .style("pointer-events", "none")
            .merge(icons);

        icons
            .style("left", d => {
                return (
                    this._world.viewport.translate_to_zoom({x: d.x, y: 0}).x -
                    24 +
                    "px"
                );
            })
            .style("top", d => {
                return (
                    this._world.viewport.translate_to_zoom({x: 0, y: d.y}).y -
                    24 +
                    "px"
                );
            });
    }
}

//#.
//#   .-Nodes Layer--------------------------------------------------------.
//#   |      _   _           _             _                               |
//#   |     | \ | | ___   __| | ___  ___  | |    __ _ _   _  ___ _ __      |
//#   |     |  \| |/ _ \ / _` |/ _ \/ __| | |   / _` | | | |/ _ \ '__|     |
//#   |     | |\  | (_) | (_| |  __/\__ \ | |__| (_| | |_| |  __/ |        |
//#   |     |_| \_|\___/ \__,_|\___||___/ |_____\__,_|\__, |\___|_|        |
//#   |                                               |___/                |
//#   +--------------------------------------------------------------------+

export class LayeredNodesLayer extends FixLayer {
    static class_name = "nodes";
    node_instances: {[name: string]: AbstractGUINode};
    link_instances: {[name: string]: AbstractLink};
    _links_for_node: {[name: string]: AbstractLink[]} = {};
    last_scale: number;

    nodes_selection: d3SelectionG;
    links_selection: d3SelectionG;
    popup_menu_selection: d3SelectionDiv;

    constructor(world: NodevisWorld, selections: LayerSelections) {
        super(world, selections);
        this.last_scale = 1;
        // Node instances by id
        this.node_instances = {};
        // NodeLink instances
        this.link_instances = {};

        // Nodes/Links drawn on screen
        this.links_selection = this._svg_selection
            .append("g")
            .attr("name", "viewport_layered_links")
            .attr("id", "links");
        this.nodes_selection = this._svg_selection
            .append("g")
            .attr("name", "viewport_layered_nodes")
            .attr("id", "nodes");
        this.popup_menu_selection = this._div_selection
            .append("div")
            .attr("id", "popup_menu")
            .style("pointer-events", "all")
            .style("position", "absolute")
            .classed("popup_menu", true)
            .style("display", "none");
    }

    id() {
        return "nodes";
    }

    get_node_by_id(node_id: string): AbstractGUINode | null {
        return this.node_instances[node_id];
    }

    get_nodevis_node_by_id(node_id: string): NodevisNode | null {
        const gui_node = this.get_node_by_id(node_id);
        if (!gui_node) return null;
        return gui_node.node;
    }

    get_links_for_node(node_id: string): AbstractLink[] {
        return this._links_for_node[node_id] || [];
    }

    simulation_end() {
        for (const name in this.node_instances) {
            this.node_instances[name].simulation_end_actions();
        }
    }

    z_index(): number {
        return 50;
    }

    name() {
        return "Nodes Layer";
    }

    setup(): void {
        return;
    }

    render_line_style(into_selection: d3SelectionG): void {
        const line_style_row = into_selection
            .selectAll("table.line_style tr")
            .data([null])
            .join(enter =>
                enter.append("table").classed("line_style", true).append("tr")
            );

        line_style_row
            .selectAll("td.label")
            .data([null])
            .join("td")
            .classed("label", true)
            .text("Line style");

        const select = line_style_row
            .selectAll("td.select")
            .data([null])
            .join(enter =>
                enter
                    .append("td")
                    .classed("select", true)
                    .append("select")
                    .style("pointer-events", "all")
                    .style("width", "200px")
                    .on("change", event => this._change_line_style(event))
            );

        let current_style = "round";
        this._world.viewport.get_hierarchy_list().forEach(node_chunk => {
            current_style = node_chunk.layout_settings.config.line_config.style;
        });

        select
            .selectAll<HTMLOptionElement, any>("option")
            .data(["straight", "round", "elbow"])
            .join("option")
            .property("value", d => d)
            .property("selected", d => d == current_style)
            .text(d => d);
    }

    _change_line_style(event): void {
        const new_line_style = d3.select(event.target).property("value");
        this._world.viewport.get_hierarchy_list().forEach(node_chunk => {
            // @ts-ignore
            node_chunk.layout_instance.line_config.style = new_line_style;
            // @ts-ignore
            node_chunk.layout_settings.config.line_config.style =
                new_line_style;
        });

        this.update_data();
        this.update_gui(true);
    }

    zoomed(): void {
        // Interrupt any gui transitions whenever the zoom factor is changed
        if (this.last_scale != this._world.viewport.last_zoom.k)
            this._svg_selection
                .selectAll(".node_element, .link_element")
                .interrupt();

        for (const idx in this.node_instances)
            this.node_instances[idx].update_quickinfo_position();

        if (this.last_scale != this._world.viewport.last_zoom.k)
            this.update_gui(true);

        this.last_scale = this._world.viewport.last_zoom.k;
    }

    update_data(): void {
        this._update_nodes();
        this._update_links();
    }

    _update_nodes(): void {
        const visible_nodes = this._world.viewport
            .get_all_nodes()
            .filter(d => !d.data.invisible);

        const old_node_instances: {[name: string]: AbstractGUINode} =
            this.node_instances;
        this.node_instances = {};

        // Update data
        const node_ids: string[] = [];
        visible_nodes.forEach(node_config => {
            const new_node = this._create_node(node_config);
            this.node_instances[new_node.id()] = new_node;
            node_ids.push(new_node.id());
        });

        // Update GUI
        this.nodes_selection
            .selectAll<SVGGElement, string>(".node_element")
            .data(node_ids, d => {
                return d;
            })
            .join(
                enter => enter.append("g").classed("node_element", true),
                update => update,
                exit =>
                    exit.each((node_id, idx, node_list) => {
                        this._add_node_vanish_animation(
                            d3.select(node_list[idx]),
                            node_id,
                            old_node_instances
                        );
                    })
            )
            .each((node_id, idx, node_list) => {
                this.node_instances[node_id].render_into(
                    d3.select(node_list[idx])
                );
            });
    }

    _add_node_vanish_animation(node, node_id, old_node_instances) {
        const old_instance = old_node_instances[node_id];
        if (!old_instance) {
            node.remove();
            return;
        }

        const vanish_coords = this._world.viewport.scale_to_zoom(
            this._world.viewport.compute_spawn_coords(
                old_instance.node.data.chunk,
                old_instance.node
            )
        );

        // Move vanishing nodes, back to their parent nodes
        node.transition()
            .duration(DefaultTransition.duration())
            .attr(
                "transform",
                "translate(" + vanish_coords.x + "," + vanish_coords.y + ")"
            )
            .style("opacity", 0)
            .remove();
    }

    _update_links(): void {
        const link_configs = this._world.viewport.get_all_links();
        this._links_for_node = {};

        // Recreate instances
        this.link_instances = {};
        const link_ids: Set<string> = new Set();
        link_configs.forEach(link_config => {
            const link_id = compute_link_id(link_config);
            if (link_ids.has(link_id)) {
                return;
            }

            const new_link = this._create_link(link_config);
            this.link_instances[link_id] = new_link;
            link_ids.add(link_id);

            // Update quick references: {node_id : connected link[]}
            const source_id = link_config.source.data.id;
            const target_id = link_config.target.data.id;
            source_id in this._links_for_node ||
                (this._links_for_node[source_id] = []);
            target_id in this._links_for_node ||
                (this._links_for_node[target_id] = []);
            this._links_for_node[source_id].push(new_link);
            this._links_for_node[target_id].push(new_link);
        });

        // Update GUI
        this.links_selection
            .selectAll<SVGGElement, string>("g.link_element")
            .data(link_ids, d => d)
            .join("g")
            .classed("link_element", true)
            .each((link_id, idx, nodes) => {
                this.link_instances[link_id].render_into(d3.select(nodes[idx]));
            });
    }

    _create_node(node_data: NodevisNode): AbstractGUINode {
        const node_class = node_type_class_registry.get_class(
            node_data.data.node_type
        );
        // @ts-ignore
        return new node_class(this._world, node_data);
    }

    _create_link(link_data: NodevisLink): AbstractLink {
        const link_class = link_type_class_registry.get_class(
            link_data.config.type
        );
        return new link_class(this._world, link_data);
    }

    update_gui(force = false): void {
        this._update_position_of_context_menu();
        if (!force && this._world.force_simulation._simulation.alpha() < 0.11) {
            for (const idx in this.node_instances)
                this.node_instances[
                    idx
                ].node.data.transition_info.use_transition = false;
            return;
        }

        for (const idx in this.node_instances)
            this.node_instances[idx].update_position();

        for (const idx in this.link_instances)
            this.link_instances[idx].update_position();

        // Disable node transitions after each update step
        for (const idx in this.node_instances)
            this.node_instances[idx].node.data.transition_info.use_transition =
                false;
    }

    render_context_menu(event: MouseEvent, node_id: string | null): void {
        if (!this._world.layout_manager.edit_layout && !node_id) return; // Nothing to show

        //        let coords : Coords = {x: 0, y:0};
        //        if (node_instance) {
        //            coords = {
        //                x: node_instance.node.x,
        //                y: node_instance.node.y,
        //            }
        //        } else {
        //            let last_zoom = this._world.viewport.last_zoom;
        //            coords = {
        //                x: (event.offsetX - last_zoom.x) / last_zoom.k,
        //                y: (event.offsetY - last_zoom.y) / last_zoom.k,
        //            };
        //        }

        event.preventDefault();
        event.stopPropagation();

        // TODO: remove this, apply general update pattern..
        this.popup_menu_selection.selectAll("*").remove();
        const content_ul = this.popup_menu_selection.append("ul");

        let gui_node: AbstractGUINode | null = null;
        if (node_id) gui_node = this._world.nodes_layer.get_node_by_id(node_id);

        // Create li for each item
        if (this._world.layout_manager.edit_layout) {
            // Add elements layout manager
            this._add_elements_to_context_menu(
                content_ul,
                "layouting",
                this._world.layout_manager.get_context_menu_elements(
                    gui_node ? gui_node.node : null
                )
            );
            if (gui_node) content_ul.append("li").append("hr");
        }

        // Add elements from node
        if (gui_node)
            this._add_elements_to_context_menu(
                content_ul,
                "node",
                gui_node.get_context_menu_elements()
            );
        else {
            this.popup_menu_selection
                .style("left", event.offsetX + "px")
                .style("top", event.offsetY + "px");
        }

        this.popup_menu_selection.datum(gui_node);

        if (content_ul.selectAll("li").empty())
            this.popup_menu_selection.style("display", "none");
        else this._update_position_of_context_menu();
    }

    _add_elements_to_context_menu(
        content: d3.Selection<HTMLUListElement, unknown, any, unknown>,
        element_source: string,
        elements: ContextMenuElement[]
    ): void {
        let links = content
            .selectAll<HTMLAnchorElement, ContextMenuElement>(
                "li" + "." + element_source + " a"
            )
            .data(elements);

        links = links
            .join("li")
            .classed(element_source, true)
            .append("a")
            .classed("noselect", true);

        // Add optional href
        links.each((d, idx, nodes) => {
            if (d.href) {
                d3.select(nodes[idx])
                    .attr("href", d.href)
                    .on("click", () => this.hide_context_menu());
            }
        });

        // Add optional img
        links.each(function (d) {
            if (d.img) {
                d3.select(this)
                    .append("img")
                    .classed("icon", true)
                    .attr("src", d.img);
            }
        });

        // Add text
        links.each(function (d) {
            d3.select(this)
                .append("div")
                .style("display", "inline-block")
                .text(d.text);
        });

        // Add optional click handler
        links.each((d, idx, nodes) => {
            if (d.on) {
                d3.select(nodes[idx]).on("click", event => {
                    if (d.on) d.on(event);
                    this.hide_context_menu();
                });
            }
        });
    }

    _update_position_of_context_menu(): void {
        if (this.popup_menu_selection.selectAll("li").empty()) return;

        this.popup_menu_selection.style("display", null);

        // Set position
        const gui_node =
            this.popup_menu_selection.datum() as AbstractGUINode | null;
        if (gui_node == null) return;

        const old_coords: Coords = {x: gui_node.node.x, y: gui_node.node.y};
        const new_coords = this._world.viewport.translate_to_zoom(old_coords);

        this.popup_menu_selection
            .style("left", new_coords.x + "px")
            .style("top", new_coords.y + "px");
    }

    hide_context_menu(): void {
        this.popup_menu_selection.selectAll("*").remove();
        this.popup_menu_selection.style("display", "none");
    }
}

layer_class_registry.register(LayeredIconOverlay);
layer_class_registry.register(LayeredDebugLayer);
layer_class_registry.register(LayeredNodesLayer);
