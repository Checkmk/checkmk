/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

// Note: This file requires a complete redesign
// It uses way too much fake objects to render some simple styles
// Fortunately it has no effect on the actual NodeVisualization and is just used within the BI configuration GUI

import {hierarchy as d3_hierarchy, select} from "d3";

import {LayoutManagerLayer} from "./layout";
import {
    LayoutStyleBlock,
    LayoutStyleHierarchy,
    LayoutStyleRadial,
} from "./layout_styles";
import type {
    AbstractLayoutStyle,
    StyleConfig,
    StyleOptionSpec,
    StyleOptionValues,
} from "./layout_utils";
import {compute_node_position, render_style_options} from "./layout_utils";
import type {
    d3SelectionDiv,
    d3SelectionG,
    d3SelectionSvg,
    NodeData,
    NodevisNode,
    NodevisWorld,
} from "./type_defs";
import {get_bounding_rect} from "./utils";

type _ExampleOptions = Record<string, number>;
interface ExampleOptions extends _ExampleOptions {
    total_nodes: number;
    depth: number;
}

export class LayoutStyleExampleGenerator {
    _varprefix: string;
    _viewport_width = 600;
    _viewport_height = 400;
    _example_generator_div: d3SelectionDiv;

    _style_choice_selection: d3SelectionDiv;
    _options_selection: d3SelectionDiv;
    _example_selection: d3SelectionDiv;
    _viewport_selection: d3SelectionSvg;

    _viewport_zoom: d3SelectionG;
    _viewport_zoom_links: d3SelectionG;
    _viewport_zoom_nodes: d3SelectionG;

    _example_options_spec: {
        total_nodes: StyleOptionSpec;
        depth: StyleOptionSpec;
    };
    _example_options: ExampleOptions;

    _style_config: StyleConfig;
    _style_hierarchy: NodevisNode;
    _style_instance: AbstractLayoutStyle | null = null;

    _fake_world: NodevisWorld;

    constructor(varprefix: string) {
        this._varprefix = varprefix;
        this._example_generator_div = select("#" + this._varprefix);
        const options = this._example_generator_div
            .append("div")
            .style("float", "left");

        this._style_choice_selection = options.append("div");
        this._options_selection = options
            .append("div")
            .style("margin-top", "12px");
        this._example_selection = options
            .append("div")
            .style("margin-top", "12px");
        this._viewport_selection = this._example_generator_div
            .append("svg")
            .attr("id", "viewport")
            .style("float", "left")
            .attr("width", this._viewport_width)
            .attr("height", this._viewport_height);
        this._example_options_spec = {
            total_nodes: {
                id: "total_nodes",
                option_type: "range",
                values: {default: 5, min: 1, max: 50},
                text: "Sample nodes",
            },
            depth: {
                id: "depth",
                option_type: "range",
                values: {default: 1, min: 1, max: 5},
                text: "Maximum depth",
            },
        };
        this._example_options = {
            total_nodes: 20,
            depth: 2,
        };

        this._style_instance = null;
        this._style_config = {
            type: "none",
            weight: 0,
            position: {x: 0, y: 0},
            options: {},
            matcher: {},
        };
        this._viewport_zoom = this._viewport_selection.append("g");
        this._viewport_zoom_links = this._viewport_zoom.append("g");
        this._viewport_zoom_nodes = this._viewport_zoom.append("g");
        this._viewport_selection
            .append("rect")
            .attr("stroke", "grey")
            .attr("fill", "none")
            .attr("x", 4)
            .attr("y", 4)
            .attr("width", this._viewport_width - 8)
            .attr("height", this._viewport_height - 8);

        this._style_hierarchy = this._create_example_hierarchy(
            this._example_options_spec,
            this._example_options,
        );
        this._fake_world = this._create_fake_world();
    }

    style_instance(): AbstractLayoutStyle {
        if (this._style_instance == null) throw "Missing style instance";
        return this._style_instance;
    }

    _create_fake_world(): NodevisWorld {
        //@ts-ignore
        const layout_manager = {
            get_node_positioning:
                LayoutManagerLayer.prototype.get_node_positioning,
            create_undo_step: () => null,
            update_style_indicators: () => null,
            layout_applier: {
                apply_all_layouts: () => null,
            },
        };
        return {
            layout_manager: layout_manager,
            force_simulation: {
                restart_with_alpha: () => null,
            },
            viewport: {
                update_layers: () => {
                    this._update_nodes();
                    this._render_nodes_and_links();
                },
                last_zoom: {
                    k: 1,
                },
                get_viewport_percentage_of_node: (node: NodevisNode) => {
                    return {
                        x: (100.0 * node.x) / 600,
                        y: (100.0 * node.y) / 400,
                    };
                },
                get_layout_manager: () => {
                    return layout_manager;
                },
                restart_force_simulation: () => null,
                get_size: () => {
                    return {width: 600, height: 400};
                },
            },
        } as unknown as NodevisWorld;
    }

    _update_viewport_visibility(): void {
        if (this._style_config.type == "none") {
            this._viewport_selection.attr("height", 0);
            this._example_selection.style("display", "none");
        } else {
            this._viewport_selection.attr("height", this._viewport_height);
            this._example_selection.style("display", null);
        }
    }

    create_example(style_settings: StyleConfig): void {
        this._style_config = style_settings;
        this._render_style_choice(this._style_choice_selection);
        this._update_viewport_visibility();
        this._style_hierarchy = this._create_example_hierarchy(
            this._example_options_spec,
            this._example_options,
        );

        let style_class: typeof AbstractLayoutStyle | null;
        switch (this._style_config.type) {
            case "none": {
                style_class = null;
                break;
            }
            case LayoutStyleHierarchy.prototype.class_name(): {
                style_class = LayoutStyleHierarchy;
                break;
            }
            case LayoutStyleRadial.prototype.class_name(): {
                style_class = LayoutStyleRadial;
                break;
            }
            case LayoutStyleBlock.prototype.class_name(): {
                style_class = LayoutStyleBlock;
                break;
            }
            default:
                style_class = null;
        }

        if (style_class == null) return;

        this._style_instance = new style_class(
            this._fake_world,
            this._style_config,
            this._style_hierarchy,
            //@ts-ignore
            this._viewport_selection,
        );
        this._style_instance.show_style_configuration = () => null;
        this._update_example();
    }

    _update_example(): void {
        this._update_nodes();
        this._render_nodes_and_links();
        this._render_example_settings(this._example_selection);

        if (this._style_instance)
            render_style_options(
                this._style_instance.type(),
                this._options_selection,
                this._style_instance.get_style_options(),
                this._style_instance.style_config.options,
                (new_options: StyleOptionValues) => {
                    if (this._style_instance)
                        this._style_instance.changed_options(new_options);
                },
                () => {
                    if (this._style_instance)
                        this._style_instance.reset_default_options();
                },
            );
    }

    _render_style_choice(style_choice_selection: d3SelectionDiv): void {
        const style_choices = [["none", "None"]];
        const use_styles = [
            LayoutStyleHierarchy,
            LayoutStyleRadial,
            LayoutStyleBlock,
        ];
        use_styles.forEach(style => {
            style_choices.push([
                style.prototype.class_name(),
                style.prototype.description(),
            ]);
        });

        style_choice_selection
            .selectAll("select")
            .data([null])
            .enter()
            .append("select")
            .attr("name", this._varprefix + "type")
            .on("change", event => this._changed_style(event))
            .selectAll("option")
            .data(style_choices)
            .enter()
            .append("option")
            .property("value", d => d[0])
            .property("selected", d => d[0] == this._style_config.type)
            .text(d => d[1]);
    }

    _changed_style(event: InputEvent): void {
        if (event.target == null) return;
        // @ts-ignore
        this._style_config.type = event.target.value;

        this._options_selection.selectAll("*").remove();
        this._viewport_selection.selectAll(".block_style_overlay").remove();
        if (this._style_config.type == "none") {
            this._style_instance = null;
            this._example_selection.selectAll("*").remove();
            this._update_viewport_visibility();
            return;
        }
        this.create_example(this._style_config);
    }

    _render_example_settings(div_selection: d3SelectionDiv): void {
        div_selection
            .selectAll("#headline")
            .data([null])
            .enter()
            .append("b")
            .attr("id", "headline")
            .text("Example settings");

        let table = div_selection
            .selectAll<HTMLTableElement, null>("table")
            .data([null]);
        table = table.enter().append("table").merge(table);

        const options: StyleOptionSpec[] = [];
        options.push(this._example_options_spec.total_nodes);
        if (this._style_config.type != LayoutStyleBlock.prototype.class_name())
            options.push(this._example_options_spec.depth);

        let rows = table
            .selectAll<HTMLTableRowElement, StyleOptionSpec>("tr")
            .data(options);
        rows.exit().remove();
        const rows_enter = rows
            .enter()
            .append("tr")
            .classed("range_input", true);
        rows_enter
            .append("td")
            .text(d => d.text)
            .classed("style_infotext", true);
        rows_enter
            .append("td")
            .classed("range_input slider", true)
            .append("input")
            .classed("range", true)
            .attr("id", d => d.id)
            .attr("type", "range")
            .attr("step", 1)
            .attr("min", d => d.values.min as number)
            .attr("max", d => d.values.max as number)
            .property("value", d => this._example_options[d.id])
            .on("input", (event, d) => {
                this._example_options[d.id] = parseInt(event.target.value);
                this._style_hierarchy = this._create_example_hierarchy(
                    this._example_options_spec,
                    this._example_options,
                );
                this.style_instance().style_root_node =
                    this._style_hierarchy.descendants()[0];
                this._update_example();
            });
        rows_enter.append("td").classed("text", true);
        rows = rows_enter.merge(rows);
        rows.select("td.text").text(d => {
            return div_selection.select("input#" + d.id).property("value");
        });
    }

    _update_nodes(): void {
        this.style_instance().style_root_node.x = 0;
        this.style_instance().style_root_node.y = 0;
        this.style_instance().update_data();
        this.style_instance().translate_coords();
        this._style_hierarchy.descendants().forEach(node => {
            compute_node_position(node);
        });
        this._center_hierarchy_nodes(this._style_hierarchy);
    }

    _render_nodes_and_links(no_transition = false): void {
        this.style_instance().generate_overlay();
        this._paint_links(this._style_hierarchy, no_transition);
        this._paint_nodes(this._style_hierarchy, no_transition);
    }

    _center_hierarchy_nodes(hierarchy: NodevisNode): void {
        const nodes = hierarchy.descendants();
        const width = parseInt(this._viewport_selection.attr("width")) - 30;
        const height = parseInt(this._viewport_selection.attr("height")) - 30;
        const bounding_rect = get_bounding_rect(nodes);

        const width_ratio = bounding_rect.width / width;
        const height_ratio = bounding_rect.height / height;
        const ratio = Math.max(1, Math.max(width_ratio, height_ratio));

        const x_offset = (width - bounding_rect.width) / 2;
        const y_offset = (height - bounding_rect.height) / 2;

        nodes.forEach(node => {
            node.x += x_offset - bounding_rect.x_min + 15;
            node.y += y_offset - bounding_rect.y_min + 15;
        });

        if (ratio > 1) {
            const rect_x = -(width - width * ratio) / 2;
            const rect_y = -(height - height * ratio) / 2;
            this._viewport_zoom.attr(
                "transform",
                "scale(" +
                    1 / ratio +
                    ") translate(" +
                    rect_x +
                    "," +
                    rect_y +
                    ")",
            );
            let default_scale = this._viewport_selection
                .selectAll<SVGTextElement, null>("text")
                .data([null]);
            default_scale = default_scale
                .enter()
                .append("text")
                .text("Default scale")
                .merge(default_scale);
            default_scale
                .attr("x", 10)
                .attr("y", 20)
                .text("Scale 1:" + ratio.toFixed(2));
        } else {
            this._viewport_zoom.attr("transform", null);
            this._viewport_selection.selectAll("text").remove();
        }
    }

    _create_example_hierarchy(
        _example_settings: {
            [name: string]: StyleOptionSpec;
        },
        example_options: StyleOptionValues,
    ): NodevisNode {
        let id_counter = 0;

        const maximum_nodes = example_options.total_nodes;
        let generated_nodes = 0;

        function _add_hierarchy_children(
            parent_node: NodeData,
            cancel_delta: number,
            cancel_chance: number,
        ) {
            parent_node.children = [];
            for (;;) {
                if (
                    // 2365: Operator '>=' cannot be applied to types 'number'
                    // and 'number | boolean'.
                    // @ts-ignore
                    generated_nodes >= maximum_nodes ||
                    (cancel_chance < 1 && cancel_chance - Math.random() <= 0)
                ) {
                    if (parent_node.children.length == 0)
                        delete parent_node.children;
                    break;
                }
                const new_child = {name: "child"} as NodeData;
                generated_nodes += 1;
                _add_hierarchy_children(
                    new_child,
                    cancel_delta,
                    cancel_chance - cancel_delta,
                );
                parent_node.children.push(new_child);
            }
        }

        const hierarchy_raw: NodeData = {
            name: "Root node",
            children: [],
        } as unknown as NodeData;
        let cancel_delta = 1 / (example_options.depth as number);
        // Maximum depth of block style is 1
        if (this._style_config.type == LayoutStyleBlock.prototype.class_name())
            cancel_delta = 1;

        _add_hierarchy_children(hierarchy_raw, cancel_delta, 1);

        const hierarchy = d3_hierarchy<NodeData>(hierarchy_raw) as NodevisNode;
        hierarchy.descendants().forEach(node => {
            node.x = 50;
            node.y = 50;
            id_counter += 1;
            node.data.id = id_counter.toString();
            node.data.hostname = "Demohost";
            node.data.transition_info = {};
        });
        return hierarchy;
    }

    _paint_nodes(hierarchy: NodevisNode, no_transition: boolean): void {
        let nodes = this._viewport_zoom_nodes
            .selectAll<SVGCircleElement, NodevisNode>(".node.alive")
            .data<NodevisNode>(hierarchy.descendants());
        nodes
            .exit()
            .classed("alive", false)
            .transition()
            .duration(500)
            .attr("opacity", 0)
            .remove();

        nodes = nodes
            .enter()
            .append("circle")
            .classed("node", true)
            .classed("alive", true)
            .attr("fill", "#13d389")
            .attr("r", d => (d.parent ? 6 : 12))
            .attr("cx", () => this._viewport_width / 2)
            .attr("cy", () => this._viewport_height / 2)
            .attr("opacity", 1)
            .merge(nodes);

        if (no_transition) nodes.attr("cx", d => d.x).attr("cy", d => d.y);
        else
            nodes
                .transition()
                .duration(500)
                .attr("cx", d => d.x)
                .attr("cy", d => d.y);
    }

    _paint_links(hierarchy: NodevisNode, no_transition: boolean): void {
        let links = this._viewport_zoom_links
            .selectAll<SVGPathElement, NodevisNode>(".link.alive")
            .data<NodevisNode>(
                hierarchy.descendants().filter(d => {
                    return !d.data.current_positioning.hide_node_link;
                }),
            );
        links
            .exit()
            .classed("alive", false)
            .transition()
            .duration(500)
            .attr("opacity", 0)
            .remove();

        links = links
            .enter()
            .append("path")
            .classed("link", true)
            .classed("alive", true)
            .attr("stroke-width", 2)
            .attr("fill", "none")
            .attr("stroke-width", 2)
            .style("stroke", "grey")
            .attr("opacity", 0)
            .attr("d", d => this.diagonal(d, d.parent))
            .merge(links);

        if (no_transition)
            links.attr("d", d => this.diagonal(d, d.parent)).attr("opacity", 1);
        else
            links
                .transition()
                .duration(500)
                .attr("d", d => this.diagonal(d, d.parent))
                .attr("opacity", 1);
    }

    diagonal(source: NodevisNode, target: NodevisNode | null): string {
        if (!target) return "";
        const s = {
            y: source.x,
            x: source.y,
        };
        const d = {
            y: target.x,
            x: target.y,
        };
        return `M ${s.y} ${s.x}
                C ${(s.y + d.y) / 2} ${s.x},
                  ${(s.y + d.y) / 2} ${d.x},
                  ${d.y} ${d.x}`;
    }
}
