import {LineConfig} from "nodevis/layout_utils";
import {
    d3SelectionG,
    NodevisLink,
    NodevisNode,
    NodevisWorld,
} from "nodevis/type_defs";
import {AbstractClassRegistry, DefaultTransition} from "nodevis/utils";

export function compute_link_id(link_data: NodevisLink): string {
    return link_data.source.data.id + "#@#" + link_data.target.data.id;
}

export class AbstractLink {
    static class_name = "abstract";
    _world: NodevisWorld;
    _link_data: NodevisLink;
    _selection: d3SelectionG | null;
    _line_config: LineConfig;

    constructor(world: NodevisWorld, link_data: NodevisLink) {
        this._world = world;
        this._link_data = link_data;
        this._selection = null;
        this._line_config =
            this._link_data.source.data.chunk.layout_settings.config.line_config;
    }

    selection(): d3SelectionG {
        if (this._selection == null)
            throw Error("Missing selection for node " + this.id());
        return this._selection;
    }

    id(): string {
        return compute_link_id(this._link_data);
    }

    render_into(selection): void {
        // Straigth line style
        const line_selection = selection
            .selectAll("line")
            .data(this._line_config.style == "straight" ? [this.id()] : [])
            .join("line")
            .attr("marker-end", "url(#triangle)")
            .attr("stroke-width", function (d) {
                return Math.max(1, 2 - d.depth);
            })
            .style("stroke", this._color());

        // Elbow and round style
        const path_selection = selection
            .selectAll("path")
            .data(this._line_config.style != "straight" ? [this.id()] : [])
            .join("path")
            .attr("fill", "none")
            .attr("stroke-width", 1)
            .style("stroke", this._color());

        this._selection =
            this._line_config.style == "straight"
                ? line_selection
                : path_selection;
        if (this._line_config.dashed) this.selection().classed("dashed", true);
    }

    _color(): string {
        return "darkgrey";
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
        this.selection().style("stroke-opacity", 0.3);

        const x1 = source.data.target_coords.x;
        const y1 = source.data.target_coords.y;
        const x2 = target.data.target_coords.x;
        const y2 = target.data.target_coords.y;

        this._add_fancy_line_transitition(source, target);

        const tmp_selection = this.add_optional_transition(this.selection());
        switch (this._line_config.style) {
            case "straight": {
                tmp_selection
                    .attr("x1", x1)
                    .attr("y1", y1)
                    .attr("x2", x2)
                    .attr("y2", y2);
                break;
            }
            case "round": {
                tmp_selection.attr("d", () =>
                    this.diagonal_line(x1, y1, x2, y2)
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
        target: NodevisNode
    ): void {
        const source_selection = source.data.selection;
        const target_selection = target.data.selection;
        if (!source_selection || !target_selection) return;

        const source_node = source_selection.node();
        const target_node = target_selection.node();
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
                transform_target.f
            )
        );
    }

    elbow(source_x, source_y, target_x, target_y) {
        return (
            "M" + source_x + "," + source_y + "V" + target_y + "H" + target_x
        );
    }

    // Creates a curved (diagonal) path from parent to the child nodes
    diagonal_line(
        source_x: number,
        source_y: number,
        target_x: number,
        target_y: number
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
            this._world.layout_manager.dragging
        )
            return selection;

        return DefaultTransition.add_transition(
            selection.attr("in_transit", 100)
        )
            .on("end", () => null)
            .attr("in_transit", 0)
            .on("interrupt", () => {
                this.selection().attr("in_transit", 0);
            })
            .attr("in_transit", 0);
    }
}

class LinkTypeClassRegistry extends AbstractClassRegistry<
    typeof AbstractLink
> {}

export const link_type_class_registry = new LinkTypeClassRegistry();
