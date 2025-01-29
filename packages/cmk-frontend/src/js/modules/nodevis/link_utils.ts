/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import type {BaseType, Transition} from "d3";

import type {ForceOptions, SimulationForce} from "./force_utils";
import type {LineConfig} from "./layout_utils";
import type {
    d3SelectionG,
    NodevisLink,
    NodevisNode,
    NodevisWorld,
} from "./type_defs";
import type {TypeWithName} from "./utils";
import {AbstractClassRegistry, DefaultTransition} from "./utils";

export function compute_link_id(link_data: NodevisLink): string {
    return link_data.source.data.id + "#@#" + link_data.target.data.id;
}

export class AbstractLink implements TypeWithName {
    _world: NodevisWorld;
    _link_data: NodevisLink;
    _root_selection: d3SelectionG | null;
    _selection: d3SelectionG | null;
    _line_config: LineConfig;

    constructor(world: NodevisWorld, link_data: NodevisLink) {
        this._world = world;
        this._link_data = link_data;
        this._root_selection = null;
        this._selection = null;
        this._line_config = this._world.viewport
            .get_layout_manager()
            .get_layout().line_config;
    }

    class_name() {
        return "abstract";
    }

    selection(): d3SelectionG {
        if (this._selection == null)
            throw Error("Missing selection for node " + this.id());
        return this._selection;
    }

    id(): string {
        return compute_link_id(this._link_data);
    }

    render_into(selection: d3SelectionG, add_hidden_halo = false): void {
        this._root_selection = selection;

        const lines: [string, number, number, boolean][] = [];
        lines.push([this.id(), 1, 1, false]);
        if (add_hidden_halo)
            lines.push(["hidden_halo_" + this.id(), 15, 0, true]);

        // Straight line style
        const line_selection = selection
            .selectAll<SVGLineElement, [string, number, number, boolean]>(
                "line",
            )
            .data(this._line_config.style == "straight" ? lines : [], d => d[0])
            .join("line")
            .classed("halo_line", d => d[3])
            .attr("opacity", d => d[2])
            .attr("stroke-width", d => d[1]);

        // Elbow and round style
        const path_selection = selection
            .selectAll<SVGPathElement, [string, number, number, boolean]>(
                "path",
            )
            .data(this._line_config.style != "straight" ? lines : [], d => d[0])
            .join("path")
            .attr("fill", "none")
            .classed("halo_line", d => d[3])
            .attr("opacity", d => d[2])
            .attr("stroke-width", d => d[1]);

        // @ts-ignore
        this._selection =
            this._line_config.style == "straight"
                ? line_selection
                : path_selection;
    }

    update_position(_enforce_transition = false) {
        const source = this._link_data.source;
        const target = this._link_data.target;
        const force_type = "force";

        const is_force =
            source.data.current_positioning.type == force_type ||
            target.data.current_positioning.type == force_type;
        if (
            source.data.transition_info.use_transition ||
            target.data.transition_info.use_transition ||
            is_force
        ) {
            this.selection().interrupt();
        }

        if (parseInt(this.selection().attr("in_transit")) > 0 && !is_force) {
            return;
        }

        if (source.data.current_positioning.hide_node_link) {
            this.selection().style("stroke-opacity", 0);
            return;
        }
        const x1 = source.data.target_coords.x;
        const y1 = source.data.target_coords.y;
        const x2 = target.data.target_coords.x;
        const y2 = target.data.target_coords.y;

        this._add_fancy_line_transitition(source, target);

        const tmp_selection = this.add_optional_transition(this.selection());
        switch (this._line_config.style) {
            case "straight": {
                (
                    tmp_selection.attr("x1", x1) as Transition<
                        SVGGElement,
                        unknown,
                        BaseType,
                        unknown
                    >
                )
                    .attr("y1", y1)
                    .attr("x2", x2)
                    .attr("y2", y2);
                break;
            }
            case "round": {
                tmp_selection.attr("d", () =>
                    this.diagonal_line(x1, y1, x2, y2),
                );
                break;
            }
            case "elbow": {
                tmp_selection.attr("d", () => this.elbow(x1, y1, x2, y2));
                break;
            }
        }
    }

    _add_fancy_line_transitition(
        source: NodevisNode,
        target: NodevisNode,
    ): void {
        const source_selection = this._world.viewport
            .get_nodes_layer()
            .get_node_by_id(source.data.id);
        const target_selection = this._world.viewport
            .get_nodes_layer()
            .get_node_by_id(target.data.id);
        if (!source_selection || !target_selection) return;

        const source_node = source_selection.selection().node();
        const target_node = target_selection.selection().node();
        if (!source_node || !target_node) return;

        const source_baseVal = source_node.transform.baseVal;
        const target_baseVal = target_node.transform.baseVal;
        if (source_baseVal.length == 0 || target_baseVal.length == 0) return;

        const transform_source = source_baseVal[0].matrix;
        const transform_target = target_baseVal[0].matrix;
        this.selection().attr("d", () =>
            this.diagonal_line(
                transform_source.e,
                transform_source.f,
                transform_target.e,
                transform_target.f,
            ),
        );
    }

    elbow(
        source_x: number,
        source_y: number,
        target_x: number,
        target_y: number,
    ) {
        return (
            "M" + source_x + "," + source_y + "V" + target_y + "H" + target_x
        );
    }

    // Creates a curved (diagonal) path from parent to the child nodes
    diagonal_line(
        source_x: number,
        source_y: number,
        target_x: number,
        target_y: number,
    ) {
        const s = {
            y: source_x,
            x: source_y,
        };
        const d = {
            y: target_x,
            x: target_y,
        };

        return `M ${s.y} ${s.x}
                C ${(s.y + d.y) / 2} ${s.x},
                  ${(s.y + d.y) / 2} ${d.x},
                  ${d.y} ${d.x}`;
    }

    add_optional_transition(selection: d3SelectionG) {
        const source = this._link_data.source;
        const target = this._link_data.target;
        if (
            (!source.data.transition_info.use_transition &&
                !target.data.transition_info.use_transition) ||
            this._world.viewport.get_layout_manager().dragging
        )
            return selection;

        return DefaultTransition.add_transition(
            selection.attr("in_transit", 100),
        )
            .on("end", () => null)
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
        return this._get_link_type_specific_force(force_name, force_options);
    }

    _get_link_type_specific_force(
        force_name: SimulationForce,
        force_options: ForceOptions,
    ): number {
        return force_options[force_name];
    }
}

class LinkTypeClassRegistry extends AbstractClassRegistry<AbstractLink> {}

export const link_type_class_registry = new LinkTypeClassRegistry();
