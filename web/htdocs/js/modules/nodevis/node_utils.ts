// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

import {
    ContextMenuElement,
    d3SelectionG,
    NodevisNode,
    NodevisWorld,
} from "nodevis/type_defs";
import * as d3 from "d3";

import {
    AbstractClassRegistry,
    DefaultTransition,
    TypeWithName,
} from "nodevis/utils";
import {ForceOptions, SimulationForce} from "nodevis/force_simulation";

type d3SelectionNodeText = d3.Selection<
    SVGTextElement,
    NodevisNode,
    SVGGElement,
    any
>;

type d3SelectionQuickinfo = d3.Selection<
    HTMLDivElement,
    NodevisNode,
    HTMLDivElement,
    any
>;
export type BasicQuickinfo = {
    name: string;
    value: string;
    css_classes?: string[];
};

export class AbstractGUINode implements TypeWithName {
    class_name = "abstract";
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
    _text_selection: d3.Selection<
        SVGTextElement,
        string,
        SVGGElement,
        any
    > | null;
    _quickinfo_selection: d3SelectionQuickinfo | null;

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

    selection(): d3SelectionG {
        if (this._selection == null)
            throw Error("Missing selection for node " + this.id());
        return this._selection;
    }

    text_selection(): d3.Selection<SVGTextElement, string, SVGGElement, any> {
        if (this._text_selection == null)
            throw Error("Missing text selection for node " + this.id());
        return this._text_selection;
    }

    quickinfo_selection(): d3SelectionQuickinfo {
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

    update_node_data(node, selection) {
        // TODO: make this obsolete. this class should only know the id, not the data reference
        this._clear_cached_data();
        node.data.selection = selection;
        this.node = node;
        this.update_node_state();
    }

    update_node_state() {
        this.selection()
            .select("circle.state_circle")
            .classed("state0", false)
            .classed("state1", false)
            .classed("state2", false)
            .classed("state3", false)
            .classed("state" + this.node.data.state, true);

        const ack_selection = this.selection()
            .selectAll("image.acknowledged")
            .data(this.node.data.acknowledged ? [null] : []);
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
            .data(this.node.data.in_downtime ? [null] : []);
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
        // TODO: check usage
        this.node.data.selection = this._selection;

        this.render_object();
        this.render_text();
        this.update_node_state();
    }

    _get_text(node_id: string): string {
        const node = this._world.nodes_layer.get_nodevis_node_by_id(node_id);
        if (!node) return "";
        if (node.data.chunk.aggr_type == "single" && node.data.service)
            return node.data.service;
        return node.data.name;
    }

    render_text(): void {
        if (this.node.data.show_text == false) {
            if (this._text_selection) this.text_selection().remove();
            this._text_selection = null;
            return;
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
                .attr(
                    "transform",
                    "translate(" +
                        (this.radius + 3) +
                        "," +
                        (this.radius + 3) +
                        ")"
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
                this.radius
            );
        } else {
            this.add_optional_transition(this.text_selection()).call(
                selection =>
                    this._default_text_positioning(selection, this.radius)
            );
        }
    }

    _default_text_positioning(selection, radius) {
        selection.attr(
            "transform",
            "translate(" + (radius + 3) + "," + (radius + 3) + ")"
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

        this.node.data.target_coords = {x: spawn_point_x, y: spawn_point_y};
        selection
            .attr(
                "transform",
                "translate(" + spawn_point_x + "," + spawn_point_y + ")"
            )
            .style("pointer-events", "all")
            .on("mouseover", () => this._show_quickinfo())
            .on("mouseout", () => this._hide_quickinfo())
            .on("contextmenu", event => {
                this._world.nodes_layer.render_context_menu(event, this.id());
            });
        return selection;
    }

    _get_details_url(): string {
        return "";
    }

    get_context_menu_elements() {
        const elements: ContextMenuElement[] = [];
        elements.push({
            text: "Details of Host",
            href:
                "view.py?host=" +
                encodeURIComponent(this.node.data.hostname) +
                "&view_name=host",
            img: "themes/facelift/images/icon_status.svg",
        });
        if (this.node.data.service && this.node.data.service != "") {
            elements.push({
                text: "Details of Service",
                href:
                    "view.py?host=" +
                    encodeURIComponent(this.node.data.hostname) +
                    "&service=" +
                    encodeURIComponent(this.node.data.service) +
                    "&view_name=service",
                img: "themes/facelift/images/icon_status.svg",
            });
        }
        return elements;
    }

    _filter_root_cause(node) {
        // TODO: looks like duplicate (viewport.ts)
        if (!node._children) return;
        const critical_children: NodevisNode[] = [];
        node._children.forEach(child_node => {
            if (child_node.data.state != 0) {
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

    _clear_node_positioning_of_tree(tree_root) {
        tree_root.data.node_positioning = {};
        if (!tree_root._children) return;

        tree_root._children.forEach(child_node => {
            this._clear_node_positioning_of_tree(child_node);
        });
    }

    collapse_node() {
        this.node.children = [];
        this.node.data.user_interactions.bi = "collapsed";
        this._world.viewport.recompute_node_chunk_descendants_and_links(
            this.node.data.chunk
        );
        this._world.viewport.update_layers();
        this.update_collapsed_indicator(this.node);
    }

    expand_node() {
        this.node.children = this.node._children || [];
        delete this.node.data.user_interactions.bi;
        this._world.viewport.recompute_node_chunk_descendants_and_links(
            this.node.data.chunk
        );
        this._world.viewport.update_layers();
        this.update_collapsed_indicator(this.node);
    }

    expand_node_including_children(node) {
        if (node._children) {
            node.children = node._children;
            node.children.forEach(child_node =>
                this.expand_node_including_children(child_node)
            );
        }
        delete node.data.user_interactions.bi;
        this.update_collapsed_indicator(node);
    }

    update_collapsed_indicator(node) {
        if (!node._children) return;

        const collapsed = node.children != node._children;
        const outer_circle = node.data.selection.select("circle");
        outer_circle.classed("collapsed", collapsed);

        const nodes = this._world.viewport.get_all_nodes();
        for (const idx in nodes) {
            nodes[idx].data.transition_info.use_transition = true;
        }
    }

    _fixate_quickinfo() {
        if (this._world.layout_manager.edit_layout) return;

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

        if (this._world.layout_manager.edit_layout) return;

        const div_selection = this._world.nodes_layer
            .get_div_selection()
            .selectAll<HTMLDivElement, NodevisNode>("div.quickinfo")
            .data<NodevisNode>([this.node], d => d.data.id);
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
                    this._external_quickinfo_data.data.cloneNode(true).body
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

    _get_basic_quickinfo(): BasicQuickinfo[] {
        return [];
    }

    _show_table_quickinfo() {
        const table_selection = this.quickinfo_selection()
            .selectAll<HTMLTableSectionElement, string>("body table tbody")
            .data([this.id()], d => d);
        const table = table_selection
            .enter()
            .append("body")
            .append("table")
            .classed("data", true)
            .classed("single", true)
            .append("tbody")
            .merge(table_selection);

        let even = "even";
        const quickinfo = this._get_basic_quickinfo();
        const rows = table.selectAll("tr").data(quickinfo).enter().append("tr");
        rows.each(function () {
            this.setAttribute("class", even.concat("0 data"));
            even = even == "even" ? "odd" : "even";
        });
        rows.append("td")
            .classed("left", true)
            .text(d => d.name);
        rows.append("td")
            .text(d => d.value)
            .each((d, idx, tds) => {
                const td = d3.select(tds[idx]);
                if (d.css_classes) td.classed(d.css_classes.join(" "), true);
            });
        this.update_quickinfo_position();
    }

    _got_quickinfo(json_data) {
        const now = Math.floor(new Date().getTime() / 1000);
        this._external_quickinfo_data = {
            fetched_at_timestamp: now,
            data: json_data,
        };
        this._quickinfo_fetch_in_progress = false;
        if (this._quickinfo_selection) this._show_quickinfo();
    }

    _state_to_text(state) {
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
                        const a = d3.select(nodes[idx]);
                        const details_url = this._get_details_url();
                        if (details_url != "")
                            a.attr("xlink:href", details_url);
                    })
                    .append("circle")
                    .attr("r", this.radius)
                    .classed("state_circle", true)
            );
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
            enforce_transition
        );
        transition.attr(
            "transform",
            "translate(" +
                this.node.data.target_coords.x +
                "," +
                this.node.data.target_coords.y +
                ")"
        );

        this.update_quickinfo_position();
        this._update_text_position();
        this.node.data.transition_info.type =
            this.node.data.current_positioning.type;
    }

    update_quickinfo_position() {
        if (this._quickinfo_selection == null) return;
        const coords = this._world.viewport.translate_to_zoom({
            x: this.node.x,
            y: this.node.y,
        });
        this._quickinfo_selection
            .style("left", coords.x + this.radius + "px")
            .style("top", coords.y + "px");
    }

    add_optional_transition(selection, enforce_transition = false) {
        // TODO: remove
        if (this._world.layout_manager.skip_optional_transitions)
            return selection;

        if (
            (!this.node.data.transition_info.use_transition &&
                !enforce_transition) ||
            this._world.layout_manager.dragging
        )
            return selection;

        return DefaultTransition.add_transition(
            selection.attr("in_transit", 100)
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
        force_options: ForceOptions
    ): number {
        return this._get_node_type_specific_force(force_name, force_options);
    }

    _get_node_type_specific_force(
        force_name: SimulationForce,
        force_options: ForceOptions
    ): number {
        return force_options[force_name];
    }

    _get_explicit_force_option(force_name: string): number | null {
        const explicit_force_options = this.node.data.explicit_force_options;
        if (explicit_force_options == null) return null;

        if (explicit_force_options[force_name]) {
            return explicit_force_options[force_name];
        }
        return null;
    }

    simulation_end_actions(): void {
        return;
    }
}

export function get_custom_node_settings(node: NodevisNode) {
    node.data.custom_node_settings = node.data.custom_node_settings || {
        id: node.data.id,
    };
    return node.data.custom_node_settings;
}

// Stores node visualization classes
class NodeTypeClassRegistry extends AbstractClassRegistry<
    typeof AbstractGUINode
> {}

export const node_type_class_registry = new NodeTypeClassRegistry();
