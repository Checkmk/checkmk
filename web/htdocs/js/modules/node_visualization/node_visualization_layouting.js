import * as node_visualization_viewport_utils from "node_visualization_viewport_utils"
import * as node_visualization_layout from "node_visualization_layout"
import * as node_visualization_toolbar_utils from "node_visualization_toolbar_utils"
import * as node_visualization_utils from "node_visualization_utils"

import * as node_visualization_layouting_utils from "node_visualization_layouting_utils"
import * as node_visualization_layout_styles from "node_visualization_layout_styles"

import * as ajax from "ajax"
import * as d3 from "d3";

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


export class LayoutManagerLayer extends node_visualization_viewport_utils.LayeredLayerBase {
    id() {
        return "layout_manager"
    }

    name() {
        return "Layout Manager"
    }

    constructor(viewport) {
        super(viewport)
        this._mouse_events_overlay = new LayoutingMouseEventsOverlay(this)

        // Setup layout applier and instantiate default style_force
        this.layout_applier = new LayoutApplier(this)
        this.force_style = this.layout_applier.layout_style_factory.instantiate_style_class(node_visualization_layout_styles.LayoutStyleForce)

        // Edit tools
        this.edit_layout = false // Indicates whether the layout manager is active
        this.allow_layout_updates = true // Indicates if layout updates are allowed

        // Instantiated styles
        this._active_styles = {}

    }

    add_active_style(style) {
        this._active_styles[style.id()] = style
    }

    get_active_style(style_id) {
        return this._active_styles[style_id]
    }

    remove_active_style(style) {
        delete this._active_styles[style.id()]
        style.remove()
        style.style_root_node.data.use_style = null
    }

    get_context_menu_elements(node) {
        return this.layout_applier.get_context_menu_elements(node)
    }


    setup() {
        this.styles_selection = this.selection.append("g").attr("id", "hierarchies")
    }

    show_layout_options() {
        this.edit_layout = true
        this.allow_layout_updates = false
        this._mouse_events_overlay.update_data()
        this.viewport.selection.select("#svg_layers #nodes").classed("edit", true)
    }

    hide_layout_options() {
        this.edit_layout = false
        this.allow_layout_updates = true
        this.viewport.selection.select("#svg_layers #nodes").classed("edit", false)
        this.styles_selection.selectAll(".layout_style").selectAll("*").remove()
        this.div_selection.selectAll("img").remove()
        this.update_style_indicators(true)
    }

    register_toolbar_plugin() {
        this.toolbar_plugin = new LayoutingToolbarPlugin(this)
        this.viewport.main_instance.toolbar.add_toolbar_plugin_instance(this.toolbar_plugin)
        this.viewport.main_instance.toolbar.update_toolbar_plugins()
    }


    size_changed() {
        this.force_style.size_changed()
    }

    update_data() {
        if (!this.toolbar_plugin) {
            this.register_toolbar_plugin()
        }

        // TODO: use only update_current_style
        this.toolbar_plugin.update_content()
        this.force_style.update_data()

        for (var idx in this._active_styles) {
            this._active_styles[idx].update_data()
        }

        this.translate_layout()
        this.compute_node_positions()
        this._mouse_events_overlay.update_data()

    }

    update_gui() {
        this.force_style.update_gui()

        for (var idx in this._active_styles) {
            this._active_styles[idx].update_gui()
        }

        this.update_style_indicators()
    }

    update_style_indicators(force) {
        if (!force && !this.edit_layout)
            return

        this.viewport.get_hierarchy_list().forEach(hierarchy=>
            hierarchy.nodes.forEach(node=>{
                if (node.data.use_style)
                    node.data.use_style.update_style_indicator(this.edit_layout)
            })
        )
    }

    compute_layout() {
        this.compute_tree_layout()
        this.compute_node_layout()
    }

    translate_layout() {
        for (var idx in this._active_styles) {
            this._active_styles[idx].translate_coords()
        }
    }

    zoomed() {
        for (var idx in this._active_styles) {
            this._active_styles[idx].zoomed()
        }
    }

    get_viewport_percentage_of_node(node) {
        let coords = node.data.chunk.coords
        let x_perc = 100.0 * (node.x - coords.x) / coords.width
        let y_perc = 100.0 * (node.y - coords.y) / coords.height
        return {x: x_perc, y: y_perc}
    }

    get_absolute_node_coords(perc_coords, node) {
        let coords = node.data.chunk.coords
        let x = coords.x + coords.width  * perc_coords.x / 100
        let y = coords.y + coords.height * perc_coords.y / 100
        return {x: x, y: y}
    }

    get_node_positioning(node) {
        if (node.data.node_positioning == null) {
            node.data.node_positioning = {}
        }
        return node.data.node_positioning
    }

    add_node_positioning(id, node, positioning_force) {
        if (node.data.node_positioning == null) {
            node.data.node_positioning = {}
        }
        node.data.node_positioning[id] = positioning_force
    }

    compute_node_positions() {
        // Determines the positioning force with the highest weight
        // console.log("compute node positions")
        this.viewport.get_hierarchy_list().forEach(hierarchy=>{
                hierarchy.nodes.forEach(node=>this.compute_node_position(node))
        })
    }

    compute_node_position(node) {
        var current_positioning = {
                weight: 0,
                free: true,
        }

        for (var force_id in node.data.node_positioning) {
            var force = node.data.node_positioning[force_id]
            if (force.weight > current_positioning.weight) {
                current_positioning = force
            }
        }

        // Beside of x/y coords, the layout may have additional info
        // E.g. text positioning
        node.data.current_positioning = current_positioning
        if (current_positioning.free) {
            node.fx = null
            node.fy = null
            node.use_transition = false
        } else {
            let viewport_boundary = 5000
            node.fx = Math.max(Math.min(current_positioning.fx, viewport_boundary), -viewport_boundary)
            node.fy = Math.max(Math.min(current_positioning.fy, viewport_boundary), -viewport_boundary)
            node.x = node.fx
            node.y = node.fy
            node.use_transition = current_positioning.use_transition
        }
        if (node.selection) {
            node.selection.selectAll("circle").classed("style_root_node", node.data.use_style)
            node.selection.selectAll("circle").classed("free_floating_node", current_positioning.free == true)
        }
    }

    save_layout(layout) {
        this.save_layout_template(layout)
    }

    delete_layout_id(layout_id) {
        ajax.post_url("ajax_delete_bi_template_layout.py", "layout_id=" + encodeURIComponent(layout_id), ()=>this.toolbar_plugin.fetch_all_layouts())
    }

    save_layout_template(layout_config) {
        ajax.post_url("ajax_save_bi_template_layout.py",
            "layout=" + encodeURIComponent(JSON.stringify(layout_config)), ()=>this.toolbar_plugin.fetch_all_layouts())
    }

    // TODO: check parameters
    save_layout_for_aggregation(layout_config, aggregation_name) {
        ajax.post_url("ajax_save_bi_aggregation_layout.py",
            "layout=" + encodeURIComponent(JSON.stringify(layout_config))+
            "&aggregation_name=" + encodeURIComponent(aggregation_name),
            ()=>{
                this.viewport.main_instance.datasource_manager.schedule(true)
                this.toolbar_plugin.fetch_all_layouts()
            }
        )
    }

    delete_layout_for_aggregation(aggregation_name) {
        ajax.post_url("ajax_delete_bi_aggregation_layout.py",
            "aggregation_name=" + encodeURIComponent(aggregation_name),
            ()=>{
                this.allow_layout_updates = true
                this.viewport.main_instance.datasource_manager.schedule(true)
                this.toolbar_plugin.fetch_all_layouts()
            }
        )
    }
}


export class LayoutStyleConfiguration {
    constructor(toolbar_plugin) {
        this.toolbar_plugin = toolbar_plugin
        this.layout_manager = toolbar_plugin.layout_manager
    }

    render_style_config(style_div_box) {
        this.selection = style_div_box
        let style_div = this.selection.selectAll("div#style_div").data([null])
        let style_div_enter = style_div.enter().append("div").attr("id", "style_div")

        style_div_enter.selectAll("#styleconfig_headline").data([null]).enter().append("h2")
                        .attr("id", "styleconfig_headline").text("Style configuration")


        style_div_enter.selectAll("div.style_component").data(["style_options", "style_matcher"]).enter()
                      .append("div").attr("id", d=>d)
                      .classed("style_component", true)


        // Add foldable trees for basic and advanced matchers
        let style_matcher = style_div_enter.select("#style_matcher")
        style_matcher.append("b").text("Matcher settings")
        style_matcher.append("br")
        style_matcher.append("label").text("(How to find the root node of this style)")
        style_matcher.append("br")
        style_matcher.append("br")

        let theme_prefix = this.layout_manager.viewport.main_instance.get_theme_prefix()
        let matcher_topics = [
            {id: "basic_matchers", text: "Basic matching", default_open: true},
            {id: "advanced_matchers", text: "Advanced matching", default_open: false},
        ]
        let matchers_enter = style_matcher.selectAll("div.foldable#matcher_topic").data(matcher_topics, d=>d.id).enter()
                        .append("div").classed("matcher_topic", true).classed("foldable", true)
        matchers_enter.append("img")
                        .classed("treeangle", true)
                        .classed("open", d=>d.default_open)
                        .attr("src",  theme_prefix + "/images/tree_closed.png")
                        .on("click", function() {
                            let image = d3.select(this)
                            image.classed("open", !image.classed("open"))
                            image.classed("closed", image.classed("open"))
                            d3.select(this.parentNode).select(".matcher_topic_content").style("display", image.classed("open") ? null : "none")
                        })
        matchers_enter.append("b").classed("treeangle", true).classed("title", true).text(d=>d.text).style("color", "black")
                        .on("click", function() {
                            let image = d3.select(this.parentNode).select("img")
                            image.classed("open", !image.classed("open"))
                            image.classed("closed", image.classed("open"))
                            d3.select(this.parentNode).select(".matcher_topic_content").style("display", image.classed("open") ? null : "none")
                        })
        matchers_enter.append("div").classed("matcher_topic_content", true).attr("id", d=>d.id)
                       .style("display", d=>d.default_open ? null : "none")
        matchers_enter.append("br")

        this.update_current_style(this.current_style)
    }

    update_current_style(style) {
        if (style != this.current_style)
            this._cleanup_old_style_config()

        this.current_style = style

        let hide_style_config = false
        if (!this.current_style)
            hide_style_config = true
        else if (this.current_style.type() == node_visualization_layout_styles.LayoutStyleForce.prototype.type())
            hide_style_config = false
        else if (this.current_style.get_matcher() == null || this.current_style.get_style_options().length == 0)
            hide_style_config = true

        if (hide_style_config) {
            this.selection
                .transition().duration(node_visualization_utils.DefaultTransition.duration())
                .style("height", "0px")
                .style("display", "none")
            return
        }
        this.selection.style("height", null)
        this.selection.style("display", null)

        this._update_current_style_options()
        this._update_current_style_matcher()
    }

    _cleanup_old_style_config() {
        this.selection.selectAll("div#style_options").selectAll("*").remove()
        this.selection.selectAll(".matcher_topic_content").selectAll("*").remove()
    }

    _update_current_style_options() {
        let options_selection = this.selection.select("#style_options")
        this.current_style.render_options(options_selection)
    }

    _update_current_style_matcher() {
        let matcher = this.current_style.get_matcher()
        if (!matcher) {
            this.selection.select("#style_matcher").style("display", "none")
            return
        }
        this.selection.select("#style_matcher").style("display", null)


        this._update_basic_matcher_config(matcher)
        this._update_advanced_matcher_config(matcher)
    }

    _update_basic_matcher_config(matcher) {
        let basic_matcher_config = this.selection.select("#basic_matchers")
        let basic_matcher_table = basic_matcher_config.selectAll("table").data([matcher])
        basic_matcher_table = basic_matcher_table.enter().append("div").append("table").merge(basic_matcher_table)
        let input_fields = []
        if (this.current_style.style_root_node.data.node_type == "bi_leaf") {
            input_fields.push({name: "Hostname", id: "hostname"})
            input_fields.push({name: "Service Description", id: "service"})
        }
        else if (this.current_style.style_root_node.data.node_type == "bi_aggregator") {
            input_fields.push({name: "Aggregation Rule ID", id: "rule_id"})
            input_fields.push({name: "Aggregation Rule Name", id: "rule_name"})
        }
        let input_selection = basic_matcher_table.selectAll("div.input_field").data(input_fields)
        let divs = input_selection.enter().append("tr").append("td").append("div").classed("input_field", true)
        divs.append("input").attr("type", "checkbox").property("checked", d=>!matcher[d.id].disabled)
                            .on("change", d=>this.toggle_matcher_condition(d.id))
        divs.append("b").text(d=>d.name).append("br")
        divs.append("input").attr("value", d=>matcher[d.id].value)
                            .attr("id", d=>"matcher_text_" + d.id)
                            .on("input", d=>this.update_matcher_condition_text(d.id))
    }

    _update_advanced_matcher_config(matcher) {
        // Create topics
        let advanced_matcher_config = this.selection.select("#advanced_matchers")
        let advanced_matcher_table = advanced_matcher_config.selectAll("table").data([matcher])

        advanced_matcher_table = advanced_matcher_table.enter().append("div").append("table").merge(advanced_matcher_table)
        let input_fields = []
        input_fields.push({name: "Aggregation Rule Path ID", id: "aggr_path_id", value: matcher.aggr_path_id.value})
        input_fields.push({name: "Aggregation Rule Path Name", id: "aggr_path_name", value: matcher.aggr_path_name.value})
        let input_selection = advanced_matcher_table.selectAll("div.input_field").data(input_fields)
        let divs = input_selection.enter().append("tr")
                                          .append("td")
                                          .append("div")
                                            .attr("id", d=>d.id)
                                            .classed("input_field", true)
        divs.append("input").attr("type", "checkbox").property("checked", d=>!matcher[d.id].disabled)
                            .on("change", d=>this.toggle_matcher_condition(d.id))
        divs.append("b").text(d=>d.name)
        divs.append("br")
        divs.append("div").classed("path_details", true)

        this.selection.selectAll(".path_details").each(this._render_aggr_path_table)
    }

    _render_aggr_path_table(data) {
        let table = d3.select(this).selectAll("table").data([null])
        let table_enter = table.enter().append("table")
        let table_header = table_enter.append("tr")
        table_header.append("th").text("Name")
        table_header.append("th").text("Instance number")
        table = table_enter.merge(table)

        let rows = table.selectAll("tr.content").data(data.value)
        rows.exit().remove()
        let rows_enter = rows.enter().append("tr").classed("content", true)
        rows_enter.append("td").text(d=>d[0]).style("width", "100%")
        rows_enter.append("td").text(d=>d[1]).style("text-align", "right")
    }

    toggle_matcher_condition(condition_id) {
        let matcher = this.current_style.get_matcher()
        if (matcher[condition_id].disabled)
            delete matcher[condition_id].disabled
        else
            matcher[condition_id].disabled = true

        this.current_style.set_matcher(matcher)
        this.layout_manager.layout_applier.apply_all_layouts()
    }

    update_matcher_condition_text(condition_id) {
        let matcher = this.current_style.get_matcher()
        let value = this.selection.selectAll("#matcher_text_" + condition_id).property("value")
        matcher[condition_id].value = value
        this.current_style.set_matcher(matcher)
        this.layout_manager.layout_applier.apply_all_layouts()
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
export class LayoutingToolbarPlugin extends node_visualization_toolbar_utils.ToolbarPluginBase {
    id() {
        return "layouting_toolbar"
    }

    constructor(layout_manager) {
        super("Modify Layout")
        this.layout_manager = layout_manager
        this.sort_index = 0
        this.layout_style_configuration = new LayoutStyleConfiguration(this)
    }

    render_togglebutton(selection) {
        this.togglebutton_selection.append("img")
                        .attr("src", this.layout_manager.viewport.main_instance.get_theme_prefix() + "/images/icon_aggr.png")
                        .attr("title", "Layout Designer")
    }

    enable_actions() {
        this.layout_manager.show_layout_options()

        // TODO: update_gui instead of update_data
        this.layout_manager.update_data()

        this.content_selection.selectAll(".edit_mode_only").style("display", null)
        this.content_selection
                .transition().duration(node_visualization_utils.DefaultTransition.duration())
                .style("height", null)

        this.fetch_all_layouts()
    }

    disable_actions() {
        this.layout_manager.hide_layout_options()
        this.layout_manager.viewport.update_gui_of_layers()
        this.content_selection.selectAll(".edit_mode_only").style("display", "none")

        this.content_selection
                .transition().duration(node_visualization_utils.DefaultTransition.duration())
                .style("height", "0px")

//        this.content_selection.selectAll("div.box")
//                .transition().duration(node_visualization_utils.DefaultTransition.duration())
//                .style("height", "0px")
    }

    remove() {
//        this.content_selection.select("div.toolbar_layouting").transition().duration(node_visualization_utils.DefaultTransition.duration()).style("height", "0px").remove()
    }

    render_content() {
        this.update_content()
    }

    update_content() {
        if (!this.layout_manager.edit_layout)
            return

        let layouting_div = this.content_selection.selectAll("div#layout_management").data([null])

        // Layout management box
        layouting_div = layouting_div.enter().append("div").attr("id", "layout_management")
                                    .classed("noselect", true)
                                    .classed("box", true)
                                .merge(layouting_div)
        let aggr_div = layouting_div.selectAll("div#aggr_div").data([null])
        aggr_div = aggr_div.enter().append("div").attr("id", "aggr_div").merge(aggr_div)
        let template_div = layouting_div.selectAll("div#template_div").data([null])
        template_div = template_div.enter().append("div").attr("id", "template_div").merge(template_div)

        // Overlay management box
        let overlay_div_box = this.content_selection.selectAll("div#overlay_management").data([null])
        overlay_div_box = overlay_div_box.enter().append("div").attr("id", "overlay_management")
                                    .classed("noselect", true)
                                    .classed("box", true)
                                .merge(overlay_div_box)


        let overlay_div = overlay_div_box.selectAll("div#overlay_div").data([null])
        overlay_div = overlay_div.enter().append("div").attr("id", "overlay_div").merge(overlay_div)

        // Style management box
        let style_div_box = this.content_selection.selectAll("div#style_management").data([null])
        style_div_box = style_div_box.enter().append("div").attr("id", "style_management")
                                    .classed("noselect", true)
                                    .classed("box", true)
                                .merge(style_div_box)



        this._render_aggregation_configuration(aggr_div)
        this._render_layout_management(template_div)
        this._render_layout_overlays_configuration(overlay_div)
        this.layout_style_configuration.render_style_config(style_div_box)
    }

    _render_aggregation_configuration(into_selection) {
        let chunk = this.layout_manager.viewport.get_hierarchy_list()[0]
        let aggr_name = chunk.tree.data.name

        into_selection.selectAll("#aggregation_headline").data([null]).enter().append("h2")
                        .attr("id", "aggregation_headline").text("Aggregation layout")

        let table_selection = into_selection.selectAll("table#layout_settings").data([null])
        let table_enter = table_selection.enter().append("table").attr("id", "layout_settings")

        let row_enter = table_enter.append("tr")
        row_enter.append("td").text("Name")
        row_enter.append("td").text(aggr_name)

        row_enter = table_enter.append("tr")
        row_enter.append("td").text("Layout origin")
        row_enter.append("td").attr("id", "layout_origin")

        row_enter = table_enter.append("tr")
        row_enter.append("td").append("input").attr("type", "button")
            .classed("button", true)
            .attr("value", "Use this layout")
            .style("margin-top", null)
            .style("margin-bottom", null)
            .style("width", "100%")
            .on("click", d=>{
                this._save_explicit_layout_clicked()
            })

        row_enter.append("td").append("input").attr("type", "button")
            .classed("button", true)
            .attr("value", "Use configured template")
            .attr("id", "remove_explicit_layout")
            .style("margin-top", null)
            .style("margin-bottom", null)
            .style("width", "100%")
            // TODO: fix this css
            .style("margin-right", "-4px")
            .on("click", d=>{
                this._delete_explicit_layout_clicked()
            })

        let table = table_enter.merge(table_selection)
        table.select("#layout_origin").text(chunk.layout_origin)

        let explicit_set = chunk.layout_origin == "Explicit set"
        table.select("input#remove_explicit_layout")
            .classed("disabled", !explicit_set)
            .attr("disabled", explicit_set ? null : true)

    }


    _render_layout_overlays_configuration(into_selection) {
        into_selection.selectAll("#overlays_headline").data([null]).enter().append("h2")
                        .attr("id", "overlays_headline").text("Layout Overlays")

        let layers = this.layout_manager.viewport.get_layers()
        let configurable_layers = []
        for (let idx in layers) {
            if (layers[idx].is_toggleable())
                configurable_layers.push(layers[idx])
        }

        let table_selection = into_selection.selectAll("table#overlay_configuration").data([null]).style("width", "100%")
        let table_enter = table_selection.enter().append("table").attr("id", "overlay_configuration")
                                                    .style("width", "100%")
                                                    .on("change", ()=>this.overlay_options_changed())

        let row_enter = table_enter.append("tr").classed("header", true)
        row_enter.append("th").text("")
        row_enter.append("th").text("Active")
        row_enter.append("th").text("Configurable")

        let table = table_enter.merge(table_selection)

        // TODO: fixme
        table.selectAll(".configurable_overlay").remove()
        let current_overlay_config = this.layout_manager.layout_applier.current_layout_group.overlay_config
        let rows = table.selectAll("tr.configurable_overlay").data(configurable_layers)
        let rows_enter = rows.enter().append("tr").classed("configurable_overlay", true)

        rows_enter.append("td").text(d=>d.name()).classed("noselect", true)
        let elements = ["active", "configurable"]
        for (let idx in elements) {
            let element = elements[idx]
            rows_enter.append("td")
                .style("text-align", "center")
              .append("input")
                .attr("option_id", d=>element)
                .attr("overlay_id", d=>d.id())
                .attr("type", "checkbox")
              .merge(rows_enter)
                .property("checked", d=>{
                    if (!current_overlay_config[d.id()])
                        return false
                    return current_overlay_config[d.id()][element]
                })
        }
    }

    fetch_all_layouts() {
        d3.json("ajax_get_all_bi_template_layouts.py", {credentials: "include"}).then((json_data)=>this.update_available_layouts(json_data.result))
    }

    update_available_layouts(layouts) {
        this.layout_manager.layout_applier.layouts = layouts
        let choices = [""]
        choices = choices.concat(Object.keys(layouts))

        choices.sort()
        let choice_selection = this.content_selection.select("#available_layouts")

        let active_id = null
        if (this.layout_manager.layout_applier.current_layout_group.id)
            active_id = this.layout_manager.layout_applier.current_layout_group.id
        else if (choices.length > 0)
            active_id = choices[0]

        this.add_dropdown_choice(choice_selection, choices, active_id, () => this.layout_changed_callback())

        if (active_id)
            this.content_selection.select("#layout_name").property("value", active_id)
        this.update_save_layout_button()
    }

    layout_changed_callback() {
        let selected_id = d3.event.target.value
        this.layout_manager.layout_applier.apply_layout_id(selected_id)
        this.layout_style_configuration.update_current_style()
        this.content_selection.select("#layout_name").property("value", selected_id)
        this.update_content()
        this.update_save_layout_button()
    }

    overlay_options_changed() {
        let current_overlay_config = this.layout_manager.layout_applier.current_layout_group.overlay_config
        let checkbox = d3.select(d3.event.target)
        let checked = checkbox.property("checked")
        let option_id = checkbox.attr("option_id")
        let overlay_id = checkbox.attr("overlay_id")
        if (!current_overlay_config[overlay_id])
            current_overlay_config[overlay_id] = {}
        current_overlay_config[overlay_id][option_id] = checked
        this.layout_manager.viewport.update_active_overlays()
    }

    _render_layout_management(into_selection) {
        let table = into_selection.selectAll("table#layout_management").data([null])

        into_selection.selectAll("#template_headline").data([null]).enter().append("h2")
                        .attr("id", "template_headline").text("Layout templates")

        let table_selection = into_selection.selectAll("table#template_configuration").data([null])
        let table_enter = table_selection.enter().append("table").attr("id", "template_configuration")

        // Dropdown choice and delete button
        let row_enter = table_enter.append("tr")
        let td_enter = row_enter.append("td").attr("id", "available_layouts")
        this.add_dropdown_choice(td_enter, [], null, () => this.layout_changed_callback())
        row_enter.append("td").append("input")
                            .attr("type", "button")
                            .classed("button", true)
                            .style("width", "100%")
                            .attr("value", "Delete template")
                            .on("click", d=>{
                                let selected_layout = this.content_selection.select("#available_layouts").select("select").property("value")
                                if (!selected_layout)
                                   return
                                this.layout_manager.delete_layout_id(selected_layout)
                            })


        // Text input and save button
        row_enter = table_enter.append("tr")
        row_enter.append("td").append("input")
            .attr("value", "")
            .attr("id", "layout_name")
            .style("width", "100%")
            .style("box-sizing", "border-box")
            .on("input", ()=>this.update_save_layout_button())
            .on("keydown", ()=>{
                let save_button = this.content_selection.select("#save_button")
                if (save_button.attr("disabled"))
                    return
                if (d3.event.keyCode == 13) {
                  this._save_layout_clicked()
                }
            })

        row_enter.append("td").append("input").attr("type", "button")
                           .classed("button", true)
                           .style("width", "100%")
                           .attr("id", "save_button")
                           .attr("value", "Save template")
                           .on("click", d=>this._save_layout_clicked())
        table_enter.append("tr").append("td").attr("colspan", "2").attr("id", "infotext").text("")
    }

    update_save_layout_button() {
        let dropdown_id = this.content_selection.select("#available_layouts").select("select").property("value").trim()
        let input_id= this.content_selection.select("#layout_name").property("value").trim()
        let button = this.content_selection.select("#save_button")
        let infotext = this.content_selection.select("#infotext")
        infotext.text("")

        if (input_id== "") {
            button.attr("disabled", true)
            button.classed("disabled", true)
            button.attr("value", "Save template")
        }
        else if (dropdown_id == input_id) {
            button.attr("disabled", null)
            button.classed("disabled", false)
            button.attr("value", "Save template")
        }
        else if (Object.keys(this.layout_manager.layout_applier.layouts).indexOf(input_id) == -1) {
            button.attr("disabled", null)
            button.classed("disabled", false)
            button.attr("value", "Save as new template")
        }
        else {
            button.attr("disabled", true)
            button.classed("disabled", true)
            button.attr("value", "Save as")
            infotext.text("Can not override existing layout")
                    .style("color", "red")
        }
    }

    _save_layout_clicked() {
       let new_id = this.content_selection.select("#layout_name").property("value");
       let current_layout_group = this.layout_manager.layout_applier.get_current_layout_group()
       let new_layout = {}
       new_layout[new_id] = current_layout_group
       this.layout_manager.save_layout_template(new_layout)
       this.layout_manager.layout_applier.current_layout_group.id = new_id
    }

    _save_explicit_layout_clicked(){
       let aggr_name = this.layout_manager.viewport.get_hierarchy_list()[0].tree.data.name
       let current_layout_group = this.layout_manager.layout_applier.get_current_layout_group()
       let new_layout = {}
       new_layout[aggr_name] = current_layout_group
       this.layout_manager.save_layout_for_aggregation(new_layout, aggr_name)
    }

    _delete_explicit_layout_clicked(){
       let aggr_name = this.layout_manager.viewport.get_hierarchy_list()[0].tree.data.name
       this.layout_manager.delete_layout_for_aggregation(aggr_name)
    }

    add_text_input(into_selection, value) {
        var input = into_selection.selectAll("input").data([""])
        input = input.enter().append("input").merge(input)
        input.attr("type", "text").attr("value", value)
    }

    add_dropdown_choice(into_selection, choices, default_choice, callback_function) {
        var select = into_selection.selectAll("select").data([null])
        select = select.enter().append("select").merge(select)
                        .style("width", "100%")

        var options = select.on("change", callback_function)
               .selectAll("option")
               .data(choices)
        options.exit().remove()
        options = options.enter().append("option").merge(options)

        options.property("value", d=>d)
               .property("selected", d=>d==default_choice)
               .text(d=>d)
    }

    render_table(selection, table_data) {
        var table = selection.selectAll("table").data([""])
        table = table.enter().append("table").merge(table)

        if (table_data.headers) {
            var thead = table.selectAll("thead").data([""])
            thead = thead.enter().append("thead").append("tr").merge(thead)
            // append the header row
            var th = thead.selectAll('th').data(table_data.headers)
            th.enter().append('th').merge(th).text(d=>d)
            th.exit().remove()
        }

        var tbody = table.selectAll("tbody").data([""])
        tbody = tbody.enter().append("tbody").merge(tbody)

        var tr = tbody.selectAll('tr').data(table_data.rows, d=>d)
        tr.exit().remove()
        tr = tr.enter().append('tr').merge(tr)

        var td = tr.selectAll('td').remove()
        td = tr.selectAll('td').data(d=>d, d=>d)
        td = td.enter().append("td").merge(td).tex/t(d=>"HMM " + d)
    }
}

class LayoutingMouseEventsOverlay {
    constructor(layout_manager) {
        this.layout_manager = layout_manager
        this.drag = d3.drag()
            .on("start.drag", () => this._dragstarted())
            .on("drag.drag", () => this._dragging())
            .on("end.drag", () => this._dragended())

        this.dragged_node = null
    }

    update_data() {
        // TODO: check this
        let nodes_layer = this.layout_manager.viewport.get_layer("nodes")
        if (!nodes_layer)
             return
        let nodes_selection = nodes_layer.nodes_selection
        nodes_selection.selectAll(".node_element").call(this.drag)
    }

    _dragstarted() {
        if (!this.layout_manager.edit_layout)
            return
        d3.event.sourceEvent.stopPropagation();
        this._dragged_node = d3.select(d3.event.sourceEvent.target).datum()
        this._apply_drag_force(this._dragged_node, d3.event.x, d3.event.y)
        this.drag_start_x = d3.event.x
        this.drag_start_y = d3.event.y

        if (this._dragged_node.data.use_style)
            this.layout_manager.toolbar_plugin.layout_style_configuration.update_current_style(this._dragged_node.data.use_style)

        this.layout_manager.dragging = true
    }

    _apply_drag_force(node, x, y) {
        node.data.node_positioning["drag"] = {}
        let force = node.data.node_positioning["drag"]
        force.use_transition = false
        if (node.data.use_style)
            force.weight = 1000
        else
            force.weight = 5
        force.fx = x;
        force.fy = y;
    }

    _dragging() {
        if (!this.layout_manager.edit_layout)
            return
        let scale = 1.0
        let delta_x = d3.event.x - this.drag_start_x
        let delta_y = d3.event.y - this.drag_start_y

        let last_zoom = this.layout_manager.viewport.last_zoom
        scale = 1/last_zoom.k

        this._apply_drag_force(this._dragged_node, this.drag_start_x + (delta_x * scale),
                                                 this.drag_start_y + (delta_y * scale))

        let node_data = d3.select(d3.event.sourceEvent.target).datum()
        this.layout_manager.force_style.restart_with_alpha(0.5)
        this.layout_manager.compute_node_position(this._dragged_node)
        if (this._dragged_node.data.use_style)
            this._dragged_node.data.use_style.force_style_translation()
        this.layout_manager.translate_layout()
        this.layout_manager.compute_node_positions()
        this.layout_manager.viewport.update_gui_of_layers()
    }

    _dragended() {
        this.layout_manager.dragging = false
        if (!this.layout_manager.edit_layout)
            return

        if (this._dragged_node.data.use_style) {
            let new_position = this.layout_manager.get_viewport_percentage_of_node(this._dragged_node)
            this._dragged_node.data.use_style.style_config.position = new_position
        }

        if (this._dragged_node.data.use_style && this._dragged_node.data.use_style.type() == "fixed") {
            this._dragged_node.data.use_style.fix_node(this._dragged_node)
        } 

        delete this._dragged_node.data.node_positioning["drag"]
        this.layout_manager.compute_node_position(this._dragged_node)
    }
}

class LayoutApplier{
    constructor(layout_manager) {
        this.layout_manager = layout_manager
        this.viewport = layout_manager.viewport

        this.layout_style_factory = new node_visualization_layouting_utils.LayoutStyleFactory(this.layout_manager)
        this.current_layout_group = new node_visualization_layout.NodeVisualizationLayout(this.viewport)

        this.layouts = {}
    }

    get_context_menu_elements(node) {
        if (node && !(node.data.node_type == "bi_leaf" || node.data.node_type == "bi_aggregator")) {
            return []
        }

        let elements = []
        let styles = this.layout_style_factory.get_styles()
        for (let idx in styles) {
            let style = styles[idx]
            if (node) {
                elements.push({text: "Convert to " + style.prototype.description(),
                               on: ()=> this._convert_node(node, style),
                               href: "",
                               img: this.layout_manager.viewport.main_instance.get_theme_prefix() + "/images/icon_aggr.png"})
            } else {
                elements.push({text: "Convert all nodes to " + style.prototype.description(),
                           on: ()=> this._convert_all(style),
                           href: "",
                           img: this.layout_manager.viewport.main_instance.get_theme_prefix() + "/images/icon_aggr.png"})
            }
        }
        let modification_element = this.layout_manager.toolbar_plugin.layout_style_configuration
        elements.push({text: "Show " + node_visualization_layout_styles.LayoutStyleForce.prototype.description() + " options",
                       on: ()=>modification_element.update_current_style(this.layout_manager.force_style),
                       href: "",
                       img: this.layout_manager.viewport.main_instance.get_theme_prefix() + "/images/icon_aggr.png"})
        return elements
    }

    _convert_node(node, style_class) {
        let chunk_layout = node.data.chunk.layout
        let current_style = node.data.use_style

        // Do nothing on same style
        if (current_style && current_style.type() == style_class.prototype.type())
            return

        // Remove existing style
        if (current_style) {
            chunk_layout.remove_style(current_style)
        }

        let new_style = null
        if (style_class != node_visualization_layout_styles.LayoutStyleForce) {
            new_style = this.layout_style_factory.instantiate_style_class(style_class, node)
            chunk_layout.save_style(new_style.style_config)
        }
        this.layout_manager.layout_applier.apply_all_layouts()
        // TODO: fix workaround
        this.layout_manager.toolbar_plugin.layout_style_configuration.update_current_style(null)
        this.layout_manager.toolbar_plugin.layout_style_configuration.update_current_style(new_style)
    }

    _convert_all(style_class) {
        let current_style = null
        this.layout_manager.viewport.get_hierarchy_list().forEach(node_chunk=>{
            node_chunk.layout.clear_styles()
            if (style_class == node_visualization_layout_styles.LayoutStyleFixed) {
                node_chunk.nodes.forEach(node=>{
                    node_chunk.layout.save_style(this.layout_style_factory.instantiate_style_class(style_class, node).style_config)
                })
            }
            else if (style_class != node_visualization_layout_styles.LayoutStyleForce) {
                current_style = this.layout_style_factory.instantiate_style_class(style_class, node_chunk.nodes[0])
                node_chunk.layout.save_style(current_style.style_config)
            }
        })

        this.apply_all_layouts()
        // TODO: fix workaround
        this.layout_manager.toolbar_plugin.layout_style_configuration.update_current_style(null)
        this.layout_manager.toolbar_plugin.layout_style_configuration.update_current_style(current_style)
    }

    apply_layout_id(layout_id) {
        let new_layout = new node_visualization_layout.NodeVisualizationLayout(this.viewport, layout_id)
        if (layout_id != "") {
            let config = JSON.parse(JSON.stringify(this.layouts[layout_id]))
            config.id = layout_id
            new_layout.deserialize(config)
        }
        this.apply(new_layout)
    }

    apply(new_layout) {
        this._apply_force_style_options(new_layout)

        let node_matcher = new node_visualization_utils.NodeMatcher(this.layout_manager.viewport.get_hierarchy_list())
        let nodes_with_style = this.find_nodes_for_layout(new_layout, node_matcher)
        this._update_node_specific_styles(nodes_with_style)

        this.current_layout_group = new_layout

        this.layout_manager.viewport.get_hierarchy_list().forEach(chunk=>{
            chunk.layout = new_layout
        })

        this.viewport.update_active_overlays()
    }

    apply_all_layouts(global_layout_config=null) {
        this.apply_multiple_layouts(this.viewport.get_hierarchy_list(), global_layout_config)
    }

    apply_multiple_layouts(node_chunk_list, global_layout_config) {
        let nodes_with_style = []
        let skip_layout_alignment = false

        let used_layout_id = null

        node_chunk_list.forEach(node_chunk=>{
            let node_matcher = new node_visualization_utils.NodeMatcher([node_chunk])
            // TODO: When removing an explicit layout, the new layout should replace the explict one
            if (!node_chunk.layout) {
                node_chunk.layout = new node_visualization_layout.NodeVisualizationLayout(this)

                if (global_layout_config) {
                    // A layout which may span over multiple chunks has been set
                    // Each chunk gets its own layout config instance, since config-wise chunks are still separated after all..
                    let enforced_layout = new node_visualization_layout.NodeVisualizationLayout(this.viewport)
                    enforced_layout.deserialize(global_layout_config)
                    node_chunk.layout = enforced_layout
                } else if (node_chunk.use_layout) {
                    node_chunk.layout.deserialize(node_chunk.use_layout)
                    // TODO: fix id handling
                    if (node_chunk.template_layout_id)
                        used_layout_id = node_chunk.template_layout_id
                }
                else if (node_chunk.use_default_layout && node_chunk.use_default_layout != "force") {
                    let default_style = this.layout_style_factory.instantiate_style_name(node_chunk.use_default_layout, node_chunk.tree)
                    default_style.style_config.position = {x: 50, y: 50}
                    node_chunk.layout.save_style(default_style.style_config)
                }
            }
            else
                skip_layout_alignment = true

            nodes_with_style = nodes_with_style.concat(this.find_nodes_for_layout(node_chunk.layout, node_matcher))
            this._apply_force_style_options(node_chunk.layout)
        })
        this._update_node_specific_styles(nodes_with_style, skip_layout_alignment)

        this.current_layout_group = this.get_current_layout_group()
        // TODO: fix id handling
        if (used_layout_id)
            this.current_layout_group.id = used_layout_id

        this.viewport.update_active_overlays()

        if (this.layout_manager.edit_layout)
            this.layout_manager.allow_layout_updates = false
    }

    align_layouts(nodes_with_style) {
        this.viewport.get_hierarchy_list().forEach(node_chunk=>{
            let box = {x_min: 50000, x_max: -50000, y_min: 50000, y_max: -50000}
            node_chunk.nodes.forEach(node=>{
                box.x_min = Math.min(box.x_min, node.x)
                box.x_max = Math.max(box.x_max, node.x)
                box.y_min = Math.min(box.y_min, node.y)
                box.y_max = Math.max(box.y_max, node.y)
            })

            let box_width = box.x_max - box.x_min
            let box_height = box.y_max - box.y_min
            let translate_perc = {
                x: -((box.x_min - (node_chunk.coords.width - box_width)/2)/node_chunk.coords.width) * 100,
                y: -((box.y_min - (node_chunk.coords.height - box_height)/2)/node_chunk.coords.height) * 100,
            }

            node_chunk.nodes.forEach(node=>{
                if (node.data.use_style) {
                    node.data.use_style.style_config.position.x += translate_perc.x
                    node.data.use_style.style_config.position.y += translate_perc.y
                }
            })
        })
        this._update_node_specific_styles(nodes_with_style, true)
    }

    _apply_force_style_options(new_layout) {
        for (let idx in new_layout.style_configs) {
            let style = new_layout.style_configs[idx]
            if (style.type == node_visualization_layout_styles.LayoutStyleForce.prototype.type())
                this.layout_manager.force_style.style_config.options = style.options
        }
    }

    _update_node_specific_styles(nodes_with_style, skip_align=false) {
//        console.log("update node styles")
        let filtered_nodes_with_style = []
        let used_nodes = []
        for (let idx in nodes_with_style) {
            let config = nodes_with_style[idx]
            if (used_nodes.indexOf(config.node) >= 0) {
//                console.log("filtered duplicate style assignment",
//                    this.layout_style_factory.get_style_class(config.style).prototype.compute_id(config.node))
                continue
            }
            used_nodes.push(config.node)
            filtered_nodes_with_style.push(nodes_with_style[idx])
        }

        let node_styles = this.layout_manager.styles_selection.selectAll(".layout_style").data(
                    filtered_nodes_with_style,
                    d=>{
                        return this.layout_style_factory.get_style_class(d.style).prototype.compute_id(d.node)
                    })

        node_styles.exit().each(d=>{
//                console.log("removing style " + this.layout_style_factory.get_style_class(d.style).prototype.compute_id(d.node))
            this.layout_manager.remove_active_style(d.node.data.use_style)
            this.layout_manager.compute_node_position(d.node)
        }).remove()

        node_styles.enter().append("g")
            .classed("layout_style", true)
            .each((d, idx, nodes)=> {
//                console.log("create style " + this.layout_style_factory.get_style_class(d.style).prototype.compute_id(d.node))
                if (d.node.data.use_style) {
                    this.layout_manager.remove_active_style(d.node.data.use_style)
                }
                let new_style = this.layout_style_factory.instantiate_style(
                    d.style,
                    d.node,
                    d3.select(nodes[idx]),
                )
                this.layout_manager.add_active_style(new_style)
            }).merge(node_styles).each(d=>{
//                console.log("updating style " + this.layout_style_factory.get_style_class(d.style).prototype.compute_id(d.node))
                let style_id = this.layout_style_factory.get_style_class(d.style).prototype.compute_id(d.node)

                let style = this.layout_manager.get_active_style(style_id)
                d.node.data.use_style = style
                d.node.data.use_style.style_config.options = d.style.options
                d.node.data.use_style.style_root_node = d.node
                d.node.data.use_style.force_style_translation()

                let abs_coords = this.layout_manager.get_absolute_node_coords({x: style.style_config.position.x, y: style.style_config.position.y}, d.node)
                d.node.fx = abs_coords.x
                d.node.fy = abs_coords.y
                d.node.x  = abs_coords.x
                d.node.y  = abs_coords.y
            })

//        console.log("############ active styles")
//        for (let idx in this.layout_manager._active_styles)
//            console.log(idx, this.layout_manager._active_styles[idx].style_config)
        this.layout_manager.update_data()

        // Experimental
        if (!skip_align)
            this.align_layouts(nodes_with_style)
    }

    find_nodes_for_layout(layout, node_matcher) {
        let nodes = []
        layout.style_configs.forEach(style=>{
            if (!style.matcher)
                return

            let node = node_matcher.find_node(style.matcher)
            if (!node)
                return

            nodes.push({node: node, style: style})
        })
        return nodes
    }

    get_current_layout_group() {
        // TODO: experimental, use layout_manager active_styles instead
        let layouts = []
        let style_configs = []
        let chunk_layout = null
        this.viewport.get_hierarchy_list().forEach(node_chunk=>{
            chunk_layout = node_chunk.layout.serialize()
            for (let idx in chunk_layout.style_configs)
                if (chunk_layout.style_configs[idx].type != "force")
                    style_configs.push(chunk_layout.style_configs[idx])
        })
        chunk_layout.style_configs = style_configs
        chunk_layout.style_configs.push(this.layout_manager.force_style.get_config())
        chunk_layout.reference_size = {width: this.viewport.width, height: this.viewport.height}
        return chunk_layout
    }
}

