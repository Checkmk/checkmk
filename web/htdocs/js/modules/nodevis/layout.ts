// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

import * as ajax from "ajax";
import * as d3 from "d3";
import {
    ContextMenuElement,
    Coords,
    d3SelectionDiv,
    d3SelectionG,
    ForceOptions,
    NodevisNode,
    NodevisWorld,
} from "nodevis/type_defs";
import {
    FixLayer,
    layer_class_registry,
    LayerSelections,
    ToggleableLayer,
} from "nodevis/layer_utils";
import {ToolbarPluginBase} from "nodevis/toolbar_utils";
import {
    AbstractLayoutStyle,
    compute_style_id,
    layout_style_class_registry,
    LayoutHistoryStep,
    LayoutStyleFactory,
    NodeForce,
    NodePositioning,
    NodeVisualizationLayout,
    SerializedNodevisLayout,
    StyleConfig,
} from "nodevis/layout_utils";
import {LayoutStyleFixed, LayoutStyleForce} from "nodevis/layout_styles";
import {LayeredNodesLayer} from "./layers";
import {
    DefaultTransition,
    get_bounding_rect,
    log,
    NodeMatcher,
} from "nodevis/utils";

//#.
//#   .-Layout Manager-----------------------------------------------------.
//#   |                  _                            _                    |
//#   |                 | |    __ _ _   _  ___  _   _| |_                  |
//#   |                 | |   / _` | | | |/ _ \| | | | __|                 |
//#   |                 | |__| (_| | |_| | (_) | |_| | |_                  |
//#   |                 |_____\__,_|\__, |\___/ \__,_|\__|                 |
//#   |                             |___/                                  |
//#   |              __  __                                                |
//#   |             |  \/  | __ _ _ __   __ _  __ _  ___ _ __              |
//#   |             | |\/| |/ _` | '_ \ / _` |/ _` |/ _ \ '__|             |
//#   |             | |  | | (_| | | | | (_| | (_| |  __/ |                |
//#   |             |_|  |_|\__,_|_| |_|\__,_|\__, |\___|_|                |
//#   |                                       |___/                        |
//#   +--------------------------------------------------------------------+

export function compute_node_positions_from_list_of_nodes(
    list_of_nodes: NodevisNode[]
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
        const viewport_boundary = 5000;
        node.fx = Math.max(
            Math.min(current_positioning.fx, viewport_boundary),
            -viewport_boundary
        );
        node.fy = Math.max(
            Math.min(current_positioning.fy, viewport_boundary),
            -viewport_boundary
        );
        node.x = node.fx;
        node.y = node.fy;
        node.data.transition_info.use_transition =
            current_positioning.use_transition;
    }
    if (node.data.selection) {
        node.data.selection
            .selectAll("circle")
            .classed("style_root_node", node.data.use_style ? true : false);
        node.data.selection
            .selectAll("circle")
            .classed("free_floating_node", current_positioning.free == true);
    }
}

export class LayoutManagerLayer extends FixLayer {
    static class_name = "layout_manager";
    _mouse_events_overlay: LayoutingMouseEventsOverlay;
    layout_applier: LayoutApplier;
    toolbar_plugin: LayoutingToolbarPlugin;

    // Edit tools
    edit_layout = false; // Indicates whether the layout manager is active
    _node_dragging_allowed = false; // If the user is able to drag nodes with the mouse
    _node_dragging_enforced = false; // If the user is able to drag nodes with the mouse
    allow_layout_updates = true; // Indicates if layout updates are allowed

    // Instantiated styles
    _active_styles = {};

    // Register layout manager toolbar plugin

    styles_selection: d3SelectionG;
    dragging = false;

    constructor(world: NodevisWorld, selections: LayerSelections) {
        super(world, selections);
        this.toolbar_plugin = new LayoutingToolbarPlugin(world);

        // Register layout manager toolbar plugin
        this._world.toolbar.add_toolbar_plugin_instance(this.toolbar_plugin);
        this._mouse_events_overlay = new LayoutingMouseEventsOverlay(world);
        this.layout_applier = new LayoutApplier(world);
        //        this._world.toolbar.update_toolbar_plugins();
        this.styles_selection = this._svg_selection
            .append("g")
            .attr("id", "hierarchies");
    }

    id(): string {
        return "layout_manager";
    }

    z_index(): number {
        return 40;
    }

    name(): string {
        return "Layout Manager";
    }

    create_undo_step(): void {
        this.layout_applier.create_undo_step();
        this.toolbar_plugin._update_history_icons();
    }

    add_active_style(style: AbstractLayoutStyle): void {
        this._active_styles[style.id()] = style;
    }

    get_active_style(style_id: string): AbstractLayoutStyle {
        return this._active_styles[style_id];
    }

    remove_active_style(style: AbstractLayoutStyle): void {
        delete this._active_styles[style.id()];
        style.remove();
        style.style_root_node.data.use_style = null;
    }

    get_context_menu_elements(node: NodevisNode | null): ContextMenuElement[] {
        return this.layout_applier.get_context_menu_elements(node);
    }

    show_layout_options(): void {
        this.edit_layout = true;
        this.enable_node_dragging();
        this.allow_layout_updates = false;
        this._mouse_events_overlay.update_data();
        // TODO: implement different edit indicator, e.g into the world
        this._world.viewport
            .get_layer("nodes")
            ._svg_selection.classed("edit", true);
        this.update_style_indicators();
    }

    hide_layout_options(): void {
        this.edit_layout = false;
        this.disable_node_dragging();
        this.allow_layout_updates = true;
        this._world.viewport
            .get_layer("nodes")
            ._svg_selection.classed("edit", false);
        this.styles_selection
            .selectAll(".layout_style")
            .selectAll("*")
            .remove();
        this._div_selection.selectAll("img").remove();
        this.update_style_indicators(true);
    }

    enforce_node_drag(): void {
        this._node_dragging_enforced = true;
    }

    enable_node_dragging(): void {
        this._node_dragging_allowed = true;
    }

    disable_node_dragging(): void {
        this._node_dragging_allowed = false;
    }

    is_node_drag_allowed(): boolean {
        return this._node_dragging_enforced || this._node_dragging_allowed;
    }

    size_changed(): boolean {
        // TODO: check this
        //        node_visualization_layout_styles.force_simulation.size_changed()
        return false;
    }

    update_data(): void {
        this.toolbar_plugin.update_content();

        const sorted_styles: [number, AbstractLayoutStyle][] = [];
        for (const idx in this._active_styles) {
            sorted_styles.push([
                this._active_styles[idx].style_root_node.depth,
                this._active_styles[idx],
            ]);
        }

        // Sort styles, ordering them from leaf to root
        // Style in leaf need be be computed first, since they have a size-impact on any parent style
        sorted_styles.sort(function (a, b) {
            if (a[0] > b[0]) return -1;
            if (a[0] < b[0]) return 1;
            return 0;
        });
        sorted_styles.forEach(sorted_style => sorted_style[1].update_data());

        this.translate_layout();
        this.compute_node_positions();
        this._mouse_events_overlay.update_data();
    }

    update_gui(): void {
        for (const idx in this._active_styles) {
            this._active_styles[idx].update_gui();
        }
    }

    update_style_indicators(force = false): void {
        if (!force && !this.edit_layout) return;

        this._world.viewport.get_hierarchy_list().forEach(hierarchy =>
            hierarchy.nodes.forEach(node => {
                if (node.data.use_style)
                    node.data.use_style.update_style_indicator(
                        this.edit_layout
                    );
            })
        );
    }

    translate_layout(): void {
        for (const idx in this._active_styles) {
            this._active_styles[idx].translate_coords();
        }
    }

    zoomed(): void {
        for (const idx in this._active_styles) {
            this._active_styles[idx].zoomed();
        }
    }

    get_viewport_percentage_of_node(node: NodevisNode): {x: number; y: number} {
        const coords = node.data.chunk.coords;
        const x_perc = (100.0 * (node.x - coords.x)) / coords.width;
        const y_perc = (100.0 * (node.y - coords.y)) / coords.height;
        return {x: x_perc, y: y_perc};
    }

    get_absolute_node_coords(
        perc_coords: Coords,
        node: NodevisNode
    ): {x: number; y: number} {
        const coords = node.data.chunk.coords;
        const x = coords.x + (coords.width * perc_coords.x) / 100;
        const y = coords.y + (coords.height * perc_coords.y) / 100;
        return {x: x, y: y};
    }

    get_node_positioning(node: NodevisNode): NodePositioning {
        if (node.data.node_positioning == null) {
            node.data.node_positioning = {};
        }
        return node.data.node_positioning;
    }

    add_node_positioning(
        id: string,
        node: NodevisNode,
        positioning_force: NodeForce
    ): void {
        if (node.data.node_positioning == null) {
            node.data.node_positioning = {};
        }
        node.data.node_positioning[id] = positioning_force;
    }

    compute_node_positions(): void {
        // Determines the positioning force with the highest weight
        this._world.viewport.get_hierarchy_list().forEach(hierarchy => {
            hierarchy.nodes.forEach(node => compute_node_position(node));
        });
    }

    save_layout(layout: SerializedNodevisLayout): void {
        this.save_layout_template(layout);
    }

    delete_layout_id(layout_id: string): void {
        ajax.call_ajax("ajax_delete_bi_template_layout.py", {
            method: "POST",
            post_data: "layout_id=" + encodeURIComponent(layout_id),
            response_handler: () => this.toolbar_plugin.fetch_all_layouts(),
        });
    }

    save_layout_template(layout_config: SerializedNodevisLayout): void {
        ajax.call_ajax("ajax_save_bi_template_layout.py", {
            method: "POST",
            post_data:
                "layout=" + encodeURIComponent(JSON.stringify(layout_config)),
            response_handler: () => this.toolbar_plugin.fetch_all_layouts(),
        });
    }

    // TODO: check parameters
    save_layout_for_aggregation(
        layout_config: {[name: string]: SerializedNodevisLayout},
        aggregation_name: string
    ): void {
        ajax.call_ajax("ajax_save_bi_aggregation_layout.py", {
            method: "POST",
            post_data:
                "layout=" +
                encodeURIComponent(JSON.stringify(layout_config)) +
                "&aggregation_name=" +
                encodeURIComponent(aggregation_name),
            response_handler: () => {
                this._world.datasource_manager.schedule(true);
                this.toolbar_plugin.fetch_all_layouts();
            },
        });
    }

    delete_layout_for_aggregation(aggregation_name) {
        ajax.call_ajax("ajax_delete_bi_aggregation_layout.py", {
            method: "POST",
            post_data:
                "aggregation_name=" + encodeURIComponent(aggregation_name),
            response_handler: () => {
                this.allow_layout_updates = true;
                this._world.datasource_manager.schedule(true);
                this.toolbar_plugin.fetch_all_layouts();
            },
        });
    }
}

layer_class_registry.register(LayoutManagerLayer);

export class LayoutStyleConfiguration {
    toolbar_plugin: ToolbarPluginBase;
    layout_manager: LayoutManagerLayer;
    _style_config_selection: d3SelectionDiv;
    current_style: AbstractLayoutStyle | null = null;

    constructor(
        world: NodevisWorld,
        toolbar_plugin: ToolbarPluginBase,
        config_selection: d3SelectionDiv
    ) {
        this.toolbar_plugin = toolbar_plugin;
        this.layout_manager = world.layout_manager;
        this._style_config_selection = config_selection;
    }

    render_style_config(): void {
        const style_div = this._style_config_selection
            .selectAll("div#style_div")
            .data([null]);
        const style_div_enter = style_div
            .enter()
            .append("div")
            .attr("id", "style_div");

        style_div_enter
            .selectAll("#styleconfig_headline")
            .data([null])
            .enter()
            .append("h2")
            .attr("id", "styleconfig_headline")
            .text("Style configuration");

        style_div_enter
            .selectAll("div.style_component")
            .data(["style_options", "style_matcher"])
            .enter()
            .append("div")
            .attr("id", d => d)
            .classed("style_component", true);

        // TODO: matchers are currently disabled
        //        // Add foldable trees for basic and advanced matchers
        //        let style_matcher = style_div_enter.select("#style_matcher")
        //        style_matcher.append("b").text("Matcher settings")
        //        style_matcher.append("br")
        //        style_matcher.append("label").text("(How to find the root node of this style)")
        //        style_matcher.append("br")
        //        style_matcher.append("br")
        //
        //        let theme_prefix = utils.get_theme()
        //        let matcher_topics = [
        //            {id: "basic_matchers", text: "Basic matching", default_open: true},
        //            {id: "advanced_matchers", text: "Advanced matching", default_open: false},
        //        ]
        //        let matchers_enter = style_matcher.selectAll("div.foldable#matcher_topic").data(matcher_topics, d=>d.id).enter()
        //                        .append("div").classed("matcher_topic", true).classed("foldable", true)
        //        matchers_enter.append("img")
        //                        .classed("treeangle", true)
        //                        .classed("open", d=>d.default_open)
        //                        .attr("src",  theme_prefix + "/images/tree_closed.svg")
        //                        .on("click", function() {
        //                            let image = d3.select(this)
        //                            image.classed("open", !image.classed("open"))
        //                            image.classed("closed", image.classed("open"))
        //                            d3.select(this.parentNode).select(".matcher_topic_content").style("display", image.classed("open") ? null : "none")
        //                        })
        //        matchers_enter.append("b").classed("treeangle", true).classed("title", true).text(d=>d.text).style("color", "black")
        //                        .on("click", function() {
        //                            let image = d3.select(this.parentNode).select("img")
        //                            image.classed("open", !image.classed("open"))
        //                            image.classed("closed", image.classed("open"))
        //                            d3.select(this.parentNode).select(".matcher_topic_content").style("display", image.classed("open") ? null : "none")
        //                        })
        //        matchers_enter.append("div").classed("matcher_topic_content", true).attr("id", d=>d.id)
        //                       .style("display", d=>d.default_open ? null : "none")
        //        matchers_enter.append("br")

        this.show_style_configuration(this.current_style);
    }

    show_style_configuration(style) {
        // Cleanup GUI config if style differs
        if (style != this.current_style) this._cleanup_old_style_config();

        // Remove style focus on old style
        if (this.current_style)
            this.current_style.style_root_node.data.selection
                .select("circle.style_indicator")
                .classed("focus", false);

        if (style == null) {
            this._style_config_selection.style("display", "none");
            return;
        }

        this._style_config_selection.style("display", null);

        // Set style focus on new style
        style.style_root_node.data.selection
            .select("circle.style_indicator")
            .classed("focus", true);
        this.current_style = style;

        let hide_style_config = false;
        if (!this.current_style) hide_style_config = true;
        else if (this.current_style.type() == "force")
            hide_style_config = false;
        else if (this.current_style.get_matcher() == null)
            hide_style_config = true;

        if (hide_style_config) {
            this._style_config_selection
                .transition()
                .duration(DefaultTransition.duration())
                .style("height", "0px")
                .style("display", "none");
            return;
        }
        this._style_config_selection.style("height", null);
        this._style_config_selection.style("display", null);

        this._show_style_configuration_options(style);
    }

    _cleanup_old_style_config() {
        this._style_config_selection
            .selectAll("div#style_options")
            .selectAll("*")
            .remove();
        this._style_config_selection
            .selectAll(".matcher_topic_content")
            .selectAll("*")
            .remove();
    }

    _show_style_configuration_options(style: AbstractLayoutStyle): void {
        const options_selection =
            this._style_config_selection.select<HTMLDivElement>(
                "#style_options"
            );
        style.render_options(options_selection);
    }
}

//#.
//#   .-Toolbar Plugin-----------------------------------------------------.
//#   |  _____           _ _                  ____  _             _        |
//#   | |_   _|__   ___ | | |__   __ _ _ __  |  _ \| |_   _  __ _(_)_ __   |
//#   |   | |/ _ \ / _ \| | '_ \ / _` | '__| | |_) | | | | |/ _` | | '_ \  |
//#   |   | | (_) | (_) | | |_) | (_| | |    |  __/| | |_| | (_| | | | | | |
//#   |   |_|\___/ \___/|_|_.__/ \__,_|_|    |_|   |_|\__,_|\__, |_|_| |_| |
//#   |                                                     |___/          |
//#   +--------------------------------------------------------------------+
export class LayoutingToolbarPlugin extends ToolbarPluginBase {
    _layout_style_configuration: LayoutStyleConfiguration | null = null;

    constructor(world: NodevisWorld) {
        super(world, "Modify Layout");
        this.active = false;
    }

    id() {
        return "layouting_toolbar";
    }

    layout_style_configuration(): LayoutStyleConfiguration {
        if (this._layout_style_configuration == null)
            throw "Missing layout_style_configuration";
        return this._layout_style_configuration;
    }

    setup_selections(content_selection: d3SelectionDiv) {
        this._div_selection = content_selection;
        this._layout_style_configuration = new LayoutStyleConfiguration(
            this._world,
            this,
            this.div_selection()
        );
    }

    render_togglebutton(selection: d3SelectionDiv) {
        selection.style("cursor", "pointer");
        selection
            .append("img")
            .attr("src", "themes/facelift/images/icon_aggr.svg")
            .attr("title", "Layout Designer")
            .style("opacity", 1);
    }

    enable_actions() {
        this._world.layout_manager.show_layout_options();

        this._world.viewport.update_gui_of_layers();
        for (const idx in this._world.layout_manager._active_styles) {
            this._world.layout_manager._active_styles[idx].generate_overlay();
        }

        this.div_selection()
            .transition()
            .duration(DefaultTransition.duration())
            .style("opacity", 1)
            .style("display", null);
    }

    disable_actions() {
        if (this._world.layout_manager.edit_layout) {
            this._world.layout_manager.hide_layout_options();
            this._world.viewport.update_gui_of_layers();
        }

        this.div_selection()
            .transition()
            .duration(DefaultTransition.duration())
            .style("opacity", 0)
            .style("display", "none");
    }

    remove_content() {
        this.div_selection()
            .select("div.toolbar_layouting")
            .transition()
            .duration(DefaultTransition.duration())
            .style("height", "0px")
            .remove();
    }

    render_content() {
        this.update_content();
    }

    update_content() {
        if (!this._world.layout_manager.edit_layout) return;

        // Layout configuration box
        let configuration_div_box = this.div_selection()
            .selectAll<HTMLDivElement, null>("div#configuration_management")
            .data([null]);
        configuration_div_box = configuration_div_box
            .enter()
            .append("div")
            .attr("id", "configuration_management")
            .classed("noselect", true)
            .classed("box", true)
            .merge(configuration_div_box);

        let configuration_div = configuration_div_box
            .selectAll<HTMLDivElement, null>("div#configuration_div")
            .data([null]);
        configuration_div = configuration_div
            .enter()
            .append("div")
            .attr("id", "configuration_div")
            .merge(configuration_div);
        configuration_div
            .selectAll<HTMLDivElement, null>("#layout_configuration_headline")
            .data([null])
            .enter()
            .append("h2")
            .attr("id", "layout_configuration_headline")
            .text("Layout Configuration");
        if (this._world.current_datasource == "bi_aggregations") {
            this._render_aggregation_configuration(configuration_div);

            // Render layout history
            let history_div_box = this.div_selection()
                .selectAll<HTMLDivElement, null>("div#history_icons")
                .data([null]);
            history_div_box = history_div_box
                .enter()
                .append("div")
                .attr("id", "history_icons")
                .classed("noselect", true)
                .merge(history_div_box);
            this._render_layout_history(history_div_box);

            // Style management box
            const style_div_box = this.div_selection()
                .selectAll<HTMLDivElement, null>("div#style_management")
                .data([null]);
            style_div_box
                .enter()
                .append("div")
                .attr("id", "style_management")
                .classed("noselect", true)
                .classed("box", true)
                .merge(style_div_box);

            const current_style =
                this.layout_style_configuration().current_style;
            if (current_style)
                this.layout_style_configuration().render_style_config();
        }
        this._render_layout_configuration(configuration_div);
    }

    _render_aggregation_configuration(into_selection): void {
        const chunks = this._world.viewport.get_hierarchy_list();
        if (chunks.length == 0) return;

        const chunk = chunks[0];
        const aggr_name = chunk.tree.data.name;

        const table_selection = into_selection
            .selectAll("table#layout_settings")
            .data([null]);
        const table_enter = table_selection
            .enter()
            .append("table")
            .attr("id", "layout_settings");

        let row_enter = table_enter.append("tr");
        row_enter.append("td").text("Aggregation Name");
        row_enter.append("td").text(aggr_name);

        row_enter = table_enter.append("tr");
        row_enter.append("td").text("Layout origin");
        row_enter.append("td").attr("id", "layout_origin");

        row_enter = table_enter.append("tr");
        row_enter
            .append("td")
            .append("input")
            .attr("type", "button")
            .classed("button", true)
            .attr("value", "Save this layout")
            .style("margin-top", null)
            .style("margin-bottom", null)
            .style("width", "100%")
            .on("click", () => {
                this._save_explicit_layout_clicked();
            });

        row_enter
            .append("td")
            .append("input")
            .attr("type", "button")
            .classed("button", true)
            .attr("value", "Use auto-generated layout")
            .attr("id", "remove_explicit_layout")
            .style("margin-top", null)
            .style("margin-bottom", null)
            .style("width", "100%")
            // TODO: fix this css
            .style("margin-right", "-4px")
            .on("click", () => {
                this._delete_explicit_layout_clicked();
            });

        const table = table_enter.merge(table_selection);
        table.select("#layout_origin").text(chunk.layout_settings.origin_info);

        const explicit_set = chunk.layout_settings.origin_type == "explicit";
        table
            .select("input#remove_explicit_layout")
            .classed("disabled", !explicit_set)
            .attr("disabled", explicit_set ? null : true);
    }

    _render_layout_configuration(into_selection) {
        (
            this._world.viewport.get_layer("nodes") as LayeredNodesLayer
        ).render_line_style(into_selection);

        const layers = this._world.viewport.get_layers();
        const configurable_layers: ToggleableLayer[] = [];
        for (const idx in layers) {
            const layer = layers[idx];
            if (layer instanceof ToggleableLayer)
                configurable_layers.push(layer);
        }

        const table_selection = into_selection
            .selectAll("table#overlay_configuration")
            .data([null])
            .style("width", "100%");
        const table_enter = table_selection
            .enter()
            .append("table")
            .attr("id", "overlay_configuration")
            .style("width", "100%")
            .on("change", event =>
                this._overlay_checkbox_options_changed(event)
            );

        const row_enter = table_enter.append("tr").classed("header", true);
        row_enter.append("th").text("");
        row_enter.append("th").text("Active");
        row_enter.append("th").text("Configurable");

        const table = table_enter.merge(table_selection);

        // TODO: fixme
        table.selectAll(".configurable_overlay").remove();
        const current_overlay_config =
            this._world.viewport.get_overlay_configs();
        const rows = table
            .selectAll("tr.configurable_overlay")
            .data(configurable_layers);
        const rows_enter = rows
            .enter()
            .append("tr")
            .classed("configurable_overlay", true);

        rows_enter
            .append("td")
            .text(d => d.name())
            .classed("noselect", true);
        const elements = ["active", "configurable"];
        for (const idx in elements) {
            const element = elements[idx];
            rows_enter
                .append("td")
                .style("text-align", "center")
                .append("input")
                .attr("option_id", () => element)
                .attr("overlay_id", d => d.id())
                .attr("type", "checkbox")
                .merge(rows_enter)
                .property("checked", d => {
                    if (!current_overlay_config[d.id()]) return false;
                    return current_overlay_config[d.id()][element];
                });
        }
    }

    _render_layout_history(history_selection): void {
        const icons = [
            {
                icon: "icon_undo.svg",
                id: "undo",
                title: "Undo",
                handler: () => this._move_in_history(1),
            },
            {
                icon: "icon_redo.svg",
                id: "redo",
                title: "Redo",
                handler: () => this._move_in_history(-1),
            },
        ];

        const icon_selection = history_selection
            .selectAll("img.icon")
            .data(icons);

        icon_selection
            .enter()
            .append("img")
            .classed("icon", true)
            .classed("box", true)
            .attr("id", d => d.id)
            .attr("title", d => d.title)
            .attr("src", d => "themes/facelift/images/" + d.icon)
            .on("click", (event, d) => d.handler())
            .merge(icon_selection);

        if (this._world.layout_manager.layout_applier._undo_history.length == 0)
            this._world.layout_manager.layout_applier.create_undo_step();

        this._update_history_icons();
    }

    _update_history_icons(): void {
        const history_icons = this.div_selection().select("#history_icons");
        const end_offset =
            this._world.layout_manager.layout_applier._undo_end_offset;
        const history_length =
            this._world.layout_manager.layout_applier._undo_history.length;
        history_icons
            .selectAll("#undo")
            .classed("disabled", history_length - end_offset <= 1);
        history_icons.selectAll("#redo").classed("disabled", end_offset == 0);
    }

    _move_in_history(step_direction: number): void {
        const total_length =
            this._world.layout_manager.layout_applier._undo_history.length;
        if (total_length == 0) return;

        const new_index =
            total_length -
            1 -
            this._world.layout_manager.layout_applier._undo_end_offset -
            step_direction;
        if (new_index > total_length - 1 || new_index < 0) return;

        this._world.layout_manager.layout_applier._undo_end_offset +=
            step_direction;

        const layout_settings = JSON.parse(
            JSON.stringify(
                this._world.layout_manager.layout_applier._undo_history[
                    new_index
                ]
            )
        );
        this._world.viewport.get_hierarchy_list().forEach(node_chunk => {
            node_chunk.layout_settings = layout_settings;
            // TODO: check this change
            node_chunk.layout_instance = null;
            //            if (layout_instance)
            //                delete node_chunk.layout_instance;
        });

        this._update_history_icons();
        this._world.layout_manager.layout_applier.apply_all_layouts();
    }

    fetch_all_layouts() {
        this._world.force_simulation.restart_with_alpha(0.5);
        // d3.json("ajax_get_all_bi_template_layouts.py", {credentials: "include"}).then((json_data)=>this.update_available_layouts(json_data.result))
    }

    update_available_layouts(layouts): void {
        this._world.layout_manager.layout_applier.layouts = layouts;
        let choices = [""];
        choices = choices.concat(Object.keys(layouts));

        choices.sort();
        const choice_selection =
            this.div_selection().select("#available_layouts");

        let active_id: null | string = null;
        if (this._world.layout_manager.layout_applier.current_layout_group.id)
            active_id =
                this._world.layout_manager.layout_applier.current_layout_group
                    .id;
        else if (choices.length > 0) active_id = choices[0];

        this.add_dropdown_choice(choice_selection, choices, active_id, event =>
            this.layout_changed_callback(event)
        );

        if (active_id)
            this.div_selection()
                .select("#layout_name")
                .property("value", active_id);
        this.update_save_layout_button();
    }

    layout_changed_callback(event): void {
        const selected_id = event.target.value;
        this._world.layout_manager.layout_applier.apply_layout_id(selected_id);
        const current_style = this.layout_style_configuration().current_style;
        if (current_style)
            this.layout_style_configuration().show_style_configuration(
                current_style
            );
        this.div_selection()
            .select("#layout_name")
            .property("value", selected_id);
        this.update_content();
        this.update_save_layout_button();
    }

    // TODO: check typing
    _overlay_checkbox_options_changed(event): void {
        const current_overlay_configs =
            this._world.viewport.get_overlay_configs();
        const checkbox = d3.select(event.target);
        const checked = checkbox.property("checked");
        const option_id = checkbox.attr("option_id");
        const overlay_id = checkbox.attr("overlay_id");

        const overlay_config = current_overlay_configs[overlay_id] || {};
        overlay_config[option_id] = checked;
        this._world.viewport.set_overlay_config(overlay_id, overlay_config);
    }

    _render_layout_management(into_selection: d3SelectionDiv): void {
        into_selection.selectAll("table#layout_management").data([null]);

        into_selection
            .selectAll("#template_headline")
            .data([null])
            .enter()
            .append("h2")
            .attr("id", "template_headline")
            .text("Layout templates");

        const table_selection = into_selection
            .selectAll("table#template_configuration")
            .data([null]);
        const table_enter = table_selection
            .enter()
            .append("table")
            .attr("id", "template_configuration");

        // Dropdown choice and delete button
        let row_enter = table_enter.append("tr");
        const td_enter = row_enter.append("td").attr("id", "available_layouts");
        this.add_dropdown_choice(td_enter, [], null, event =>
            this.layout_changed_callback(event)
        );
        row_enter
            .append("td")
            .append("input")
            .attr("type", "button")
            .classed("button", true)
            .style("width", "100%")
            .attr("value", "Delete template")
            .on("click", () => {
                const selected_layout = this.div_selection()
                    .select("#available_layouts")
                    .select("select")
                    .property("value");
                if (!selected_layout) return;
                this._world.layout_manager.delete_layout_id(selected_layout);
            });

        // Text input and save button
        row_enter = table_enter.append("tr");
        row_enter
            .append("td")
            .append("input")
            .attr("value", "")
            .attr("id", "layout_name")
            .style("width", "100%")
            .style("box-sizing", "border-box")
            .on("input", () => this.update_save_layout_button())
            .on("keydown", event => {
                const save_button = this.div_selection().select("#save_button");
                if (save_button.attr("disabled")) return;
                if (event.keyCode == 13) {
                    this._save_layout_clicked();
                }
            });

        row_enter
            .append("td")
            .append("input")
            .attr("type", "button")
            .classed("button", true)
            .style("width", "100%")
            .attr("id", "save_button")
            .attr("value", "Save template")
            .on("click", () => this._save_layout_clicked());
        table_enter
            .append("tr")
            .append("td")
            .attr("colspan", "2")
            .attr("id", "infotext")
            .text("");
    }

    update_save_layout_button() {
        const dropdown_id = this.div_selection()
            .select("#available_layouts")
            .select("select")
            .property("value")
            .trim();
        const input_id = this.div_selection()
            .select("#layout_name")
            .property("value")
            .trim();
        const button = this.div_selection().select("#save_button");
        const infotext = this.div_selection().select("#infotext");
        infotext.text("");

        if (input_id == "") {
            button.attr("disabled", true);
            button.classed("disabled", true);
            button.attr("value", "Save template");
        } else if (dropdown_id == input_id) {
            button.attr("disabled", null);
            button.classed("disabled", false);
            button.attr("value", "Save template");
        } else if (
            Object.keys(
                this._world.layout_manager.layout_applier.layouts
            ).indexOf(input_id) == -1
        ) {
            button.attr("disabled", null);
            button.classed("disabled", false);
            button.attr("value", "Save as new template");
        } else {
            button.attr("disabled", true);
            button.classed("disabled", true);
            button.attr("value", "Save as");
            infotext
                .text("Can not override existing layout")
                .style("color", "red");
        }
    }

    _save_layout_clicked() {
        const new_id = this.div_selection()
            .select("#layout_name")
            .property("value");
        const current_layout_group =
            this._world.layout_manager.layout_applier.get_current_layout_group();
        const new_layout = {};
        new_layout[new_id] = current_layout_group;
        // @ts-ignore
        this._world.layout_manager.save_layout_template(new_layout);
        this._world.layout_manager.layout_applier.current_layout_group.id =
            new_id;
    }

    _save_explicit_layout_clicked() {
        const aggr_name =
            this._world.viewport.get_hierarchy_list()[0].tree.data.name;
        const current_layout_group =
            this._world.layout_manager.layout_applier.get_current_layout_group();
        const new_layout: {[name: string]: SerializedNodevisLayout} = {};
        new_layout[aggr_name] = current_layout_group;
        // @ts-ignore
        this._world.layout_manager.save_layout_for_aggregation(
            new_layout,
            aggr_name
        );
    }

    _delete_explicit_layout_clicked() {
        const node_chunks = this._world.viewport.get_hierarchy_list();
        const aggr_name = node_chunks[0].tree.data.name;
        node_chunks.forEach(chunk => {
            chunk.layout_instance = null;
        });
        this._world.layout_manager.delete_layout_for_aggregation(aggr_name);
    }

    add_text_input(into_selection, value) {
        let input = into_selection.selectAll("input").data([""]);
        input = input.enter().append("input").merge(input);
        input.attr("type", "text").attr("value", value);
    }

    add_dropdown_choice(
        into_selection,
        choices,
        default_choice,
        callback_function
    ) {
        let select = into_selection.selectAll("select").data([null]);
        select = select
            .enter()
            .append("select")
            .merge(select)
            .style("width", "100%");

        let options = select
            .on("change", callback_function)
            .selectAll("option")
            .data(choices);
        options.exit().remove();
        options = options.enter().append("option").merge(options);

        options
            .property("value", d => d)
            .property("selected", d => d == default_choice)
            .text(d => d);
    }

    render_table(selection, table_data) {
        let table = selection.selectAll("table").data([""]);
        table = table.enter().append("table").merge(table);

        if (table_data.headers) {
            let thead = table.selectAll("thead").data([""]);
            thead = thead.enter().append("thead").append("tr").merge(thead);
            // append the header row
            const th = thead.selectAll("th").data(table_data.headers);
            th.enter()
                .append("th")
                .merge(th)
                .text(d => d);
            th.exit().remove();
        }

        let tbody = table.selectAll("tbody").data([""]);
        tbody = tbody.enter().append("tbody").merge(tbody);

        let tr = tbody.selectAll("tr").data(table_data.rows, d => d);
        tr.exit().remove();
        tr = tr.enter().append("tr").merge(tr);

        tr.selectAll("td")
            .remove()
            .selectAll("td")
            .data(
                d => d,
                d => d
            );
    }
}

class LayoutingMouseEventsOverlay {
    _world: NodevisWorld;
    drag: d3.DragBehavior<any, any, any>;
    _dragged_node: d3.Selection<any, any, any, any> | null = null;
    _drag_start_x = 0;
    _drag_start_y = 0;

    constructor(world: NodevisWorld) {
        this._world = world;
        this.drag = d3
            .drag()
            .on("start.drag", event => this._dragstarted(event))
            .on("drag.drag", event => this._dragging(event))
            .on("end.drag", event => this._dragended(event));
    }

    update_data() {
        this._world.nodes_layer
            .get_svg_selection()
            .selectAll(".node_element")
            .call(this.drag);
    }

    _dragstarted(event) {
        if (!this._world.layout_manager.is_node_drag_allowed()) return;
        event.sourceEvent.stopPropagation();
        this._dragged_node = d3.select(event.sourceEvent.target);
        const dragged_node_datum = this._dragged_node.datum();
        if (!dragged_node_datum) return;

        this._apply_drag_force(dragged_node_datum, event.x, event.y);
        this._drag_start_x = event.x;
        this._drag_start_y = event.y;

        const use_style = dragged_node_datum.data.use_style;
        if (use_style) {
            this._world.layout_manager.toolbar_plugin
                .layout_style_configuration()
                .show_style_configuration(use_style);
        } else {
            this._world.layout_manager.layout_applier._convert_node(
                dragged_node_datum,
                LayoutStyleFixed
            );
        }

        this._world.layout_manager.dragging = true;
    }

    _apply_drag_force(node: NodevisNode, x, y) {
        node.data.node_positioning["drag"] = {};
        const force = node.data.node_positioning["drag"];
        force.use_transition = false;
        if (node.data.use_style) force.weight = 1000;
        else force.weight = 500;
        force.fx = x;
        force.fy = y;
    }

    _dragging(event) {
        if (
            this._dragged_node == null ||
            !this._world.layout_manager.is_node_drag_allowed()
        )
            return;

        const dragged_node_datum = this._dragged_node.datum();
        if (!dragged_node_datum) return;

        if (dragged_node_datum.data.use_style) {
            if (
                !dragged_node_datum.data.use_style.style_config.options
                    .detach_from_parent
            ) {
                dragged_node_datum.data.use_style.style_config.options.detach_from_parent =
                    true;
                // TODO: fix refresh
                this._world.layout_manager.toolbar_plugin
                    .layout_style_configuration()
                    .show_style_configuration(null);
                this._world.layout_manager.toolbar_plugin
                    .layout_style_configuration()
                    .show_style_configuration(
                        dragged_node_datum.data.use_style
                    );
            }
        }

        let scale = 1.0;
        const delta_x = event.x - this._drag_start_x;
        const delta_y = event.y - this._drag_start_y;

        const last_zoom = this._world.viewport.last_zoom;
        scale = 1 / last_zoom.k;

        this._apply_drag_force(
            dragged_node_datum,
            this._drag_start_x + delta_x * scale,
            this._drag_start_y + delta_y * scale
        );

        this._world.force_simulation.restart_with_alpha(0.5);
        if (dragged_node_datum.data.use_style) {
            dragged_node_datum.data.use_style.force_style_translation();
            dragged_node_datum.data.use_style.translate_coords();
        }
        compute_node_position(dragged_node_datum);

        // TODO: EXPERIMENTAL, will be removed in later commit
        for (const idx in this._world.layout_manager._active_styles) {
            this._world.layout_manager._active_styles[idx].update_data();
        }

        // TODO: translate and compute node is overkill for a simple drag procedure
        this._world.layout_manager.translate_layout();
        this._world.layout_manager.compute_node_positions();
        this._world.viewport.update_gui_of_layers();
    }

    _dragended(_event) {
        this._world.layout_manager.dragging = false;
        if (
            this._dragged_node == null ||
            !this._world.layout_manager.is_node_drag_allowed()
        )
            return;

        const dragged_node_datum = this._dragged_node.datum();
        if (!dragged_node_datum) return;

        if (dragged_node_datum.data.use_style) {
            const new_position =
                this._world.layout_manager.get_viewport_percentage_of_node(
                    dragged_node_datum
                );
            dragged_node_datum.data.use_style.style_config.position =
                new_position;
            dragged_node_datum.data.use_style.force_style_translation();
        }

        if (
            dragged_node_datum.data.use_style &&
            dragged_node_datum.data.use_style.constructor.prototype
                .class_name == "fixed"
        ) {
            dragged_node_datum.data.use_style.fix_node(dragged_node_datum);
        }

        delete dragged_node_datum.data.node_positioning["drag"];
        this._world.layout_manager.translate_layout();

        compute_node_position(dragged_node_datum);
        this._world.layout_manager.create_undo_step();
    }
}

class LayoutApplier {
    _world: NodevisWorld;
    layout_style_factory: LayoutStyleFactory;
    current_layout_group: NodeVisualizationLayout;

    layouts = {}; // Each chunk has its own layout
    _align_layouts = true;
    _undo_history: LayoutHistoryStep[] = [];
    _undo_end_offset = 0;

    constructor(world: NodevisWorld) {
        this._world = world;
        this.layout_style_factory = new LayoutStyleFactory(this._world);
        // TODO: Check type: looks broken
        this.current_layout_group = new NodeVisualizationLayout(
            this._world.viewport,
            "default"
        );
    }

    get_context_menu_elements(node: NodevisNode | null): ContextMenuElement[] {
        if (
            (node &&
                !(
                    node.data.node_type == "bi_leaf" ||
                    node.data.node_type == "bi_aggregator"
                )) ||
            this._world.layout_manager._world.current_datasource !=
                "bi_aggregations"
        ) {
            return [];
        }

        const elements: ContextMenuElement[] = [];
        const styles = this.layout_style_factory.get_styles();
        for (const [_key, style] of Object.entries(styles)) {
            if (node) {
                elements.push({
                    text: "Convert to " + style.description,
                    on: () => this._convert_node(node, style),
                    href: "",
                    img: "themes/facelift/images/icon_aggr.svg",
                });
            } else {
                elements.push({
                    text: "Convert all nodes to " + style.description,
                    on: () => this._convert_all(style),
                    href: "",
                    img: "themes/facelift/images/icon_aggr.svg",
                });
            }
        }
        if (node && node.data.use_style) {
            elements.push({
                text: "Remove style",
                on: () => this._convert_node(node, null),
                href: "",
                img: "themes/facelift/images/icon_aggr.svg",
            });
        }

        return elements;
    }

    _convert_node(node, style_class) {
        const chunk_layout = node.data.chunk.layout_instance;
        const current_style = node.data.use_style;

        // Do nothing on same style
        if (
            current_style &&
            style_class != null &&
            current_style.type() == style_class.prototype.type()
        )
            return;

        // Remove existing style
        if (current_style) {
            chunk_layout.remove_style(current_style);
        }

        let new_style: AbstractLayoutStyle | null = null;
        if (style_class != null) {
            new_style = this.layout_style_factory.instantiate_style_class(
                style_class,
                node,
                this._world.layout_manager.get_div_selection()
            );
            chunk_layout.save_style(new_style.style_config);
        }

        this._world.layout_manager.layout_applier.apply_all_layouts();
        if (new_style) new_style.update_style_indicator();
        this._world.layout_manager.toolbar_plugin
            .layout_style_configuration()
            .show_style_configuration(new_style);
        this._world.layout_manager.create_undo_step();
    }

    _convert_all(style_class) {
        const used_style: AbstractLayoutStyle[] = [];
        const current_style: AbstractLayoutStyle | null = null;
        this._world.viewport.get_hierarchy_list().forEach(node_chunk => {
            const layout_instance = node_chunk.layout_instance;
            if (layout_instance == null) return;
            layout_instance.clear_styles();
            if (style_class == LayoutStyleFixed) {
                node_chunk.nodes.forEach(node => {
                    const scoped_instance = node_chunk.layout_instance;
                    if (scoped_instance == null) return;
                    scoped_instance.save_style(
                        this.layout_style_factory.instantiate_style_class(
                            style_class,
                            node,
                            this._world.layout_manager.get_div_selection()
                        ).style_config
                    );
                });
            } else {
                const new_style =
                    this.layout_style_factory.instantiate_style_class(
                        style_class,
                        node_chunk.nodes[0],
                        this._world.layout_manager.get_div_selection()
                    );
                layout_instance.save_style(new_style.style_config);
            }
        });

        this.apply_all_layouts();
        const last_style = used_style.at(-1);
        if (last_style) {
            last_style.update_style_indicator();
            this._world.layout_manager.toolbar_plugin
                .layout_style_configuration()
                .show_style_configuration(current_style);
        }
        this._world.layout_manager.create_undo_step();
    }

    create_undo_step(): void {
        this._undo_history = this._undo_history.slice(
            0,
            this._undo_history.length - this._undo_end_offset
        );
        this._undo_end_offset = 0;
        this._undo_history.push(this._create_manual_layout_settings());
    }

    _create_manual_layout_settings(): LayoutHistoryStep {
        const current_layout_group =
            this._world.layout_manager.layout_applier.get_current_layout_group();
        const layout_settings = {
            origin_info: "Explicit set",
            origin_type: "explicit",
            config: JSON.parse(JSON.stringify(current_layout_group)),
        };
        return layout_settings;
    }

    apply_layout_id(layout_id) {
        this._world.viewport.get_hierarchy_list().forEach(chunk => {
            const new_layout = new NodeVisualizationLayout(
                this._world.viewport,
                layout_id
            );
            if (layout_id != "") {
                const config = JSON.parse(
                    JSON.stringify(this.layouts[layout_id])
                );
                config.id = layout_id;
                new_layout.deserialize(config);
            }
            chunk.layout_instance = new_layout;
        });
        // TODO: cleanup
        this.apply_multiple_layouts(
            this._world.viewport._node_chunk_list,
            true
        );
    }

    apply_all_layouts() {
        this.apply_multiple_layouts(this._world.viewport.get_hierarchy_list());
    }

    apply_multiple_layouts(node_chunk_list, update_layouts = true) {
        let nodes_with_style: NodeWithStyle[] = [];

        let used_layout_id = null;

        node_chunk_list.forEach(node_chunk => {
            const layout_settings = node_chunk.layout_settings;
            const node_matcher = new NodeMatcher([node_chunk]);
            // TODO: When removing an explicit layout, the new layout should replace the explicit one
            if (!node_chunk.layout_instance) {
                node_chunk.layout_instance = new NodeVisualizationLayout(
                    this,
                    "default"
                );

                // Add styles from aggregation rules only during instance creation
                if (layout_settings.config) {
                    if (!layout_settings.config.ignore_rule_styles)
                        node_chunk.nodes.forEach(node => {
                            if (
                                node.data.rule_layout_style != undefined &&
                                node.data.rule_layout_style.type != "none"
                            ) {
                                const style_name =
                                    node.data.rule_layout_style.type;
                                const style_options =
                                    node.data.rule_layout_style.style_config;
                                const new_style =
                                    this.layout_style_factory.instantiate_style_name(
                                        style_name,
                                        node,
                                        this._world.layout_manager.get_div_selection()
                                    );
                                new_style.style_config.options = style_options;

                                node_chunk.layout_instance.save_style(
                                    new_style.style_config
                                );
                                nodes_with_style.push({
                                    node: node,
                                    style: new_style.style_config,
                                });
                            }
                        });
                }

                if (layout_settings.origin_type) {
                    // Add generic and explicit styles
                    if (layout_settings.origin_type == "default_template") {
                        const default_style =
                            this.layout_style_factory.instantiate_style_name(
                                layout_settings.default_id,
                                node_chunk.tree,
                                this._world.layout_manager.get_div_selection()
                            );
                        default_style.style_config.position = {x: 50, y: 50};
                        node_chunk.layout_instance.save_style(
                            default_style.style_config
                        );
                    } else {
                        node_chunk.layout_instance.deserialize(
                            layout_settings.config
                        );
                        if (node_chunk.template_layout_id)
                            used_layout_id = node_chunk.template_layout_id;
                    }
                }
            }

            nodes_with_style = nodes_with_style.concat(
                this.find_nodes_for_layout(
                    node_chunk.layout_instance,
                    node_matcher
                )
            );
        });

        // Sort styles
        nodes_with_style.sort(function (a, b) {
            if (a.node.depth > b.node.depth) return 1;
            if (a.node.depth < b.node.depth) return -1;
            return 0;
        });

        // Add boxed style indicators
        const grouped_styles = this._get_grouped_styles(nodes_with_style);

        nodes_with_style = grouped_styles.concat(nodes_with_style);

        this._update_node_specific_styles(nodes_with_style);

        // @ts-ignore
        this.current_layout_group = this.get_current_layout_group();
        // TODO: fix id handling
        if (used_layout_id) this.current_layout_group.id = used_layout_id;

        if (this._world.layout_manager.edit_layout)
            this._world.layout_manager.allow_layout_updates = false;

        if (update_layouts)
            this._world.layout_manager._world.force_simulation.restart_with_alpha(
                2
            );
    }

    _get_grouped_styles(nodes_with_style) {
        // Cycle through the sorted styles and add the box_leaf_nodes hint
        nodes_with_style.forEach(entry => {
            const box_leafs = entry.style.options.box_leaf_nodes == true;
            entry.node.each(node => {
                node.data.box_leaf_nodes = box_leafs;
            });
            entry.node.data.box_leaf_nodes = box_leafs;
        });
        // Apply styles
        const box_candidates: NodevisNode[] = [];
        this._world.viewport.get_hierarchy_list().forEach(node_chunk => {
            node_chunk.nodes.forEach(node => {
                if (!node._children) return;
                if (!node.data.box_leaf_nodes) return;
                node.count();
                if (node.value == node._children.length) {
                    let child_with_childs = false;
                    node._children.forEach(child => {
                        if (child._children) child_with_childs = true;
                    });
                    if (!child_with_childs) box_candidates.push(node);
                }
            });
        });

        // Cleanup box_leaf_nodes hint
        nodes_with_style.forEach(entry =>
            entry.node.descendants().forEach(d => delete d.data.box_leaf_nodes)
        );

        const grouped_styles: NodeWithStyle[] = [];

        // Add styles for box candidates
        box_candidates.forEach(node => {
            const new_style = this.layout_style_factory.instantiate_style_name(
                "block",
                node,
                this._world.layout_manager.get_div_selection()
            );
            new_style.style_config.options = {};
            grouped_styles.push({node: node, style: new_style.style_config});
        });
        return grouped_styles;
    }

    align_layouts(nodes_with_style) {
        this._world.viewport.get_hierarchy_list().forEach(node_chunk => {
            const bounding_rect = get_bounding_rect(node_chunk.nodes);
            const translate_perc = {
                x:
                    -(
                        (bounding_rect.x_min -
                            (node_chunk.coords.width - bounding_rect.width) /
                                2) /
                        node_chunk.coords.width
                    ) * 100,
                y:
                    -(
                        (bounding_rect.y_min -
                            (node_chunk.coords.height - bounding_rect.height) /
                                2) /
                        node_chunk.coords.height
                    ) * 100,
            };

            node_chunk.nodes.forEach(node => {
                const use_style = node.data.use_style;
                if (use_style == null) return;

                const position = use_style.style_config.position;
                if (position == null) return;

                position.x += translate_perc.x;
                position.y += translate_perc.y;
            });
        });
        this._update_node_specific_styles(nodes_with_style);
    }

    _update_node_specific_styles(nodes_with_style: NodeWithStyle[]): void {
        const filtered_nodes_with_style: NodeWithStyle[] = [];
        const used_nodes: NodevisNode[] = [];
        for (const idx in nodes_with_style) {
            const config = nodes_with_style[idx];
            if (used_nodes.indexOf(config.node) >= 0) {
                log(
                    7,
                    "  filtered duplicate style assignment" +
                        compute_style_id(
                            layout_style_class_registry.get_class(
                                config.style.type
                            ),
                            config.node
                        )
                );
                continue;
            }
            used_nodes.push(config.node);
            filtered_nodes_with_style.push(nodes_with_style[idx]);
        }

        const node_styles = this._world.layout_manager.styles_selection
            .selectAll<SVGGElement, NodeWithStyle>(".layout_style")
            .data(filtered_nodes_with_style, d => {
                // TODO: check if prototype is not required
                return compute_style_id(
                    layout_style_class_registry.get_class(d.style.type),
                    d.node
                );
            });

        node_styles
            .exit<NodeWithStyle>()
            .each(d => {
                log(
                    7,
                    "  removing style " +
                        compute_style_id(
                            layout_style_class_registry.get_class(d.style.type),
                            d.node
                        )
                );
                const use_style = d.node.data.use_style;
                if (use_style)
                    this._world.layout_manager.remove_active_style(use_style);
                compute_node_position(d.node);
            })
            .remove();

        node_styles
            .enter()
            .append("g")
            .classed("layout_style", true)
            .each((d, idx, nodes) => {
                log(
                    7,
                    "  create style " +
                        compute_style_id(
                            layout_style_class_registry.get_class(d.style.type),
                            d.node
                        )
                );
                if (d.node.data.use_style) {
                    this._world.layout_manager.remove_active_style(
                        d.node.data.use_style
                    );
                }
                const new_style = this.layout_style_factory.instantiate_style(
                    d.style,
                    d.node,
                    d3.select(nodes[idx])
                );
                this._world.layout_manager.add_active_style(new_style);
            })
            .merge(node_styles)
            .each(d => {
                log(
                    7,
                    "  updating style " +
                        compute_style_id(
                            layout_style_class_registry.get_class(d.style.type),
                            d.node
                        )
                );
                const style_id = compute_style_id(
                    layout_style_class_registry.get_class(d.style.type),
                    d.node
                );
                const style =
                    this._world.layout_manager.get_active_style(style_id);
                d.node.data.use_style = style;
                d.node.data.use_style.style_config.options = d.style.options;
                d.node.data.use_style.style_config.position = d.style.position;
                d.node.data.use_style.style_root_node = d.node;
                this._compute_force_options(d.node.data.chunk.tree);
                d.node.data.use_style.force_style_translation();

                if (style.type() != "force") {
                    const position = style.style_config.position;
                    if (position == null) return;

                    const abs_coords =
                        this._world.layout_manager.get_absolute_node_coords(
                            {x: position.x, y: position.y},
                            d.node
                        );
                    d.node.fx = abs_coords.x;
                    d.node.fy = abs_coords.y;
                    d.node.x = abs_coords.x;
                    d.node.y = abs_coords.y;
                }
            });

        // Compute force options an initialize transition_info
        this._world.viewport.get_hierarchy_list().forEach(node_chunk => {
            this._compute_force_options(node_chunk.tree);
        });

        const all_nodes = this._world.viewport.get_all_nodes();
        const all_links = this._world.viewport.get_all_links();
        this._world.force_simulation.update_nodes_and_links(
            all_nodes,
            all_links
        );
        this._world.layout_manager.update_data();

        // Experimental
        if (this._align_layouts) {
            this._align_layouts = false;
            this.align_layouts(nodes_with_style);
        }
    }

    _compute_force_options(node) {
        log(6, "LayoutManager: _compute_force_options");
        let new_force_options: ForceOptions;
        if (
            node.data.use_style &&
            node.data.use_style.constructor.class_name == "force"
        )
            new_force_options = node.data.use_style.style_config.options;
        else if (node.parent)
            new_force_options = node.parent.data.force_options;
        else {
            const force_style =
                this.layout_style_factory.instantiate_style_class(
                    LayoutStyleForce,
                    node.data.chunk.tree,
                    this._world.layout_manager.get_div_selection()
                );
            new_force_options = force_style.style_config
                .options as unknown as ForceOptions;
        }

        node.data.force_options = new_force_options;
        if (!node._children) return;

        node._children.forEach(child => this._compute_force_options(child));
    }

    find_nodes_for_layout(layout, node_matcher: NodeMatcher): NodeWithStyle[] {
        const nodes: NodeWithStyle[] = [];
        layout.style_configs.forEach(style => {
            if (!style.matcher) return;

            const node = node_matcher.find_node(style.matcher);
            if (!node) return;

            nodes.push({node: node, style: style});
        });
        return nodes;
    }

    get_current_layout_group(): SerializedNodevisLayout {
        const chunk_layouts: SerializedNodevisLayout[] = [];
        this._world.viewport.get_hierarchy_list().forEach(node_chunk => {
            if (node_chunk.layout_instance) {
                chunk_layouts.push(node_chunk.layout_instance.serialize());
            }
        });

        if (chunk_layouts.length == 0) {
            // @ts-ignore
            return this.current_layout_group;
        }

        const chunk_layout = chunk_layouts[0];
        const style_configs: StyleConfig[] = [];
        for (const idx in this._world.layout_manager._active_styles) {
            style_configs.push(
                this._world.layout_manager._active_styles[idx].style_config
            );
        }
        return {
            style_configs: style_configs,
            reference_size: {
                width: this._world.viewport.width,
                height: this._world.viewport.height,
            },
            line_config: chunk_layout.line_config,
        };
    }
}

interface NodeWithStyle {
    node: NodevisNode;
    style: StyleConfig;
}
