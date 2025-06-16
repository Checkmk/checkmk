/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import type {Simulation} from "d3";
import {
    forceCollide,
    forceLink,
    forceManyBody,
    forceSimulation,
    forceX as d3_forceX,
    forceY as d3_forceY,
} from "d3";

import type {ForceConfig, ForceOptions, SimulationForce} from "./force_utils";
import type {StyleOptionValues} from "./layout_utils";
import {compute_node_positions_from_list_of_nodes} from "./layout_utils";
import {compute_link_id} from "./link_utils";
import type {NodevisLink, NodevisNode} from "./type_defs";
import type {Viewport} from "./viewport";

export class ForceSimulation {
    _simulation: Simulation<NodevisNode, NodevisLink>;
    _last_gui_update_duration = 0;
    _all_nodes: NodevisNode[] = [];
    _all_links: NodevisLink[] = [];
    _force_config: ForceConfig;
    _viewport: Viewport;

    constructor(viewport: Viewport, force_config_class: typeof ForceConfig) {
        this._viewport = viewport;
        this._simulation = forceSimulation<NodevisNode>();
        this._simulation.stop();
        this._simulation.alpha(0);
        this._simulation.alphaMin(0.1);
        this._simulation.on("tick", () => this.tick_called());
        this._simulation.on("end", () => this._simulation_end());
        this._force_config = new force_config_class(this);
    }

    get_force_config(): ForceConfig {
        return this._force_config;
    }

    set_force_options(force_options: ForceOptions): void {
        this._force_config.options = force_options;
    }

    get_force_options(): ForceOptions {
        return this._force_config.options;
    }

    show_force_config() {
        this._viewport.get_layout_manager().show_configuration(
            "force",
            this._force_config.get_style_options(),
            this._force_config.options,
            (options: StyleOptionValues) =>
                this._force_config.changed_options(options),
            () => {
                this._force_config.changed_options(
                    this._force_config.get_default_options(),
                );
                this.show_force_config();
            },
        );
    }

    set_force_config_class(force_config_class: typeof ForceConfig) {
        this._force_config = new force_config_class(this);
    }

    tick_called(): void {
        // GUI updates with hundreds of nodes might cause rendering stress
        // The laggy_rendering_limit (ms) throttles the visual update to a reasonable amount
        // When the simulation is finished, a final visual update is started anyway.
        const laggy_rendering_limit = 10;
        if (this._last_gui_update_duration > laggy_rendering_limit) {
            this._last_gui_update_duration -= laggy_rendering_limit;
            return;
        }
        this._last_gui_update_duration = this._update_gui();
    }

    _simulation_end(): void {
        this._update_gui();
        this._viewport.get_layout_manager().simulation_end_actions();
    }

    _update_gui(): number {
        const update_start = window.performance.now();
        this._enforce_free_float_styles_retranslation();
        const force_nodes = this._get_force_nodes();
        if (force_nodes.length == 0) {
            this._simulation.alpha(0);
            return window.performance.now() - update_start;
        }
        compute_node_positions_from_list_of_nodes(this._get_force_nodes());
        this._viewport.update_gui_of_layers();
        return window.performance.now() - update_start;
    }

    _get_force_nodes(): NodevisNode[] {
        const force_nodes: NodevisNode[] = [];
        this._viewport.get_all_nodes().forEach(node => {
            if (node.data.current_positioning.free) force_nodes.push(node);
        });
        return force_nodes;
    }

    _enforce_free_float_styles_retranslation(): void {
        const layout_manager = this._viewport.get_layout_manager();
        for (const idx in layout_manager._active_styles) {
            const style = layout_manager._active_styles[idx];
            if (!style.has_fixed_position() && style.type() != "force") {
                style.force_style_translation();
                style.translate_coords();
                compute_node_positions_from_list_of_nodes(
                    style.filtered_descendants,
                );
                style.filtered_descendants.forEach(
                    node => (node.use_transition = false),
                );
            }
        }
    }

    restart_with_alpha(alpha: number): void {
        if (this._simulation.alpha() < 0.12) this._simulation.restart();
        this._simulation.alpha(alpha);
    }

    update_nodes_and_links(
        all_nodes: NodevisNode[],
        all_links: NodevisLink[],
    ): void {
        this._all_nodes = all_nodes;
        this._all_links = all_links;
        this._simulation.nodes(this._all_nodes);
        this.setup_forces();
    }

    setup_forces(): void {
        this._update_charge_force();
        this._update_collision_force();
        this._update_center_force();
        this._update_link_force();
    }

    _compute_force(node: NodevisNode, force_name: SimulationForce): number {
        const gui_node = this._viewport
            .get_nodes_layer()
            .get_node_by_id(node.data.id);
        if (gui_node == null) return 0;
        return gui_node.get_force(force_name, this._force_config.options);
    }

    _compute_link_force(
        link: NodevisLink,
        force_name: SimulationForce,
    ): number {
        const link_instance =
            this._viewport.get_nodes_layer().link_instances[
                compute_link_id(link)
            ];
        if (link_instance == null) return 0;
        return link_instance.get_force(force_name, this._force_config.options);
    }

    _update_charge_force(): void {
        const charge_force = forceManyBody<NodevisNode>()
            .strength(node => {
                return this._compute_force(node, "charge");
            })
            .distanceMax(800);
        this._simulation.force("charge_force", charge_force);
    }

    _update_collision_force(): void {
        const collide_force = forceCollide<NodevisNode>(node => {
            return this._compute_force(node, "collide");
        });
        this._simulation.force("collide", collide_force);
    }

    _update_center_force(): void {
        const size = this._viewport.get_size();
        const half_width = size.width / 2;
        const half_height = size.height / 2;
        const forceX = d3_forceX<NodevisNode>(_d => {
            // X Position is currently fixed
            return half_width;
        }).strength(d => {
            return this._compute_force(d, "center");
        });

        const forceY = d3_forceY<NodevisNode>(_d => {
            return half_height;
        }).strength(d => {
            return this._compute_force(d, "center");
        });
        this._simulation.force("x", forceX);
        this._simulation.force("y", forceY);
    }

    _update_link_force(): void {
        const link_force = forceLink<NodevisNode, NodevisLink>(this._all_links)
            .id(function (d) {
                return d.data.id;
            })
            .distance(d => {
                return this._compute_link_force(d, "link_distance");
            })
            .strength(d => {
                return this._compute_link_force(d, "link_strength");
            });
        this._simulation.force("links", link_force);
    }
}
