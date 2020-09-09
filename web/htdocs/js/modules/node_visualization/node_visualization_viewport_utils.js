// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

import * as node_visualization_utils from "node_visualization_utils"
import * as d3 from "d3"

export class LayeredLayerBase {
    constructor(viewport, enabled=true) {
        this.toggleable = false
        this.enabled = enabled
        this.viewport = viewport
        this.selection = null
    }


    // Shows the layer
    enable(layer_selections) {
        this.enabled = true
        this.selection = layer_selections.svg
        this.div_selection = layer_selections.div

        // Setup components
        this.setup()
        // Scale to size
        this.size_changed()

        // Without data simply return
        if (this.viewport.get_all_nodes().length == 0)
            return

        // Adjust zoom
        this.zoomed()
        // Update data references
        this.update_data()
        // Update gui
        this.update_gui()
    }

    disable() {
        this.enabled = false

        this.disable_hook()

        if (this.selection) {
            this.selection.selectAll("*").remove()
            this.selection = null
        }

        if (this.div_selection) {
            this.div_selection.selectAll("*").remove()
            this.div_selection = null
        }
    }

    disable_hook() {}

    setup() {}

    // Called when the viewport size has changed
    size_changed() {}

    zoomed() {}

    set_enabled(is_enabled) {
        this.enabled = is_enabled
        if (this.enabled)
            this.viewport.enable_layer(this.id())
        else
            this.viewport.disable_layer(this.id())
    }

    is_enabled() {
        return this.enabled
    }

    is_toggleable() {
        return this.toggleable
    }

    update_data() {}

    update_gui() {}

}


// base class for viewports
export class AbstractViewportPlugin {
    static id() {
        alert("Cannot fetch ID of abstract plugin");
    }

    constructor(master_viewport) {
        this._master_viewport = master_viewport;
        this.main_instance = this._master_viewport.main_instance;
    }

    setup(into_selection) {}

    feed_data(json_data) {}

    get_current_datasource() {
        return this._master_viewport.get_current_datasource();
    }
}


// base class for layered viewport overlays
export class LayeredOverlayBase extends LayeredLayerBase {
    constructor(viewport, enabled=true) {
        super(viewport, enabled)
        this.toggleable = true
    }
}

export class AbstractGUINode {
    constructor(nodes_layer, node) {
        this.nodes_layer = nodes_layer
        this.viewport = nodes_layer.viewport
        this.node = node
        this.radius = 5

        this.selection = null
        this._text_selection = null

        this._quickinfo_selection = null
        // Data fetched from external sources, e.g livestatus
        //
        this._has_quickinfo = true
        this._provides_external_quickinfo_data = false
        this._quickinfo_fetch_in_progress = false
        this._external_quickinfo_data = null
    }

    id() {
        return this.node.data.id
    }

    _clear_cached_data() {
        this._external_quickinfo_data = null
    }

    update_node_data(node, selection) {
        this._clear_cached_data()
        node.selection = selection
        this.node = node
        this.update_node_state()
    }

    update_node_state() {
        this.selection.select("circle.state_circle")
            .classed("state0", false)
            .classed("state1", false)
            .classed("state2", false)
            .classed("state3", false)
            .classed("state" + this.node.data.state, true)


        let ack = []
        if (this.node.data.acknowledged)
            ack.push(null)
        let ack_selection = this.selection.selectAll("image.acknowledged").data(ack)
        ack_selection.enter().append("svg:image")
                .classed("acknowledged", true)
                .attr("xlink:href", this.viewport.main_instance.get_theme_prefix() + "/images/icon_ack.png")
                .attr("x", -24)
                .attr("y", this.radius - 8)
                .attr("width", 24)
                .attr("height", 24)
        ack_selection.exit().remove()

        let in_dt = []
        if (this.node.data.in_downtime)
            in_dt.push(null)
        let dt_selection = this.selection.selectAll("image.in_downtime").data(in_dt)
        dt_selection.enter().append("svg:image")
                .classed("in_downtime", true)
                .attr("xlink:href", this.viewport.main_instance.get_theme_prefix() + "/images/icon_downtime.png")
                .attr("x", 0)
                .attr("y", this.radius - 8)
                .attr("width", 24)
                .attr("height", 24)
        dt_selection.exit().remove()
    }

    render_into(selection) {
        this.selection = this._render_into_transform(selection)
        this.node.selection = this.selection

        this.render_object()
        this.render_text()
        this.update_node_state()
    }

    render_text() {
        if (this.node.data.show_text == false) {
            this.text_selection.remove()
            this.text_selection = null
            return
        }

        if (this.text_selection == null) {
            let text_selection = this.selection.selectAll("g").data([this.node.data])
            this.text_selection = text_selection.enter().append("g")
                   .append("text")
                   .style("pointer-events", "none")
                   .classed("noselect", true)
                   .attr("transform", "translate(" + (this.radius+3) + "," + (this.radius+3) + ")")
                   .attr("text-anchor", "start")
                   .text(d=>{
                       if (d.chunk.aggr_type == "single" && d.service)
                           return d.service
                       return d.name
                   })
                   .merge(text_selection)
        }

        let text_positioning = this.node.data.current_positioning.text_positioning
        if (text_positioning) {
            this.add_optional_transition(this.text_selection).call(text_positioning, this.radius)
        } else {
            this.add_optional_transition(this.text_selection).call((selection)=>this._default_text_positioning(selection,this.radius))
        }
    }

    _default_text_positioning(selection, radius) {
        selection.attr("transform", "translate(" + (radius+3) + "," + (radius+3) + ")")
        selection.attr("text-anchor", "start")
    }

    _render_into_transform(selection) {
        let spawn_point_x = this.node.x
        let spawn_point_y = this.node.y

        let coords = this.nodes_layer.viewport.scale_to_zoom({x: spawn_point_x, y: spawn_point_y})

        this.node.data.target_coords = {x: spawn_point_x, y: spawn_point_y}
        return selection.append("g")
             .classed("node_element", true)
             .attr("transform", "translate("+spawn_point_x+","+spawn_point_y+")")
             .style("pointer-events", "all")
             .on("mouseover", () => this._show_quickinfo())
             .on("mouseout", () => this._hide_quickinfo())
             .on("contextmenu", () => this.nodes_layer.render_context_menu(this))
    }

    _get_details_url() {
        return null
    }

    get_context_menu_elements() {
        let elements = []
        elements.push({text: "Details of Host", href:
                "view.py?host=" + encodeURIComponent(this.node.data.hostname) +
               "&view_name=host",
                img: this.viewport.main_instance.get_theme_prefix() + "/images/icon_status.png"
        })
        if (this.node.data.service && this.node.data.service != "") {
            elements.push({text: "Details of Service", href:
                "view.py?host=" + encodeURIComponent(this.node.data.hostname) + "&service=" +
                encodeURIComponent(this.node.data.service) +
                "&view_name=service",
                img: this.viewport.main_instance.get_theme_prefix() + "/images/icon_status.png"
            })
        }

    // Debugging: Writes node content to console
    // elements.push({text:  "Dump node",
    //         on: ()=> console.log(this.node)
    // })
        return elements
    }

    _filter_root_cause(node) {
        if (!node._children)
            return
        let critical_children = []
        node._children.forEach(child_node=>{
            if (child_node.data.state != 0) {
                critical_children.push(child_node)
                this._filter_root_cause(child_node)
            } else {
                this._clear_node_positioning_of_tree(child_node)
            }
        })
        node.children = critical_children
        this.update_collapsed_indicator(node)
    }

    _clear_node_positioning_of_tree(tree_root) {
        tree_root.data.node_positioning = {}
        if (!tree_root._children)
            return

        tree_root._children.forEach(child_node=>{
            this._clear_node_positioning_of_tree(child_node)
        })
    }

    toggle_collapse() {
        d3.event.stopPropagation()
        if (!this.node._children)
            return

        this.node.children = this.node.children ? null : this.node._children
        this.viewport.recompute_node_chunk_descendants_and_links(this.node.data.chunk)
        this.update_collapsed_indicator(this.node)
        this.viewport.update_layers()
    }

    collapse_node() {
        this.node.children = null
        this.viewport.recompute_node_chunk_descendants_and_links(this.node.data.chunk)
        this.update_collapsed_indicator(this.node)
        this.viewport.update_layers()
    }

    expand_node() {
        this.node.children = this.node._children
        this.viewport.recompute_node_chunk_descendants_and_links(this.node.data.chunk)
        this.update_collapsed_indicator(this.node)
        this.viewport.update_layers()
    }

    expand_node_including_children(node) {
        if (node._children) {
            node.children = node._children
            node.children.forEach(child_node=>this.expand_node_including_children(child_node))
        }
        this.update_collapsed_indicator(node)
    }

    update_collapsed_indicator(node) {
        if (!node._children)
            return

        let collapsed = node.children != node._children
        let outer_circle = node.selection.select("#outer_circle")
        outer_circle.classed("collapsed", collapsed)

        let nodes = this.viewport.get_all_nodes()
        for (let idx in nodes) {
            nodes[idx].data.transition_info.use_transition = true
        }
    }

    _fixate_quickinfo() {
        if (this.viewport.layout_manager.edit_layout)
            return

        if (this._quickinfo_selection && this._quickinfo_selection.classed("fixed")) {
            this._hide_quickinfo(true)
            return
        }

        this._show_quickinfo()
        this._quickinfo_selection.classed("fixed", true)
    }

    _hide_quickinfo(force=false) {
        if (!this._quickinfo_selection || (this._quickinfo_selection.classed("fixed") && !force))
            return

        this._quickinfo_selection.remove()
        this._quickinfo_selection = null
    }

    _show_quickinfo() {
        if (!this._has_quickinfo)
            return

        if (this.viewport.layout_manager.edit_layout)
            return

        let div_selection = this.nodes_layer.div_selection.selectAll("div.quickinfo").data([this.node], d=>d.data.id)
        div_selection.exit().remove()
        this._quickinfo_selection = div_selection.enter().append("div")
                            .classed("quickinfo", true)
                            .classed("noselect", true)
                            .classed("box", true)
                            .style("position", "absolute")
                            .style("pointer-events", "all")
                            .on("click", ()=>this._hide_quickinfo(true))
                        .merge(div_selection)

        if (this._provides_external_quickinfo_data)
            this._show_external_html_quickinfo()
        else
            this._show_table_quickinfo()
    }

    _show_external_html_quickinfo() {
        if (this._external_quickinfo_data != null && this.viewport.feed_data_timestamp < this._external_quickinfo_data.fetched_at_timestamp) {
            // Replace content
            this._quickinfo_selection.selectAll("*").remove()
            this._quickinfo_selection.node().append(this._external_quickinfo_data.data.cloneNode(true).body)
        }
        else if (!this._quickinfo_fetch_in_progress)
                this._fetch_external_quickinfo()
        if (this._quickinfo_fetch_in_progress)
            this._quickinfo_selection.selectAll(".icon.reloading").data([null]).enter()
                .append("img")
                .classed("icon", true)
                .classed("reloading", true)
                .attr("src", this.viewport.main_instance.get_theme_prefix() + "/images/load_graph.png")
        else
            this._quickinfo_selection.selectAll(".icon.reloading").remove()

        this.update_quickinfo_position()
    }

    _show_table_quickinfo() {
        let table_selection = this._quickinfo_selection.selectAll("table").data([this.node], d=>d.data.id)
        let table = table_selection.enter().append("body").append("table")
                .classed("data", true)
                .classed("single", true)
                .append("tbody")
                .merge(table_selection)

        let even = "even";
        let quickinfo = this._get_basic_quickinfo()
        let rows = table.selectAll("tr").data(quickinfo).enter().append("tr");
        rows.each(function() {
            this.setAttribute("class", even.concat("0 data"));
            even = (even == "even") ? "odd" : "even";
        });
        rows.append("td").classed("left", true).text(d=>d.name)
        rows.append("td").text(d=>d.value).each((d, idx, tds)=>{
                let td = d3.select(tds[idx])
                if ("css_classes" in d)
                    d.css_classes.forEach(name=>td.classed(name, true))
            })
        this.update_quickinfo_position()
    }

    _got_quickinfo(json_data) {
        let now = Math.floor(new Date().getTime()/1000);
        this._external_quickinfo_data = {fetched_at_timestamp: now, data: json_data}
        this._quickinfo_fetch_in_progress = false
        if (this._quickinfo_selection)
            this._show_quickinfo()
    }

    _state_to_text(state) {
        let monitoring_states = {"0": "OK", "1": "WARN", "2": "CRIT", "3": "UNKNOWN"}
        return monitoring_states[state]
    }

    render_object() {
        this.selection
              .append("a")
              .attr("xlink:href", this._get_details_url())
              .append("circle")
              .attr("r", this.radius)
              .classed("state_circle", true)

        this.update_node_state()
    }


    update_position(enforce_transition=false) {
        this.node.data.target_coords = this.viewport.scale_to_zoom({x: this.node.x, y: this.node.y})

        if (this.node.data.transition_info.use_transition || this.node.data.current_positioning.type == "force")
            this.selection.interrupt()

        if (this.selection.attr("in_transit") > 0) {
            return
        }
        this.add_optional_transition(this.selection, enforce_transition)
            .attr("transform", "translate("+this.node.data.target_coords.x+","+this.node.data.target_coords.y+")")

        this.update_quickinfo_position()
        this.render_text()
        this.node.data.transition_info.type = this.node.data.current_positioning.type
    }

    update_quickinfo_position() {
        if (this._quickinfo_selection == null)
            return
        let coords = this.viewport.translate_to_zoom({x: this.node.x, y: this.node.y})
        this._quickinfo_selection
            .style("left", (coords.x + this.radius) + "px")
            .style("top", coords.y + "px")
    }

    add_optional_transition(selection, enforce_transition) {
        if ((!this.node.data.transition_info.use_transition && !enforce_transition) || this.viewport.layout_manager.dragging)
            return selection
        return node_visualization_utils.DefaultTransition.add_transition(selection.attr("in_transit", 100))
            .on("end", d=>{
                let matrix = this.selection.node().transform.baseVal[0].matrix
                // TODO: check this preliminary fix. target_coords might be empty
                if (!this.node.data.target_coords)
                    return
                if (matrix.e.toFixed(2) != this.node.data.target_coords.x.toFixed(2) ||
                    matrix.f.toFixed(2) != this.node.data.target_coords.y.toFixed(2)) {
                    this.update_position(true)
                    node_visualization_utils.log(7, "update position after transition")
                }
            }).attr("in_transit", 0)
            .on("interrupt", ()=>{
               node_visualization_utils.log(7, "node update position interrupt")
                this.selection.attr("in_transit", 0)
            }).attr("in_transit", 0)
    }
}

export class TopologyNode extends AbstractGUINode {
    static id() {
        return "topology"
    }

    constructor(nodes_layer, node) {
        super(nodes_layer, node)
        this.radius = 9
        this._provides_external_quickinfo_data = true
    }

    render_object() {
        AbstractGUINode.prototype.render_object.call(this)

        if (this.node.data.has_no_parents)
            this.selection.select("circle").classed("has_no_parents", true)

        this.selection.on("dblclick", ()=>this._toggle_growth_continue())
    }

    update_position() {
        AbstractGUINode.prototype.update_position.call(this);

        // Growth root
        let growth_root_selection = this.selection.selectAll("circle.growth_root").data([this.node]);
        if (this.node.data.growth_root) {
            growth_root_selection.enter().append("circle")
                    .classed("growth_root", true)
                    .attr("r", this.radius + 4)
                    .attr("fill", "none")
        }
        else
            growth_root_selection.remove();

        // Growth possible
        let growth_possible_selection = this.selection.selectAll("image.growth_possible").data([this.node]);
        if (this.node.data.growth_possible) {
            growth_possible_selection.enter().append("svg:image")
                .classed("growth_possible", true)
                .attr("xlink:href", this.viewport.main_instance.get_theme_prefix() + "/images/icon_hierarchy.svg")
                .attr("width", 16)
                .attr("height", 16)
                .attr("x", -8)
                .attr("y", 0);
        }
        else
            growth_possible_selection.remove();


        // Growth forbidden
        let growth_forbidden_selection = this.selection.selectAll("image.growth_forbidden").data([this.node]);
        if (this.node.data.growth_forbidden) {
            growth_forbidden_selection.enter().append("svg:image")
                .classed("growth_forbidden", true)
                .attr("xlink:href", this.viewport.main_instance.get_theme_prefix() + "/images/icon_no_entry.svg")
                .attr("width", 16)
                .attr("height", 16)
                .attr("x", -28)
                .attr("y", 0);
        }
        else
            growth_forbidden_selection.remove();
    }

    _fetch_external_quickinfo() {
        this._quickinfo_fetch_in_progress = true
        let view_url = null
        view_url = "view.py?view_name=topology_hover_host&display_options=I&host=" + encodeURIComponent(this.node.data.hostname)
        d3.html(view_url ,{credentials: "include"}).then(html=>this._got_quickinfo(html))
    }

    get_context_menu_elements() {
        let elements = AbstractGUINode.prototype.get_context_menu_elements.call(this)
        elements = elements.concat(this._get_topology_menu_elements())
        return elements
    }


    _get_topology_menu_elements() {
        // Toggle root node
        let elements = []
        let root_node_text = "Add root node"
        if (this.node.data.growth_root)
            root_node_text = "Remove root node"
        elements.push({text: root_node_text,
                on: ()=> this._toggle_root_node()
        })

        // Use this node as exclusive root node
        elements.push({text: "Set root node",
                on: ()=> this._set_root_node()
        })

        // Forbid further growth
        let growth_forbidden_text = "Forbid further hops"
        if (this.node.data.growth_forbidden)
            growth_forbidden_text = "Allow further hops"
        elements.push({text:  growth_forbidden_text,
                on: ()=> this._toggle_stop_growth()
        })
        return elements
    }

    _toggle_stop_growth() {
        this.node.data.growth_forbidden = !this.node.data.growth_forbidden;
        this.nodes_layer.viewport.main_instance.update_data();
    }

    _toggle_root_node() {
        this.node.data.growth_root = !this.node.data.growth_root;
        this.nodes_layer.viewport.main_instance.update_data();
    }

    _set_root_node() {
        this.nodes_layer.viewport.get_all_nodes().forEach(node=>{
            node.data.growth_root = false
        })
        this.node.data.growth_root = true
        this.nodes_layer.viewport.main_instance.update_data();
    }

    _toggle_growth_continue() {
        this.node.data.growth_continue = !this.node.data.growth_continue;
        this.nodes_layer.viewport.main_instance.update_data();
    }

}

node_visualization_utils.node_type_class_registry.register(TopologyNode)
