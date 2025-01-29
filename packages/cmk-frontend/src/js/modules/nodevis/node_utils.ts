/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import type {BaseType, Selection} from "d3";
import {select} from "d3";

import type {ForceOptions, SimulationForce} from "./force_utils";
import {get} from "./texts";
import type {
    ContextMenuElement,
    CoreInfo,
    d3SelectionDiv,
    d3SelectionG,
    NodevisNode,
    NodevisWorld,
    QuickinfoEntry,
} from "./type_defs";
import type {TypeWithName} from "./utils";
import {
    AbstractClassRegistry,
    add_basic_quickinfo,
    DefaultTransition,
} from "./utils";

export class AbstractGUINode implements TypeWithName {
    _world: NodevisWorld;
    _id: string;
    node: NodevisNode;
    radius: number;

    // Quickinfo popup
    _has_quickinfo: boolean;
    _external_quickinfo_data: null | {fetched_at_timestamp: number; data: any};
    _provides_external_quickinfo_data: boolean;
    _quickinfo_fetch_in_progress: boolean;

    // DOM references
    _selection: d3SelectionG | null;
    _text_selection: Selection<SVGTextElement, string, SVGGElement, any> | null;
    _quickinfo_selection: d3SelectionDiv | null;

    constructor(world: NodevisWorld, node: NodevisNode) {
        this._world = world;
        this._id = node.data.id;
        this.node = node;
        this.radius = 5;

        // DOM references
        this._selection = null;
        this._text_selection = null;
        this._quickinfo_selection = null;

        // Data fetched from external sources, e.g. livestatus
        this._has_quickinfo = true;
        this._provides_external_quickinfo_data = false;
        this._quickinfo_fetch_in_progress = false;
        this._external_quickinfo_data = null;
    }

    class_name() {
        return "abstract";
    }

    selection(): d3SelectionG {
        if (this._selection == null)
            throw Error("Missing selection for node " + this.id());
        return this._selection;
    }

    text_selection(): Selection<SVGTextElement, string, SVGGElement, any> {
        if (this._text_selection == null)
            throw Error("Missing text selection for node " + this.id());
        return this._text_selection;
    }

    quickinfo_selection(): d3SelectionDiv {
        if (this._quickinfo_selection == null)
            throw Error("Missing text selection for node " + this.id());
        return this._quickinfo_selection;
    }

    id() {
        return this._id;
    }

    _clear_cached_data() {
        this._external_quickinfo_data = null;
    }

    update_node_data(node: NodevisNode, _selection: d3SelectionG) {
        // TODO: make this obsolete. this class should only know the id, not the data reference
        this._clear_cached_data();
        this.node = node;
        this.update_node_state();
    }

    update_node_state() {
        if (!this.node.data.type_specific.core) return;
        this.selection()
            .select("circle.state_circle")
            .classed("state0", false)
            .classed("state1", false)
            .classed("state2", false)
            .classed("state3", false)
            .classed("state" + this.node.data.type_specific.core.state, true);

        const ack_selection = this.selection()
            .selectAll("image.acknowledged")
            .data(this.node.data.type_specific.core.acknowledged ? [null] : []);
        ack_selection
            .enter()
            .append("svg:image")
            .classed("acknowledged", true)
            .attr("xlink:href", "themes/facelift/images/icon_ack.png")
            .attr("x", -24)
            .attr("y", this.radius - 8)
            .attr("width", 24)
            .attr("height", 24);
        ack_selection.exit().remove();

        const dt_selection = this.selection()
            .selectAll("image.in_downtime")
            .data(this.node.data.type_specific.core.in_downtime ? [null] : []);
        dt_selection
            .enter()
            .append("svg:image")
            .classed("in_downtime", true)
            .attr("xlink:href", "themes/facelift/images/icon_downtime.svg")
            .attr("x", 0)
            .attr("y", this.radius - 8)
            .attr("width", 24)
            .attr("height", 24);
        dt_selection.exit().remove();
    }

    render_into(selection: d3SelectionG) {
        this._selection = this._render_into_transform(selection);
        this.render_object();
        this.render_text();
        this.update_node_state();
    }

    _get_text(node_id: string): string {
        return this._world.viewport.get_node_by_id(node_id).data.name;
    }

    render_text(): void {
        if (this.node.data.show_text == false) {
            if (this._text_selection) this.text_selection().remove();
            this._text_selection = null;
            return;
        }

        let is_host_text = false;
        let is_service_text = false;
        let is_other_text = false;
        const core_info = this.node.data.type_specific.core;
        if (this.node.data.node_type != "topology_site") {
            if (core_info) {
                is_service_text = !!core_info.service;
                if (!core_info.hostname) is_other_text = true;
                else is_host_text = !is_service_text;
            } else {
                is_other_text = true;
            }
        }

        if (this._text_selection == null) {
            const text_selection = this.selection()
                .selectAll<SVGTextElement, string>("g text")
                .data([this.id()]);
            this._text_selection = text_selection
                .enter()
                .append("g")
                .append("text")
                .style("pointer-events", "none")
                .classed("noselect", true)
                .classed("host_text", is_host_text)
                .classed("service_text", is_service_text)
                .classed("other_text", is_other_text)
                .attr(
                    "transform",
                    "translate(" +
                        (this.radius + 3) +
                        "," +
                        (this.radius + 3) +
                        ")",
                )
                .attr("text-anchor", "start")
                .text(d => {
                    return this._get_text(d);
                })
                .merge(text_selection);
        }
    }

    _update_text_position() {
        if (!this._text_selection) return;
        const text_positioning =
            this.node.data.current_positioning.text_positioning;
        if (text_positioning) {
            this.add_optional_transition(this.text_selection()).call(
                text_positioning,
                this.radius,
            );
        } else {
            this.add_optional_transition(this.text_selection()).call(
                //@ts-ignore
                (
                    selection: Selection<
                        SVGTextElement,
                        string,
                        SVGGElement,
                        any
                    >,
                ) => this._default_text_positioning(selection, this.radius),
            );
        }
    }

    _default_text_positioning(
        selection: Selection<SVGTextElement, string, SVGGElement, any>,
        radius: number,
    ) {
        selection.attr(
            "transform",
            "translate(" + (radius + 3) + "," + (radius + 3) + ")",
        );
        selection.attr("text-anchor", "start");
    }

    _render_into_transform(selection: d3SelectionG): d3SelectionG {
        if (selection.attr("transform") != null) return selection;

        let spawn_reference = this.node;
        if (this.node.parent && this.node.parent.x) {
            spawn_reference = this.node.parent;
        }
        const spawn_point_x = spawn_reference.x;
        const spawn_point_y = spawn_reference.y;

        if (this.node.data.target_coords == null)
            this.node.data.target_coords = {x: spawn_point_x, y: spawn_point_y};
        selection
            .attr(
                "transform",
                "translate(" + spawn_point_x + "," + spawn_point_y + ")",
            )
            .on("mouseover", () => this._show_quickinfo())
            .on("mouseout", () => this._hide_quickinfo())
            .on("contextmenu", event => {
                this._world.viewport
                    .get_nodes_layer()
                    .render_context_menu(event, this.id());
            });
        return selection;
    }

    _get_details_url(): string {
        return "";
    }

    _get_hostname_and_service(): [string, string] {
        const core_info = get_core_info(this.node)!;
        return [core_info.hostname, core_info.service || ""];
    }

    get_context_menu_elements(): ContextMenuElement[] {
        const elements: ContextMenuElement[] = [];
        const core_info = this.node.data.type_specific.core;
        if (!core_info) return elements;

        const [hostname, service] = this._get_hostname_and_service();
        elements.push({
            text: get("host_details"),
            href:
                "view.py?host=" +
                encodeURIComponent(hostname) +
                "&view_name=host",
            img: "themes/facelift/images/icon_status.svg",
        });
        if (service && service != "") {
            elements.push({
                text: get("service_details"),
                href:
                    "view.py?host=" +
                    encodeURIComponent(hostname) +
                    "&service=" +
                    encodeURIComponent(service) +
                    "&view_name=service",
                img: "themes/facelift/images/icon_status.svg",
            });
        }
        return elements;
    }

    _filter_root_cause(node: NodevisNode) {
        // TODO: looks like duplicate (viewport.ts)
        if (!node._children) return;
        const critical_children: NodevisNode[] = [];
        node._children.forEach(child_node => {
            if (child_node.data.type_specific.core.state != 0) {
                critical_children.push(child_node);
                this._filter_root_cause(child_node);
            } else {
                this._clear_node_positioning_of_tree(child_node);
            }
        });
        node.children = critical_children;
        node.data.user_interactions.bi = "root_cause";
        this.update_collapsed_indicator(node);
    }

    _clear_node_positioning_of_tree(tree_root: NodevisNode) {
        tree_root.data.node_positioning = {};
        if (!tree_root._children) return;

        tree_root._children.forEach(child_node => {
            this._clear_node_positioning_of_tree(child_node);
        });
    }

    collapse_node() {
        this.node.children = [];
        this.node.data.user_interactions.bi = "collapsed";
        this._world.viewport.recompute_node_and_links();
        this._world.viewport.update_layers();
        this.update_collapsed_indicator(this.node);
    }

    expand_node() {
        this.node.children = this.node._children || [];
        delete this.node.data.user_interactions.bi;
        this._world.viewport.recompute_node_and_links();
        this._world.viewport.update_layers();
        this.update_collapsed_indicator(this.node);
    }

    expand_node_including_children(node: NodevisNode) {
        if (node._children) {
            node.children = node._children;
            node.children.forEach(child_node =>
                this.expand_node_including_children(child_node),
            );
        }
        delete node.data.user_interactions.bi;
        this.update_collapsed_indicator(node);
    }

    update_collapsed_indicator(node: NodevisNode) {
        if (!node._children) return;

        const collapsed = node.children != node._children;
        const gui_node = this._world.viewport
            .get_nodes_layer()
            .get_node_by_id(node.data.id);
        if (gui_node) {
            const outer_circle = gui_node.selection().select("circle");
            outer_circle.classed("collapsed", collapsed);
        }

        const nodes = this._world.viewport.get_all_nodes();
        for (const idx in nodes) {
            nodes[idx].data.transition_info.use_transition = true;
        }
    }

    _fixate_quickinfo() {
        if (this._world.viewport.get_layout_manager().edit_layout) return;

        if (this.quickinfo_selection().classed("fixed")) {
            this._hide_quickinfo(true);
            return;
        }

        this._show_quickinfo();
        this.quickinfo_selection().classed("fixed", true);
    }

    _hide_quickinfo(force = false) {
        if (
            !this._quickinfo_selection ||
            (this._quickinfo_selection.classed("fixed") && !force)
        )
            return;

        this._quickinfo_selection.remove();
        this._quickinfo_selection = null;
    }

    _show_quickinfo() {
        if (!this._has_quickinfo) return;

        if (this._world.viewport.get_layout_manager().edit_layout) return;

        const div_selection = this._world.viewport
            .get_nodes_layer()
            .get_div_selection()
            .selectAll<HTMLDivElement, string>("div.quickinfo")
            .data([null]);
        div_selection.exit().remove();
        this._quickinfo_selection = div_selection
            .enter()
            .append("div")
            .classed("quickinfo", true)
            .classed("noselect", true)
            .classed("box", true)
            .style("position", "absolute")
            .style("pointer-events", "all")
            .on("click", () => this._hide_quickinfo(true))
            .merge(div_selection);

        if (this._provides_external_quickinfo_data)
            this._show_external_html_quickinfo();
        else this._show_table_quickinfo();
    }

    _show_external_html_quickinfo() {
        if (
            this._external_quickinfo_data != null &&
            this._world.viewport.feed_data_timestamp <
                this._external_quickinfo_data.fetched_at_timestamp
        ) {
            // Replace content
            this.quickinfo_selection().selectAll("*").remove();
            const node = this.quickinfo_selection().node();
            if (node)
                // make typescript happy
                node.append(
                    this._external_quickinfo_data.data.cloneNode(true).body,
                );
        } else if (!this._quickinfo_fetch_in_progress)
            this._fetch_external_quickinfo();
        if (this._quickinfo_fetch_in_progress)
            this.quickinfo_selection()
                .selectAll(".icon.reloading")
                .data([null])
                .enter()
                .append("img")
                .classed("icon", true)
                .classed("reloading", true)
                .attr("src", "themes/facelift/images/load_graph.png");
        else this.quickinfo_selection().selectAll(".icon.reloading").remove();

        this.update_quickinfo_position();
    }

    _fetch_external_quickinfo(): void {
        return;
    }

    _get_basic_quickinfo(): QuickinfoEntry[] {
        return [];
    }

    _show_table_quickinfo() {
        const quickinfo = this._get_basic_quickinfo();
        add_basic_quickinfo(this.quickinfo_selection(), quickinfo);
        this.update_quickinfo_position();
    }

    _got_quickinfo(json_data: Record<string, any>) {
        const now = Math.floor(new Date().getTime() / 1000);
        this._external_quickinfo_data = {
            fetched_at_timestamp: now,
            data: json_data,
        };
        this._quickinfo_fetch_in_progress = false;
        if (this._quickinfo_selection) this._show_quickinfo();
    }

    _state_to_text(state: 0 | 1 | 2 | 3) {
        const monitoring_states = {0: "OK", 1: "WARN", 2: "CRIT", 3: "UNKNOWN"};
        return monitoring_states[state];
    }

    render_object() {
        this.selection()
            .selectAll("a")
            .data([this.id()])
            .join(enter =>
                enter
                    .append("a")
                    .each((_data, idx, nodes) => {
                        const a = select(nodes[idx]);
                        const details_url = this._get_details_url();
                        if (details_url != "")
                            a.attr("xlink:href", details_url);
                    })
                    .append("circle")
                    .attr("r", this.radius)
                    .classed("state_circle", true),
            );

        const icon_url = this._get_icon_url();
        const icon_object = this.selection()
            .selectAll<SVGImageElement, string>("g image.main_icon")
            .data(icon_url ? [icon_url] : [], d => d)
            .enter()
            .append("g")
            .attr("transform", "translate(-24,-24)")
            .append("svg:image")
            .classed("main_icon", true)
            .attr("xlink:href", d => d)
            .attr("width", 24)
            .attr("height", 24);
        icon_object.append("title").text(get("icon_in_monitoring"));
    }

    _get_icon_url(): string | null {
        // Return the URL of the icon to be used for the node
        // Explicit images are preferred over the default ones from the core
        const type_specific = this.node.data.type_specific;
        if (!type_specific) return "";

        const explicit_icon = type_specific.node_images?.icon;
        if (explicit_icon) return explicit_icon;

        const core_icon = type_specific.core?.icon;
        if (core_icon) return core_icon;
        return null;
    }

    update_position(enforce_transition = false) {
        this.node.data.target_coords = this._world.viewport.scale_to_zoom({
            x: this.node.x,
            y: this.node.y,
        });

        if (
            this.node.data.transition_info.use_transition ||
            this.node.data.current_positioning.type == "force"
        )
            this.selection().interrupt();

        // TODO: remove in_transit COMPLETELY, way too over-engineered
        if (parseInt(this.selection().attr("in_transit")) > 0) {
            return;
        }

        const transition = this.add_optional_transition(
            this.selection(),
            enforce_transition,
        );
        transition.attr(
            "transform",
            "translate(" +
                this.node.data.target_coords.x +
                "," +
                this.node.data.target_coords.y +
                ")",
        );

        this.update_quickinfo_position();
        this._update_text_position();
        this.node.data.transition_info.type =
            this.node.data.current_positioning.type;
    }

    update_quickinfo_position() {
        if (this._quickinfo_selection == null) return;
        const gui_node = this._world.viewport
            .get_nodes_layer()
            .get_node_by_id(this.id());
        if (!gui_node) return;
        const coords = this._world.viewport.translate_to_zoom({
            x: gui_node.node.x,
            y: gui_node.node.y,
        });
        this._quickinfo_selection
            .style("left", coords.x + this.radius + "px")
            .style("top", coords.y + "px");
    }

    add_optional_transition<GType extends BaseType, Data>(
        selection: Selection<GType, Data, SVGGElement, any>,
        enforce_transition = false,
    ) {
        // TODO: remove
        if (this._world.viewport.get_layout_manager().skip_optional_transitions)
            return selection;

        if (
            (!this.node.data.transition_info.use_transition &&
                !enforce_transition) ||
            this._world.viewport.get_layout_manager().dragging
        )
            return selection;

        return DefaultTransition.add_transition(
            selection.attr("in_transit", 100),
        )
            .on("end", () => {
                const node = this.selection().node();
                if (!node) return;

                if (node.transform.baseVal.length == 0) return;

                const matrix = node.transform.baseVal[0].matrix;
                // TODO: check this preliminary fix. target_coords might be empty
                if (!this.node.data.target_coords) return;
                if (
                    matrix.e.toFixed(2) !=
                        this.node.data.target_coords.x.toFixed(2) ||
                    matrix.f.toFixed(2) !=
                        this.node.data.target_coords.y.toFixed(2)
                ) {
                    this.update_position(true);
                }
            })
            .attr("in_transit", 0)
            .on("interrupt", () => {
                this.selection().attr("in_transit", 0);
            })
            .attr("in_transit", 0);
    }

    get_force(
        force_name: SimulationForce,
        force_options: ForceOptions,
    ): number {
        return this._get_node_type_specific_force(force_name, force_options);
    }

    _get_node_type_specific_force(
        force_name: SimulationForce,
        force_options: ForceOptions,
    ): number {
        return force_options[force_name];
    }

    simulation_end_actions(): void {
        return;
    }
}

export function get_core_info(node: NodevisNode): CoreInfo | null {
    return node.data.type_specific.core ? node.data.type_specific.core : null;
}

export function get_custom_node_settings(node: NodevisNode) {
    node.data.type_specific.custom_node_settings =
        node.data.type_specific.custom_node_settings || {};
    return node.data.type_specific.custom_node_settings;
}

// Stores node visualization classes
class NodeTypeClassRegistry extends AbstractClassRegistry<AbstractGUINode> {}

export const node_type_class_registry = new NodeTypeClassRegistry();
