import {
    NodevisLink,
    NodevisNode,
    NodevisWorld,
    SimulationForce,
} from "nodevis/type_defs";
import * as d3 from "d3";
import {Simulation} from "d3";
import {LayoutStyleForce} from "nodevis/layout_styles";
import {compute_node_positions_from_list_of_nodes} from "nodevis/layout";

export class ForceSimulation {
    _world: NodevisWorld;
    _simulation: Simulation<NodevisNode, NodevisLink>;
    _last_gui_update_duration = 0;
    _all_nodes: NodevisNode[] = [];
    _all_links: NodevisLink[] = [];

    constructor(world: NodevisWorld) {
        this._world = world;
        this._simulation = d3.forceSimulation<NodevisNode>();
        this._simulation.alpha(0);
        this._simulation.alphaMin(0.1);
        this._simulation.on("tick", () => this.tick_called());
        this._simulation.on("end", () => this._simulation_end());
        this.setup_forces();
    }

    tick_called(): void {
        if (!this._world.viewport) return;

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
        if (!this._world.viewport) return;
        this._update_gui();
    }

    _update_gui(): number {
        const update_start = window.performance.now();
        this._enforce_free_float_styles_retranslation();
        compute_node_positions_from_list_of_nodes(this._get_force_nodes());
        this._world.viewport.update_gui_of_layers();
        return window.performance.now() - update_start;
    }

    _get_force_nodes(): NodevisNode[] {
        const force_nodes: NodevisNode[] = [];
        this._world.viewport.get_hierarchy_list().forEach(chunk => {
            chunk.nodes.forEach(node => {
                if (node.data.current_positioning.free) force_nodes.push(node);
            });
        });
        return force_nodes;
    }

    _enforce_free_float_styles_retranslation(): void {
        for (const idx in this._world.layout_manager._active_styles) {
            const style = this._world.layout_manager._active_styles[idx];
            if (
                !style.has_fixed_position() &&
                style.type() != LayoutStyleForce.class_name
            ) {
                style.force_style_translation();
                style.translate_coords();
                compute_node_positions_from_list_of_nodes(
                    style.filtered_descendants
                );
                style.filtered_descendants.forEach(
                    node => (node.use_transition = false)
                );
            }
        }
    }

    setup_forces(): void {
        this._update_charge_force();
        this._update_collision_force();
        this._update_center_force();
        this._update_link_force();
    }

    _compute_force(node: NodevisNode, force_name: SimulationForce): number {
        const gui_node = this._world.nodes_layer.get_node_by_id(node.data.id);
        if (gui_node == null) return 0;
        return gui_node.get_force(force_name);
    }

    _update_charge_force(): void {
        const charge_force = d3
            .forceManyBody<NodevisNode>()
            .strength(node => {
                return this._compute_force(node, "charge_force");
            })
            .distanceMax(800);
        this._simulation.force("charge_force", charge_force);
    }

    _update_collision_force(): void {
        const collide_force = d3.forceCollide<NodevisNode>(node => {
            return this._compute_force(node, "collide");
        });
        this._simulation.force("collide", collide_force);
    }

    _update_center_force(): void {
        const forceX = d3
            .forceX<NodevisNode>(d => {
                // X Position is currently fixed
                return d.data.chunk.coords.x + d.data.chunk.coords.width / 2;
            })
            .strength(d => {
                return this._compute_force(d, "center");
            });

        const forceY = d3
            .forceY<NodevisNode>(d => {
                // Y Position is currently fixed
                return d.data.chunk.coords.y + d.data.chunk.coords.height / 2;
            })
            .strength(d => {
                return this._compute_force(d, "center");
            });
        this._simulation.force("x", forceX);
        this._simulation.force("y", forceY);
    }

    _update_link_force(): void {
        const link_force = d3
            .forceLink<NodevisNode, NodevisLink>(this._all_links)
            .id(function (d) {
                return d.data.id;
            })
            .distance(d => {
                return this._compute_force(d.source, "link_distance");
            })
            .strength(d => {
                return this._compute_force(d.source, "link_strength");
            });
        this._simulation.force("links", link_force);
    }

    update_nodes_and_links(
        all_nodes: NodevisNode[],
        all_links: NodevisLink[]
    ): void {
        this._all_nodes = all_nodes;
        this._all_links = all_links;
        this._simulation.nodes(this._all_nodes);
        this.setup_forces();
    }

    restart_with_alpha(alpha: number): void {
        if (this._simulation.alpha() < 0.12) this._simulation.restart();
        this._simulation.alpha(alpha);
    }
}
