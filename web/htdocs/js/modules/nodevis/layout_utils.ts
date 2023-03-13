// Copyright (C) 2023 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

import {
    Coords,
    d3SelectionDiv,
    NodevisNode,
    NodevisWorld,
    Rectangle,
    XYCoords,
} from "nodevis/type_defs";
import {
    AbstractClassRegistry,
    DefaultTransition,
    get_bounding_rect,
    log,
} from "nodevis/utils";
import {compute_node_positions_from_list_of_nodes} from "nodevis/layout";
import * as d3 from "d3";
import {ForceOptions} from "nodevis/force_simulation";

export class LineConfig {
    style: "straight" | "elbow" | "round" = "round";
    dashed = false;
}

export interface SerializedNodevisLayout {
    reference_size: Rectangle;
    style_configs: StyleConfig[];
    line_config: LineConfig;
    force_options: ForceOptions;
}

// TODO: fix styles
export class NodeVisualizationLayout {
    id: string;
    reference_size: Rectangle;
    style_configs: StyleConfig[];
    line_config: LineConfig;

    constructor(viewport, id) {
        this.id = id;
        this.reference_size = {height: 0, width: 0};
        this.style_configs = [];
        this.line_config = new LineConfig();
    }

    save_style(style_config: StyleConfig): void {
        this.style_configs.push(style_config);
    }

    clear_styles(): void {
        this.style_configs = [];
    }

    remove_style(style_instance: AbstractLayoutStyle) {
        const idx = this.style_configs.indexOf(style_instance.style_config);
        this.style_configs.splice(idx, 1);
    }

    serialize(world: NodevisWorld): SerializedNodevisLayout {
        return {
            reference_size: this.reference_size,
            style_configs: this.style_configs,
            line_config: this.line_config,
            force_options: world.force_simulation.get_force_options(),
        };
    }

    deserialize(data: SerializedNodevisLayout): void {
        this.reference_size = data.reference_size;
        this.style_configs = data.style_configs;
        this.line_config = data.line_config;
    }
}

export function compute_style_id(
    style_class: typeof AbstractLayoutStyle,
    node: NodevisNode
) {
    return style_class.class_name + "_" + node.data.id;
}

export class AbstractLayoutStyle extends Object {
    static class_name = "abstract";
    static description = "abstract description";
    _world: NodevisWorld;
    style_config: StyleConfig;
    style_root_node: NodevisNode;
    selection: d3SelectionDiv; // TODO: rename _div_selection
    _default_options: {[name: string]: number | boolean} = {};
    _style_translated = false; // If set, suppresses translationn of style_node offsets
    _vertices: [number, number][] = []; // Coords [x,y] for each node in this style
    _style_root_node_offsets: [NodevisNode, number, number][] = [];
    filtered_descendants: NodevisNode[] = [];
    use_transition = true;

    options_selection: d3SelectionDiv | null = null;

    constructor(
        world: NodevisWorld,
        style_config: StyleConfig,
        node: NodevisNode,
        selection
    ) {
        super();
        // Contains all configurable options for this style
        this._world = world;
        this.style_config = style_config;
        // The selection for the styles graphical overlays
        this.selection = selection;

        // Root node for this style
        this.style_root_node = node;
        if (this.style_root_node) {
            // Chunk this root node resides in
            if (style_config.position) {
                const coords = this.style_root_node.data.chunk.coords;
                this.style_root_node.x =
                    (style_config.position.x / 100) * coords.width + coords.x;
                this.style_root_node.y =
                    (style_config.position.y / 100) * coords.height + coords.y;
            }
        }

        // Apply missing default values to options
        this._initialize_style_config();

        // Default options lookup
        const style_options = this.get_style_options();
        style_options.forEach(option => {
            this._default_options[option.id] = option.values.default;
        });
    }

    _compute_svg_vertex(x, y): [number, number] {
        // TODO: check actual/upcoming usage
        return [x, y];
    }

    _initialize_style_config(): void {
        if (this.style_config.options == null) {
            this.style_config.options = {};
        }

        // options
        this.get_style_options().forEach(option => {
            if (this.style_config.options[option.id] == null)
                this.style_config.options[option.id] = option.values.default;
        });

        if (this.style_root_node) {
            // matcher
            const matcher = this.get_matcher();
            if (matcher) this.style_config.matcher = matcher;

            // position
            if (!this.style_config.position) {
                this.style_config.position =
                    this._world.layout_manager.get_viewport_percentage_of_node(
                        this.style_root_node
                    );
            }
        }
    }

    id(): string {
        return compute_style_id(
            this.constructor as typeof AbstractLayoutStyle,
            this.style_root_node
        );
    }

    show_style_configuration() {
        this._world.layout_manager.toolbar_plugin
            .layout_style_configuration()
            .show_style_configuration(this);
    }

    get_style_options(): StyleOptionSpec[] {
        return [];
    }

    generate_overlay(): void {
        return;
    }

    get_default_options(): StyleOptionValues {
        const default_options: StyleOptionValues = {};
        this.get_style_options().forEach(option => {
            default_options[option.id] = option.values.default;
        });
        return default_options;
    }

    reset_default_options(event): void {
        this.changed_options(event, this.get_default_options());
    }

    changed_options(event, new_options: StyleOptionValues) {
        this._world.layout_manager.skip_optional_transitions = true;
        this.style_config.options = new_options;
        this.force_style_translation();

        if (this.style_root_node)
            compute_node_positions_from_list_of_nodes(
                this.style_root_node.descendants()
            );

        this._world.force_simulation.restart_with_alpha(0.5);
        this._world.viewport.update_layers();
        this._world.layout_manager.skip_optional_transitions = false;
        this.show_style_configuration();
    }

    get_size(): XYCoords {
        const vertices: Coords[] = [];
        this._style_root_node_offsets.forEach(offset =>
            vertices.push({x: offset[1], y: offset[2]})
        );
        const bounding_rect = get_bounding_rect(vertices);
        return [
            bounding_rect.width * 1.1 + 100,
            bounding_rect.height * 1.1 + 100,
        ];
    }

    get_rotation(): number {
        let rotation = this.style_config.options.rotation as number;
        if (rotation == undefined) return 0;
        if (this.style_config.options.include_parent_rotation == true) {
            const root_node = this._find_parent_with_style(
                this.style_root_node
            );
            if (root_node) {
                const use_style = root_node.data.use_style;
                if (use_style) rotation += use_style.get_rotation();
            }
        }
        return rotation;
    }

    _find_parent_with_style(node): NodevisNode | null {
        if (!node.parent) return null;
        if (node.parent.data.use_style) return node.parent;
        else return this._find_parent_with_style(node.parent);
    }

    style_color(): string {
        return "#000000";
    }

    type(): string {
        return "abstract";
    }

    set_matcher(matcher: StyleMatcherConditions): void {
        this.style_config.matcher = matcher;
    }

    get_matcher(): StyleMatcherConditions {
        // TODO: refactor/remove. The correct matcher should be created within the AbstractGUINode
        // The AbstractGUINode knows its type and conditions
        const matcher_conditions: StyleMatcherConditions = {};

        if (
            this.style_root_node.data.node_type == "bi_aggregator" ||
            this.style_root_node.data.node_type == "bi_leaf"
        ) {
            // Match by aggr_path: The path of rule_ids up to the node
            matcher_conditions.aggr_path_id = {
                value: this.style_root_node.data.aggr_path_id,
                disabled: true,
            };
            matcher_conditions.aggr_path_name = {
                value: this.style_root_node.data.aggr_path_name,
                disabled: true,
            };

            if (this.style_root_node.data.node_type == "bi_aggregator") {
                // Aggregator: Match by rule_id
                matcher_conditions.rule_id = {
                    value: this.style_root_node.data.rule_id.rule,
                };
                matcher_conditions.rule_name = {
                    value: this.style_root_node.data.name,
                };
            } else {
                // End node: Match by hostname or service
                matcher_conditions.hostname = {
                    value: this.style_root_node.data.hostname,
                };
                matcher_conditions.service = {
                    value: this.style_root_node.data.service,
                };
            }
        } else {
            // Generic node
            matcher_conditions.hostname = {
                value: this.style_root_node.data.hostname,
            };
        }

        // Override default options with user customized settings.
        // May disable match types and modify match texts
        for (const idx in this.style_config.matcher) {
            matcher_conditions[idx] = this.style_config.matcher[idx];
        }
        return matcher_conditions;
    }

    update_style_indicator(indicator_shown = true): void {
        const style_indicator = this.style_root_node.data.selection.selectAll<
            SVGCircleElement,
            AbstractLayoutStyle
        >("circle.style_indicator");

        if (!indicator_shown) {
            style_indicator.remove();
            return;
        }

        style_indicator
            .data<AbstractLayoutStyle>([this])
            .enter()
            .insert("circle", "#outer_circle")
            .classed("style_indicator", true)
            .attr("pointer-events", "none")
            .attr("r", 30)
            .attr("fill", d => d.style_color());
    }

    // positioning_weight of the layout positioning
    // If multiple positioning forces are applied to one node, the one with the highest positioning_weight wins
    positioning_weight(): number {
        return 0;
    }

    force_style_translation(): void {
        log(7, "force style translation of " + this.id());
        this._style_translated = false;
    }

    has_fixed_position(): boolean {
        const ancestors = this.style_root_node.ancestors();
        for (const idx in ancestors) {
            const node = ancestors[idx];
            if (!node.data.use_style) continue;
            const style_options = node.data.use_style.style_config.options;
            if (style_options.detach_from_parent) return true;
            if (
                !node.parent &&
                (!node.data.use_style ||
                    // @ts-ignore
                    node.data.use_style.constructor.class_name == "force")
            )
                return false;
        }
        return true;
    }

    zoomed(): void {
        return;
    }

    update_data(): void {
        return;
    }

    update_gui(): void {
        return;
    }

    fix_node(node: NodevisNode): void {
        // TODO: find better implementation without deep copying
        const force = this.get_default_node_force(node) as unknown as NodeForce;
        force.fx = node.x;
        force.fy = node.y;
        force.use_transition = true;
    }

    get_default_node_force(node: NodevisNode): NodeForce {
        return (this._world.layout_manager.get_node_positioning(node)[
            this.id()
        ] = {
            weight: this.positioning_weight(),
            type: this.type(),
        });
    }

    // Computes offsets use for node translate
    _compute_node_offsets(): void {
        return;
    }

    // Translates the nodes by the computed offsets
    translate_coords(): void {
        return;
    }

    remove(): void {
        delete this.style_root_node.data.node_positioning[this.id()];
        // TODO: might get added/removed on the same call..
        this.get_div_selection().remove();
        this.update_style_indicator(false);
    }

    add_option_icons(coords: Coords, elements): void {
        for (const idx in elements) {
            const idx_num = Number.parseInt(idx);
            const element = elements[idx];
            let img = this.get_div_selection()
                .selectAll<HTMLImageElement, NodevisNode>("img." + element.type)
                .data([element], d => d.node.data.id);
            img = img
                .enter()
                .append("img")
                .classed(element.type, true)
                .classed("layouting_icon", true)
                .classed("box", true)
                .attr("src", element.image)
                .style("position", "absolute")
                .style("pointer-events", "all")
                .each((d, idx, nodes) => {
                    if (d.call) d3.select(nodes[idx]).call(d.call);
                })
                .each((d, idx, nodes) => {
                    if (d.onclick) d3.select(nodes[idx]).on("click", d.onclick);
                })
                .style("top", coords.y - 62 + "px")
                .style("left", coords.x + idx_num * (30 + 12) + "px")
                .merge(img);

            const offset = parseInt(img.style("width"), 10);
            img.style("top", () => coords.y - 62 + "px").style(
                "left",
                () => coords.x + idx_num * (offset + 12) + "px"
            );
        }
    }

    get_div_selection() {
        const div_selection = this._world.layout_manager
            .get_div_selection()
            .selectAll<HTMLDivElement, string>("div.hierarchy")
            .data([this.id()]);
        return div_selection
            .enter()
            .append("div")
            .classed("hierarchy", true)
            .merge(div_selection);
    }

    add_enclosing_hull(into_selection, vertices) {
        if (vertices.length < 2) {
            into_selection.selectAll("path.style_overlay").remove();
            return;
        }

        const boundary = 30;
        const hull_vertices: [number, number][] = [];
        vertices.forEach(entry => {
            hull_vertices.push([entry[0] + boundary, entry[1] + boundary]);
            hull_vertices.push([entry[0] - boundary, entry[1] - boundary]);
            hull_vertices.push([entry[0] + boundary, entry[1] - boundary]);
            hull_vertices.push([entry[0] - boundary, entry[1] + boundary]);
        });
        let hull = into_selection
            .selectAll("path.style_overlay")
            .data([d3.polygonHull(hull_vertices)]);
        hull = hull
            .enter()
            .append("path")
            .classed("style_overlay", true)
            .style("opacity", 0)
            .merge(hull);
        hull.interrupt();
        this.add_optional_transition(
            hull.attr("d", function (d) {
                return "M" + d.join("L") + "Z";
            })
        ).style("opacity", null);
    }

    add_optional_transition(selection_with_node_data) {
        if (this._world.layout_manager.skip_optional_transitions)
            return selection_with_node_data;

        // TODO: deprecate this option
        if (this._world.layout_manager.dragging)
            return selection_with_node_data;

        return selection_with_node_data
            .transition()
            .duration(DefaultTransition.duration());
    }
}

// TODO: finalize
export class LayoutStyleFactory {
    _world: NodevisWorld;

    constructor(world: NodevisWorld) {
        this._world = world;
    }

    get_styles(): {[name: string]: typeof AbstractLayoutStyle} {
        if (this._world.current_datasource == "topology")
            return {fixed: layout_style_class_registry.get_class("fixed")};
        return layout_style_class_registry.get_classes();
    }

    // Creates a style instance with the given style_config
    instantiate_style(style_config, node, selection) {
        // @ts-ignore
        return new (layout_style_class_registry.get_class(style_config.type))(
            this._world,
            style_config,
            node,
            selection
        );
    }

    instantiate_style_name(style_name, node, selection): AbstractLayoutStyle {
        return this.instantiate_style({type: style_name}, node, selection);
    }

    instantiate_style_class(
        style_class: typeof AbstractLayoutStyle,
        node: NodevisNode,
        selection: d3SelectionDiv
    ): AbstractLayoutStyle {
        return this.instantiate_style(
            {type: style_class.class_name},
            node,
            selection
        );
    }
}

export type StyleOptionValue = boolean | number;
export type StyleOptionValues = {[name: string]: StyleOptionValue};

export interface StyleOptionSpec {
    id: string;
    option_type: string;
    text: string;
    values: any;
}

export interface StyleOptionSpecRange extends StyleOptionSpec {
    values: {default: number; min: number; max: number; step: number};
    option_type: "range";
}

export interface StyleOptionSpecCheckbox extends StyleOptionSpec {
    values: {default: boolean};
    option_type: "checkbox";
}

interface MatcherConditionValue {
    value: [string, number][] | string;
    disabled?: boolean;
}

export interface StyleMatcherConditions {
    aggr_path_id?: MatcherConditionValue;
    aggr_path_name?: MatcherConditionValue;
    rule_id?: MatcherConditionValue;
    rule_name?: MatcherConditionValue;
    hostname?: MatcherConditionValue;
    service?: MatcherConditionValue;
}

export interface StyleConfig {
    type: string;
    position: Coords | null;
    weight: number;
    options: StyleOptionValues;
    matcher: StyleMatcherConditions;
}

export interface NodeForce {
    fx?: number;
    fy?: number;
    use_transition?: boolean;
    text_positioning?: (x, y) => any;
    hide_node_link?: boolean;
    weight: number;
    type: string;
}

export interface NodePositioning {
    [name: string]: NodeForce;
}

export interface LayoutHistoryStep {
    origin_info: string;
    origin_type: string;
    config: SerializedNodevisLayout;
}

class LayoutStyleClassRegistry extends AbstractClassRegistry<
    typeof AbstractLayoutStyle
> {}

export const layout_style_class_registry = new LayoutStyleClassRegistry();

export function render_style_options(
    style_id: string,
    into_selection: d3SelectionDiv,
    style_option_specs: StyleOptionSpec[],
    style_option_values: StyleOptionValues,
    options_changed_callback,
    reset_default_options_callback: (event) => void = _event => {
        return;
    }
) {
    into_selection
        .selectAll("#styleoptions_headline")
        .data([null])
        .join("b")
        .attr("id", "styleoptions_headline")
        .text("Options");

    const table = into_selection
        .selectAll<HTMLTableElement, string>("table")
        .data([style_id], d => d)
        .join("table");

    _render_range_options(
        table,
        style_option_specs,
        style_option_values,
        options_changed_callback
    );
    _render_checkbox_options(
        table,
        style_option_specs,
        style_option_values,
        options_changed_callback
    );

    into_selection
        .selectAll<HTMLInputElement, string>("input.reset_options")
        .data([style_id], d => d)
        .join(enter =>
            enter
                .append("input")
                .attr("type", "button")
                .classed("button", true)
                .classed("reset_options", true)
                .attr("value", "Reset default values")
                .on("click", event => {
                    reset_default_options_callback(event);
                })
        );
}

function _get_style_option_values(
    from_selection: d3.Selection<HTMLTableElement, string, any, unknown>,
    style_option_specs: StyleOptionSpec[]
): StyleOptionValues {
    const option_values: StyleOptionValues = {};
    style_option_specs.forEach(option_spec => {
        switch (option_spec.option_type) {
            case "range":
                option_values[option_spec.id] = parseFloat(
                    from_selection
                        .select("input#" + option_spec.id)
                        .property("value")
                );
                break;
            case "checkbox":
                option_values[option_spec.id] = from_selection
                    .select("input#" + option_spec.id)
                    .property("checked");
                break;
        }
    });
    return option_values;
}

function _render_range_options(
    table: d3.Selection<HTMLTableElement, string, any, unknown>,
    style_option_specs: StyleOptionSpec[],
    style_option_values: StyleOptionValues,
    option_changed_callback: (any, StyleOptionValues) => void
): void {
    const rows = table
        .selectAll<HTMLTableRowElement, StyleOptionSpecRange>("tr.range_option")
        .data(style_option_specs.filter(d => d.option_type == "range"))
        .join<HTMLTableRowElement>(enter =>
            enter.append("tr").classed("range_option", true)
        );

    rows.selectAll("td.text")
        .data(d => [d])
        .join(enter => enter.append("td").classed("text", true))
        .text(d => d.text);

    rows.selectAll("td input")
        .data(d => [d])
        .join("td")
        .selectAll("input")
        .data(d => [d])
        .join(enter =>
            enter
                .append("input")
                .classed("range", true)
                .attr("id", d => d.id)
                .attr("name", d => "type_value_" + d.id)
                .attr("type", "range")
                .attr("step", d => d.values.step || 1)
                .attr("min", d => d.values.min)
                .attr("max", d => d.values.max)
                .on("input", event => {
                    const new_options = _get_style_option_values(
                        table,
                        style_option_specs
                    );
                    option_changed_callback(event, new_options);
                    _render_range_options(
                        table,
                        style_option_specs,
                        new_options,
                        option_changed_callback
                    );
                })
                .on("change", event => {
                    const new_options = _get_style_option_values(
                        table,
                        style_option_specs
                    );
                    option_changed_callback(event, new_options);
                    _render_range_options(
                        table,
                        style_option_specs,
                        new_options,
                        option_changed_callback
                    );
                })
        );

    rows.selectAll("td.value")
        .data(d => [d])
        .join(enter => enter.append("td").classed("value", true))
        .text(d => style_option_values[d.id]);

    rows.selectAll("input")
        .data(d => [d])
        .property("value", d => style_option_values[d.id]);
}

function _render_checkbox_options(
    table: d3.Selection<HTMLTableElement, string, any, unknown>,
    style_option_specs: StyleOptionSpec[],
    style_option_values: StyleOptionValues,
    options_changed_callback: (any, StyleOptionValues) => void
): void {
    const rows = table
        .selectAll<HTMLTableRowElement, StyleOptionSpecCheckbox>(
            "tr.checkbox_option"
        )
        .data(style_option_specs.filter(d => d.option_type == "checkbox"))
        .join(enter => enter.append("tr").classed("checkbox_option", true));

    rows.selectAll("td.text")
        .data(d => [d])
        .join(enter => enter.append("td").classed("text", true))
        .text(d => d.text);

    rows.selectAll("td input")
        .data(d => [d])
        .join(enter =>
            enter
                .append("td")
                .append("input")
                .classed("checkbox", true)
                .attr("id", d => d.id)
                .attr("name", d => "type_checkbox_" + d.id)
                .attr("type", "checkbox")
                .property("checked", d => style_option_values[d.id])
                .on("input", event => {
                    const new_options = _get_style_option_values(
                        table,
                        style_option_specs
                    );
                    options_changed_callback(event, new_options);
                    _render_checkbox_options(
                        table,
                        style_option_specs,
                        new_options,
                        options_changed_callback
                    );
                })
        );
}
