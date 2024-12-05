/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import type {BaseType, D3DragEvent, Selection} from "d3";
import {polygonHull, select} from "d3";

import type {ForceOptions} from "./force_utils";
import {ForceConfig} from "./force_utils";
import type {AbstractNodeVisConstructor, OverlayElement} from "./layer_utils";
import {get} from "./texts";
import type {
    Coords,
    d3SelectionDiv,
    NodevisNode,
    NodevisWorld,
    Rectangle,
    XYCoords,
} from "./type_defs";
import {InputRangeOptions} from "./type_defs";
import type {TypeWithName} from "./utils";
import {
    AbstractClassRegistry,
    DefaultTransition,
    get_bounding_rect,
    log,
    render_input_range,
} from "./utils";

export type LineStyle = "straight" | "elbow" | "round";
export class LineConfig {
    style: LineStyle = "round";
    dashed = false;
}

export interface SerializedNodevisLayout {
    reference_size: Rectangle;
    line_config: LineConfig;
    force_config: ForceOptions;
    style_configs: StyleConfig[];
    delayed_style_configs?: StyleConfig[];
    default_id?: string;
    origin_info?: string;
    origin_type?: string;
}

// TODO: fix styles
export class NodeVisualizationLayout {
    reference_size: Rectangle;
    style_configs: StyleConfig[];
    line_config: LineConfig;
    force_config: ForceOptions;
    origin_info: string;
    origin_type: string;

    constructor() {
        this.reference_size = {height: 0, width: 0};
        this.style_configs = [];
        this.line_config = new LineConfig();
        this.force_config = ForceConfig.prototype.get_default_options();
        this.origin_info = "";
        this.origin_type = "";
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

    serialize(): SerializedNodevisLayout {
        return {
            reference_size: this.reference_size,
            style_configs: this.style_configs,
            line_config: this.line_config,
            force_config: this.force_config,
            origin_info: this.origin_info,
            origin_type: this.origin_type,
        };
    }

    deserialize(
        data: SerializedNodevisLayout,
        default_size: Rectangle,
        default_force: ForceOptions,
    ): void {
        this.reference_size = data.reference_size || default_size;
        this.style_configs = data.style_configs || [];
        this.line_config = data.line_config || new LineConfig();
        this.force_config =
            Object.entries(data.force_config).length > 0
                ? data.force_config
                : default_force;
        this.origin_info = data.origin_info || "";
        this.origin_type = data.origin_type || "";
    }
}

export function compute_style_id(
    style_class: AbstractNodeVisConstructor<AbstractLayoutStyle>,
    node: NodevisNode,
) {
    return style_class.prototype.class_name() + "_" + node.data.id;
}

interface StyleWithDescription {
    description: () => string;
}

export function compute_node_positions_from_list_of_nodes(
    list_of_nodes: NodevisNode[],
): void {
    if (list_of_nodes == undefined) return;
    list_of_nodes.forEach(node => compute_node_position(node));
}

export function compute_node_position(node: NodevisNode) {
    let current_positioning = {
        weight: 0,
        free: true,
        type: "force",
        fx: 0,
        fy: 0,
        use_transition: true,
    };

    if (
        node.data.use_style &&
        Object.keys(node.data.node_positioning).length == 0
    ) {
        return;
    }

    for (const force_id in node.data.node_positioning) {
        const force = node.data.node_positioning[force_id];
        if (force.weight > current_positioning.weight) {
            current_positioning = force;
        }
    }

    // Beside of x/y coords, the layout may have additional info
    // E.g. text positioning
    node.data.current_positioning = current_positioning;
    if (current_positioning.free) {
        node.fx = null;
        node.fy = null;
        node.data.transition_info.use_transition = false;
    } else {
        const viewport_boundary = 20000;
        node.fx = Math.max(
            Math.min(current_positioning.fx, viewport_boundary),
            -viewport_boundary,
        );
        node.fy = Math.max(
            Math.min(current_positioning.fy, viewport_boundary),
            -viewport_boundary,
        );
        node.x = node.fx;
        node.y = node.fy;
        node.data.transition_info.use_transition =
            current_positioning.use_transition;
    }
}

export class AbstractLayoutStyle implements TypeWithName, StyleWithDescription {
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
        selection: d3SelectionDiv,
    ) {
        // Contains all configurable options for this style
        this._world = world;
        this.style_config = style_config;
        // The selection for the styles graphical overlays
        this.selection = selection;

        // Root node for this style
        this.style_root_node = node;
        if (this.style_root_node) {
            if (style_config.position) {
                const coords = this._world.viewport.get_size();
                this.style_root_node.x =
                    (style_config.position.x / 100) * coords.width;
                this.style_root_node.y =
                    (style_config.position.y / 100) * coords.height;
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

    description() {
        return "abstract description";
    }

    _compute_svg_vertex(x: number, y: number): [number, number] {
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
                    this._world.viewport.get_viewport_percentage_of_node(
                        this.style_root_node,
                    );
            }
        }
    }

    id(): string {
        return compute_style_id(
            this.constructor as AbstractNodeVisConstructor<AbstractLayoutStyle>,
            this.style_root_node,
        );
    }

    show_style_configuration() {
        this._world.viewport
            .get_layout_manager()
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

    reset_default_options(): void {
        this.changed_options(this.get_default_options());
    }

    changed_options(new_options: StyleOptionValues) {
        this._world.viewport.get_layout_manager().skip_optional_transitions =
            true;
        this.style_config.options = new_options;
        this.force_style_translation();

        if (this.style_root_node)
            compute_node_positions_from_list_of_nodes(
                this.style_root_node.descendants(),
            );

        this._world.viewport.restart_force_simulation(0.5);
        this._world.viewport.update_layers();
        this._world.viewport.get_layout_manager().skip_optional_transitions =
            false;
        this.show_style_configuration();
    }

    get_size(): XYCoords {
        const vertices: Coords[] = [];
        this._style_root_node_offsets.forEach(offset =>
            vertices.push({x: offset[1], y: offset[2]}),
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
                this.style_root_node,
            );
            if (root_node) {
                const use_style = root_node.data.use_style;
                if (use_style) rotation += use_style.get_rotation();
            }
        }
        return rotation;
    }

    _find_parent_with_style(node: NodevisNode): NodevisNode | null {
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
                // End node: Match by id
                matcher_conditions.id = {
                    value: this.style_root_node.data.id,
                };
            }
        } else {
            // Generic node
            matcher_conditions.id = {
                value: this.style_root_node.data.id,
            };
        }

        // Override default options with user customized settings.
        // May disable match types and modify match texts
        for (const idx in this.style_config.matcher) {
            //@ts-ignore
            matcher_conditions[idx] = this.style_config.matcher[idx];
        }
        return matcher_conditions;
    }

    update_style_indicator(indicator_shown = true): void {
        const gui_node = this._world.viewport
            .get_nodes_layer()
            .get_node_by_id(this.style_root_node.data.id);
        if (gui_node == null || gui_node._selection == null) return;
        const style_indicator = gui_node
            .selection()
            .selectAll<
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
                    node.data.use_style.class_name() == "force")
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
        return (this._world.viewport
            .get_layout_manager()
            .get_node_positioning(node)[this.id()] = {
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

    add_option_icons(coords: Coords, elements: OverlayElement[]): void {
        for (const idx in elements) {
            const idx_num = Number.parseInt(idx);
            const element = elements[idx];
            let img = this.get_div_selection()
                .selectAll<HTMLImageElement, OverlayElement>(
                    "img." + element.type,
                )
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
                    if (d.call) select(nodes[idx]).call(d.call);
                })
                .each((d, idx, nodes) => {
                    if (d.onclick) select(nodes[idx]).on("click", d.onclick);
                })
                .style("top", coords.y - 62 + "px")
                .style("left", coords.x + idx_num * (30 + 12) + "px")
                .merge(img);

            const offset = parseInt(img.style("width"), 10);
            img.style("top", () => coords.y - 62 + "px").style(
                "left",
                () => coords.x + idx_num * (offset + 12) + "px",
            );
        }
    }

    get_div_selection() {
        const div_selection = this._world.viewport
            .get_layout_manager()
            .get_div_selection()
            .selectAll<HTMLDivElement, string>("div.style_overlay")
            .data([this.id()], d => d);

        return div_selection
            .enter()
            .append("div")
            .classed("style_overlay", true)
            .merge(div_selection);
    }

    add_enclosing_hull(
        into_selection: d3SelectionDiv,
        vertices: [number, number][],
    ) {
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
            .selectAll<SVGPathElement, unknown>("path.style_overlay")
            .data([polygonHull(hull_vertices)]);
        hull = hull
            .enter()
            .append("path")
            .classed("style_overlay", true)
            .style("opacity", 0)
            .merge(hull);
        hull.interrupt();

        this.add_optional_transition(
            hull.attr("d", function (d) {
                return "M" + d!.join("L") + "Z";
            }),
            // @ts-ignore
        ).style("opacity", null);
    }

    add_optional_transition<GType extends BaseType, Data>(
        selection_with_node_data: Selection<GType, Data, BaseType, unknown>,
    ) {
        if (this._world.viewport.get_layout_manager().skip_optional_transitions)
            return selection_with_node_data;

        // TODO: deprecate this option
        if (this._world.viewport.get_layout_manager().dragging)
            return selection_with_node_data;

        return selection_with_node_data
            .transition()
            .duration(DefaultTransition.duration());
    }

    class_name(): string {
        return "abstract";
    }
}

// TODO: finalize
export class LayoutStyleFactory {
    _world: NodevisWorld;
    constructor(world: NodevisWorld) {
        this._world = world;
    }

    get_styles(): {
        [name: string]: AbstractNodeVisConstructor<AbstractLayoutStyle>;
    } {
        return layout_style_class_registry.get_classes();
    }

    // Creates a style instance with the given style_config
    instantiate_style(
        style_config: {type: string},
        node: NodevisNode,
        selection:
            | d3SelectionDiv
            | Selection<SVGGElement, unknown, null, undefined>,
    ) {
        return new (layout_style_class_registry.get_class(style_config.type))(
            this._world,
            //@ts-ignore
            style_config,
            node,
            selection,
        );
    }

    instantiate_style_name(
        style_name: string,
        node: NodevisNode,
        selection: d3SelectionDiv,
    ): AbstractLayoutStyle {
        return this.instantiate_style({type: style_name}, node, selection);
    }

    instantiate_style_class(
        style_class: AbstractNodeVisConstructor<AbstractLayoutStyle>,
        node: NodevisNode,
        selection: d3SelectionDiv,
    ): AbstractLayoutStyle {
        return this.instantiate_style(
            {type: style_class.prototype.class_name()},
            node,
            selection,
        );
    }
}

export type StyleOptionValue = boolean | number;
export type StyleOptionValues = Record<string, StyleOptionValue>;

export interface StyleOptionSpec {
    id: string;
    option_type: string;
    hidden?: boolean;
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
    id?: MatcherConditionValue;
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
    text_positioning?: (x?: any, y?: any) => any;
    hide_node_link?: boolean;
    weight: number;
    type: string;
}

export type NodePositioning = Record<string, NodeForce>;

class LayoutStyleClassRegistry extends AbstractClassRegistry<AbstractLayoutStyle> {}

export const layout_style_class_registry = new LayoutStyleClassRegistry();

export function render_style_options(
    style_id: string,
    into_selection: d3SelectionDiv,
    style_option_specs: StyleOptionSpec[],
    style_option_values: StyleOptionValues,
    options_changed_callback: (styleOptionValues: StyleOptionValues) => void,
    reset_default_options_callback: (
        event: D3DragEvent<any, any, any>,
    ) => void = _event => {
        return;
    },
) {
    const table = into_selection
        .selectAll<HTMLTableElement, string>("table")
        .data([style_id], d => d)
        .join(enter =>
            enter.append("table").classed("style_configuration", true),
        );

    function option_changed(option_id: string, new_value: any) {
        style_option_values[option_id] = new_value;
        options_changed_callback(style_option_values);
    }

    _render_range_options(
        table,
        style_option_specs,
        style_option_values,
        option_changed,
    );
    _render_checkbox_options(
        table,
        style_option_specs,
        style_option_values,
        option_changed,
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
                .attr("value", get("reset"))
                .on("click", reset_default_options_callback),
        );
}

function _render_range_options(
    table: Selection<HTMLTableElement, string, any, unknown>,
    style_option_specs: StyleOptionSpec[],
    style_option_values: StyleOptionValues,
    option_changed_callback: (option_id: string, new_value: number) => void,
): void {
    const rows = table
        .selectAll<HTMLTableRowElement, StyleOptionSpecRange>("tr.range_input")
        .data(
            style_option_specs.filter(
                d => d.option_type == "range" && !d.hidden,
            ),
        )
        .join<HTMLTableRowElement>(enter =>
            enter.append("tr").classed("range_input", true),
        );

    rows.each((style_option, idx, nodes) => {
        const current_value =
            style_option_values[style_option.id] || style_option.values.default;
        render_input_range(
            select(nodes[idx]),
            new InputRangeOptions(
                style_option.id,
                style_option.text,
                style_option.values.step,
                style_option.values.min,
                style_option.values.max,
                style_option.values.default,
            ),
            current_value,
            option_changed_callback,
        );
    });
}

function _render_checkbox_options(
    table: Selection<HTMLTableElement, string, any, unknown>,
    style_option_specs: StyleOptionSpec[],
    style_option_values: StyleOptionValues,
    option_changed_callback: (option_id: string, new_value: boolean) => void,
): void {
    const rows = table
        .selectAll<HTMLTableRowElement, StyleOptionSpecCheckbox>(
            "tr.checkbox_option",
        )
        .data(
            style_option_specs.filter(
                d => d.option_type == "checkbox" && !d.hidden,
            ),
        )
        .join(enter => enter.append("tr").classed("checkbox_option", true));

    rows.selectAll<HTMLTableCellElement, StyleOptionSpecCheckbox>(
        "td nobr.checkbox_text",
    )
        .data(
            d => [d],
            d => d.id,
        )
        .enter()
        .append("td")
        .append("nobr")
        .classed("checkbox_text", true)
        .text(d => d.text);

    rows.selectAll<HTMLDivElement, StyleOptionSpec>(
        "div.toggle_switch_container",
    )
        .data(
            d => [d],
            d => d.id,
        )
        .join(enter =>
            enter
                .append("div")
                .classed("nodevis toggle_switch_container", true)
                .on("click", (event, d) => {
                    const node = select(event.target);
                    const new_value = node.classed("on") == true ? "off" : "on";
                    node.classed("on off", false);
                    node.classed(new_value, true);
                    option_changed_callback(d.id, new_value == "on");
                }),
        )
        .each((d, idx, nodes) => {
            const state = style_option_values[d.id] ? "on" : "off";
            nodes[idx].classList.add(state);
        });
}
