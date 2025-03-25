/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import type {D3DragEvent, DragBehavior, Selection} from "d3";
import {drag, select} from "d3";

import {LayoutAggregations} from "./aggregations";
import type {AbstractNodeVisConstructor, LayerSelections} from "./layer_utils";
import {FixLayer, layer_class_registry} from "./layer_utils";
import type {LayeredNodesLayer} from "./layers";
import {LayoutStyleFixed, LayoutStyleHierarchy} from "./layout_styles";
import type {
    AbstractLayoutStyle,
    LineStyle,
    NodePositioning,
    SerializedNodevisLayout,
    StyleConfig,
    StyleOptionSpec,
    StyleOptionValues,
} from "./layout_utils";
import {
    compute_node_position,
    compute_style_id,
    layout_style_class_registry,
    LayoutStyleFactory,
    NodeVisualizationLayout,
    render_style_options,
} from "./layout_utils";
import {get} from "./texts";
import {LayoutTopology} from "./topology";
import type {
    ContextMenuElement,
    Coords,
    d3SelectionDiv,
    d3SelectionG,
    NodeConfig,
    NodevisNode,
    NodevisWorld,
    Rectangle,
} from "./type_defs";
import {
    DefaultTransition,
    log,
    NodeMatcher,
    RadioGroupOption,
    render_radio_group,
} from "./utils";
import type {Viewport} from "./viewport";

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

class LayoutHistory {
    _layout_manager: LayoutManagerLayer;
    _selection: d3SelectionDiv;

    _undo_history: SerializedNodevisLayout[] = [];
    _undo_end_offset = 0;

    constructor(layout_manager: LayoutManagerLayer, selection: d3SelectionDiv) {
        this._layout_manager = layout_manager;
        this._selection = selection;
    }

    length(): number {
        return this._undo_history.length;
    }

    create_undo_step(): void {
        this._undo_history = this._undo_history.slice(
            0,
            this._undo_history.length - this._undo_end_offset,
        );
        this._undo_end_offset = 0;
        this._undo_history.push(this._create_manual_layout_settings());
        this._update_history_icons();
    }

    _create_manual_layout_settings(): SerializedNodevisLayout {
        const serialized_layout = this._layout_manager.get_layout().serialize();
        const layout = JSON.parse(
            JSON.stringify(serialized_layout),
        ) as SerializedNodevisLayout;
        layout.origin_info = "Explicit set";
        layout.origin_type = "explicit";
        return layout;
    }

    render(): void {
        const icons_div = this._selection
            .selectAll<HTMLDivElement, null>("div#history_icons")
            .data([null])
            .join(enter =>
                enter
                    .insert("div", "div#line_style_config")
                    .attr("id", "history_icons")
                    .classed("noselect", true),
            );

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

        icons_div
            .selectAll<HTMLImageElement, unknown>("img.icon")
            .data(icons)
            .enter()
            .append("img")
            .classed("icon", true)
            .classed("box", true)
            .attr("id", d => d.id)
            .attr("title", d => d.title)
            .attr("src", d => "themes/facelift/images/" + d.icon)
            .on("click", (_event: Event, d) => d.handler());

        if (this.length() == 0) this.create_undo_step();

        this._update_history_icons();
    }

    _update_history_icons(): void {
        const end_offset = this._undo_end_offset;
        const history_length = this.length();
        this._selection!.selectAll("#undo").classed(
            "disabled",
            history_length - end_offset <= 1,
        );
        this._selection!.selectAll("#redo").classed(
            "disabled",
            end_offset == 0,
        );
    }

    _move_in_history(step_direction: number): void {
        const total_length = this._undo_history.length;
        if (total_length == 0) return;

        const new_index =
            total_length - 1 - this._undo_end_offset - step_direction;
        if (new_index > total_length - 1 || new_index < 0) return;

        this._undo_end_offset += step_direction;

        const layout_settings = JSON.parse(
            JSON.stringify(this._undo_history[new_index]),
        );

        this._layout_manager.update_layout(layout_settings);
        this._update_history_icons();
        this._layout_manager.apply_current_layout();
        this._layout_manager.hide_style_configuration();
    }
}

export class LayoutManagerLayer extends FixLayer {
    _mouse_events_overlay: LayoutingMouseEventsOverlay;
    layout_applier: LayoutApplier;
    _toolbar: LayoutingToolbar;
    _viewport: Viewport;

    // Edit tools
    edit_layout = false; // Indicates whether the layout manager is active
    _node_dragging_allowed = false; // If the user is able to drag nodes with the mouse

    // Instantiated styles
    _active_styles: Record<string, AbstractLayoutStyle> = {};

    // Register layout manager toolbar plugin

    styles_selection: d3SelectionG;
    dragging = false;

    skip_optional_transitions = false;

    _layout_settings: SerializedNodevisLayout | null = null;
    _layout: NodeVisualizationLayout = new NodeVisualizationLayout();

    show_force_config(): void {
        return this._viewport.show_force_config();
    }

    toggle_toolbar() {
        const new_state = !this._toolbar.active;
        new_state ? this._toolbar.enable() : this._toolbar.disable();
        return new_state;
    }
    get_layout(): NodeVisualizationLayout {
        return this._layout;
    }

    get_layout_settings(): SerializedNodevisLayout {
        return this._layout_settings!;
    }

    change_line_style(new_line_style: LineStyle): void {
        this._layout.line_config.style = new_line_style;
        this._viewport.get_nodes_layer().update_data();
        this._viewport.get_nodes_layer().update_gui(true);
    }

    show_style_configuration(new_style: AbstractLayoutStyle | null) {
        this._toolbar.layout_style_configuration.show_style_configuration(
            new_style,
        );
    }

    hide_style_configuration() {
        this._toolbar.layout_style_configuration.hide_configuration();
    }

    show_configuration(
        style_id: string,
        style_option_spec: StyleOptionSpec[],
        options: StyleOptionValues,
        options_changed_callback: (changed_options: StyleOptionValues) => void,
        reset_default_options_callback: (
            event: D3DragEvent<any, any, any>,
        ) => void,
    ) {
        this._toolbar.layout_style_configuration.show_configuration(
            style_id,
            style_option_spec,
            options,
            options_changed_callback,
            reset_default_options_callback,
        );
    }

    constructor(world: NodevisWorld, selections: LayerSelections) {
        super(world, selections);
        this._viewport = this._world.viewport;
        this._toolbar = new LayoutingToolbar(world, this, selections.div);

        // Register layout manager toolbar plugin
        this._mouse_events_overlay = new LayoutingMouseEventsOverlay(
            world,
            this,
        );
        this.layout_applier = new LayoutApplier(world, this);
        this.styles_selection = this._svg_selection
            .append("g")
            .attr("id", "hierarchies");
    }

    override class_name() {
        return "layout_manager";
    }

    override id(): string {
        return "layout_manager";
    }

    override z_index(): number {
        return 40;
    }

    override name(): string {
        return "Layout Manager";
    }

    create_undo_step(): void {
        this._toolbar._layout_history.create_undo_step();
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

    update_layout(layout_settings: SerializedNodevisLayout) {
        this._toolbar._layout_history.render();

        let force_config = this._viewport.get_default_force_config();
        this._layout_settings = layout_settings;
        if (Object.entries(layout_settings.force_config).length > 0)
            force_config = layout_settings.force_config;

        this._layout.deserialize(
            layout_settings,
            this._viewport.get_size(),
            force_config,
        );
    }

    apply_current_layout(trigger_force_simulation = true) {
        this.layout_applier.apply_layout(
            this._viewport._node_config,
            trigger_force_simulation,
        );
    }

    show_layout_options(): void {
        this.edit_layout = true;
        this.enable_node_dragging();
        this._mouse_events_overlay.update_data();
        // TODO: implement different edit indicator, e.g into the world
        this._viewport.get_layer("nodes")._svg_selection.classed("edit", true);
        this.update_style_indicators();
        // this._world.root_div.classed("edit_layout", true);
    }

    hide_layout_options(): void {
        this.edit_layout = false;
        this.disable_node_dragging();
        this._viewport.get_layer("nodes")._svg_selection.classed("edit", false);
        this.styles_selection
            .selectAll(".layout_style")
            .selectAll("*")
            .remove();
        this._div_selection
            .selectAll("div.style_overlay")
            // .selectAll("img")
            .remove();
        this.update_style_indicators(true);
    }

    enable_node_dragging(): void {
        this._node_dragging_allowed = true;
    }

    disable_node_dragging(): void {
        this._node_dragging_allowed = false;
    }

    is_node_drag_allowed(): boolean {
        return this._node_dragging_allowed;
    }

    override size_changed(): boolean {
        // TODO: check this
        //        node_visualization_layout_styles.force_simulation.size_changed()
        return false;
    }

    override update_data(): void {
        this._toolbar.update_layout_configuration();

        const sorted_styles: [number, AbstractLayoutStyle][] = [];
        for (const idx in this._active_styles) {
            sorted_styles.push([
                this._active_styles[idx].style_root_node.depth,
                this._active_styles[idx],
            ]);
        }

        // Sort styles, ordering them from leaf to root
        // Style in leaf needs to be computed first, since they have a size-impact on any parent style
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

    override update_gui(): void {
        for (const idx in this._active_styles) {
            this._active_styles[idx].update_gui();
        }
        this.update_style_indicators();
        this._render_viewport_markers();
    }

    _render_viewport_markers(): void {
        const size = this._viewport.get_size();
        const offset = 30;

        let edge_markers: Coords[] = [];
        if (this.edit_layout)
            edge_markers = [
                this._viewport.scale_to_zoom({x: offset, y: offset}),
                this._viewport.scale_to_zoom({
                    x: size.width - offset,
                    y: offset,
                }),
                this._viewport.scale_to_zoom({
                    x: size.width - offset,
                    y: size.height - offset,
                }),
                this._viewport.scale_to_zoom({
                    x: offset,
                    y: size.height - offset,
                }),
            ];
        this._svg_selection
            .selectAll<SVGCircleElement, Coords>("circle.edge_marker")
            .data(edge_markers)
            .join("circle")
            .classed("edge_marker", true)
            .attr("transform", d => "translate(" + d.x + "," + d.y + ")");
    }

    update_style_indicators(force = false): void {
        if (!force && !this.edit_layout) return;

        this._viewport.get_all_nodes().forEach(node => {
            if (node.data.use_style)
                node.data.use_style.update_style_indicator(this.edit_layout);
        });
    }

    translate_layout(): void {
        for (const idx in this._active_styles) {
            this._active_styles[idx].translate_coords();
        }
    }

    override zoomed(): void {
        show_viewport_information(this._viewport);
        if (!this.edit_layout) return;
        for (const idx in this._active_styles) {
            this._active_styles[idx].zoomed();
        }
    }

    get_viewport_percentage_of_node(node: NodevisNode): {x: number; y: number} {
        const coords = this._viewport.get_size();
        return {
            x: (100.0 * node.x) / coords.width,
            y: (100.0 * node.y) / coords.height,
        };
    }

    get_absolute_node_coords(perc_coords: Coords, size: Rectangle): Coords {
        return {
            x: (size.width * perc_coords.x) / 100,
            y: (size.height * perc_coords.y) / 100,
        };
    }

    get_node_positioning(node: NodevisNode): NodePositioning {
        if (node.data.node_positioning == null) {
            node.data.node_positioning = {};
        }
        return node.data.node_positioning;
    }

    compute_node_positions(): void {
        this._viewport.get_all_nodes().forEach(node => {
            compute_node_position(node);
        });
    }

    simulation_end_actions() {
        // Actions when the force simulation ends
        const nodes_layer = this._viewport.get_layer(
            "nodes",
        ) as LayeredNodesLayer;
        nodes_layer.simulation_end();
        const layout_settings = this.get_layout_settings();
        const delayed_styles = layout_settings.delayed_style_configs;
        if (delayed_styles) {
            const layout = this.get_layout();
            delete layout_settings["delayed_style_configs"];
            delayed_styles.forEach(style_config => {
                layout.save_style(style_config);
            });
        }

        nodes_layer.links_selection
            .selectAll("g.link_element path")
            .attr("in_transit", null);
        nodes_layer.links_selection
            .selectAll("g.link_element line")
            .attr("in_transit", null);
        nodes_layer.nodes_selection
            .selectAll("g.node_element")
            .attr("in_transit", null);
        if (delayed_styles) this.apply_current_layout();
    }
}

layer_class_registry.register(LayoutManagerLayer);

export class LayoutStyleConfiguration {
    _world: NodevisWorld;
    _style_config_selection: d3SelectionDiv;
    _style_options_selection: d3SelectionDiv;
    _previous_style_node_id: string | null = null;
    current_style: AbstractLayoutStyle | null = null;
    active_style_id: string | null = null;

    constructor(style_config_selection: d3SelectionDiv, world: NodevisWorld) {
        this._world = world;
        this._style_config_selection = style_config_selection;
        this._style_config_selection.style("display", "none");
        this._style_options_selection = this.setup_style_config();
    }

    setup_style_config(): d3SelectionDiv {
        const style_div = this._style_config_selection
            .append("div")
            .attr("id", "style_div");

        style_div
            .append("h2")
            .attr("id", "styleconfig_headline")
            .text(get("selected_style_configuration"));

        return style_div;
    }

    show_configuration(
        style_id: string,
        style_option_spec: StyleOptionSpec[],
        options: StyleOptionValues,
        options_changed_callback: (changed_options: StyleOptionValues) => void,
        reset_default_options_callback: (
            event: D3DragEvent<any, any, any>,
        ) => void,
    ) {
        if (style_option_spec.length == 0) {
            this.hide_configuration();
            return;
        }

        this.active_style_id = style_id;
        this._style_config_selection.style("display", null);
        render_style_options(
            style_id,
            this._style_options_selection,
            style_option_spec,
            options,
            options_changed_callback,
            reset_default_options_callback,
        );
    }

    hide_configuration() {
        this.current_style = null;
        this.active_style_id = null;
        this._style_config_selection.style("display", "none");
    }

    show_style_configuration(layout_style: AbstractLayoutStyle | null) {
        if (layout_style == null) {
            this.hide_configuration();
            return;
        }

        if (this._previous_style_node_id) {
            const gui_node = this._world.viewport
                .get_nodes_layer()
                .get_node_by_id(this._previous_style_node_id);
            gui_node
                .selection()
                .select("circle.style_indicator")
                .classed("focus", false);
        }
        if (layout_style.selection) {
            const new_node_id = layout_style.style_root_node.data.id;
            const gui_node = this._world.viewport
                .get_nodes_layer()
                .get_node_by_id(new_node_id);
            this._previous_style_node_id = new_node_id;
            gui_node
                .selection()
                .select("circle.style_indicator")
                .classed("focus", true);
        }

        this.show_configuration(
            layout_style.id(),
            layout_style.get_style_options(),
            layout_style.style_config.options,
            new_options => layout_style.changed_options(new_options),
            () => layout_style.reset_default_options(),
        );
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

function hide_viewport_information(mousemove_selection: d3SelectionDiv): void {
    mousemove_selection.on("mousemove.viewport_info", null);
}

function show_viewport_information(viewport: Viewport) {
    const selection = viewport.get_div_selection();
    const zoom = viewport.last_zoom;
    function setup_div() {
        const viewport_div = selection
            .selectAll("div#viewport_information")
            .data([null])
            .join(enter =>
                enter.append("div").attr("id", "viewport_information"),
            );
        const new_row = viewport_div
            .selectAll("tr")
            .data([["panning_info", "zoom_minus", "zoom_info", "zoom_plus"]])
            .join("table")
            .classed("noselect", true)
            .selectAll("tr")
            .data(d => [d])
            .enter()
            .append("tr");
        const panning_info_cell = new_row
            .append("td")
            .attr("id", "panning_info");
        panning_info_cell.append("div").text(get("panning"));
        panning_info_cell
            .append("div")
            .attr("id", "panning_value")
            .text("-7/10px");
        new_row
            .append("td")
            .attr("id", "zoom_minus")
            .text("-")
            .on("click", () => viewport.change_zoom(-10));
        const zoom_options_cell = new_row
            .append("td")
            .attr("id", "zoom_options");
        new_row
            .append("td")
            .attr("id", "zoom_plus")
            .text("+")
            .on("click", () => viewport.change_zoom(10));

        const zoom_select = zoom_options_cell
            .selectAll("select")
            .data([null])
            .join("select")
            .on("input", event => {
                if (event.target.value == "zoom_reset") viewport.zoom_reset();
                else if (event.target.value == "zoom_fit") viewport.zoom_fit();
                else if (event.target.value == "50%") viewport.set_zoom(50);
                else if (event.target.value == "100%") viewport.set_zoom(100);
                else if (event.target.value == "150%") viewport.set_zoom(150);
                else if (event.target.value == "200%") viewport.set_zoom(200);
                event.target.selectedIndex = 0;
            });
        zoom_select
            .selectAll("option")
            .data([
                ["current_zoom", "100%"],
                ["zoom_fit", get("zoom_fit")],
                ["50%", "50%"],
                ["100%", "100%"],
                ["150%", "150%"],
                ["200%", "200%"],
            ])
            .enter()
            .append("option")
            .attr("id", d => d[0])
            .property("value", d => d[0])
            .text(d => d[1]);
    }

    let viewport_div = selection.selectAll("div#viewport_information");
    if (viewport_div.empty()) {
        // An explicit setup prevents needless empty selection actions for followup calls
        // This function here is called quite often, so this should improve performance
        setup_div();
        viewport_div = selection.selectAll("div#viewport_information");
    }
    viewport_div
        .select("#panning_value")
        .text(zoom.x.toFixed(0) + "/" + zoom.y.toFixed(0) + "px");
    viewport_div
        .select("option#current_zoom")
        .text((zoom.k * 100).toFixed(0) + "%");
}

export class LayoutingToolbar {
    layout_style_configuration: LayoutStyleConfiguration;
    _filter_mutation_observer: MutationObserver | null = null;
    _selection: d3SelectionDiv;
    _toolbar_selection: d3SelectionDiv;
    _datasource_specific_settings: LayoutAggregations | LayoutTopology;
    _world: NodevisWorld;
    active: boolean;
    _layout_manager: LayoutManagerLayer;
    _layout_history: LayoutHistory;

    constructor(
        world: NodevisWorld,
        layout_manager: LayoutManagerLayer,
        selection: d3SelectionDiv,
    ) {
        this._world = world;
        this._layout_manager = layout_manager;
        this._selection = selection;
        this.active = false;

        this._datasource_specific_settings =
            this._get_datasource_specific_elements(this._world.datasource);
        this._toolbar_selection = this._create_toolbar_selection(
            this._selection,
        );
        this._layout_history = new LayoutHistory(
            layout_manager,
            this._toolbar_selection,
        );
        this.layout_style_configuration = new LayoutStyleConfiguration(
            this._selection.select("#style_management"),
            world,
        );
    }

    _get_datasource_specific_elements(datasource: string) {
        if (datasource == "bi_aggregations")
            return new LayoutAggregations(this._world);
        else if (datasource == "topology")
            return new LayoutTopology(this._world);
        throw "Invalid datasource information for world: " + datasource;
    }

    _create_toolbar_selection(into_selection: d3SelectionDiv) {
        // Layout configuration box

        const toolbar_selection = into_selection
            .selectAll<HTMLDivElement, null>("div#layouting_toolbar")
            .data([null])
            .join(enter =>
                enter
                    .append("div")
                    .attr("id", "layouting_toolbar")
                    .classed("box", true)
                    .style("opacity", 0)
                    .style("display", "none"),
            );

        toolbar_selection
            .selectAll<HTMLDivElement, null>("#layout_configuration_headline")
            .data([null])
            .enter()
            .append("h2")
            .attr("id", "layout_configuration_headline")
            .text(get("layout_configuration"));

        this._render_line_style(toolbar_selection, "straight");
        this._show_viewport_information();

        toolbar_selection
            .selectAll<HTMLDivElement, null>("div#style_management")
            .data([null])
            .join(enter => enter.append("div").attr("id", "style_management"));
        this._add_search_filter_mutation_observer();

        return toolbar_selection;
    }

    _render_line_style(
        into_selection: d3SelectionDiv,
        line_style: LineStyle,
    ): void {
        const options = [
            new RadioGroupOption("round", get("round")),
            new RadioGroupOption("straight", get("straight")),
            new RadioGroupOption("elbow", get("elbow")),
        ];
        render_radio_group(
            into_selection,
            get("line_style"),
            "line_style",
            options,
            line_style,
            (new_style: string) =>
                this._change_line_style(new_style as LineStyle),
        );
    }

    _change_line_style(new_line_style: LineStyle): void {
        this._layout_manager.change_line_style(new_line_style);
    }

    _show_viewport_information() {
        show_viewport_information(this._world.viewport);
    }

    enable() {
        this.active = true;
        this._layout_manager.show_layout_options();
        this.update_layout_configuration();
        this._show_viewport_information();

        this._render_line_style(
            this._toolbar_selection!,
            this._layout_manager._layout.line_config.style,
        );

        this._world.viewport.update_gui_of_layers();
        for (const idx in this._layout_manager._active_styles) {
            this._layout_manager._active_styles[idx].generate_overlay();
        }

        this._toolbar_selection
            .transition()
            .duration(DefaultTransition.duration())
            .style("opacity", 1)
            .style("display", null);
    }

    disable() {
        this.active = false;
        if (this._layout_manager.edit_layout) {
            this._layout_manager.hide_layout_options();
            this._world.viewport.update_gui_of_layers();
        }
        hide_viewport_information(this._world.viewport.get_div_selection());
        this._toolbar_selection
            .transition()
            .duration(DefaultTransition.duration())
            .style("opacity", 0)
            .style("display", "none");
    }

    _update_position() {
        if (select("div#popup_filters").classed("active")) {
            this._toolbar_selection
                .transition()
                .duration(DefaultTransition.duration())
                .style("right", "380px");
            this._world.viewport
                .get_div_selection()
                .select("#viewport_information")
                .transition()
                .duration(DefaultTransition.duration())
                .style("right", "380px");
        } else {
            this._toolbar_selection
                .transition()
                .duration(DefaultTransition.duration())
                .style("right", "12px");
            this._world.viewport
                .get_div_selection()
                .select("#viewport_information")
                .transition()
                .duration(DefaultTransition.duration())
                .style("right", "12px");
        }
    }

    _add_search_filter_mutation_observer() {
        if (this._filter_mutation_observer != null) return;
        const filter_node = select(
            "div#popup_filters",
        ).node() as HTMLDivElement;
        if (filter_node == null) return;

        this._filter_mutation_observer = new MutationObserver(() => {
            this._update_position();
        });
        this._filter_mutation_observer.observe(filter_node, {attributes: true});
    }

    update_layout_configuration() {
        this._datasource_specific_settings.render_layout(
            this._toolbar_selection,
        );
    }
}

class LayoutingMouseEventsOverlay {
    _world: NodevisWorld;
    _layout_manager: LayoutManagerLayer;
    drag: DragBehavior<any, any, any>;
    _dragged_node: Selection<any, any, any, any> | null = null;
    _drag_start_x = 0;
    _drag_start_y = 0;
    _dragging_class = LayoutStyleHierarchy; // convert into this class while dragging

    constructor(world: NodevisWorld, layout_manager: LayoutManagerLayer) {
        this._world = world;
        this._layout_manager = layout_manager;
        this.drag = drag<SVGElement, string>()
            .on("start.drag", event => this._dragstarted(event))
            .on("drag.drag", event => this._dragging(event))
            .on("end.drag", event => this._dragended(event));
    }

    update_data() {
        this._world.viewport
            .get_nodes_layer()
            .get_svg_selection()
            .selectAll(".node_element")
            .call(this.drag);
    }

    _get_scaled_event_coords(event: D3DragEvent<any, any, any>): {
        x: number;
        y: number;
    } {
        return {
            x: event.x / this._world.viewport.last_zoom.k,
            y: event.y / this._world.viewport.last_zoom.k,
        };
    }

    _dragstarted(event: D3DragEvent<any, any, any>) {
        if (!this._layout_manager.is_node_drag_allowed()) return;
        event.sourceEvent.stopPropagation();
        this._dragged_node = select(event.sourceEvent.target);

        const nodevis_node = this._world.viewport.get_node_by_id(
            this._dragged_node.datum(),
        );
        if (!nodevis_node) return;

        const scaled_event = this._get_scaled_event_coords(event);
        this._apply_drag_force(nodevis_node, scaled_event.x, scaled_event.y);

        this._drag_start_x = scaled_event.x;
        this._drag_start_y = scaled_event.y;

        const use_style = nodevis_node.data.use_style;
        if (use_style) {
            this._layout_manager.show_style_configuration(use_style);
        } else {
            // TODO: improve
            this._layout_manager.layout_applier._convert_node(
                nodevis_node,
                this._dragging_class,
                // LayoutStyleHierarchy
                // LayoutStyleRadial
                // LayoutStyleFixed
            );
        }

        this._layout_manager.dragging = true;
    }

    _apply_drag_force(node: NodevisNode, x: number, y: number) {
        node.data.node_positioning["drag"] = {};
        const force = node.data.node_positioning["drag"];
        force.use_transition = false;
        if (node.data.use_style) force.weight = 1000;
        else force.weight = 500;
        force.fx = x;
        force.fy = y;
    }

    _dragging(event: D3DragEvent<any, any, any>) {
        if (
            this._dragged_node == null ||
            !this._layout_manager.is_node_drag_allowed()
        )
            return;

        const nodevis_node = this._world.viewport.get_node_by_id(
            this._dragged_node.datum(),
        );
        if (!nodevis_node) return;

        if (nodevis_node.data.use_style) {
            if (
                !nodevis_node.data.use_style.style_config.options
                    .detach_from_parent
            ) {
                nodevis_node.data.use_style.style_config.options.detach_from_parent =
                    true;
                this._layout_manager.show_style_configuration(
                    nodevis_node.data.use_style,
                );
            }
        }

        const scaled_event = this._get_scaled_event_coords(event);
        const delta_x = scaled_event.x - this._drag_start_x;
        const delta_y = scaled_event.y - this._drag_start_y;

        this._apply_drag_force(
            nodevis_node,
            this._drag_start_x + delta_x,
            this._drag_start_y + delta_y,
        );

        this._world.viewport.restart_force_simulation(0.5);
        if (nodevis_node.data.use_style) {
            nodevis_node.data.use_style.force_style_translation();
            nodevis_node.data.use_style.translate_coords();
        }
        compute_node_position(nodevis_node);

        // TODO: EXPERIMENTAL, will be removed in later commit
        for (const idx in this._layout_manager._active_styles) {
            this._layout_manager._active_styles[idx].update_data();
        }

        // TODO: translate and compute node is overkill for a simple drag procedure
        this._layout_manager.translate_layout();
        this._layout_manager.compute_node_positions();
        this._world.viewport.update_gui_of_layers();
    }

    _dragended(_event: D3DragEvent<any, any, any>) {
        this._layout_manager.dragging = false;
        if (
            this._dragged_node == null ||
            !this._layout_manager.is_node_drag_allowed()
        )
            return;

        const nodevis_node = this._world.viewport.get_node_by_id(
            this._dragged_node.datum(),
        );
        if (!nodevis_node) return;

        if (nodevis_node.data.use_style) {
            const new_position =
                this._world.viewport.get_viewport_percentage_of_node(
                    nodevis_node,
                );
            nodevis_node.data.use_style.style_config.position = new_position;
            nodevis_node.data.use_style.force_style_translation();
        }

        if (
            nodevis_node.data.use_style &&
            nodevis_node.data.use_style instanceof this._dragging_class
        ) {
            nodevis_node.data.use_style.fix_node(nodevis_node);
        }

        delete nodevis_node.data.node_positioning["drag"];
        this._layout_manager.translate_layout();

        compute_node_position(nodevis_node);
        this._layout_manager.create_undo_step();
    }
}

class LayoutApplier {
    _layout_manager: LayoutManagerLayer;
    layout_style_factory: LayoutStyleFactory;

    constructor(world: NodevisWorld, layout_manager: LayoutManagerLayer) {
        this._layout_manager = layout_manager;
        this.layout_style_factory = new LayoutStyleFactory(world);
    }

    get_context_menu_elements(node: NodevisNode | null): ContextMenuElement[] {
        const elements: ContextMenuElement[] = [];
        const styles = this.layout_style_factory.get_styles();

        const nested: ContextMenuElement = {
            text: node ? get("convert_to") : get("convert_all_nodes_to"),
            children: [],
        };
        for (const [_key, style] of Object.entries(styles)) {
            if (node) {
                nested.children!.push({
                    text: style.prototype.description(),
                    on: () => this._convert_node(node, style),
                    href: "",
                });
            } else {
                nested.children!.push({
                    text: style.prototype.description(),
                    on: () => this._convert_all(style),
                    href: "",
                });
            }
        }
        if (!node) {
            nested.children!.push({
                text: get("free_floating_style"),
                on: () => this._convert_all(null),
                href: "",
            });
        }

        elements.push(nested);

        if (node && node.data.use_style) {
            elements.push({
                text: get("remove_style"),
                on: () => this._convert_node(node, null),
                href: "",
                img: "themes/facelift/images/icon_aggr.svg",
            });
        }

        elements.push({
            text: get("show_force_configuration"),
            on: () => this._layout_manager.show_force_config(),
            href: "",
            img: "",
        });

        return elements;
    }

    _convert_node(
        node: NodevisNode,
        style_class: AbstractNodeVisConstructor<AbstractLayoutStyle> | null,
    ) {
        const layout = this._layout_manager.get_layout();
        const current_style = node.data.use_style;

        // Do nothing on same style
        if (
            current_style &&
            style_class != null &&
            current_style.class_name() == style_class.prototype.class_name()
        )
            return;

        // Remove existing style
        if (current_style) {
            layout.remove_style(current_style);
        }

        let new_style: AbstractLayoutStyle | null = null;
        if (style_class != null) {
            new_style = this.layout_style_factory.instantiate_style_class(
                style_class,
                node,
                this._layout_manager.get_div_selection(),
            );
            new_style.style_config.options.detach_from_parent = true;
            layout.save_style(new_style.style_config);
        }

        this._layout_manager.apply_current_layout();
        if (new_style) new_style.update_style_indicator();
        this._layout_manager.show_style_configuration(new_style);
        this._layout_manager.create_undo_step();
    }

    _convert_all(
        style_class: AbstractNodeVisConstructor<AbstractLayoutStyle> | null,
    ) {
        const used_style: AbstractLayoutStyle[] = [];
        const current_style: AbstractLayoutStyle | null = null;

        const layout = this._layout_manager.get_layout();
        layout.clear_styles();
        if (style_class != null) {
            const all_nodes = this._layout_manager._viewport.get_all_nodes();
            if (style_class == LayoutStyleFixed) {
                // LayoutStyleFixed converts all shown nodes to a FixedStyle
                all_nodes.forEach(node => {
                    layout.save_style(
                        this.layout_style_factory.instantiate_style_class(
                            LayoutStyleFixed,
                            node,
                            this._layout_manager.get_div_selection(),
                        ).style_config,
                    );
                });
            } else {
                // For all other styles, only the root node is given a style class
                const new_style =
                    this.layout_style_factory.instantiate_style_class(
                        style_class,
                        all_nodes[0],
                        this._layout_manager.get_div_selection(),
                    );
                layout.save_style(new_style.style_config);
            }
        }

        this._layout_manager.apply_current_layout();
        const last_style = used_style.at(-1);
        if (last_style) {
            last_style.update_style_indicator();
            this._layout_manager.show_style_configuration(current_style);
        }

        this._layout_manager.update_style_indicators(true);

        if (style_class == LayoutStyleFixed) {
            this._layout_manager._viewport.get_all_nodes().forEach(node => {
                const use_style = node.data.use_style;
                if (!use_style) return;
                use_style.update_style_indicator();
            });
        }

        this._layout_manager.create_undo_step();
    }

    apply_layout(node_config: NodeConfig, trigger_force_simulation = true) {
        const layout = this._layout_manager.get_layout();
        const layout_settings = this._layout_manager.get_layout_settings();
        // TODO: move this code into the backend
        if (layout.origin_type) {
            // Add generic and explicit styles
            if (layout.origin_type == "default_template") {
                const default_style =
                    this.layout_style_factory.instantiate_style_name(
                        layout_settings.default_id!,
                        node_config.hierarchy,
                        this._layout_manager.get_div_selection(),
                    );
                default_style.style_config.position = {x: 50, y: 50};
                layout.clear_styles();
                layout.save_style(default_style.style_config);
            }
        }

        let nodes_with_style: NodeWithStyle[] = [];
        const node_matcher = new NodeMatcher(node_config);
        nodes_with_style = this.find_nodes_for_layout(
            layout,
            node_matcher,
        ).concat(nodes_with_style);
        // Sort styles, as the layout of the parent node takes precedence
        nodes_with_style.sort(function (a, b) {
            if (a.node.depth > b.node.depth) return 1;
            if (a.node.depth < b.node.depth) return -1;
            return 0;
        });

        // Add boxed style indicators
        const boxed_styles = this._get_boxed_styles(nodes_with_style);

        nodes_with_style = boxed_styles.concat(nodes_with_style);

        // TODO: better access
        this._layout_manager._viewport._force_simulation.set_force_options(
            layout.force_config,
        );
        this._update_node_specific_styles(nodes_with_style);

        if (trigger_force_simulation)
            this._layout_manager._viewport.restart_force_simulation(2);
    }

    _merge_styles(
        primary: StyleConfig[],
        secondary: StyleConfig[],
    ): StyleConfig[] {
        const merged_styles: Map<string, StyleConfig> = new Map();
        primary.forEach(style_config => {
            merged_styles.set(
                JSON.stringify({
                    matcher: style_config.matcher,
                    type: style_config.type,
                }),
                style_config,
            );
        });
        secondary.forEach(style_config => {
            const style_id = JSON.stringify({
                matcher: style_config.matcher,
                type: style_config.type,
            });
            if (merged_styles.has(style_id)) return;
            merged_styles.set(style_id, style_config);
        });
        return Array.from(merged_styles.values());
    }

    _get_boxed_styles(nodes_with_style: NodeWithStyle[]) {
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
        this._layout_manager._viewport.get_all_nodes().forEach(node => {
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

        // Cleanup box_leaf_nodes hint
        nodes_with_style.forEach(entry =>
            entry.node.descendants().forEach(d => delete d.data.box_leaf_nodes),
        );

        const grouped_styles: NodeWithStyle[] = [];

        // Add styles for box candidates
        box_candidates.forEach(node => {
            const new_style = this.layout_style_factory.instantiate_style_name(
                "block",
                node,
                this._layout_manager.get_div_selection(),
            );
            new_style.style_config.options = {};
            grouped_styles.push({node: node, style: new_style.style_config});
        });
        return grouped_styles;
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
                                config.style.type,
                            ),
                            config.node,
                        ),
                );
                continue;
            }
            used_nodes.push(config.node);
            filtered_nodes_with_style.push(nodes_with_style[idx]);
        }

        const node_styles = this._layout_manager.styles_selection
            .selectAll<SVGGElement, NodeWithStyle>(".layout_style")
            .data(filtered_nodes_with_style, d => {
                // TODO: check if prototype is not required
                return compute_style_id(
                    layout_style_class_registry.get_class(d.style.type),
                    d.node,
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
                            d.node,
                        ),
                );
                const use_style = d.node.data.use_style;
                if (use_style)
                    this._layout_manager.remove_active_style(use_style);
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
                            d.node,
                        ),
                );
                if (d.node.data.use_style) {
                    this._layout_manager.remove_active_style(
                        d.node.data.use_style,
                    );
                }
                const new_style = this.layout_style_factory.instantiate_style(
                    d.style,
                    d.node,
                    select(nodes[idx]),
                );
                this._layout_manager.add_active_style(new_style);
            })
            .merge(node_styles)
            .each(d => {
                log(
                    7,
                    "  updating style " +
                        compute_style_id(
                            layout_style_class_registry.get_class(d.style.type),
                            d.node,
                        ),
                );
                const style_id = compute_style_id(
                    layout_style_class_registry.get_class(d.style.type),
                    d.node,
                );
                const style = this._layout_manager.get_active_style(style_id);
                d.node.data.use_style = style;
                d.node.data.use_style.style_config.options = d.style.options;
                d.node.data.use_style.style_config.position = d.style.position;
                d.node.data.use_style.style_root_node = d.node;
                d.node.data.use_style.update_data();
                d.node.data.use_style.translate_coords();

                if (style.type() != "force") {
                    const position = style.style_config.position;
                    if (position == null) return;

                    const abs_coords =
                        this._layout_manager.get_absolute_node_coords(
                            {x: position.x, y: position.y},
                            this._layout_manager._viewport.get_size(),
                        );
                    d.node.fx = abs_coords.x;
                    d.node.fy = abs_coords.y;
                    d.node.x = abs_coords.x;
                    d.node.y = abs_coords.y;
                }
            });

        const all_nodes = this._layout_manager._viewport.get_all_nodes();
        const all_links = this._layout_manager._viewport.get_all_links();
        this._layout_manager._viewport.update_nodes_and_links(
            all_nodes,
            all_links,
        );
        this._layout_manager.update_data();
    }

    find_nodes_for_layout(
        layout: NodeVisualizationLayout,
        node_matcher: NodeMatcher,
    ): NodeWithStyle[] {
        const nodes: NodeWithStyle[] = [];
        layout.style_configs.forEach(style => {
            if (!style.matcher) return;

            const node = node_matcher.find_node(style.matcher);
            if (!node) return;

            nodes.push({node: node, style: style});
        });
        return nodes;
    }
}

interface NodeWithStyle {
    node: NodevisNode;
    style: StyleConfig;
}
