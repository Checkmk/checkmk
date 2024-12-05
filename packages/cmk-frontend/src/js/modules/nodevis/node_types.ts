/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import {html} from "d3";

import {AbstractGUINode, node_type_class_registry} from "./node_utils";
import {get} from "./texts";
import type {
    ContextMenuElement,
    d3SelectionG,
    NodevisNode,
    NodevisWorld,
    QuickinfoEntry,
} from "./type_defs";
import type {TypeWithName} from "./utils";
import {bound_monitoring_host, SearchFilters, show_tooltip} from "./utils";

export class TopologyNode extends AbstractGUINode {
    constructor(world: NodevisWorld, node: NodevisNode) {
        super(world, node);
        this.radius = 9;
        this._provides_external_quickinfo_data = true;
    }

    override class_name(): string {
        return "topology";
    }

    override render_object() {
        AbstractGUINode.prototype.render_object.call(this);

        const growth_settings = this.node.data.growth_settings;

        if (
            growth_settings.indicator_growth_possible ||
            growth_settings.growth_forbidden ||
            growth_settings.growth_continue
        )
            this.selection().on("dblclick", () => {
                const nodevis_node = this._world.viewport.get_node_by_id(
                    this.node.data.id,
                );
                if (!nodevis_node) return;
                _toggle_growth_continue(nodevis_node);
                this._world.update_data();
            });

        if (this.node.data.type_specific?.topology_classes) {
            const data: [string, boolean][] =
                this.node.data.type_specific.topology_classes;
            data.forEach(entry => {
                this.selection().classed(entry[0], entry[1]);
            });
        }

        this.update_growth_indicators();

        this.selection()
            .on("mouseover.tooltip", event => {
                show_tooltip(
                    event,
                    this.node.data.type_specific.tooltip || {},
                    this._world.viewport,
                );
            })
            .on("mouseout.tooltip", event => {
                show_tooltip(event, {}, this._world.viewport);
            })
            .on("mousemove.tooltip", event => {
                show_tooltip(
                    event,
                    this.node.data.type_specific.tooltip || {},
                    this._world.viewport,
                );
            });
    }

    override update_node_data(node: NodevisNode, selection: d3SelectionG) {
        AbstractGUINode.prototype.update_node_data.call(this, node, selection);
        this.update_growth_indicators();
    }

    update_growth_indicators() {
        const growth_settings = this.node.data.growth_settings;
        // Growth root
        this.selection()
            .selectAll("circle.indicator_growth_root")
            .data(
                growth_settings.indicator_growth_root
                    ? [this.node.data.id]
                    : [],
            )
            .join(enter =>
                enter
                    .append("circle")
                    .classed("indicator_growth_root", true)
                    .attr("r", this.radius + 4)
                    .attr("fill", "none"),
            );

        // Growth possible
        this.selection()
            .selectAll("image.indicator_growth_possible")
            .data(
                growth_settings.indicator_growth_possible
                    ? [this.node.data.id]
                    : [],
            )
            .join(enter =>
                enter
                    .append("svg:image")
                    .classed("indicator_growth_possible", true)
                    .attr(
                        "xlink:href",
                        "themes/facelift/images/icon_hierarchy.svg",
                    )
                    .attr("width", 16)
                    .attr("height", 16)
                    .attr("x", -8)
                    .attr("y", 0)
                    .append("title")
                    .text(get("can_grow_here")),
            );

        // Growth forbidden
        this.selection()
            .selectAll("image.growth_forbidden")
            .data(growth_settings.growth_forbidden ? [this.node.data.id] : [])
            .join(enter =>
                enter
                    .append("svg:image")
                    .classed("growth_forbidden", true)
                    .attr(
                        "xlink:href",
                        "themes/facelift/images/icon_topic_general.png",
                    )
                    .attr("width", 16)
                    .attr("height", 16)
                    .attr("x", -28)
                    .attr("y", 0)
                    .append("title")
                    .text(get("growth_stops_here")),
            );

        // Growth continue
        this.selection()
            .selectAll("image.growth_continue")
            .data(growth_settings.growth_continue ? [this.node.data.id] : [])
            .join(enter =>
                enter
                    .append("svg:image")
                    .classed("growth_continue", true)
                    .attr(
                        "xlink:href",
                        "themes/facelift/images/icon_topic_agents.png",
                    )
                    .attr("width", 16)
                    .attr("height", 16)
                    .attr("x", -28)
                    .attr("y", 0)
                    .append("title")
                    .text(get("growth_continues_here")),
            );
    }

    override _fetch_external_quickinfo() {
        if (!this.node.data.type_specific.core) return;
        this._quickinfo_fetch_in_progress = true;
        const view_url =
            "view.py?view_name=topology_hover_host&display_options=I&host=" +
            encodeURIComponent(this.node.data.type_specific.core.hostname);
        html(view_url, {credentials: "include"}).then(html =>
            this._got_quickinfo(html),
        );
    }

    override get_context_menu_elements(): ContextMenuElement[] {
        let elements =
            AbstractGUINode.prototype.get_context_menu_elements.call(this);
        elements = elements.concat(this._get_topology_menu_elements());
        return elements;
    }

    _get_topology_menu_elements() {
        // Toggle root node
        const elements: ContextMenuElement[] = [];
        const node_id = this.node.data.id;

        // Use this node as exclusive root node
        const bound_host = bound_monitoring_host(this.node);
        if (bound_host) {
            // This node can be used within the Hostname filter
            elements.push({
                text: get("set_root_node"),
                on: () => {
                    const nodevis_node =
                        this._world.viewport.get_node_by_id(node_id);
                    if (!nodevis_node) return;
                    _clear_root_nodes(this._world);
                    new SearchFilters().set_host_regex_filter(bound_host + "$");
                    // _set_root_node(nodevis_node, this._world);
                    this._world.update_data();
                },
            });
        }

        const growth_settings = this.node.data.growth_settings;
        elements.push({
            text: growth_settings.growth_root
                ? get("remove_root_node")
                : get("add_root_node"),
            on: () => {
                const nodevis_node =
                    this._world.viewport.get_node_by_id(node_id);
                if (!nodevis_node) return;
                _toggle_root_node(nodevis_node);
                this._world.update_data();
            },
        });

        // Forbid further growth
        elements.push({
            text: growth_settings.growth_forbidden
                ? get("allow_hops")
                : get("forbid_hops"),
            on: () => {
                const nodevis_node =
                    this._world.viewport.get_node_by_id(node_id);
                if (!nodevis_node) return;
                _toggle_stop_growth(nodevis_node);
                this._world.update_data();
            },
        });

        // Continue here
        if (growth_settings.indicator_growth_possible)
            elements.push({
                text: growth_settings.growth_continue
                    ? get("stop_continue_hop")
                    : get("continue_hop"),
                on: () => {
                    const nodevis_node =
                        this._world.viewport.get_node_by_id(node_id);
                    if (!nodevis_node) return;
                    _toggle_growth_continue(nodevis_node);
                    this._world.update_data();
                },
            });

        return elements;
    }
}

export class TopologyMeshRoot extends TopologyNode {
    constructor(world: NodevisWorld, node: NodevisNode) {
        super(world, node);
        this._has_quickinfo = false;
    }

    override class_name(): string {
        return "mesh_root";
    }

    override render_text(): void {
        return;
    }

    override render_object() {
        return;
    }
}

function _toggle_root_node(nodevis_node: NodevisNode): boolean {
    nodevis_node.data.growth_settings.growth_root =
        !nodevis_node.data.growth_settings.growth_root;
    return nodevis_node.data.growth_settings.growth_root;
}

function _clear_root_nodes(world: NodevisWorld) {
    world.viewport.get_all_nodes().forEach(node => {
        node.data.growth_settings.growth_root = false;
    });
}

function _set_root_node(nodevis_node: NodevisNode, world: NodevisWorld): void {
    _clear_root_nodes(world);
    nodevis_node.data.growth_settings.growth_root = true;
}

function _toggle_growth_continue(nodevis_node: NodevisNode): boolean {
    const growth_settings = nodevis_node.data.growth_settings;
    growth_settings.growth_continue = !growth_settings.growth_continue;
    if (growth_settings.growth_continue)
        growth_settings.growth_forbidden = false;
    return growth_settings.growth_continue;
}

function _toggle_stop_growth(nodevis_node: NodevisNode): boolean {
    const growth_settings = nodevis_node.data.growth_settings;
    growth_settings.growth_forbidden = !growth_settings.growth_forbidden;
    if (growth_settings.growth_forbidden)
        growth_settings.growth_continue = false;
    return growth_settings.growth_forbidden;
}

export class TopologyCentralNode extends TopologyNode {
    constructor(world: NodevisWorld, node: NodevisNode) {
        super(world, node);
        this.radius = 30;
        this._has_quickinfo = false;
    }

    override class_name(): string {
        return "topology_center";
    }

    override render_text(): void {
        return;
    }

    override render_object() {
        this.selection()
            .classed("topology_center", true)
            .selectAll("image")
            .data([this.id()])
            .enter()
            .append("svg:image")
            .attr("xlink:href", "themes/facelift/images/logo_cmk_small.png")
            .attr("x", -25)
            .attr("y", -25)
            .attr("width", 50)
            .attr("height", 50);
    }
}

export class TopologySiteNode extends TopologyNode {
    constructor(world: NodevisWorld, node: NodevisNode) {
        super(world, node);
        this.radius = 16;
        this._has_quickinfo = false;
    }

    override class_name(): string {
        return "topology_site";
    }

    override render_object() {
        this.selection()
            .selectAll("circle")
            .data([this.id()])
            .enter()
            .append("circle")
            .attr("r", this.radius)
            .classed("topology_remote", true);

        this.selection()
            .selectAll("image")
            .data([this.id()])
            .enter()
            .append("svg:image")
            .attr("xlink:href", "themes/facelift/images/icon_sites.svg")
            .attr("x", -15)
            .attr("y", -15)
            .attr("width", 30)
            .attr("height", 30);
    }
}

export class BILeafNode extends AbstractGUINode implements TypeWithName {
    constructor(world: NodevisWorld, node: NodevisNode) {
        super(world, node);
        this.radius = 9;
        this._provides_external_quickinfo_data = true;
    }

    override class_name(): string {
        return "bi_leaf";
    }

    override _get_basic_quickinfo(): QuickinfoEntry[] {
        const quickinfo: QuickinfoEntry[] = [];

        const core_info = this.node.data.type_specific.core;
        quickinfo.push({
            name: "Host name",
            value: core_info.hostname,
        });
        if (this.node.data.service)
            quickinfo.push({
                name: "Service description",
                value: core_info.service,
            });
        return quickinfo;
    }

    override _fetch_external_quickinfo(): void {
        this._quickinfo_fetch_in_progress = true;
        let view_url;
        const core_info = this.node.data.type_specific.core;
        if (!core_info) return;

        if (core_info.service)
            // TODO: add site to url
            view_url =
                "view.py?view_name=bi_map_hover_service&display_options=I&host=" +
                encodeURIComponent(core_info.hostname) +
                "&service=" +
                encodeURIComponent(core_info.service);
        else
            view_url =
                "view.py?view_name=bi_map_hover_host&display_options=I&host=" +
                encodeURIComponent(core_info.hostname);

        html(view_url, {credentials: "include"}).then(html =>
            this._got_quickinfo(html),
        );
    }

    override _get_details_url(): string {
        if (this.node.data.service && this.node.data.service != "") {
            return (
                "view.py?view_name=service" +
                "&host=" +
                encodeURIComponent(this.node.data.type_specific.core.hostname) +
                "&service=" +
                encodeURIComponent(this.node.data.type_specific.core.service)
            );
        } else {
            return (
                "view.py?view_name=host&host=" +
                encodeURIComponent(this.node.data.type_specific.core.hostname)
            );
        }
    }
}

export class BIAggregatorNode extends AbstractGUINode {
    constructor(world: NodevisWorld, node: NodevisNode) {
        super(world, node);
        this.radius = 12;
        if (!this.node.parent)
            // the root node gets a bigger radius
            this.radius = 16;
    }

    override class_name(): string {
        return "bi_aggregator";
    }

    override _get_basic_quickinfo(): QuickinfoEntry[] {
        const quickinfo: QuickinfoEntry[] = [];
        quickinfo.push({name: "Rule Title", value: this.node.data.name});
        quickinfo.push({
            name: "State",
            value: this._state_to_text(this.node.data.state),
        });
        quickinfo.push({name: "Pack ID", value: this.node.data.rule_id.pack});
        quickinfo.push({name: "Rule ID", value: this.node.data.rule_id.rule});
        quickinfo.push({
            name: "Aggregation Function",
            value: this.node.data.rule_id.aggregation_function_description,
        });
        return quickinfo;
    }

    override get_context_menu_elements(): ContextMenuElement[] {
        const elements: ContextMenuElement[] = [];

        elements.push({
            text: "Edit rule",
            href:
                "wato.py?mode=bi_edit_rule&id=" +
                this.node.data.rule_id.rule +
                "&pack=" +
                this.node.data.rule_id.pack,
            img: "themes/facelift/images/icon_edit.svg",
        });

        if (this.node.children != this.node._children)
            elements.push({
                text: "Below this node, expand all nodes",
                on: event => {
                    event!.stopPropagation();
                    this.expand_node_including_children(this.node);
                    this._world.viewport.recompute_node_and_links();
                },
                href: "",
                img: "themes/facelift/images/icon_expand.png",
            });
        else
            elements.push({
                text: "Collapse this node",
                on: event => {
                    event!.stopPropagation();
                    this.collapse_node();
                },
                href: "",
                img: "themes/facelift/images/icon_collapse.png",
            });

        elements.push({
            text: "Expand all nodes",
            on: event => {
                event!.stopPropagation();
                this.expand_node_including_children(
                    this._world.viewport.get_all_nodes()[0],
                );
                this._world.viewport.recompute_node_and_links();
            },
            href: "",
            img: "themes/facelift/images/icon_expand.png",
        });

        elements.push({
            text: "Below this node, show only problems",
            on: event => {
                event!.stopPropagation();
                this._filter_root_cause(this.node);
                this._world.viewport.recompute_node_and_links();
            },
            img: "themes/facelift/images/icon_error.png",
        });
        return elements;
    }
}

node_type_class_registry.register(TopologyNode);
node_type_class_registry.register(TopologyMeshRoot);
node_type_class_registry.register(TopologySiteNode);
node_type_class_registry.register(TopologyCentralNode);
node_type_class_registry.register(BILeafNode);
node_type_class_registry.register(BIAggregatorNode);
