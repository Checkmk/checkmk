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
        this._mouse_events_overlay = new MouseEventsOverlay(this)

        // Setup layout applier and instantiate default style_force
        this.layout_applier = new LayoutApplier(this)
        this.force_style = this.layout_applier.layout_style_factory.instantiate_style_class(node_visualization_layout_styles.LayoutStyleForce)

        // Edit tools
        this.edit_layout = false

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
        this._mouse_events_overlay.update_data()
        this.viewport.selection.select("#svg_layers #nodes").classed("edit", true)
    }

    hide_layout_options() {
        this.edit_layout = false
        this.viewport.selection.select("#svg_layers #nodes").classed("edit", false)
        this.styles_selection.selectAll(".layout_style").selectAll("*").remove()
        this.div_selection.selectAll("img").remove()
        this.update_style_indicators(true)
    }

    register_toolbar_plugin() {
        this.toolbar_plugin = new LayoutingToolbarPlugin(this)
        this.viewport.main_instance.toolbar.add_toolbar_plugin_instance(this.toolbar_plugin)
    }


    size_changed() {
        this.force_style.size_changed()
    }

    update_data() {
        if (!this.toolbar_plugin)
            this.register_toolbar_plugin()

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
                "weight": 0,
                "free": true,
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
}


//#.
//#   .-Modify Element-----------------------------------------------------.
//#   |                   __  __           _ _  __                         |
//#   |                  |  \/  | ___   __| (_)/ _|_   _                   |
//#   |                  | |\/| |/ _ \ / _` | | |_| | | |                  |
//#   |                  | |  | | (_) | (_| | |  _| |_| |                  |
//#   |                  |_|  |_|\___/ \__,_|_|_|  \__, |                  |
//#   |                                            |___/                   |
//#   |                _____ _                           _                 |
//#   |               | ____| | ___ _ __ ___   ___ _ __ | |_               |
//#   |               |  _| | |/ _ \ '_ ` _ \ / _ \ '_ \| __|              |
//#   |               | |___| |  __/ | | | | |  __/ | | | |_               |
//#   |               |_____|_|\___|_| |_| |_|\___|_| |_|\__|              |
//#   |                                                                    |
//#   +--------------------------------------------------------------------+
export class LayoutModificationElement {
    constructor(toolbar_plugin) {
        this.toolbar_plugin = toolbar_plugin
        this.layout_manager = toolbar_plugin.layout_manager

        this.hide_from_mathias = false
    }

    show() {
        this.selection = this.toolbar_plugin.content_selection
                .append("div")
                    .classed("box", true)
                    .classed("toolbar_layout_options", true)
                    .style("pointer-events", "all")
                    .style("display", "none")
                    .attr("id", "toolbar_modify_layout")

        this.setup_gui_components()
    }

    hide() {
        this.toolbar_plugin.content_selection.select(".toolbar_layout_options")
                    .transition().duration(node_visualization_utils.DefaultTransition.duration())
                    .style("height", "0px")
                    .remove()

        this.layout_manager.viewport.selection.select("#togglebox_choices")
                .transition()
                .duration(node_visualization_utils.DefaultTransition.duration())
                .style("top", null)
    }

    setup_gui_components() {
        this.setup_style_config()
    }

    setup_style_config(style_config_selection) {
        this.style_config_selection = this.selection.append("div").attr("id", "style_config")

        if (!this.hide_from_mathias) {
            this.style_config_selection.append("div").attr("id", "matcher_config")
            this.style_config_selection.append("hr")
        }

        let current_style_group = this.style_config_selection.append("div")
                                                 .attr("id", "current_style_group")
                                                 .classed("noselect", true)
        current_style_group.append("div").attr("id", "current_style")
        current_style_group.append("div").attr("id", "style_options")
    }

    update_current_style(style) {
        this.current_style = style
        if (!this.current_style) {
            this.selection.style("display", "none")
            return
        }

        let matcher = this.current_style.get_matcher()
        let style_options = this.current_style.get_style_options()
        if ((this.hide_from_mathias || matcher == null) && style_options.length == 0)
            return

        this.selection.style("display", null)
        this.update_current_style_matcher(style)
        this.style_config_selection.select("#current_style").text(style.description() + " options")
        this.update_current_style_options()
    }

    update_current_style_matcher() {
        let matcher = this.current_style.get_matcher()
        if (matcher == null)
            return

        this.selection.style("display", null)
        let matcher_config = this.style_config_selection.select("#matcher_config")
        matcher_config.selectAll("label#matcher_headline").data([null]).enter()
        //                        .append("label").attr("id", "matcher_headline").text("Matcher configuration (how to find the node)")
                        .append("label").attr("id", "matcher_headline").text("Assign this style to nodes matching")



        let matcher_table = matcher_config.selectAll("table").data([matcher])
        matcher_table = matcher_table.enter().append("div").append("table").merge(matcher_table)
        matcher_table.selectAll("*").remove()

        let input_fields = []

        if (this.current_style.style_root_node.data.node_type == "bi_leaf") {
            input_fields.push({name: "Hostname", id: "hostname"})
            input_fields.push({name: "Service Description", id: "service"})
        }
        else if (this.current_style.style_root_node.data.node_type == "bi_aggregator") {
            input_fields.push({name: "Aggregation Rule ID", id: "rule_id"})
            input_fields.push({name: "Aggregation Rule Name", id: "rule_name"})
        }

        input_fields.push({name: "Aggregation Path ID", id: "aggr_path_id"})

        input_fields.push({name: "Aggregation Path Name", id: "aggr_path_name"})

        let input_selection = matcher_table.selectAll("div.input_field").data(input_fields)
        let divs = input_selection.enter().append("tr")
                                          .append("td")
                                          .append("div")
                                            .classed("input_field", true)
                                    .merge(input_selection)

        divs.append("input").attr("type", "checkbox").property("checked", d=>!matcher[d.id].disabled)
                            .on("change", (d)=>this.toggle_matcher_condition(d.id))
        divs.append("b").text(d=>d.name).append("br")
        divs.append("input").attr("value", d=>matcher[d.id].value)
                            .attr("id", d=>"matcher_text_" + d.id)
                            .on("input", (d)=>this.update_matcher_condition_text(d.id))
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
        let value = this.style_config_selection.select("#matcher_text_" + condition_id).property("value")
        matcher[condition_id].value = value
        this.current_style.set_matcher(matcher)
        this.layout_manager.layout_applier.apply_all_layouts()
    }

    update_current_style_options() {
        let options_selection = this.style_config_selection.select("#style_options")
        options_selection.selectAll("*").remove()
        this.current_style.render_options(options_selection)
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
        return "layouting"
    }

    constructor(layout_manager) {
        super("Modify Layout")
        this.layout_manager = layout_manager
        this.sort_index = 0
        this.layout_modification_element = new LayoutModificationElement(this)
    }

    render_togglebutton(selection) {
        this.togglebutton_selection.append("img")
                        .attr("src", "themes/facelift/images/icon_aggr.png")
                        .attr("title", "Layout Designer")
    }

    enable_actions() {
        this.layout_manager.show_layout_options()
        this.layout_modification_element.show()

        // TODO: update_gui instead of update_data
        this.layout_manager.update_data()

        this.content_selection.selectAll(".edit_mode_only").style("display", null)
        this.content_selection.select("#toolbar_layouting")
                .transition().duration(node_visualization_utils.DefaultTransition.duration())
                .style("height", "284px")
                .style("left", null)
    }

    disable_actions() {
        this.layout_manager.hide_layout_options()
        this.layout_modification_element.hide()
        this.layout_manager.viewport.update_gui_of_layers()
        this.content_selection.selectAll(".edit_mode_only").style("display", "none")
        this.content_selection.select("#toolbar_layouting")
                .transition().duration(node_visualization_utils.DefaultTransition.duration())
                .style("height", "30px")
                .style("left", "332px")
        this.content_selection.select("#toolbar_layouting")
    }

    remove() {
//        this.content_selection.select("div.toolbar_layouting").transition().duration(node_visualization_utils.DefaultTransition.duration()).style("height", "0px").remove()
    }

    render_content() {
        this.update_content()
    }

    update_content() {
        let layouting_div = this.content_selection.selectAll("div#toolbar_layouting").data([null])
                                .classed("noselect", true)
        if (layouting_div.empty()) {
            layouting_div = layouting_div.enter().append("div")
                            .attr("id", "toolbar_layouting")
                            .classed("box", true)
            let height = layouting_div.style("height")
            let right = layouting_div.style("right")
            layouting_div.style("height", "0px").transition().duration(node_visualization_utils.DefaultTransition.duration()).style("height", height)
        }
        layouting_div = layouting_div.merge(layouting_div)
        this.render_layout_management(layouting_div)
        this.render_layout_overlay_configuration(layouting_div)
    }

    fetch_all_layouts() {
        d3.json("ajax_get_all_bi_templates.py", {credentials: "include"}).then((json_data) => this.update_available_layouts(json_data.result))
    }

    update_available_layouts(layouts) {
        this.layout_manager.layout_applier.layouts = layouts
        let choices = Object.keys(layouts)

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
        this.layout_manager.viewport.update_active_overlays()
        this.content_selection.select("#layout_name").property("value", selected_id)
        this.update_content()

        this.update_save_layout_button()
    }

    render_layout_overlay_configuration(into_selection) {
        let layers = this.layout_manager.viewport.get_layers()
        let configurable_layers = []
        for (let idx in layers) {
            if (layers[idx].is_toggleable())
                configurable_layers.push(layers[idx])
        }

        let table = into_selection.selectAll("div#overlay_configuration table").data([null])
        table = table.enter().append("div")
                        .classed("edit_mode_only", true)
                        .attr("id", "overlay_configuration")
                        .on("change", ()=>this.overlay_options_changed())
                      .append("table").merge(table)

        let tr_header = table.selectAll("tr.header").data([null])
        let th_enter = tr_header.enter().append("tr").classed("header", true)
        th_enter.append("th").text("Name")
        th_enter.append("th").text("Active")
        th_enter.append("th").text("Configurable")


        // TODO: fixme
        table.selectAll(".configurable_overlay").remove()
        let current_overlay_config = this.layout_manager.layout_applier.current_layout_group.overlay_config
        let rows = table.selectAll("tr.configurable_overlay").data(configurable_layers)
        let rows_enter = rows.enter().append("tr").classed("configurable_overlay", true)

        rows_enter.append("td").text(d=>d.name()).classed("noselect", true)
        let elements = ["active", "configurable"]
        for (let idx in elements) {
            let element = elements[idx]
            rows_enter.append("td").append("input")
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
//        rows_enter.append("td").text("Work in progress")
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

    render_layout_management(into_selection) {
        let table = into_selection.selectAll("table#layout_management").data([null])

        if (table.empty()) {
            table = table.enter().append("table").attr("id", "layout_management")
            let row = table.append("tr")
//            row.append("td").text("Current")

            let td = row.append("td").attr("id", "available_layouts")
            this.add_dropdown_choice(td, [], null, () => this.layout_changed_callback())
            row.append("td").classed("edit_mode_only", true).append("input").attr("type", "button")
                               .classed("button", true)
                               .style("width", "100%")
                               .attr("value", "Delete template")
                               .on("click", d=>{
                                    let selected_layout = this.content_selection.select("#available_layouts").select("select").property("value")
                                    if (!selected_layout)
                                       return
                                    this.layout_manager.layout_applier.delete_layout_id(selected_layout)
                                    setTimeout(()=>this.fetch_all_layouts(), 500)
                                })

            table.append("tr").classed("edit_mode_only", true).append("td").attr("colspan", 2).append("hr")

            row = table.append("tr").classed("edit_mode_only", true)
//            row.append("td").text("Save")
            row.append("td").append("input")
                .attr("value", "demo_layout")
                .attr("id", "layout_name")
                .style("width", "100%")
                .style("box-sizing", "border-box")
                .on("input", ()=>this.update_save_layout_button())
                .on("keydown", ()=>{
                    let save_button = this.content_selection.select("#save_button")
                    if (save_button.attr("disabled"))
                        return
                    if (d3.event.keyCode == 13) {
                      this.save_layout_clicked()
                      // TODO: fixme, callback handler
                      setTimeout(()=>this.fetch_all_layouts(), 500)
                    } // Enter key
                })

            // Save template
            row.append("td").append("input").attr("type", "button")
                               .classed("button", true)
                               .style("width", "100%")
                               .attr("id", "save_button")
                               .attr("value", "Save template")
                               .on("click", d=>{
                                    this.save_layout_clicked()
                                   // TODO: fixme, callback handler
                                    setTimeout(()=>this.fetch_all_layouts(), 500)
            })

            // Save aggregation
            table.append("tr")
                .classed("edit_mode_only", true)
                .classed("single_aggregation", true)
                .append("td").attr("colspan", 2).append("hr")
            row = table.append("tr")
                .classed("edit_mode_only", true)
                .classed("single_aggregation", true)
//            row.append("td")
            row.append("td")
                .attr("id", "single_aggregation_name")
            row.append("td").append("input").attr("type", "button")
                               .classed("button", true)
                               .style("width", "100%")
                               .attr("id", "save_aggregation")
                              .attr("value", "Save aggr")
                               .on("click", d=>{
                                    this.save_aggregation_clicked()
                                   // TODO: fixme, callback handler
                                    setTimeout(()=>this.fetch_all_layouts(), 500)
            })

            row = table.append("tr")
            row.append("td")
            row.append("td").attr("id", "infotext").text("")
            table.append("tr").classed("edit_mode_only", true).append("td").attr("colspan", 2).append("hr")
        }

        let hierarchy_list = this.layout_manager.viewport.get_hierarchy_list()
        if (hierarchy_list.length == 1) {
            into_selection.select("#single_aggregation_name").text(hierarchy_list[0].tree.data.name)
            into_selection.selectAll(".single_aggregation").style("display", null)
        } else {
            into_selection.selectAll(".single_aggregation").style("display", "none")
        }
    }

    update_save_layout_button() {
        let dropdown_id = this.content_selection.select("#available_layouts").select("select").property("value")
        let input_id= this.content_selection.select("#layout_name").property("value");
        let button = this.content_selection.select("#save_button")
        let infotext = this.content_selection.select("#infotext")
        infotext.text("")

        if (dropdown_id == input_id) {
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

    save_layout_clicked() {
       let new_id = this.content_selection.select("#layout_name").property("value");
       let current_layout_group = this.layout_manager.layout_applier.get_current_layout_group()
       let new_layout = {}
       new_layout[new_id] = current_layout_group
       this.layout_manager.layout_applier.save_layout_template(new_layout)
    }

    save_aggregation_clicked() {
       let aggr_name = this.layout_manager.viewport.get_hierarchy_list()[0].tree.data.name
       let current_layout_group = this.layout_manager.layout_applier.get_current_layout_group()
       let new_layout = {}
       new_layout[aggr_name] = current_layout_group
       this.layout_manager.layout_applier.save_layout_for_aggregation(new_layout, aggr_name)
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

class MouseEventsOverlay {
    constructor(layout_manager) {
        this.layout_manager = layout_manager
        this.drag = d3.drag()
            .on("start.drag", () => this._dragstarted())
            .on("drag.drag", () => this._dragging())
            .on("end.drag", () => this._dragended())

        this.dragged_node = null
    }


    update_data() {
        let nodes_layer = this.layout_manager.viewport.get_layer("nodes")
       if (!nodes_layer)
            return
       let nodes_selection = nodes_layer.nodes_selection
       nodes_selection.selectAll(".node_element").call(this.drag)
//            .on("click", () => this.clicked())
    }

//    clicked() {
//        if (!this.layout_manager.edit_layout)
//            return
//        let node = d3.select(d3.event.target).datum()
//        if (node.data.use_style.type() != node_visualization_layout_styles.LayoutStyleForce.prototype.type())
//            this.layout_manager.toolbar_plugin.layout_modification_element.update_current_style(node.data.use_style)
//    }

    _dragstarted() {
        if (!this.layout_manager.edit_layout)
            return
        d3.event.sourceEvent.stopPropagation();
        this._dragged_node = d3.select(d3.event.sourceEvent.target).datum()
        this._apply_drag_force(this._dragged_node, d3.event.x, d3.event.y)
        this.drag_start_x = d3.event.x
        this.drag_start_y = d3.event.y

        if (this._dragged_node.data.use_style)
            this.layout_manager.toolbar_plugin.layout_modification_element.update_current_style(this._dragged_node.data.use_style)

        this.layout_manager.dragging = true
    }

    _apply_drag_force(node, x, y) {
        node.data.node_positioning["drag"] = {}

        var force = node.data.node_positioning["drag"]
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
        var scale = 1.0
        var delta_x = d3.event.x - this.drag_start_x
        var delta_y = d3.event.y - this.drag_start_y

        var last_zoom = this.layout_manager.viewport.last_zoom
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
        } else {
            delete this._dragged_node.data.node_positioning["drag"]
        }
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
                               img: "themes/facelift/images/icon_aggr.png"})
            } else {
                elements.push({text: "Convert all nodes to " + style.prototype.description(),
                           on: ()=> this._convert_all(style),
                           href: "",
                           img: "themes/facelift/images/icon_aggr.png"})
            }
        }
        let modification_element = this.layout_manager.toolbar_plugin.layout_modification_element
        elements.push({text: "Show " + node_visualization_layout_styles.LayoutStyleForce.prototype.description() + " options",
                       on: ()=>modification_element.update_current_style(this.layout_manager.force_style),
                       href: "",
                       img: "themes/facelift/images/icon_aggr.png"})
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

        if (style_class != node_visualization_layout_styles.LayoutStyleForce) {
            let new_style = this.layout_style_factory.instantiate_style_class(style_class, node)
            chunk_layout.save_style(new_style.style_config)
            this.layout_manager.toolbar_plugin.layout_modification_element.update_current_style(node.data.use_style)
        }
        this.layout_manager.layout_applier.apply_all_layouts()
    }

    _convert_all(style_class) {
        this.layout_manager.viewport.get_hierarchy_list().forEach(node_chunk=>{
            node_chunk.layout.clear_styles()
            if (style_class == node_visualization_layout_styles.LayoutStyleFixed) {
                node_chunk.nodes.forEach(node=>{
                    node_chunk.layout.save_style(this.layout_style_factory.instantiate_style_class(style_class, node).style_config)
                })
            }
            else if (style_class != node_visualization_layout_styles.LayoutStyleForce) {
                node_chunk.layout.save_style(this.layout_style_factory.instantiate_style_class(style_class, node_chunk.nodes[0]).style_config)
            }
        })
        this.apply_all_layouts()
    }

    apply_layout_id(layout_id) {
        let new_layout = new node_visualization_layout.NodeVisualizationLayout(this.viewport)
        new_layout.deserialize(JSON.parse(JSON.stringify(this.layouts[layout_id])))
        this.apply(new_layout)
    }

    apply(new_layout) {
        console.log("apply layout", new_layout.id)
        this._apply_force_style_options(new_layout)

        let node_matcher = new node_visualization_utils.NodeMatcher(this.layout_manager.viewport.get_hierarchy_list())
        let nodes_with_style = this.find_nodes_for_layout(new_layout, node_matcher)
        this._update_node_specific_styles(nodes_with_style)

        this.current_layout_group = new_layout


        this.viewport.update_active_overlays()
    }

    apply_all_layouts(global_layout_config=null) {
        this.apply_multiple_layouts(this.viewport.get_hierarchy_list(), global_layout_config)
    }

    apply_multiple_layouts(node_chunk_list, global_layout_config) {
        let nodes_with_style = []
        let skip_layout_alignment = false
        node_chunk_list.forEach(node_chunk=>{
            let node_matcher = new node_visualization_utils.NodeMatcher([node_chunk])
            if (!node_chunk.layout) {
                node_chunk.layout = new node_visualization_layout.NodeVisualizationLayout(this)

                let use_layout = null
                if (global_layout_config) {
                    // A layout which may span over multiple chunks has been set
                    // Each chunk gets its own layout config instance, since config-wise chunks are still separated after all..
                    let enforced_layout = new node_visualization_layout.NodeVisualizationLayout(this.viewport)
                    enforced_layout.deserialize(global_layout_config)
                    node_chunk.layout = enforced_layout
                } else if (node_chunk.use_layout)
                    node_chunk.layout.deserialize(node_chunk.use_layout)
                else if (node_chunk.use_default_layout && node_chunk.use_default_layout != "force") {
                    let default_style = this.layout_style_factory.instantiate_style_name(node_chunk.use_default_layout, node_chunk.tree)
                    default_style.style_config.position = {x: 50, y: 50}
                    node_chunk.layout.save_style(default_style.style_config)
                }
            }
            else
                skip_layout_alignment = true

            nodes_with_style = nodes_with_style.concat(this.find_nodes_for_layout(node_chunk.layout, node_matcher))
        })
        this._update_node_specific_styles(nodes_with_style, skip_layout_alignment)
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
        console.log("update node styles")
        let filtered_nodes_with_style = []
        let used_nodes = []
        for (let idx in nodes_with_style) {
            let config = nodes_with_style[idx]
            if (used_nodes.indexOf(config.node) >= 0) {
                console.log("filtered duplicate style assignment",
                    this.layout_style_factory.get_style_class(config.style).prototype.compute_id(config.node))
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
                console.log("removing style " + this.layout_style_factory.get_style_class(d.style).prototype.compute_id(d.node))
            this.layout_manager.remove_active_style(d.node.data.use_style)
            d.node.data.use_style = null
        }).remove()

        node_styles.enter().append("g")
            .classed("layout_style", true)
            .each((d, idx, nodes)=> {
                console.log("create style " + this.layout_style_factory.get_style_class(d.style).prototype.compute_id(d.node))
                if (d.node.data.use_style) {
                    this.layout_manager.remove_active_style(d.node.data.use_style)
                    d.node.data.use_style = null
                }
                let new_style = this.layout_style_factory.instantiate_style(
                    d.style,
                    d.node,
                    d3.select(nodes[idx]),
                )
                this.layout_manager.add_active_style(new_style)
            }).merge(node_styles).each(d=>{
                console.log("updating style " + this.layout_style_factory.get_style_class(d.style).prototype.compute_id(d.node))
                let style_id = this.layout_style_factory.get_style_class(d.style).prototype.compute_id(d.node)
                d.node.data.use_style = this.layout_manager.get_active_style(style_id)
                d.node.data.use_style.style_config.options = d.style.options
                d.node.data.use_style.style_root_node = d.node
                d.node.data.use_style.force_style_translation()

                let abs_coords = this.layout_manager.get_absolute_node_coords({x: d.style.position.x, y: d.style.position.y}, d.node)
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
                style_configs.push(chunk_layout.style_configs[idx])
        })
        chunk_layout.style_configs = style_configs
        chunk_layout.reference_size = {width: this.viewport.width, height: this.viewport.height}
        return chunk_layout
    }

    save_layout(layout) {
        this.save_layout_template(layout)
    }

    delete_layout_id(layout_id) {
        ajax.post_url("ajax_delete_bi_template_layout.py?layout_id=" + encodeURIComponent(layout_id))
    }

    save_layout_template(layout_config) {
        ajax.post_url("ajax_save_bi_template_layout.py",
            "layout=" + encodeURIComponent(JSON.stringify(layout_config)))
    }

    // TODO: check parameters
    save_layout_for_aggregation(layout_config, aggregation_name) {
        ajax.post_url("save_bi_aggregation_layout.py",
            "layout=" + encodeURIComponent(JSON.stringify(layout_config))+
            "&aggregation_name=" + encodeURIComponent(aggregation_name)
        )
    }
}

