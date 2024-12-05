/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import type {Selection} from "d3";
import {html, select} from "d3";

import type {ForceOptions, SimulationForce} from "./force_utils";
import {ForceConfig} from "./force_utils";
import type {LayerSelections} from "./layer_utils";
import {DynamicToggleableLayer, layer_class_registry} from "./layer_utils";
import type {StyleOptionSpecRange} from "./layout_utils";
import {AbstractLink, link_type_class_registry} from "./link_utils";
import {TopologyNode} from "./node_types";
import type {AbstractGUINode} from "./node_utils";
import {
    get_core_info,
    get_custom_node_settings,
    node_type_class_registry,
} from "./node_utils";
import type {TranslationKey} from "./texts";
import {get} from "./texts";
import type {
    ContextMenuElement,
    d3SelectionDiv,
    d3SelectionG,
    NodevisNode,
    NodevisWorld,
    OverlaysConfig,
    QuickinfoEntry,
} from "./type_defs";
import {
    RadioGroupOption,
    render_radio_group,
    render_save_delete,
    show_tooltip,
} from "./utils";
import type {Viewport} from "./viewport";

interface TopologyForceOptions extends ForceOptions {
    charge_host: number;
    charge_service: number;
    link_distance_host2host: number;
    link_distance_host2service: number;
    link_distance_service2service: number;
    link_strength_host2host: number;
    link_strength_host2service: number;
    link_strength_service2service: number;
}

function render_hierarchy_flat(
    viewport: Viewport,
    toggle_panel: d3SelectionDiv,
) {
    const options = [
        new RadioGroupOption("flat", get("flat")),
        new RadioGroupOption("full", get("full")),
    ];

    const hierarchy_div = toggle_panel
        .selectAll<HTMLDivElement, null>("div.radio_group.hierarchy_flat")
        .data([null])
        .join(enter =>
            enter
                .insert("div", "table#overlay_configuration")
                .classed("radio_group hierarchy_flat", true),
        );
    render_radio_group(
        hierarchy_div,
        get("hierarchy"),
        "hierarchy_depth",
        options,
        viewport.get_overlays_config().computation_options.hierarchy,
        (new_option: string) => {
            viewport.get_overlays_config().computation_options.hierarchy =
                new_option;
            viewport.get_overlays_config().computation_options.enforce_hierarchy_update =
                true;
            viewport.try_fetch_data();
        },
    );
}

function render_toggle_services(
    viewport: Viewport,
    toggle_panel: d3SelectionDiv,
) {
    const options = [
        new RadioGroupOption("all", get("all")),
        new RadioGroupOption("only_problems", get("only_problems")),
        new RadioGroupOption("none", get("none")),
    ];

    const services_div = toggle_panel
        .selectAll<HTMLDivElement, null>("div.radio_group.services")
        .data([null])
        .join(enter =>
            enter
                .insert("div", "table#overlay_configuration")
                .classed("radio_group services", true),
        );
    render_radio_group(
        services_div,
        get("services"),
        "service_visibility",
        options,
        "all",
        (new_option: string) => {
            viewport.get_overlays_config().computation_options.show_services =
                new_option as "all" | "only_problems" | "none";
            viewport.try_fetch_data();
        },
    );
}

function render_toggle_panel(
    overlays_config: OverlaysConfig,
    layer_toggled_callback: (layer_id: string, enabled: boolean) => void,
    viewport: Viewport,
): void {
    const toggle_panel = viewport
        .get_div_selection()
        .selectAll<HTMLDivElement, null>("div#layout_toggle_panel")
        .data([null])
        .join(enter => enter.append("div").attr("id", "layout_toggle_panel"));
    // Parent/child does not provide service info
    if (
        overlays_config.available_layers.length > 0 &&
        !overlays_config.available_layers.includes("parent_child")
    ) {
        render_toggle_services(viewport, toggle_panel);
    }

    render_hierarchy_flat(viewport, toggle_panel);

    // Only shown on multiple datasources
    if (viewport.get_overlays_config().available_layers.length <= 1) return;
    const table = toggle_panel
        .selectAll<HTMLTableElement, null>("table#overlay_configuration")
        .data([null])
        .join("table")
        .attr("id", "overlay_configuration");

    const data: [string, string, (new_value: boolean) => void, boolean][] = [];
    data.push([
        "merge_nodes",
        get("merge_data"),
        new_value => {
            viewport.get_overlays_config().computation_options.merge_nodes =
                new_value;
            viewport.try_fetch_data();
        },
        viewport.get_overlays_config().computation_options.merge_nodes,
    ]);

    overlays_config.available_layers.forEach(layer_id => {
        // TODO: layer i18n
        data.push([
            layer_id,
            layer_id,
            (new_value: boolean) => layer_toggled_callback(layer_id, new_value),
            overlays_config.overlays[layer_id] &&
                overlays_config.overlays[layer_id].active,
        ]);
    });
    const layer_rows = table
        .selectAll<HTMLTableRowElement, [string, string, () => void]>("tr")
        .data(data, d => d[0])
        .join("tr");

    const option_td = layer_rows
        .selectAll("td.option")
        .data(d => [d])
        .join("td")
        .classed("option", true);

    option_td
        .selectAll<HTMLDivElement, string>(
            "div.nodevis.toggle_switch_container",
        )
        .data(d => [d])
        .join(enter =>
            enter
                .append("div")
                .classed("nodevis toggle_switch_container", true)
                .on("click", (event, d) => {
                    const node = select(event.target);
                    const new_value = !node.classed("on");
                    node.classed("on", new_value);
                    d[2](new_value);
                }),
        )
        .classed("on", d => d[3]);

    layer_rows
        .selectAll("td.text")
        .data(d => [d])
        .enter()
        .append("td")
        .classed("text noselect", true)
        .text(d => d[1])
        .style("pointer-events", "all")
        .on("click", (event, d) => {
            const node = select(event.target.parentNode.firstChild.firstChild);
            const new_value = !node.classed("on");
            node.classed("on", new_value);
            d[2](new_value);
        });
}

export class LayoutTopology {
    _world: NodevisWorld;

    constructor(world: NodevisWorld) {
        this._world = world;
    }

    render_layout(selection: d3SelectionDiv): void {
        this._render_save_delete_layout(selection);
        render_toggle_panel(
            this._world.viewport.get_overlays_config(),
            (layer_id, enabled) => this._toggle_layer(layer_id, enabled),
            this._world.viewport,
        );
    }

    _toggle_layer(layer_id: string, enabled: boolean) {
        const layer_config =
            this._world.viewport.get_overlay_layers_config()[layer_id] || {};
        layer_config.active = enabled;
        this._world.viewport.set_overlay_layer_config(layer_id, layer_config);
    }

    _render_save_delete_layout(
        into_selection: Selection<HTMLDivElement, null, any, unknown>,
    ): void {
        const buttons: [string, string, string, () => void][] = [
            [
                get("save"),
                "button save_delete save",
                "",
                this._world.save_layout,
            ],
            [
                get("delete_layout"),
                "button save_delete delete",
                "",
                this._world.delete_layout,
            ],
        ];
        render_save_delete(into_selection, buttons);
    }
}

export class GenericNetworkLayer extends DynamicToggleableLayer {
    _ident = "network";
    _name = "network";

    constructor(
        world: NodevisWorld,
        selections: LayerSelections,
        ident: string,
        name: string,
    ) {
        super(world, selections);
        this._ident = ident;
        this._name = name;
    }

    override is_dynamic_instance_template(): boolean {
        return true;
    }

    override class_name(): string {
        return "network@";
    }

    override id(): string {
        return this.class_name() + this._ident;
    }

    override name() {
        return this._name;
    }

    override enable_hook() {
        this._world.viewport.try_fetch_data();
    }

    override disable_hook() {
        this._world.viewport.try_fetch_data();
    }
}

layer_class_registry.register(GenericNetworkLayer);

class TopologyCoreEntity extends TopologyNode {
    highlight_connection(traversed_id: Set<string>, start = false) {
        if (traversed_id.has(this.id())) return;
        traversed_id.add(this.id());
        this.selection().classed("highlight", true);
        if (start)
            this._world.viewport
                .get_nodes_layer()
                .get_links_for_node(this.node.data.id)
                .forEach(link_instance => {
                    if (link_instance instanceof NetworkLink)
                        link_instance.highlight_connection(traversed_id);
                });
    }

    hide_connection(traversed_ids: Set<string>, _start = false) {
        if (traversed_ids.has(this.id())) return;
        traversed_ids.add(this.id());
        this.selection().classed("highlight", false);
        this._world.viewport
            .get_nodes_layer()
            .get_links_for_node(this.node.data.id)
            .forEach(link_instance => {
                if (link_instance instanceof NetworkLink)
                    link_instance.hide_connection(traversed_ids);
            });
    }

    override render_object() {
        TopologyNode.prototype.render_object.call(this);
    }

    override render_into(selection: d3SelectionG) {
        super.render_into(selection);
        this.selection()
            .on("mouseover.network", () =>
                this.highlight_connection(new Set<string>(), true),
            )
            .on("mouseout.network", () =>
                this.hide_connection(new Set<string>(), true),
            );
    }
}

class TopologyHost extends TopologyCoreEntity {
    override class_name(): string {
        return "topology_host";
    }

    override update_position() {
        super.update_position();

        this.selection()
            .selectAll("circle.has_warn_services")
            .data(
                this.node.data.type_specific.core.num_services_warn > 0
                    ? [this.node.data.type_specific.core.num_services_warn]
                    : [],
            )
            .join("circle")
            .attr("r", this.radius + 6)
            .classed("has_warn_services", true);

        this.selection()
            .selectAll("circle.has_crit_services")
            .data(
                this.node.data.type_specific.core.num_services_crit > 0
                    ? [this.node.data.type_specific.core.num_services_crit]
                    : [],
            )
            .join("circle")
            .attr("r", this.radius + 8)
            .classed("has_crit_services", true);
    }

    override get_context_menu_elements(): ContextMenuElement[] {
        const elements =
            TopologyCoreEntity.prototype.get_context_menu_elements.call(this);

        const custom_settings = get_custom_node_settings(this.node);
        const current_setting = custom_settings.show_services || "default";
        const options: [string, string][] = [
            ["default", get("global_default")],
            ["all", get("all")],
            ["only_problems", get("only_problems")],
            ["none", get("none")],
        ];

        function changed_option(world: NodevisWorld, new_option: string) {
            if (new_option == "default")
                delete custom_settings["show_services"];
            else custom_settings["show_services"] = new_option;
            world.viewport.get_nodes_layer().hide_context_menu();
            world.update_data();
        }

        const service_choice: ContextMenuElement = {
            text: get("show_services"),
            children: [],
        };

        options.forEach(([ident, text]) => {
            const world = this._world;
            service_choice.children!.push({
                tick: current_setting == ident,
                text: text,
                on: () => changed_option(world, ident),
            });
        });
        elements.push(service_choice);

        return elements;
    }

    override _get_text(node_id: string): string {
        const node = this._world.viewport.get_node_by_id(node_id);
        if (!node) return "";
        return node.data.name;
    }

    override _get_node_type_specific_force(
        force_name: SimulationForce,
        force_options: TopologyForceOptions,
    ): number {
        switch (force_name) {
            case "charge": {
                return force_options.charge_host;
            }
            default:
                return super._get_node_type_specific_force(
                    force_name,
                    force_options,
                );
        }
    }
}

class TopologyService extends TopologyCoreEntity {
    constructor(world: NodevisWorld, node: NodevisNode) {
        super(world, node);
        this.radius = 4;
        this._provides_external_quickinfo_data = true;
    }
    override class_name(): string {
        return "topology_service";
    }

    override highlight_connection(traversed_id: Set<string>, _start = false) {
        super.highlight_connection(traversed_id, true);
    }

    override update_position() {
        super.update_position();
    }
    override _get_text(node_id: string): string {
        const node = this._world.viewport.get_node_by_id(node_id);
        if (!node) return "";
        return node.data.name;
    }

    override _fetch_external_quickinfo() {
        this._quickinfo_fetch_in_progress = true;
        const [hostname, service] = this._get_hostname_and_service();
        const view_url =
            "view.py?view_name=topology_hover_service&display_options=I&host=" +
            encodeURIComponent(hostname) +
            "&service=" +
            encodeURIComponent(service) +
            "&datasource=" +
            encodeURIComponent(this._world.datasource);
        html(view_url, {credentials: "include"}).then(html =>
            this._got_quickinfo(html),
        );
    }

    override _get_node_type_specific_force(
        force_name: SimulationForce,
        force_options: TopologyForceOptions,
    ): number {
        switch (force_name) {
            case "charge": {
                return force_options.charge_service;
            }
            default:
                return super._get_node_type_specific_force(
                    force_name,
                    force_options,
                );
        }
    }
}

function get_emblem_url(node: NodevisNode): string {
    return (
        node.data.type_specific.node_images?.emblem ||
        "themes/facelift/images/icon_alert_unreach.png"
    );
}

class TopologyUnknownHost extends TopologyHost {
    constructor(world: NodevisWorld, node: NodevisNode) {
        super(world, node);
        this.radius = 3;
        this._provides_external_quickinfo_data = false;
    }

    override class_name(): string {
        return "topology_unknown_host";
    }

    override _get_basic_quickinfo(): QuickinfoEntry[] {
        return [
            {
                name: get("unknown_host"),
                value: "",
            },
            {
                name: get("host"),
                value: get_core_info(this.node)!.hostname,
            },
        ];
    }

    override render_object() {
        super.render_object();
        render_emblem(this, 30);
    }
}

class TopologyUnknownService extends TopologyService {
    constructor(world: NodevisWorld, node: NodevisNode) {
        super(world, node);
        this.radius = 3;
        this._provides_external_quickinfo_data = false;
    }

    override class_name(): string {
        return "topology_unknown_service";
    }

    override _get_basic_quickinfo(): QuickinfoEntry[] {
        return [
            {
                name: get("unknown_service"),
                value: "",
            },
            {
                name: get("host"),
                value: this.node.data.type_specific.core.hostname,
            },
            {
                name: get("service"),
                value: this.node.data.type_specific.core.service,
            },
        ];
    }

    override render_object() {
        super.render_object();
        render_emblem(this, 18);
    }
}

class TopologyUnknown extends TopologyNode {
    constructor(world: NodevisWorld, node: NodevisNode) {
        super(world, node);
        this.radius = 3;
    }

    override class_name(): string {
        return "topology_unknown";
    }

    override render_object() {
        super.render_object();
        render_emblem(this, 30);
    }
}

function render_emblem(gui_node: AbstractGUINode, size: number) {
    const selection = gui_node.selection();
    const emblem_url = get_emblem_url(gui_node.node);
    selection
        .selectAll("image.emblem")
        .data([gui_node.id()])
        .enter()
        .insert("svg:image")
        .classed("emblem", true)
        .attr("xlink:href", emblem_url)
        .attr("x", -size / 2)
        .attr("y", -size / 2)
        .attr("width", size)
        .attr("height", size);
}

node_type_class_registry.register(TopologyUnknown);
node_type_class_registry.register(TopologyUnknownHost);
node_type_class_registry.register(TopologyUnknownService);
node_type_class_registry.register(TopologyHost);
node_type_class_registry.register(TopologyService);

class NetworkLink extends AbstractLink {
    highlight_connection(traversed_ids: Set<string>) {
        if (traversed_ids.has(this.id())) return;
        traversed_ids.add(this.id());

        this.selection().each((_d, idx, nodes) => {
            const line = select(nodes[idx]);
            if (line.classed("halo_line")) return;
            line.classed("highlight", true);
        });
        [
            this._link_data.source.data.id,
            this._link_data.target.data.id,
        ].forEach(id => {
            const gui_node = this._world.viewport
                .get_nodes_layer()
                .get_node_by_id(id);
            if (gui_node instanceof TopologyCoreEntity)
                gui_node.highlight_connection(traversed_ids);
        });
    }

    hide_connection(traversed_ids: Set<string>) {
        if (traversed_ids.has(this.id())) return;
        traversed_ids.add(this.id());
        this.selection().classed("highlight", false);
        [
            this._link_data.source.data.id,
            this._link_data.target.data.id,
        ].forEach(id => {
            const gui_node = this._world.viewport
                .get_nodes_layer()
                .get_node_by_id(id);
            if (gui_node instanceof TopologyCoreEntity)
                gui_node.hide_connection(traversed_ids);
        });
    }

    _set_topology_classes() {
        const data: [TranslationKey, boolean][] = this._link_data.config
            .topology_classes as unknown as [TranslationKey, boolean][];
        this.selection().selectAll("title.topology_info").remove();
        data.forEach(entry => {
            this._root_selection!.classed(entry[0], entry[1]);
            if (entry[1]) {
                this.selection()
                    .selectAll("title.topology_info")
                    .data([entry[0]])
                    .join("title")
                    .classed("topology_info", true)
                    .text(d => get(d));
            }
        });
    }

    _set_link_class() {
        const core_source = get_core_info(this._link_data.source);
        const core_target = get_core_info(this._link_data.target);
        if (!core_source || !core_target) return;
        this._root_selection!.classed(
            "local_link",
            core_source.hostname == core_target.hostname,
        );
        this._root_selection!.classed(
            "foreign_link",
            core_source.hostname != core_target.hostname,
        );
    }

    _adjust_line_style() {
        const line_config = this._link_data.config.line_config;
        if (!line_config) return;
        if (line_config.thickness) {
            this.selection().style("stroke-width", line_config.thickness);
        }
        if (line_config.color) {
            this.selection().style("stroke", line_config.color);
        }
        if (line_config.css_styles) {
            for (const [key, value] of Object.entries(line_config.css_styles)) {
                this.selection().style(key, value);
            }
        }
    }

    override render_into(selection: d3SelectionG) {
        super.render_into(selection, true);
        this.selection().each((_d, idx, nodes) => {
            const line = select(nodes[idx]);
            if (!line.classed("halo_line")) return;
            line.style("stroke-dasharray", "none");
            line.on("mouseover", event => {
                this.highlight_connection(new Set<string>());
                show_tooltip(
                    event,
                    this._link_data.config.tooltip || {},
                    this._world.viewport,
                );
            })
                .on("mouseout", event => {
                    this.hide_connection(new Set<string>());
                    show_tooltip(event, {}, this._world.viewport);
                })
                .on("mousemove", event => {
                    show_tooltip(
                        event,
                        this._link_data.config.tooltip || {},
                        this._world.viewport,
                    );
                });
        });
        this._set_topology_classes();
        this._set_link_class();
        this._adjust_line_style();
    }
}

export class HostServiceLink extends NetworkLink {
    override class_name(): string {
        return "host2service";
    }

    override _get_link_type_specific_force(
        force_name: SimulationForce,
        force_options: TopologyForceOptions,
    ): number {
        switch (force_name) {
            case "link_distance":
                return force_options.link_distance_host2service;
            case "link_strength":
                return force_options.link_strength_host2service;
            default:
                return super._get_link_type_specific_force(
                    force_name,
                    force_options,
                );
        }
    }
}

export class HostHostLink extends NetworkLink {
    override class_name() {
        return "host2host";
    }

    override _get_link_type_specific_force(
        force_name: SimulationForce,
        force_options: TopologyForceOptions,
    ): number {
        switch (force_name) {
            case "link_distance":
                return force_options.link_distance_host2host;
            case "link_strength":
                return force_options.link_strength_host2host;
            default:
                return super._get_link_type_specific_force(
                    force_name,
                    force_options,
                );
        }
    }
}

export class ServiceServiceLink extends NetworkLink {
    override class_name() {
        return "service2service";
    }

    override _get_link_type_specific_force(
        force_name: SimulationForce,
        force_options: TopologyForceOptions,
    ): number {
        switch (force_name) {
            case "link_distance":
                return force_options.link_distance_service2service;
            case "link_strength":
                return force_options.link_strength_service2service;
            default:
                return super._get_link_type_specific_force(
                    force_name,
                    force_options,
                );
        }
    }
}

link_type_class_registry.register(HostServiceLink);
link_type_class_registry.register(HostHostLink);
link_type_class_registry.register(ServiceServiceLink);

export class TopologyForceConfig extends ForceConfig {
    override description = "Topology Force configuration";

    override get_style_options(): StyleOptionSpecRange[] {
        const options: StyleOptionSpecRange[] = [
            {
                id: "center",
                values: {default: 0.05, min: -0.08, max: 1, step: 0.01},
                option_type: "range",
                text: "Center force strength",
            },
            {
                id: "charge",
                values: {default: -300, min: -1000, max: 50, step: 1},
                option_type: "range",
                text: "General repulsion",
                hidden: true,
            },
            {
                id: "link_distance",
                values: {default: 30, min: -10, max: 500, step: 1},
                option_type: "range",
                text: "Link distance",
                hidden: true,
            },
            {
                id: "link_strength",
                values: {default: 0.3, min: 0, max: 4, step: 0.01},
                option_type: "range",
                text: "Link strenght",
                hidden: true,
            },
            {
                id: "collide",
                values: {default: 15, min: 0, max: 150, step: 1},
                option_type: "range",
                text: "Collision box",
            },
            {
                id: "charge_host",
                values: {default: -300, min: -1000, max: 50, step: 1},
                option_type: "range",
                text: "Repulsion host",
            },
            {
                id: "charge_service",
                values: {default: -300, min: -1000, max: 50, step: 1},
                option_type: "range",
                text: "Repulsion service",
            },
        ];

        const settings: [string, string, number, number][] = [
            ["service2service", "service<->service", 30, 0.3],
            ["host2service", "host<->service", 30, 0.3],
            ["host2host", "host<->host", 30, 0.3],
        ];
        settings.forEach(entry => {
            options.push({
                id: "link_distance_" + entry[0],
                values: {default: entry[2], min: -10, max: 500, step: 1},
                option_type: "range",
                text: "Link " + entry[1],
            });
        });
        settings.forEach(entry => {
            options.push({
                id: "link_strength_" + entry[0],
                values: {default: entry[3], min: 0, max: 4, step: 0.01},
                option_type: "range",
                text: "Link strength " + entry[1],
            });
        });
        return options;
    }
}
