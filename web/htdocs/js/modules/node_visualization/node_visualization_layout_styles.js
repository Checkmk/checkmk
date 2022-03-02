// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

import * as d3 from "d3";

import * as node_visualization_layouting_utils from "node_visualization_layouting_utils";
import * as node_visualization_layout from "node_visualization_layout";
import * as node_visualization_utils from "node_visualization_utils";

import * as node_visualization_layouting from "node_visualization_layouting";
import * as node_visualization_viewport from "node_visualization_viewport";

import * as d3_flextree from "d3-flextree";

export class AbstractLayoutStyle {
    constructor(layout_manager, style_config, node, selection) {
        this._layout_manager = layout_manager;
        // Contains all configurable options for this style
        this.style_config = style_config;
        // The selection for the styles graphical overlays
        this.selection = selection;

        // Root node for this style
        this.style_root_node = node;
        if (this.style_root_node) {
            // Chunk this root node resides in
            if (this.style_config.position) {
                let coords = this.style_root_node.data.chunk.coords;
                this.style_root_node.x = (style_config.position.x / 100) * coords.width + coords.x;
                this.style_root_node.y = (style_config.position.y / 100) * coords.height + coords.y;
            }
        }

        // Apply missing default values to options
        this._initialize_style_config();

        // Default options lookup
        this._default_options = {};
        let style_options = this.get_style_options();
        style_options.forEach(option => {
            this._default_options[option.id] = option.values.default;
        });

        // If set, suppresses translationn of style_node offsets
        this._style_translated = false;

        // Coords [x,y] for each node in this style
        this._vertices = [];
    }

    _initialize_style_config() {
        if (this.style_config.options == null) {
            this.style_config.options = {};
        }

        // options
        this.get_style_options().forEach(option => {
            if (this.style_config.options[option.id] == null)
                this.style_config.options[option.id] = option.values.default;
        });

        // matcher
        let matcher = this.get_matcher();
        if (matcher) this.style_config.matcher = matcher;

        // position
        if (this.style_root_node && !this.style_config.position)
            this.style_config.position = this._layout_manager.get_viewport_percentage_of_node(
                this.style_root_node
            );
    }

    id() {
        return this.compute_id(this.style_root_node);
    }

    compute_id(node) {
        return this.type() + "_" + node.data.id;
    }

    get_style_options() {
        return [];
    }

    render_options(into_selection, varprefix = "") {
        this.options_selection = into_selection;
        this._update_options_in_input_field(varprefix);
    }

    generate_overlay() {}

    _update_options_in_input_field(varprefix = "") {
        if (!this.options_selection) return;

        let style_options = this.get_style_options();
        if (style_options.length == 0) return;

        this.options_selection
            .selectAll("#styleoptions_headline")
            .data([null])
            .enter()
            .append("b")
            .attr("id", "styleoptions_headline")
            .text("Options");

        let table = this.options_selection.selectAll("table").data([null]);
        table = table.enter().append("table").merge(table);

        this._render_range_options(table, style_options, varprefix);
        this._render_checkbox_options(table, style_options, varprefix);

        this.options_selection
            .selectAll("input.reset_options")
            .data([null])
            .enter()
            .append("input")
            .attr("type", "button")
            .classed("button", true)
            .classed("reset_options", true)
            .attr("value", "Reset default values")
            .on("click", () => {
                this.reset_default_options();
            });
        this.options_selection
            .selectAll("div.clear_float")
            .data([null])
            .enter()
            .append("div")
            .classed("clear_float", true)
            .style("clear", "right");
    }

    _render_range_options(table, style_options, varprefix) {
        let rows = table
            .selectAll("tr.range_option")
            .data(style_options.filter(d => d.option_type == "range"));
        rows.exit().remove();
        let rows_enter = rows.enter().append("tr").classed("range_option", true);
        rows_enter
            .append("td")
            .text(d => d.text)
            .classed("style_infotext", true);
        rows_enter
            .append("td")
            .append("input")
            .classed("range", true)
            .attr("id", d => d.id)
            .attr("name", d => varprefix + "_type_value_" + d.id)
            .attr("type", "range")
            .attr("step", 1)
            .attr("min", d => d.values.min)
            .attr("max", d => d.values.max)
            .on("input", () => {
                this._layout_manager.dragging = true;
                this.option_changed_in_input_field();
                this.changed_options();
            })
            .on("change", () => {
                this._layout_manager.dragging = false;
                this._layout_manager.create_undo_step();
            });
        rows_enter.append("td").classed("text", true);
        rows = rows_enter.merge(rows);

        rows.select("td input.range").property("value", d => d.value);
        rows.select("td.text").text(d => d.value);
    }

    _render_checkbox_options(table, style_options, varprefix) {
        let rows = table
            .selectAll("tr.checkbox_option")
            .data(style_options.filter(d => d.option_type == "checkbox"));

        // TODO: fixme: style options handle is lost...
        rows.exit().remove();

        let rows_enter = rows.enter().append("tr").classed("checkbox_option", true);
        rows_enter
            .append("td")
            .text(d => d.text)
            .classed("style_infotext", true);
        rows_enter
            .append("td")
            .append("input")
            .classed("checkbox", true)
            .attr("id", d => d.id)
            .attr("name", d => varprefix + "_type_checkbox_" + d.id)
            .attr("type", "checkbox")
            .property("checked", d => d.value)
            .on("input", () => {
                this.option_changed_in_input_field();
                this.changed_options();
            });
        rows_enter.append("td").classed("text", true);
    }

    reset_default_options() {
        let style_options = this.get_style_options();
        for (let idx in style_options) {
            let option = style_options[idx];
            this.style_config.options[option.id] = option.values.default;
        }
        this.changed_options();
    }

    option_changed_in_input_field() {
        let style_options = this.get_style_options();
        let reapply_layouts = false;
        for (let idx in style_options) {
            let option = style_options[idx];
            if (option.option_type == "range")
                this.style_config.options[option.id] = +this.options_selection
                    .select("#" + option.id)
                    .property("value");
            else if (option.option_type == "checkbox") {
                this.style_config.options[option.id] = +this.options_selection
                    .select("#" + option.id)
                    .property("checked");
                if (
                    option.id == "box_leaf_nodes" &&
                    +this.options_selection.select("#" + option.id).property("value") !=
                        this.style_config.options[option.id]
                )
                    reapply_layouts = true;
            }
        }

        if (reapply_layouts) {
            node_visualization_utils.log(7, "Changed style option forced reapply layout");
            this._layout_manager.layout_applier.apply_all_layouts();
            this._layout_manager.update_style_indicators();
        }
    }

    changed_options(option_id) {
        this._update_options_in_input_field();
        this.force_style_translation();

        this._layout_manager.compute_node_positions_from_list_of_nodes(
            this.style_root_node.descendants()
        );

        force_simulation.restart_with_alpha(0.5);
        this._layout_manager.viewport.update_layers();
    }

    get_size() {
        let vertices = [];
        this._style_root_node_offsets.forEach(offset =>
            vertices.push({x: offset[1], y: offset[2]})
        );
        let bounding_rect = node_visualization_utils.get_bounding_rect(vertices);
        return [bounding_rect.width * 1.1 + 100, bounding_rect.height * 1.1 + 100];
    }

    get_rotation() {
        let rotation = this.style_config.options.rotation;
        if (rotation == undefined) return 0;
        if (this.style_config.options.include_parent_rotation == true) {
            let style_parent = this._find_parent_with_style(this.style_root_node);
            if (style_parent) rotation += style_parent.data.use_style.get_rotation();
        }
        return rotation;
    }

    _find_parent_with_style(node) {
        if (!node.parent) return;
        if (node.parent.data.use_style) return node.parent;
        else return this._find_parent_with_style(node.parent);
    }

    style_color() {}

    type() {}

    description() {}

    set_matcher(matcher) {
        this.style_config.matcher = matcher;
    }

    get_matcher() {
        let matcher_conditions = {};

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
                matcher_conditions.rule_id = {value: this.style_root_node.data.rule_id.rule};
                matcher_conditions.rule_name = {value: this.style_root_node.data.name};
            } else {
                // End node: Match by hostname or service
                matcher_conditions.hostname = {value: this.style_root_node.data.hostname};
                matcher_conditions.service = {value: this.style_root_node.data.service};
            }
        } else {
            // Generic node
            matcher_conditions.hostname = {value: this.style_root_node.data.hostname};
        }

        // Override default options with user customized settings.
        // May disable match types and modify match texts
        for (let idx in this.style_config.matcher) {
            matcher_conditions[idx] = this.style_config.matcher[idx];
        }
        return matcher_conditions;
    }

    get_aggregation_path(node) {
        let path = [];
        if (node.parent) path = path.concat(this.get_aggregation_path(node.parent));
        if (node.data.aggr_path) path.push(node.data.aggr_path);
        return path;
    }

    update_style_indicator(indicator_shown = true) {
        let style_indicator = this.style_root_node.selection
            .selectAll("circle.style_indicator")
            .data([this]);

        node_visualization_utils.log(
            "Update style indicator for " + this.type() + " " + this.style_root_node.data.name
        );
        if (!indicator_shown) {
            style_indicator.remove();
            return;
        }

        style_indicator
            .enter()
            .insert("circle", "#outer_circle")
            .classed("style_indicator", true)
            .attr("pointer-events", "none")
            .attr("r", 30)
            .attr("fill", d => d.style_color());
    }

    // positioning_weight of the layout positioning
    // If multiple positioning forces are applied to one node, the one with the highest positioning_weight wins
    positioning_weight() {
        return 0;
    }

    force_style_translation() {
        node_visualization_utils.log(7, "force style translation of", this.id());
        this._style_translated = false;
    }

    has_fixed_position() {
        let ancestors = this.style_root_node.ancestors();
        for (let idx in ancestors) {
            let node = ancestors[idx];
            if (!node.data.use_style) continue;
            let style_options = node.data.use_style.style_config.options;
            if (style_options.detach_from_parent) return true;
            if (!node.parent && (!node.data.use_style || node.data.use_style.type() == "force"))
                return false;
        }
        return true;
    }

    zoomed() {}

    update_data() {}

    update_gui() {}

    fix_node(node) {
        let force = this.get_default_node_force(node);
        force.fx = node.x;
        force.fy = node.y;
        force.use_transition = true;
    }

    get_default_node_force(node) {
        return (this._layout_manager.get_node_positioning(node)[this.id()] = {
            weight: this.positioning_weight(),
            type: this.type(),
        });
    }

    // Computes offsets use for node translate
    _compute_node_offsets() {}

    // Translates the nodes by the computed offsets
    translate_coords() {}

    remove() {
        delete this.style_root_node.data.node_positioning[this.id()];
        // TODO: might get added/removed on the same call..
        this.get_div_selection().remove();
        this.update_style_indicator(false);
    }

    add_option_icons(coords, elements) {
        for (let idx in elements) {
            let element = elements[idx];
            let img = this.get_div_selection()
                .selectAll("img." + element.type)
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
                .style("left", coords.x + idx * (30 + 12) + "px")
                .merge(img);

            let offset = parseInt(img.style("width"), 10);
            img.style("top", d => coords.y - 62 + "px").style(
                "left",
                d => coords.x + idx * (offset + 12) + "px"
            );
        }
    }

    get_div_selection() {
        let div_selection = this._layout_manager.div_selection
            .selectAll("div.hierarchy")
            .data([this.id()]);
        return div_selection.enter().append("div").classed("hierarchy", true).merge(div_selection);
    }

    add_enclosing_hull(into_selection, vertices) {
        if (vertices.length < 2) {
            into_selection.selectAll("path.style_overlay").remove();
            return;
        }

        let boundary = 30;
        let hull_vertices = [];
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
}

//#.
//#   .-Force--------------------------------------------------------------.
//#   |                       _____                                        |
//#   |                      |  ___|__  _ __ ___ ___                       |
//#   |                      | |_ / _ \| '__/ __/ _ \                      |
//#   |                      |  _| (_) | | | (_|  __/                      |
//#   |                      |_|  \___/|_|  \___\___|                      |
//#   |                                                                    |
//#   +--------------------------------------------------------------------+

class ForceSimulation {
    constructor() {
        this._simulation = d3.forceSimulation();
        this._simulation.alpha(0);
        this._simulation.alphaMin(0.1);
        this._simulation.on("tick", () => this.tick_called());
        this._simulation.on("end", () => this._simulation_end());
        this._last_gui_update_duration = 0;
        this._setup_forces();
        this._all_nodes = {};
        this._all_links = {};
        this._viewport = null;
    }

    register_viewport(viewport) {
        this._viewport = viewport;
    }

    tick_called() {
        if (!this._viewport) return;

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

    _simulation_end() {
        if (!this._viewport) return;
        this._update_gui();
    }

    _update_gui() {
        let update_start = window.performance.now();
        this._enforce_free_float_styles_retranslation();
        this._viewport.layout_manager.compute_node_positions_from_list_of_nodes(
            this._get_force_nodes()
        );
        this._viewport.update_gui_of_layers();
        return window.performance.now() - update_start;
    }

    _get_force_nodes() {
        let force_nodes = [];
        this._viewport.get_hierarchy_list().forEach(chunk => {
            chunk.nodes.forEach(node => {
                if (node.data.current_positioning.free) force_nodes.push(node);
            });
        });
        return force_nodes;
    }

    _enforce_free_float_styles_retranslation() {
        for (let idx in this._viewport.layout_manager._active_styles) {
            let style = this._viewport.layout_manager._active_styles[idx];
            if (!style.has_fixed_position() && style.type() != LayoutStyleForce.prototype.type()) {
                node_visualization_utils.log(6, "tick: enforce style translation ", style.type());
                style.force_style_translation();
                style.translate_coords();
                this._viewport.layout_manager.compute_node_positions_from_list_of_nodes(
                    style.filtered_descendants
                );
                style.filtered_descendants.forEach(node => (node.use_transition = false));
            }
        }
    }

    _setup_forces() {
        this._update_charge_force();
        this._update_collision_force();
        this._update_center_force();
        this._update_link_force();
    }

    _update_charge_force() {
        let charge_force = d3
            .forceManyBody()
            .strength(d => {
                let explicit_force = this._get_explicit_force_option(d.data, "repulsion");
                if (explicit_force != null) return explicit_force;
                else if (d._children) return d.data.force_options.force_aggregator;
                else return d.data.force_options.force_node;
            })
            .distanceMax(800);
        this._simulation.force("charge_force", charge_force);
    }

    _update_collision_force() {
        let collide_force = d3.forceCollide(d => {
            if (d.data.collision_force != null) {
                return d.data.collision_force;
            }
            if (d._children) return d.data.force_options.collision_force_aggregator;
            else return d.data.force_options.collision_force_node;
        });
        this._simulation.force("collide", collide_force);
    }

    _update_center_force() {
        let forceX = d3
            .forceX(d => {
                return d.data.chunk.coords.x + d.data.chunk.coords.width / 2;
            })
            .strength(d => {
                let explicit_force = this._get_explicit_force_option(d.data, "center_force");
                if (explicit_force != null) return explicit_force / 100;

                if (d.parent != null) return d.data.force_options.center_force / 300;
                return d.data.force_options.center_force / 100;
            });

        let forceY = d3
            .forceY(d => {
                return d.data.chunk.coords.y + d.data.chunk.coords.height / 2;
            })
            .strength(d => {
                let explicit_force = this._get_explicit_force_option(d.data, "center_force");
                if (explicit_force != null) return explicit_force / 100;
                if (d.parent != null) return d.data.force_options.center_force / 300;
                return d.data.force_options.center_force / 100;
            });
        this._simulation.force("x", forceX);
        this._simulation.force("y", forceY);

        this._simulation.force("charge_force").distanceMax(800);
    }

    _update_link_force() {
        let link_force = d3
            .forceLink(this._all_links)
            .id(function (d) {
                return d.data.id;
            })
            .distance(d => {
                let explicit_force = this._get_explicit_force_option(
                    d.source.data,
                    "link_distance"
                );
                if (explicit_force != null) return explicit_force;

                if (d.source._children) return d.source.data.force_options.link_force_aggregator;
                else return d.source.data.force_options.link_force_node;
            })
            .strength(d => d.source.data.force_options.link_strength / 100);
        this._simulation.force("links", link_force);
    }

    _get_explicit_force_option(data, force_name) {
        if (data.explicit_force_options && data.explicit_force_options[force_name]) {
            return data.explicit_force_options[force_name];
        }
        return null;
    }

    update_nodes_and_links(all_nodes, all_links) {
        this._all_nodes = all_nodes;
        this._all_links = all_links;
        this._simulation.nodes(this._all_nodes);
        this._setup_forces();
    }

    restart_with_alpha(alpha) {
        if (this._simulation.alpha() < 0.12) this._simulation.restart();
        this._simulation.alpha(alpha);
    }
}

export let force_simulation = new ForceSimulation();

export class LayoutStyleForce extends AbstractLayoutStyle {
    type() {
        return "force";
    }

    description() {
        return "Free-Floating style";
    }

    style_color() {
        return "#9c9c9c";
    }

    compute_id(node) {
        return this.type() + "_" + node.data.id;
    }

    id() {
        return this.compute_id(this.style_root_node);
    }

    constructor(layout_manager, style_config, node, selection) {
        super(layout_manager, style_config, node, selection);
    }

    force_style_translation() {
        force_simulation._setup_forces();
    }

    get_style_options() {
        return [
            {
                id: "center_force",
                values: {default: 5, min: -20, max: 100},
                option_type: "range",
                text: "Center force strength",
                value: this.style_config.options.center_force,
            },
            //                {id: "maxdistance", values: {default: 800, min: 10, max: 2000}, option_type:"range",
            //                 text: "Max force distance", value: this.style_config.options.maxdistance},
            {
                id: "force_node",
                values: {default: -300, min: -1000, max: 50},
                option_type: "range",
                text: "Repulsion force leaf",
                value: this.style_config.options.force_node,
            },
            {
                id: "force_aggregator",
                values: {default: -300, min: -1000, max: 50},
                option_type: "range",
                text: "Repulsion force branch",
                value: this.style_config.options.force_aggregator,
            },
            {
                id: "link_force_node",
                values: {default: 30, min: -10, max: 300},
                option_type: "range",
                text: "Link distance leaf",
                value: this.style_config.options.link_force_node,
            },
            {
                id: "link_force_aggregator",
                values: {default: 30, min: -10, max: 300},
                option_type: "range",
                text: "Link distance branches",
                value: this.style_config.options.link_force_aggregator,
            },
            {
                id: "link_strength",
                values: {default: 30, min: 0, max: 200},
                option_type: "range",
                text: "Link strength",
                value: this.style_config.options.link_strength,
            },
            {
                id: "collision_force_node",
                values: {default: 15, min: 0, max: 150},
                option_type: "range",
                text: "Collision box leaf",
                value: this.style_config.options.collision_force_node,
            },
            {
                id: "collision_force_aggregator",
                values: {default: 15, min: 0, max: 150},
                option_type: "range",
                text: "Collision box branch",
                value: this.style_config.options.collision_force_aggregator,
            },
        ];
    }
}

//#.
//#   .-Hierarchy----------------------------------------------------------.
//#   |             _   _ _                         _                      |
//#   |            | | | (_) ___ _ __ __ _ _ __ ___| |__  _   _            |
//#   |            | |_| | |/ _ \ '__/ _` | '__/ __| '_ \| | | |           |
//#   |            |  _  | |  __/ | | (_| | | | (__| | | | |_| |           |
//#   |            |_| |_|_|\___|_|  \__,_|_|  \___|_| |_|\__, |           |
//#   |                                                   |___/            |
//#   +--------------------------------------------------------------------+

export class LayoutStyleHierarchyBase extends AbstractLayoutStyle {
    positioning_weight() {
        return 10 + parseInt(this.style_root_node.depth);
    }

    remove() {
        this.get_div_selection().remove();
        AbstractLayoutStyle.prototype.remove.call(this);
        this._cleanup_style_node_positioning();
    }

    _cleanup_style_node_positioning() {
        if (this.style_root_node) {
            this.style_root_node.descendants().forEach(node => {
                if (node.data.node_positioning) delete node.data.node_positioning[this.id()];
            });
        }
    }

    update_data() {
        this.selection.attr("transform", this._layout_manager.viewport.last_zoom);
        this.use_transition = true;

        this._cleanup_style_node_positioning();

        // Remove nodes not belonging to this style
        this._set_hierarchy_filter(this.style_root_node, true);
        this.filtered_descendants = this.style_root_node.descendants();

        // Determine max_depth, used by text positioning
        this.max_depth = 1;
        this.filtered_descendants.forEach(node => {
            this.max_depth = Math.max(this.max_depth, node.depth);
        });

        // Save old coords
        let old_coords = {};
        this.filtered_descendants.forEach(node => {
            old_coords[node.data.id] = {x: node.x, y: node.y};
        });

        // Layout type specific computation
        this._compute_node_offsets();
        this.force_style_translation();

        this._reset_hierarchy_filter(this.style_root_node);

        // Reapply old coords
        this.filtered_descendants.forEach(node => {
            node.x = old_coords[node.data.id].x;
            node.y = old_coords[node.data.id].y;
        });
    }

    // Removes nodes (and their childs) with other explicit styles set
    // A style starts at the root node and ends
    // - At a leaf
    // - At a child node with another explicit style set.
    //    The child node with the style is also included for positioning computing, unless its detached from the parent
    _set_hierarchy_filter(node, first_node = false) {
        if (
            (!first_node && node.parent.data.use_style && node.parent != this.style_root_node) ||
            (!first_node &&
                node.data.use_style &&
                node.data.use_style.style_config.options.detach_from_parent)
        )
            return [];

        if (node.children) {
            node.children_backup = node.children;
            node.children = [];
            for (let idx in node.children_backup) {
                let child_node = node.children_backup[idx];
                node.children = node.children.concat(this._set_hierarchy_filter(child_node));
            }
            if (node.children.length == 0) delete node.children;
        }
        return [node];
    }

    _reset_hierarchy_filter(node) {
        if (!node.children_backup) return;

        for (let idx in node.children_backup)
            this._reset_hierarchy_filter(node.children_backup[idx]);

        node.children = node.children_backup;
        delete node.children_backup;
    }

    zoomed() {
        this.selection.attr("transform", this._layout_manager.viewport.last_zoom);
        // Update style overlays which depend on zoom
        this.generate_overlay();
    }

    get_drag_callback(drag_function) {
        return d3
            .drag()
            .on("start.drag", event => this._drag_start(event))
            .on("drag.drag", event => this._drag_drag(event, drag_function))
            .on("end.drag", event => this._drag_end(event));
    }

    _drag_start(event) {
        this.drag_start_info = {};
        this.drag_start_info.start_coords = [event.x, event.y];
        this.drag_start_info.delta = {x: 0, y: 0};
        this.drag_start_info.options = JSON.parse(JSON.stringify(this.style_config.options));
        this._layout_manager.toolbar_plugin.layout_style_configuration.show_style_configuration(
            this
        );
        this._layout_manager.dragging = true;
    }

    _drag_drag(event, drag_function) {
        this.drag_start_info.delta.x += event.dx;
        this.drag_start_info.delta.y += event.dy;
        drag_function(event);
        this.changed_options();
    }

    _drag_end(event) {
        this._layout_manager.dragging = false;
        this._layout_manager.create_undo_step();
    }

    change_rotation() {
        let rotation = (this.drag_start_info.options.rotation - this.drag_start_info.delta.y) % 360;
        if (rotation < 0) rotation += 360;
        this.style_config.options.rotation = parseInt(rotation);
        this.force_style_translation();
    }

    add_optional_transition(selection_with_node_data) {
        if (!this._layout_manager.dragging) {
            return selection_with_node_data
                .transition()
                .duration(node_visualization_utils.DefaultTransition.duration());
        }
        return selection_with_node_data;
    }
}

export class LayoutStyleHierarchy extends LayoutStyleHierarchyBase {
    constructor(layout_manager, style_config, node, selection) {
        super(layout_manager, style_config, node, selection);
    }

    type() {
        return "hierarchy";
    }

    description() {
        return "Hierarchical style";
    }

    style_color() {
        return "#ffa042";
    }

    get_style_options() {
        return [
            {
                id: "layer_height",
                values: {default: 80, min: 20, max: 500},
                text: "Layer height",
                value: this.style_config.options.layer_height,
                option_type: "range",
            },
            {
                id: "node_size",
                values: {default: 25, min: 15, max: 100},
                text: "Node size",
                value: this.style_config.options.node_size,
                option_type: "range",
            },
            {
                id: "rotation",
                values: {default: 270, min: 0, max: 359},
                text: "Rotation",
                value: this.style_config.options.rotation,
                option_type: "range",
            },
            {
                id: "include_parent_rotation",
                option_type: "checkbox",
                values: {default: false},
                text: "Include parent rotation",
                value: this.style_config.options.include_parent_rotation,
            },
            {
                id: "detach_from_parent",
                option_type: "checkbox",
                values: {default: false},
                text: "Detach from parent style",
                value: this.style_config.options.detach_from_parent,
            },
            {
                id: "box_leaf_nodes",
                option_type: "checkbox",
                values: {default: false},
                text: "Arrange leaf nodes in block",
                value: this.style_config.options.box_leaf_nodes,
            },
        ];
    }

    _compute_node_offsets() {
        let coords = this.get_hierarchy_size();

        let rad = (this.get_rotation() / 180) * Math.PI;
        let cos_x = Math.cos(rad);
        let sin_x = Math.sin(rad);

        d3_flextree.flextree().nodeSize(node => {
            if (node.data.use_style && node != this.style_root_node) {
                // TODO: improve
                if (node.data.use_style.type() == "block") {
                    return node.data.use_style.get_size();
                }

                if (node.data.use_style.style_config.options.include_parent_rotation) {
                    let rad = (node.data.use_style.style_config.options.rotation / 180) * Math.PI;
                    let bounding_rect = {height: 10, width: 10};
                    if (node.data.use_style._no_rotation_vertices)
                        bounding_rect =
                            node_visualization_utils.get_bounding_rect_of_rotated_vertices(
                                node.data.use_style._no_rotation_vertices,
                                rad
                            );
                    return [bounding_rect.height * 1.1 + 100, bounding_rect.width * 1.1 + 100];
                }

                let node_rad = (node.data.use_style.style_config.options.rotation / 180) * Math.PI;
                node_rad = node_rad + Math.PI - rad;

                let bounding_rect = {height: 10, width: 10};
                if (node.data.use_style._no_rotation_vertices)
                    bounding_rect = node_visualization_utils.get_bounding_rect_of_rotated_vertices(
                        node.data.use_style._no_rotation_vertices,
                        node_rad
                    );

                let extra_width = 0;
                if (node.data.use_style.type() == "hierarchy")
                    extra_width = Math.abs(bounding_rect.height * Math.sin(node_rad)) * 0.5;
                return [
                    extra_width + bounding_rect.height * 1.1 + 100,
                    bounding_rect.width * 1.1 + 100,
                ];
            }
            return [this.style_config.options.node_size, this.style_config.options.layer_height];
        })(this.style_root_node);

        this._style_root_node_offsets = [];
        this._no_rotation_vertices = [];
        for (let idx in this.filtered_descendants) {
            let node = this.filtered_descendants[idx];
            this._no_rotation_vertices.push({y: node.x, x: node.y});
            let x = node.x * sin_x + node.y * cos_x;
            let y = node.x * cos_x - node.y * sin_x;
            this._style_root_node_offsets.push([node, x, y]);
        }
    }

    translate_coords() {
        let nodes = this.filtered_descendants;
        let coords = this.get_hierarchy_size();

        if (this._style_translated && this.has_fixed_position()) return;

        let rad = (this.get_rotation() / 180) * Math.PI;
        let text_positioning = this.get_text_positioning(rad);

        this._vertices = [];
        this._vertices.push([this.style_root_node.x, this.style_root_node.y]);

        let sub_nodes_with_explicit_style = [];
        for (let idx in this._style_root_node_offsets) {
            let entry = this._style_root_node_offsets[idx];
            let node = entry[0];
            let x = entry[1];
            let y = entry[2];

            if (
                (node == this.style_root_node && this.style_config.options.detach_from_parent) ||
                node != this.style_root_node ||
                !this.style_root_node.parent
            ) {
                let force = this.get_default_node_force(node);
                force.fx = this.style_root_node.x + x;
                force.fy = this.style_root_node.y + y;
                force.text_positioning = text_positioning;
                force.use_transition = this.use_transition;
                this._vertices.push([force.fx, force.fy]);
            }

            if (node != this.style_root_node && node.data.use_style) {
                sub_nodes_with_explicit_style.push(node);
            }
        }

        // Retranslate styles which's position got shifted
        sub_nodes_with_explicit_style.forEach(node => {
            node_visualization_utils.log(
                7,
                "retranslate style " + node.data.use_style.type() + " of subnode " + node.data.name
            );
            this._layout_manager.compute_node_position(node);
            node.data.use_style.force_style_translation();
            node.data.use_style.translate_coords();
            this._layout_manager.compute_node_positions_from_list_of_nodes(
                node.data.use_style.filtered_descendants
            );
        });

        this.generate_overlay();

        this._style_translated = true;
        this.use_transition = false;
    }

    generate_overlay() {
        if (!this._layout_manager.edit_layout) return;

        this.add_enclosing_hull(this.selection, this._vertices);
        let elements = [
            {
                node: this.style_root_node,
                type: "scale",
                image: "themes/facelift/images/icon_resize.png",
                call: this.get_drag_callback(event => this.resize_layer_drag(event)),
            },
            {
                node: this.style_root_node,
                type: "rotation",
                image: "themes/facelift/images/icon_rotate_left.png",
                call: this.get_drag_callback(() => this.change_rotation()),
            },
        ];
        let coords = this._layout_manager.viewport.translate_to_zoom({
            x: this.style_root_node.x,
            y: this.style_root_node.y,
        });
        this.add_option_icons(coords, elements);
    }

    get_text_positioning(rad) {
        rad = rad / 2;
        if (rad > (3 / 4) * Math.PI) rad = rad - Math.PI;

        let rotate = (-rad / Math.PI) * 180;

        let anchor_options = ["start", "end"];
        let boundary = (9 / 32) * Math.PI;

        let left_side = rad > boundary && rad < Math.PI - boundary;

        let distance = 21;
        let x = Math.cos(-rad * 2) * distance;
        let y = Math.sin(-rad * 2) * distance;

        if (rad > Math.PI - boundary) {
            rotate += 180;
        } else if (left_side) {
            rotate += 90;
            anchor_options = ["end", "start"];
        }

        let text_anchor = anchor_options[0];
        let transform_text = "translate(" + x + "," + y + ") rotate(" + rotate + ")";
        return selection => {
            selection.attr("transform", transform_text).attr("text-anchor", text_anchor);
        };
    }

    resize_layer_drag(event) {
        let rotation_rad = (this.style_config.options.rotation / 180) * Math.PI;
        let coords = d3.pointer(event);
        let offset_y = this.drag_start_info.start_coords[0] - coords[0];
        let offset_x = this.drag_start_info.start_coords[1] - coords[1];

        let dx_scale =
            (100 + (Math.cos(-rotation_rad) * offset_x - Math.sin(-rotation_rad) * offset_y)) / 100;
        let dy_scale =
            (100 - (Math.cos(-rotation_rad) * offset_y + Math.sin(-rotation_rad) * offset_x)) / 100;

        let node_size = this.drag_start_info.options.node_size * dx_scale;
        let layer_height = this.drag_start_info.options.layer_height * dy_scale;

        this.style_config.options.node_size = parseInt(
            Math.max(
                this._default_options.node_size / 2,
                Math.min(this._default_options.node_size * 8, node_size)
            )
        );
        this.style_config.options.layer_height = parseInt(
            Math.max(
                this._default_options.layer_height / 2,
                Math.min(this._default_options.layer_height * 8, layer_height)
            )
        );
    }

    get_hierarchy_size() {
        let max_elements_per_layer = {};

        this.filtered_descendants.forEach(node => {
            if (node.children == null) return;
            if (max_elements_per_layer[node.depth] == null) max_elements_per_layer[node.depth] = 0;

            max_elements_per_layer[node.depth] += node.children.length;
        });
        this.layer_count = this.max_depth - this.style_root_node.depth + 2;

        let highest_density = 0;
        for (let idx in max_elements_per_layer)
            highest_density = Math.max(highest_density, max_elements_per_layer[idx]);

        let width = highest_density * this.style_config.options.node_size;
        let height = this.layer_count * this.style_config.options.layer_height;

        let coords = {};
        coords.x = +this.style_root_node.x;
        coords.y = +this.style_root_node.y;
        coords.width = width;
        coords.height = height;
        return coords;
    }
}

export class LayoutStyleRadial extends LayoutStyleHierarchyBase {
    type() {
        return "radial";
    }

    description() {
        return "Radial style";
    }

    style_color() {
        return "#13d389";
    }

    get_style_options() {
        return [
            {
                id: "radius",
                option_type: "range",
                values: {default: 120, min: 30, max: 300},
                text: "Radius",
                value: this.style_config.options.radius,
            },
            {
                id: "degree",
                option_type: "range",
                values: {default: 360, min: 10, max: 360},
                text: "Degree",
                value: this.style_config.options.degree,
            },
            {
                id: "rotation",
                option_type: "range",
                values: {default: 0, min: 0, max: 359},
                text: "Rotation",
                value: this.style_config.options.rotation,
            },
            {
                id: "include_parent_rotation",
                option_type: "checkbox",
                values: {default: false},
                text: "Include parent rotation",
                value: this.style_config.options.include_parent_rotation,
            },
            {
                id: "detach_from_parent",
                option_type: "checkbox",
                values: {default: false},
                text: "Detach from parent style",
                value: this.style_config.options.detach_from_parent,
            },
        ];
    }

    _compute_node_offsets() {
        let radius =
            this.style_config.options.radius * (this.max_depth - this.style_root_node.depth + 1);
        let rad = (this.get_rotation() / 180) * Math.PI;
        let tree = d3
            .cluster()
            .size([(this.style_config.options.degree / 360) * 2 * Math.PI, radius]);

        this._style_root_node_offsets = [];
        this._no_rotation_vertices = [];
        if (this.filtered_descendants.length == 1)
            this._style_root_node_offsets.push([this.style_root_node, 0, 0, 0]);
        else {
            tree(this.style_root_node);
            for (let idx in this.filtered_descendants) {
                let node = this.filtered_descendants[idx];

                let radius_reduction = 0;
                if (!node.children) {
                    radius_reduction = this.style_config.options.radius * 1;
                }
                this._no_rotation_vertices.push({
                    x: Math.cos(node.x) * (node.y - radius_reduction),
                    y: -Math.sin(node.x) * (node.y - radius_reduction),
                });

                let x = Math.cos(node.x + rad) * (node.y - radius_reduction);
                let y = -Math.sin(node.x + rad) * (node.y - radius_reduction);
                this._style_root_node_offsets.push([node, x, y, (node.x + rad) % (2 * Math.PI)]);
            }
        }
    }

    translate_coords() {
        if (this._style_translated && this.has_fixed_position()) return;

        let offsets = {};
        offsets.x = this.style_root_node.x;
        offsets.y = this.style_root_node.y;

        let retranslate_styled_sub_nodes = [];

        for (let idx in this._style_root_node_offsets) {
            let entry = this._style_root_node_offsets[idx];
            let node = entry[0];
            let x = entry[1];
            let y = entry[2];

            if (
                (node == this.style_root_node && this.style_config.options.detach_from_parent) ||
                node != this.style_root_node ||
                !this.style_root_node.parent
            ) {
                let force = this.get_default_node_force(node);
                force.fx = offsets.x + x;
                force.fy = offsets.y + y;
                force.text_positioning = this.get_text_positioning(entry);
                force.use_transition = this.use_transition;
            }

            if (node != this.style_root_node && node.data.use_style) {
                retranslate_styled_sub_nodes.push(node);
            }
            node.force = -500;
        }

        // Retranslate styles which's position got shifted
        retranslate_styled_sub_nodes.forEach(node => {
            this._layout_manager.compute_node_position(node);
            node.data.use_style.translate_coords();
        });

        this.generate_overlay();
        this.use_transition = false;
        this._style_translated = true;
    }

    get_text_positioning(entry) {
        let node = entry[0];
        let node_rad = entry[3];

        if (this.style_root_node == node) return;

        this.layer_count = this.max_depth - this.style_root_node.depth + 1;
        let rotate = (-node_rad / Math.PI) * 180;

        let anchor_options = ["start", "end"];
        let is_circle_left_side = node_rad > Math.PI / 2 && node_rad < (3 / 2) * Math.PI;
        if (is_circle_left_side) {
            rotate += 180;
            anchor_options = ["end", "start"];
        }

        let x = Math.cos(-node_rad) * 12;
        let y = Math.sin(-node_rad) * 12;
        let toggle_text_anchor = node.height > 0;

        let text_anchor = anchor_options[0];
        if (toggle_text_anchor) {
            x = -x;
            y = -y;
            text_anchor = anchor_options[1];
        }

        let transform_text = "translate(" + x + "," + y + ") rotate(" + rotate + ")";
        return selection => {
            selection.attr("transform", transform_text).attr("text-anchor", text_anchor);
        };
    }

    generate_overlay() {
        if (!this._layout_manager.edit_layout) return;
        let degree = Math.min(360, Math.max(0, this.style_config.options.degree));
        let end_angle = (degree / 180) * Math.PI;

        let arc = d3
            .arc()
            .innerRadius(25)
            .outerRadius(
                this.style_config.options.radius * (this.max_depth - this.style_root_node.depth + 1)
            )
            .startAngle(2 * Math.PI - end_angle + Math.PI / 2)
            .endAngle(2 * Math.PI + Math.PI / 2);

        let rotation_overlay = this.selection.selectAll("g.rotation_overlay").data([null]);
        rotation_overlay = rotation_overlay
            .enter()
            .append("g")
            .classed("rotation_overlay", true)
            .merge(rotation_overlay);
        rotation_overlay.attr(
            "transform",
            "translate(" +
                this.style_root_node.x +
                "," +
                this.style_root_node.y +
                ")" +
                "rotate(" +
                -this.get_rotation() +
                ")"
        );

        // Arc
        let path = rotation_overlay.selectAll("path").data([null]);
        path = path
            .enter()
            .append("path")
            .classed("style_overlay", true)
            .style("opacity", 0)
            .merge(path);
        this.add_optional_transition(path).attr("d", arc).style("opacity", null);

        // Icons
        let elements = [
            {
                node: this.style_root_node,
                type: "radius",
                image: "themes/facelift/images/icon_resize.png",
                call: this.get_drag_callback(() => this.change_radius()),
            },
            {
                node: this.style_root_node,
                type: "rotation",
                image: "themes/facelift/images/icon_rotate_left.png",
                call: this.get_drag_callback(() => this.change_rotation()),
            },
            {
                node: this.style_root_node,
                type: "degree",
                image: "themes/facelift/images/icon_pie_chart.png",
                call: this.get_drag_callback(() => this.change_degree()),
            },
        ];
        let coords = this._layout_manager.viewport.translate_to_zoom({
            x: this.style_root_node.x,
            y: this.style_root_node.y,
        });
        this.add_option_icons(coords, elements);
    }

    change_radius() {
        this._layout_manager.toolbar_plugin.layout_style_configuration.show_style_configuration(
            this
        );
        this.style_config.options.radius = parseInt(
            Math.min(
                500,
                Math.max(10, this.drag_start_info.options.radius - this.drag_start_info.delta.y)
            )
        );
        this.changed_options();
    }

    change_degree() {
        this._layout_manager.toolbar_plugin.layout_style_configuration.show_style_configuration(
            this
        );
        let degree = parseInt(
            Math.min(
                360,
                Math.max(10, this.drag_start_info.options.degree - this.drag_start_info.delta.y)
            )
        );
        this.style_config.options.degree = degree;
        this.changed_options();
    }
}

export class LayoutStyleFixed extends AbstractLayoutStyle {
    type() {
        return "fixed";
    }

    description() {
        return "Fixed position style";
    }

    style_color() {
        return "Burlywood";
    }

    positioning_weight() {
        return 100;
    }

    update_data() {
        this.fix_node(this.style_root_node);
    }
}

export class LayoutStyleBlock extends LayoutStyleHierarchyBase {
    type() {
        return "block";
    }

    description() {
        return "Leaf-Nodes Block style";
    }

    style_color() {
        return "#3cc2ff";
    }

    get_style_options() {
        return [
            {
                id: "detach_from_parent",
                option_type: "checkbox",
                values: {default: false},
                text: "Detach from parent style",
                value: this.style_config.options.detach_from_parent,
            },
        ];
    }

    _compute_node_offsets() {
        this._leaf_childs = [];
        if (!this.style_root_node.children) return;

        // Group only leaf childs
        this._leaf_childs = [];
        this.style_root_node.children.forEach(child => {
            if (child._children) return;
            this._leaf_childs.push(child);
        });

        let node_width = 50;
        let width = parseInt(Math.sqrt(this._leaf_childs.length)) * node_width;
        let max_cols = parseInt(width / node_width);

        this._width = width;
        this._height = node_width / 2;

        this._style_root_node_offsets = [];
        this._style_root_node_offsets.push({node: this.style_root_node, x: 0, y: 0});
        for (let idx in this._leaf_childs) {
            let node = this._leaf_childs[idx];
            let row_no = parseInt(idx / max_cols) + 1;
            let col_no = idx % max_cols;
            this._height = (row_no * node_width) / 2;
            this._style_root_node_offsets.push({
                node: node,
                x: -width / 2 + node_width / 2 + col_no * node_width,
                y: (row_no * node_width) / 2,
            });
        }
        this.use_transition = true;
    }

    get_size() {
        return [this._width * 1.1, this._height];
    }

    translate_coords() {
        if (this._style_root_node_offsets == []) return;

        node_visualization_utils.log(
            7,
            "translating block style, fixed positing:" + this.has_fixed_position()
        );

        let abs_offsets = {};
        abs_offsets.x = this.style_root_node.x;
        abs_offsets.y = this.style_root_node.y;
        this._style_root_node_offsets.forEach(offset => {
            let force = this.get_default_node_force(offset.node);
            force.fx = abs_offsets.x + offset.x;
            force.fy = abs_offsets.y + offset.y;
            force.use_transition = this.use_transition;
            if (offset.node != this.style_root_node) force.hide_node_link = true;
            force.text_positioning = (selection, radius) =>
                selection.attr(
                    "transform",
                    "translate(" + radius + "," + (radius + 4) + ") rotate(45)"
                );
            offset.node.force = -500;
        });

        this.generate_overlay();
        this.use_transition = false;
        this._style_translated = true;
        return true;
    }

    update_gui() {
        this.generate_overlay();
    }

    generate_overlay() {
        if (this._style_root_node_offsets.length < 2) return;

        let boundary = 10;
        let hull_vertices = [];
        let abs_offsets = {};
        abs_offsets.x = this.style_root_node.x;
        abs_offsets.y = this.style_root_node.y;
        this._style_root_node_offsets.forEach(offset => {
            if (offset.node == this.style_root_node) return;
            hull_vertices.push([
                offset.x + boundary + abs_offsets.x,
                offset.y + boundary + abs_offsets.y,
            ]);
            hull_vertices.push([
                offset.x - boundary + abs_offsets.x,
                offset.y - boundary + abs_offsets.y,
            ]);
            hull_vertices.push([
                offset.x + boundary + abs_offsets.x,
                offset.y - boundary + abs_offsets.y,
            ]);
            hull_vertices.push([
                offset.x - boundary + abs_offsets.x,
                offset.y + boundary + abs_offsets.y,
            ]);
        });
        let hull = this.selection
            .selectAll("path.children_boundary")
            .data([d3.polygonHull(hull_vertices)]);
        hull = hull
            .enter()
            .append("path")
            .classed("children_boundary", true)
            .classed("block_style_overlay", true)
            .attr("pointer-events", "none")
            .style("opacity", 0)
            .merge(hull);
        this.add_optional_transition(
            hull.attr("d", function (d) {
                return "M" + d.join("L") + "Z";
            })
        ).style("opacity", null);

        let connection_line = this.selection
            .selectAll("line.root_children_connection")
            .data([null]);
        connection_line
            .enter()
            .append("line")
            .classed("root_children_connection", true)
            .classed("block_style_overlay", true)
            .merge(connection_line)
            .attr("x1", this.style_root_node.x)
            .attr("y1", this.style_root_node.y)
            .attr("x2", this.style_root_node.x)
            .attr("y2", this.style_root_node.y + 15);
    }
}

node_visualization_layouting_utils.LayoutStyleFactory.style_classes.push(LayoutStyleForce);
node_visualization_layouting_utils.LayoutStyleFactory.style_classes.push(LayoutStyleHierarchy);
node_visualization_layouting_utils.LayoutStyleFactory.style_classes.push(LayoutStyleRadial);
//node_visualization_layouting_utils.LayoutStyleFactory.style_classes.push(LayoutStyleFixed)
node_visualization_layouting_utils.LayoutStyleFactory.style_classes.push(LayoutStyleBlock);

export class LayoutStyleExampleGenerator {
    constructor(varprefix) {
        this._varprefix = varprefix;
        this._example_generator_div = d3.select("#" + this._varprefix);
        let options = this._example_generator_div.append("div").style("float", "left");

        this._viewport_width = 600;
        this._viewport_height = 400;

        this._style_choice_selection = options.append("div");
        this._options_selection = options.append("div").style("margin-top", "12px");
        this._example_selection = options.append("div").style("margin-top", "12px");
        this._viewport_selection = this._example_generator_div
            .append("svg")
            .attr("id", "viewport")
            .style("float", "left")
            .attr("width", this._viewport_width)
            .attr("height", this._viewport_height);
        this._example_options = {
            total_nodes: {
                id: "total_nodes",
                values: {default: 5, min: 1, max: 50},
                text: "Sample nodes",
                value: 20,
            },
            depth: {
                id: "depth",
                values: {default: 1, min: 1, max: 5},
                text: "Maximum depth",
                value: 2,
            },
        };

        this._style_hierarchy = null;
        this._style_instance = null;
        this._layout_manager = this._create_fake_layout_manager();
        this._initialize_viewport_components();
    }

    _initialize_viewport_components() {
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
    }

    _update_viewport_visibility() {
        if (this._style_settings.type == "none") {
            this._viewport_selection.style("display", "none");
            this._example_selection.style("display", "none");
        } else {
            this._viewport_selection.style("display", null);
            this._example_selection.style("display", null);
        }
    }

    create_example(style_settings) {
        this._style_settings = style_settings;
        this._render_style_choice(this._style_choice_selection);
        this._update_viewport_visibility();
        this._create_example_hierarchy(this._example_options);

        let style_config = {options: this._style_settings.style_config};
        let style_class = null;
        switch (this._style_settings.type) {
            case "none": {
                return;
            }
            case LayoutStyleHierarchy.prototype.type(): {
                style_class = LayoutStyleHierarchy;
                break;
            }
            case LayoutStyleRadial.prototype.type(): {
                style_class = LayoutStyleRadial;
                break;
            }
            case LayoutStyleBlock.prototype.type(): {
                style_class = LayoutStyleBlock;
                break;
            }
        }
        this._style_instance = new style_class(
            this._layout_manager,
            style_config,
            this._style_hierarchy.descendants()[0],
            this._viewport_zoom
        );
        this._update_example();
    }

    _update_example() {
        this._update_nodes();
        this._render_nodes_and_links();
        this._style_instance.render_options(this._options_selection, this._varprefix);
        this._render_example_settings(this._example_selection);
    }

    _render_style_choice(style_choice_selection) {
        let style_choices = [["none", "None"]];
        let use_styles = [LayoutStyleHierarchy, LayoutStyleRadial, LayoutStyleBlock];
        use_styles.forEach(style => {
            style_choices.push([style.prototype.type(), style.prototype.description()]);
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
            .property("selected", d => d[0] == this._style_settings.type)
            .text(d => d[1]);
    }

    _changed_style(event) {
        let new_style_id = d3.select(event.target).property("value");
        this._options_selection.selectAll("*").remove();
        this._viewport_selection.selectAll(".block_style_overlay").remove();
        this.create_example({type: new_style_id, style_config: {}});
    }

    _render_example_settings(div_selection) {
        div_selection
            .selectAll("#headline")
            .data([null])
            .enter()
            .append("b")
            .attr("id", "headline")
            .text("Example settings");

        let table = div_selection.selectAll("table").data([null]);
        table = table.enter().append("table").merge(table);

        let options = [];
        options.push(this._example_options.total_nodes);
        if (this._style_settings.type != LayoutStyleBlock.prototype.type())
            options.push(this._example_options.depth);

        let rows = table.selectAll("tr").data(options);
        rows.exit().remove();
        let rows_enter = rows.enter().append("tr");
        rows_enter
            .append("td")
            .text(d => d.text)
            .classed("style_infotext", true);
        rows_enter
            .append("td")
            .append("input")
            .classed("range", true)
            .attr("id", d => d.id)
            .attr("type", "range")
            .attr("step", 1)
            .attr("min", d => d.values.min)
            .attr("max", d => d.values.max)
            .property("value", d => d.value)
            .on("input", (d, b, c) => {
                this._example_options[d.id].value = parseInt(d3.select(c[b]).property("value"));
                this._create_example_hierarchy(this._example_options);
                this._style_instance.style_root_node = this._style_hierarchy.descendants()[0];
                this._update_example();
            });
        rows_enter.append("td").classed("text", true);
        rows = rows_enter.merge(rows);
        rows.select("td.text").text(d => {
            return div_selection.select("input#" + d.id).property("value");
        });
    }

    _update_nodes() {
        this._style_instance.style_root_node.x = 0;
        this._style_instance.style_root_node.y = 0;
        this._style_instance.update_data();
        this._style_instance.translate_coords();
        this._style_hierarchy.descendants().forEach(node => {
            this._layout_manager.compute_node_position(node);
        });
        this._center_hierarchy_nodes(this._style_hierarchy);
    }

    _render_nodes_and_links(no_transition = false) {
        this._style_instance.generate_overlay();
        this._paint_links(this._style_hierarchy, no_transition);
        this._paint_nodes(this._style_hierarchy, no_transition);
    }

    _center_hierarchy_nodes(hierarchy) {
        let nodes = hierarchy.descendants();
        let width = this._viewport_selection.attr("width") - 30;
        let height = this._viewport_selection.attr("height") - 30;
        let bounding_rect = node_visualization_utils.get_bounding_rect(nodes);

        let width_ratio = bounding_rect.width / width;
        let height_ratio = bounding_rect.height / height;
        let ratio = Math.max(1, Math.max(width_ratio, height_ratio));

        let x_offset = (width - bounding_rect.width) / 2;
        let y_offset = (height - bounding_rect.height) / 2;

        nodes.forEach(node => {
            node.x += parseInt(x_offset) - bounding_rect.x_min + 15;
            node.y += parseInt(y_offset) - bounding_rect.y_min + 15;
        });

        if (ratio > 1) {
            let rect_x = -(width - width * ratio) / 2;
            let rect_y = -(height - height * ratio) / 2;
            this._viewport_zoom.attr(
                "transform",
                "scale(" + 1 / ratio + ") translate(" + rect_x + "," + rect_y + ")"
            );
            let default_scale = this._viewport_selection.selectAll("text").data([null]);
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
            let default_scale = this._viewport_selection.selectAll("text").remove();
        }
    }

    _create_fake_layout_manager() {
        let fake_layout_manager = new node_visualization_layouting.LayoutManagerLayer(
            this._create_fake_viewport()
        );
        // Disable undo feature
        fake_layout_manager.create_undo_step = () => {};
        fake_layout_manager.layout_applier = {};
        fake_layout_manager.layout_applier.apply_all_layouts = () => {};
        return fake_layout_manager;
    }

    _create_fake_viewport() {
        return {
            update_layers: () => {
                this._update_nodes();
                this._render_nodes_and_links(true);
            },
            main_instance: {
                toolbar: {
                    add_toolbar_plugin_instance: () => {},
                    update_toolbar_plugins: () => {},
                },
            },
        };
    }

    _create_example_hierarchy(example_settings) {
        let chunk = {coords: {x: 0, y: 0, width: 400, height: 400}};
        let id_counter = 0;

        let maximum_nodes = example_settings.total_nodes.value;
        let generated_nodes = 0;

        function _add_hierarchy_children(parent_node, cancel_delta, cancel_chance) {
            parent_node.children = [];
            while (true) {
                if (
                    generated_nodes >= maximum_nodes ||
                    (cancel_chance < 1 && cancel_chance - Math.random() <= 0)
                ) {
                    if (parent_node.children.length == 0) delete parent_node.children;
                    return;
                }
                let new_child = {name: "child"};
                generated_nodes += 1;
                _add_hierarchy_children(new_child, cancel_delta, cancel_chance - cancel_delta);
                parent_node.children.push(new_child);
            }
        }

        let hierarchy_raw = {name: "Root node"};
        let cancel_delta = 1 / example_settings.depth.value;
        // Maximum depth of block style is 1
        if (this._style_settings.type == LayoutStyleBlock.prototype.type()) cancel_delta = 1;

        _add_hierarchy_children(hierarchy_raw, cancel_delta, 1);

        let hierarchy = d3.hierarchy(hierarchy_raw);
        hierarchy.descendants().forEach(node => {
            node.x = 50;
            node.y = 50;
            id_counter += 1;
            node.data.id = id_counter;
            node.data.chunk = chunk;
            node.data.hostname = "Demohost";
            node.data.transition_info = {};
        });
        this._style_hierarchy = hierarchy;
    }

    _paint_nodes(hierarchy, no_transition) {
        let nodes = this._viewport_zoom_nodes
            .selectAll(".node.alive")
            .data(hierarchy.descendants());
        nodes.exit().classed("alive", false).transition().duration(500).attr("opacity", 0).remove();

        nodes = nodes
            .enter()
            .append("circle")
            .classed("node", true)
            .classed("alive", true)
            .attr("fill", "#13d389")
            .attr("r", d => (d.parent ? 6 : 12))
            .attr("cx", d => this._viewport_width / 2)
            .attr("cy", d => this._viewport_height / 2)
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

    _paint_links(hierarchy, no_transition) {
        let links = this._viewport_zoom_links.selectAll(".link.alive").data(
            hierarchy.descendants().filter(d => {
                return !d.data.current_positioning.hide_node_link;
            })
        );
        links.exit().classed("alive", false).transition().duration(500).attr("opacity", 0).remove();

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

        if (no_transition) links.attr("d", d => this.diagonal(d, d.parent)).attr("opacity", 1);
        else
            links
                .transition()
                .duration(500)
                .attr("d", d => this.diagonal(d, d.parent))
                .attr("opacity", 1);
    }

    diagonal(source, target) {
        if (!target) return;
        let s = {};
        let d = {};
        s.y = source.x;
        s.x = source.y;
        d.y = target.x;
        d.x = target.y;
        let path = `M ${s.y} ${s.x}
                C ${(s.y + d.y) / 2} ${s.x},
                  ${(s.y + d.y) / 2} ${d.x},
                  ${d.y} ${d.x}`;
        return path;
    }
}
