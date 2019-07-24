import * as d3 from "d3";
import * as node_visualization_viewport_utils from "node_visualization_viewport_utils"
import * as node_visualization_utils from "node_visualization_utils"
import * as node_visualization_layout_styles from "node_visualization_layout_styles"

export class LayeredDebugLayer extends node_visualization_viewport_utils.LayeredLayerBase {
    id() {
        return "debug_layer"
    }

    name() {
        return "Debug Layer"
    }

    setup() {
        this.overlay_active = false
    }

    update_gui() {
//        this.translation_info.selectAll("td#Simulation").text("Alpha: " + this.viewport.layout_manager.force_style.simulation.alpha().toFixed(3) +
//                                        " Tick("+node_visualization_layout_styles.tick_count+"): " + node_visualization_layout_styles.tick_duration)

//        this._update_chunk_boundaries()
        if (this.overlay_active == this.viewport.layout_manager.edit_layout)
            return

        if (this.viewport.layout_manager.edit_layout)
            this.enable_overlay()
        else
            this.disable_overlay()
    }

    _update_chunk_boundaries() {
        if (!this.viewport.layout_manager.edit_layout) {
            this.selection.selectAll("rect.boundary").remove()
            return
        }

        let boundary_list = []
        this.viewport.get_hierarchy_list().forEach(node_chunk=>{
            let coords = this.viewport.translate_to_zoom(node_chunk.coords)
            coords.id = node_chunk.tree.data.id
            boundary_list.push(coords)
        })


        let boundaries = this.selection.selectAll("rect.boundary").data(boundary_list, d=>d.id)
        boundaries.exit().remove()
        boundaries = boundaries.enter().append("rect")
            .classed("boundary", true)
            .attr("fill", "none")
            .attr("stroke", "black")
            .attr("stroke-width", 1)
            .merge(boundaries)


        boundaries.attr("x", d=>d.x)
            .attr("y", d=>d.y)
            .attr("width", d=>d.width)
            .attr("height", d=>d.height)
    }


    enable_overlay() {
        this.overlay_active = true
        this.anchor_info = this.selection.append("g").attr("transform", "translate(-50,-50)")
//        this.anchor_info.append("rect")
//            .attr("id", "horizontal")
//            .attr("x", -50)
//            .attr("height", 2)
//            .attr("fill", "black")
//        this.anchor_info.append("rect")
//            .attr("id", "vertical")
//            .attr("y", -50)
//            .attr("width", 2)
//            .attr("fill", "black")
//
//        this.anchor_info.append("text")
//            .attr("id", "horizontal_text")
//            .attr("x", -50)
//            .attr("y", -2)
//
//        this.anchor_info.append("text")
//            .attr("id", "vertical_text")
//            .attr("x", 2)
//            .attr("y", -42)

        this.div_selection.append("input")
            .style("pointer-events", "all")
            .attr("id", "reset_pan_and_zoom")
            .attr("type", "button")
            .classed("button", true)
            .attr("value", "Reset panning and zoom")
            .on("click", ()=>this.reset_pan_and_zoom())
            .style("opacity", 0)
            .transition()
            .duration(node_visualization_utils.DefaultTransition.duration())
            .style("opacity", 1)

//        this.div_selection.append("input")
//            .style("pointer-events", "all")
//            .attr("id", "reset_pan_and_zoom")
//            .attr("type", "button")
//            .classed("button", true)
//            .attr("value", "Stop simulation")
//            .on("click", ()=>{
//                this.viewport.layout_manager.force_style.simulation.alpha(0)
//            })
//            .style("opacity", 0)
//            .transition()
//            .duration(node_visualization_utils.DefaultTransition.duration())
//            .style("opacity", 1)



        this.viewport.selection.on("mousemove.translation_info", ()=>this.mousemove())
        let rows = this.div_selection.append("table")
                    .attr("id", "translation_infobox")
                    .selectAll("tr").data(["Zoom", "Panning", "Mouse"])
        let rows_enter = rows.enter().append("tr")
        rows_enter.append("td").text(d=>d).classed("noselect", true)
        rows_enter.append("td").attr("id", d=>d).classed("noselect", true)
        this.size_changed()
        this.zoomed()
    }

    disable_overlay() {
        this.overlay_active = false
        this.selection.selectAll("*").transition().duration(node_visualization_utils.DefaultTransition.duration()).attr("opacity", 0).remove()
        this.div_selection.selectAll("*").transition().duration(node_visualization_utils.DefaultTransition.duration()).style("opacity", 0).remove()
        this.viewport.selection.on("mousemove.translation_info", null)
    }

    size_changed() {
        if (!this.overlay_active)
            return
//        this.anchor_info.select("#horizontal").attr("width", this.viewport.width + 50)
//        this.anchor_info.select("#vertical").attr("height", this.viewport.height + 50)
//        this.anchor_info.select("#horizontal_text").text(parseInt(this.viewport.width) + "px")
//        this.anchor_info.select("#vertical_text").text(parseInt(this.viewport.height) + "px")
    }

    reset_pan_and_zoom() {
        this.viewport.svg_content_selection
            .transition()
            .duration(node_visualization_utils.DefaultTransition.duration())
            .call(
            this.viewport.main_zoom.transform,
            d3.zoomIdentity)
    }

    zoomed() {
        if (!this.overlay_active)
            return
        this.anchor_info.attr("transform", this.viewport.last_zoom)
        this.div_selection.selectAll("td#Zoom").text(this.viewport.last_zoom.k.toFixed(2))
        this.div_selection.selectAll("td#Panning").text("X: "+parseInt(this.viewport.last_zoom.x) +
                                                        " / Y:"+parseInt(this.viewport.last_zoom.y))
    }

    mousemove() {
        let coords = d3.mouse(this.anchor_info.node())
        this.div_selection.selectAll("td#Mouse").text("X:"+parseInt(coords[0])+ " / Y:"+parseInt(coords[1]))
    }
}

export class LayeredRuleIconOverlay extends node_visualization_viewport_utils.LayeredOverlayBase {
    id() {
        return "rule_icon_overlay"
    }

    name() {
        return "Rule icons"
    }

    update_gui() {
        let nodes = []
        this.viewport.get_all_nodes().forEach(node=>{
            if (!node.data.icon)
                return
            nodes.push(node)
        })

        let icons = this.div_selection.selectAll("img").data(nodes, d=>d.data.id)
        icons.exit().remove()
        icons = icons.enter().append("img")
                        .attr("src", d=> {return "images/icons/" + d.data.icon + ".png"})
                        .classed("bi_rule_icon", true)
                        .style("position", "absolute")
                        .style("pointer-events", "none")
                     .merge(icons)

        icons.style("left", d=>{return this.viewport.translate_to_zoom({x: d.x, y:0}).x + 5 + "px"})
             .style("top", d=>{return (this.viewport.translate_to_zoom({x: 0, y:d.y}).y - 40) + "px"})
    }
}


export class LayeredCustomOverlay extends node_visualization_viewport_utils.LayeredOverlayBase {
    id() {
        return "custom_overlay"
    }

    name() {
        return "Demo: Custom-Overlay"
    }

    constructor(viewport) {
        super(viewport)
        this.node_matcher = null
        this.previous_vertices = {}
    }

    zoomed() {
        this.overlays_container.attr("transform", this.viewport.last_zoom)
    }

    setup() {
        this.overlays_container = this.selection.append("g")
    }

    update_data() {
        this.node_matcher = new node_visualization_utils.NodeMatcher(this.viewport.get_hierarchy_list())
        this.previous_vertices = {}
    }

    update_gui() {
        let demo_elements = [
            {rule_id: "networking", text: "Network", color: "steelblue"},
            {rule_id: "other", text: "Other", color: "green"},
            {rule_id: "performance", text: "Performance", color: "red"},
            {rule_id: "filesystems", text: "Disks & Filesystems", color: "yellow"},
            {rule_id: "general", text: "General", color: "gray"}
        ]

        let demo_with_coords = []
        demo_elements.forEach(element=>{
            let node = this.node_matcher.find_node({rule_id: {value: element.rule_id}})
            if (!node)
                return
            let vertices = []
            let x_min= 10000
            let x_max= -10000
            let y_min= 10000
            let y_max= -10000

            node.descendants().forEach(descendant =>{
                vertices.push([descendant.x, descendant.y])
                x_min = Math.min(descendant.x, x_min)
                y_min = Math.min(descendant.y, y_min)
                x_max = Math.max(descendant.x, x_max)
                y_max = Math.max(descendant.y, y_max)
            })
            vertices.push([x_min, y_min - 20])
            vertices.push([x_min + 100, y_min - 20])

            let current_vertices = JSON.stringify(vertices)
            let previous_vertices = this.previous_vertices[element.rule_id]
            let requires_update = current_vertices != previous_vertices
            this.previous_vertices[element.rule_id] = current_vertices
            demo_with_coords.push({node: node,
                                   coords: {x: x_min, y: y_min, width: x_max - x_min, height: y_max - y_min},
                                   element: element, polygonHull: d3.polygonHull(vertices), requires_update: requires_update})
        })

//        this.update_rect(demo_with_coords)
        this.update_hull(demo_with_coords)
    }


    update_hull(demo_with_coords) {
        let hull = this.overlays_container.selectAll("path.custom_overlay").data(demo_with_coords, d=>d.node.data.id)
        hull.exit().each(d=>delete this.previous_vertices[d.element.rule_id]).remove()
        hull = hull.enter().append("path")
                    .classed("custom_overlay", true)
                    .attr("pointer-events", "none")
                    .attr("fill" , d=>d.element.color)
                    .attr("stroke", d=>d.element.color)
                    .attr("stroke-width", 40)
                    .attr("stroke-linejoin","round")
                    .attr("opacity" , 0.3)
                .merge(hull)

        hull.each((element, idx, paths)=>{
            if (element.requires_update) {
                let path = d3.select(paths[idx])
                this.add_optional_transition(path, element)
                    .attr("d", d=>{return "M" + d.polygonHull.join("L") + "Z";})
                    .on("interrupt", ()=>{console.log("interrupted")})
                    .on("end", ()=>{console.log("end")})
            }
        })

        let text = this.overlays_container.selectAll("text").data(demo_with_coords, d=>d.node.data.id)
        text = text.enter().append("text").text(d=>d.element.text)
                    .merge(text)
                 .attr("x", d=>d.coords.x)
                 .attr("y", d=>d.coords.y - 20)
    }

    add_optional_transition(selection, element) {
        if (this.viewport.layout_manager.dragging || Object.keys(element.node.data.node_positioning).length == 0)
            return selection
        return node_visualization_utils.DefaultTransition.add_transition(selection)
    }


    update_rect(demo_with_coords) {
        let areas = this.overlays_container.selectAll("g.area").data(demo_with_coords, d=>d.node.data.id)
        areas.exit().remove()

        let areas_enter = areas.enter().append("g").classed("area", true)
        areas_enter.append("rect")
            .attr("pointer-events", "none")
            .attr("rx" , 12)
            .attr("ry" , 12)
            .attr("fill" , d=>d.element.color)
            .attr("opacity" , 0.3)

        areas_enter.append("text").text(d=>d.element.text)
                        .attr("x", 20)
                        .attr("y", 20)

        areas = areas_enter.merge(areas)
        let boundary = 50
        areas.select("rect").attr("width" , d=>d.coords.width + 2*boundary)
                            .attr("height" , d=>d.coords.height + 2*boundary)
        areas.attr("transform", d=>{return "translate(" + (d.coords.x - boundary) + "," + (d.coords.y - boundary) + ")"})
    }
}


export class LayeredExternalDataOverlay extends node_visualization_viewport_utils.LayeredOverlayBase {
    id() {
        return "external_data_overlay"
    }

    name() {
        return "Demo: External data"
    }

    constructor(viewport) {
        super(viewport)
        this.node_matcher = null
        setInterval(()=>this.change_data(), 3500)
    }

    update_data() {
        this.node_matcher = new node_visualization_utils.NodeMatcher(this.viewport.get_hierarchy_list())
    }

    change_data() {
        this.current_value = parseInt(Math.random() * 20) + 2
        this.update_gui()
        this.update_moving_dots()
    }

    update_gui() {
        if (!this.enabled)
            return

        let crossinfo = [
            {
                source: {matcher: {service: {value: "TCP Connections"}}},
                target: {matcher: {service: {value: "Check_MK Agent"}}},
            },
        ]

        let matches = []
        crossinfo.forEach(info=>{
            let source_node = this.node_matcher.find_node(info.source.matcher)
            let target_node = this.node_matcher.find_node(info.target.matcher)
            if (source_node && target_node)
                matches.push({source_node: source_node,
                              target_node: target_node})
        })
        this.process_matches(matches)
    }


    process_matches(matches) {
        let matches_selection = this.selection.selectAll("path.crossinfo").data(matches)
        matches_selection.exit().remove()
        matches_selection.enter().append("path")
            .classed("crossinfo", true)
            .attr("stroke-width", 2)
            .attr("fill", "none")
            .style("stroke", "red")
          .merge(matches_selection)
            .attr("d", d=>this.diagonal(d))

        let scale_x = this.viewport.scale_x
        let scale_y = this.viewport.scale_y
        let text_selection = this.selection.selectAll("text.crossinfo").data(matches)
        text_selection.exit().remove()
        text_selection.enter().append("text")
            .classed("crossinfo", true)
            .merge(text_selection)
            .text(this.current_value + " Packets")
            .attr("font-size", 20)
            .attr("x", d => this.viewport.translate_to_zoom({x: (d.source_node.x + d.target_node.x + 10)/2, y:0}).x)
            .attr("y", d => this.viewport.translate_to_zoom({y: (d.source_node.y + d.target_node.y)/2, x:0}).y)
            .attr("width", 200)
            .attr("height", 50)
    }

    update_moving_dots() {
        if (!this.selection)
            return
        this.selection.selectAll("path.crossinfo")
            .each((instance, idx, paths)=> {
                this.selection.selectAll("circle.moving_dot").remove()
                let circle = this.selection.selectAll("circle.moving_dot").data([...Array(this.current_value).keys()])
                circle = circle.enter().append("circle")
                    .attr("x", instance.source_node.x)
                    .attr("y", instance.source_node.y)
                    .classed("moving_dot", true)
                    .attr("r", 6)
                    .merge(circle)
                this.transition(circle, paths[idx])
            })
    }

    transition(circle, path) {
      circle.transition()
      .delay(d=>d*60)
      .duration(3000)
      .attrTween("transform", this.translateAlong(path))
    }

    translateAlong(path) {
      let l = path.getTotalLength();
      return function(d, i, a) {
        return function(t) {
          let p = path.getPointAtLength(t * l);
          return "translate(" + p.x + "," + p.y + ")";
        };
      };
    }

    // Creates a curved (diagonal) path from parent to the child nodes
    diagonal(info) {
        let source = this.viewport.translate_to_zoom({x: info.source_node.x, y: info.source_node.y})
        let target = this.viewport.translate_to_zoom({x: info.target_node.x, y: info.target_node.y})

        let s = {}
        let d = {}
        s.y = source.x
        s.x = source.y
        d.y = target.x
        d.x = target.y
        let path = `M ${s.y} ${s.x}
                C ${(s.y + d.y) / 2} ${s.x},
                  ${(s.y + d.y) / 2} ${d.x},
                  ${d.y} ${d.x}`

        return path
    }
}

//#.
//#   .-Nodes Layer--------------------------------------------------------.
//#   |      _   _           _             _                               |
//#   |     | \ | | ___   __| | ___  ___  | |    __ _ _   _  ___ _ __      |
//#   |     |  \| |/ _ \ / _` |/ _ \/ __| | |   / _` | | | |/ _ \ '__|     |
//#   |     | |\  | (_) | (_| |  __/\__ \ | |__| (_| | |_| |  __/ |        |
//#   |     |_| \_|\___/ \__,_|\___||___/ |_____\__,_|\__, |\___|_|        |
//#   |                                               |___/                |
//#   +--------------------------------------------------------------------+


class AbstractGUINode {
    constructor(nodes_layer, node) {
        this.nodes_layer = nodes_layer
        this.viewport = nodes_layer.viewport
        this.node = node
        this.radius = 5

        this.selection = null
        this._text_selection = null

        this._quickinfo_selection = null
        // Data fetched from external sources, e.g livestatus
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
                   .text(d=>{return d.service ? d.service : d.name})
                   .merge(text_selection)
        }

        let text_positioning = this.node.data.current_positioning.text_positioning
        if (text_positioning) {
            this.text_selection.call(text_positioning, this.radius)
        } else {
            this.text_selection.call((selection)=>this._default_text_positioning(selection,this.radius))
        }
    }

    _default_text_positioning(selection, radius) {
        selection.attr("transform", "translate(" + (radius+3) + "," + (radius+3) + ")")
        selection.attr("text-anchor", "start")
    }

    _render_into_transform(selection) {
        let spawn_point_x = this.node.x
        let spawn_point_y = this.node.y

        // TODO: check spawn point mechanic
        //       Points show generally spawn in the center of the viewport
//        let spawn_point = this.nodes_layer.viewport.point_spawn_location
//        if (spawn_point) {
//            spawn_point_x = spawn_point[0]
//            spawn_point_y = spawn_point[1]
//        }
        let coords = this.nodes_layer.viewport.scale_to_zoom({x: spawn_point_x, y: spawn_point_y})

        this.node.data.target_coords = {x: spawn_point_x, y: spawn_point_y}
        return selection.append("g")
             .classed("node_element", true)
             .attr("transform", "translate("+spawn_point_x+","+spawn_point_y+")")
             .style("pointer-events", "all")
             .attr("x", coords.x)
             .attr("y", coords.y)
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
                "view.py?host=" + encodeURIComponent(this.node.data.hostname) + "&service=" + encodeURIComponent(this.node.data.service) +
                "&view_name=service",
                img: this.viewport.main_instance.get_theme_prefix() + "/images/icon_status.png"
            })
        }
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
            }
        })
        node.children = critical_children
        this.update_collapsed_indicator(node)
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

        // TODO: refactor/remove
//        this.viewport.point_spawn_location = [node.x, node.y]
        let nodes = this.viewport.get_all_nodes()
        for (let idx in nodes) {
            nodes[idx].use_transition = true
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
        if (this.viewport.layout_manager.edit_layout)
            return

        let div_selection = this.nodes_layer.div_selection.selectAll("div.quickinfo").data([this.node], d=>d.data.id)
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

        let quickinfo = this._get_basic_quickinfo()
        let rows = table.selectAll("tr").data(quickinfo).enter().append("tr").classed("data", true).classed("even0", true)
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
        let monitoring_states = {"0": "OK", "1": "WARN", "2": "CRIT", "3": "UNKOWN"}
        return monitoring_states[state]
    }

    render_object() {
        this.selection.append("circle")
              .attr("id", "outer_circle")
              .classed("collapsed", this.node.data.collapsed)
              .attr("r", this.radius + 1)
              .attr("fill", "black")

        this.selection
              .append("a")
              .attr("xlink:href", this._get_details_url())
              .append("circle")
              .attr("r", this.radius)
              .classed("state_circle", true)
//              .style("fill-opacity", 0.8)
//              .style("stroke", "black")
//              .style("stroke-width", 1)
//              .classed("state" + this.node.data.state, true)

//        this.selection.append("circle")
//              .attr("r", this.radius - 4)
//              .style("fill-opacity", 1)
//              .attr("fill", "ghostwhite");
// 
        this.update_node_state()
    }


    update_position() {
//        // TODO: transition event: end
        if (this.selection.attr("transit") > 0) {
            return
        }

        this.node.data.target_coords = this.viewport.scale_to_zoom({x: this.node.x, y: this.node.y})
        this.add_optional_transition(this.selection)
            .attr("transform", "translate("+this.node.data.target_coords.x+","+this.node.data.target_coords.y+")")

        this.update_quickinfo_position()
        this.render_text()
    }

    update_quickinfo_position() {
        if (this._quickinfo_selection == null)
            return
        let coords = this.viewport.translate_to_zoom({x: this.node.x, y: this.node.y})
        this._quickinfo_selection
            .style("left", (coords.x + this.radius) + "px")
            .style("top", coords.y + "px")
    }

    add_optional_transition(selection) {
        if (!this.node.use_transition || this.viewport.layout_manager.dragging)
            return selection

        return node_visualization_utils.DefaultTransition.add_transition(selection.attr("transit", 100)).attr("transit", 0)
    }
}

class GenericNode extends AbstractGUINode {
    constructor(nodes_layer, node) {
        super(nodes_layer, node)
        this.radius = 9
    }

    render_object() {
        AbstractGUINode.prototype.render_object.call(this)
        if (this.node.data.topology_root)
            this.selection.select("circle").classed("topology_root", true)
    }

    _get_basic_quickinfo() {
        let quickinfo = []
        quickinfo.push({name: "Host name", value: this.node.data.hostname})
        if ("service" in this.node.data)
            quickinfo.push({name: "Service description", value: this.node.data.service})
        return quickinfo
    }
}

class BILeafNode extends AbstractGUINode {
    constructor(nodes_layer, node) {
        super(nodes_layer, node)
        this.radius = 9
        this._provides_external_quickinfo_data = true
    }

    _get_basic_quickinfo() {
        let quickinfo = []
        quickinfo.push({name: "Host name", value: this.node.data.hostname})
        if ("service" in this.node.data)
            quickinfo.push({name: "Service description", value: this.node.data.service})
        return quickinfo
    }

    _fetch_external_quickinfo() {
        this._quickinfo_fetch_in_progress = true
        let view_url = null
        if ("service" in this.node.data)
            // TODO: add site to url
            view_url = "view.py?view_name=bi_map_hover_service&display_options=I&host=" +
                        encodeURIComponent(this.node.data.hostname) + "&service=" + encodeURIComponent(this.node.data.service)
        else
            view_url = "view.py?view_name=bi_map_hover_host&display_options=I&host=" + encodeURIComponent(this.node.data.hostname)

        d3.html(view_url ,{credentials: "include"}).then(html=>this._got_quickinfo(html))
    }

    _get_details_url() {
        if (this.node.data.service && this.node.data.service != "") {
            return "view.py?view_name=service" +
                "&host=" + encodeURIComponent(this.node.data.hostname) +
                "&service=" + encodeURIComponent(this.node.data.service)
        } else {
            return "view.py?view_name=host&host=" + encodeURIComponent(this.node.data.hostname)
        }
    }
}

class BIAggregatorNode extends AbstractGUINode {
    constructor(nodes_layer, node) {
        super(nodes_layer, node)
        this.radius = 12
        if (!this.node.parent)
            // the root node gets a bigger radius
            this.radius = 16
    }

    _get_basic_quickinfo() {
        let tokens = this.node.data.rule_id.function.split("!")

        let quickinfo = []

        quickinfo.push({name: "Rule Title", value: this.node.data.name})
        quickinfo.push({name: "Rule ID", value: this.node.data.rule_id.rule})

        quickinfo.push({name: "State", css_classes: ["state", "svcstate", "state" + this.node.data.state], value: this._state_to_text(this.node.data.state)})
        if (tokens[0] == "worst" || tokens[0] == "best") {
            let restriction_info = "Restrict severity to CRIT at worst."
            let infotext = "Take the " + tokens[0] + " state."
            if (tokens.length > 1) {
                restriction_info = "Restrict severity to " + this._state_to_text(tokens[2]) + " at worst."
                let count = tokens[1]
                if (count > 1)
                    infotext = "Take the " + count + "'th " + tokens[0] + " state."
            }
            quickinfo.push({name: "Condition", value: infotext})
            quickinfo.push({name: "Severity settings", value: restriction_info})
        }
        else if (tokens[0] == "count_ok") {
            let infotext_ok = "Require " + tokens[1] + " OK-nodes for a total state of OK."
            let infotext_warn = "Require " + tokens[2] + " OK-nodes for a total state of WARN."
            // TODO: finish
            quickinfo.push({name: "Condition", value: infotext_ok})
        }
       return quickinfo
    }

    get_context_menu_elements() {
        let elements = []

        let theme_prefix = this.viewport.main_instance.get_theme_prefix()

        // Local actions
// TODO: provide aggregation ID (if available)
//        if (!this.node.parent)
//        // This is the aggregation root node
//            elements.push({text: "Edit aggregation (Missing: You need to configure an ID for this aggregation)", href: "wato.py?mode=bi_edit_rule&id=" + this.node.data.rule_id.rule +
//               "&pack=" + this.node.data.rule_id.pack,
//               img: this.viewport.main_instance.get_theme_prefix() + "/images/icon_edit.png"})

        elements.push({text: "Edit rule", href: "wato.py?mode=bi_edit_rule&id=" + this.node.data.rule_id.rule +
           "&pack=" + this.node.data.rule_id.pack,
           img: theme_prefix + "/images/icon_edit.png"})

        if (this.node.children != this.node._children)
            elements.push({text: "Below this node, expand all nodes", on: ()=>{d3.event.stopPropagation(); this.expand_node()}, href: "",
                            img: theme_prefix + "/images/icons/icons8-expand-48.png"})
        else
            elements.push({text: "Collapse this node", on: ()=>{d3.event.stopPropagation(); this.collapse_node()}, href: "",
                            img: theme_prefix + "/images/icons/icons8-collapse-48.png"})

        elements.push({text: "Expand all nodes", on: ()=>{d3.event.stopPropagation();
                                                                this.expand_node_including_children(this.node.data.chunk.tree)
                                                                this.viewport.recompute_node_chunk_descendants_and_links(this.node.data.chunk)
                                                                this.viewport.update_layers()
                                                            }, href: "",
                            img: theme_prefix + "/images/icons/icons8-expand-48.png"})

        if (this.node.data.state != 0) {
            elements.push({text: "Below this node, show only problems", on: ()=>{
                                d3.event.stopPropagation()
                                this._filter_root_cause(this.node)
                                this.viewport.recompute_node_chunk_descendants_and_links(this.node.data.chunk)
                                this.viewport.update_layers()
            },
            img: theme_prefix + "/images/icons/icons8-error-48.png"})
        }
        return elements
    }
}

class NodeLink {
    constructor(nodes_layer, link_data) {
        this.nodes_layer = nodes_layer
        this.viewport = nodes_layer.viewport
        this.link_data = link_data
        this.selection = null
        this.use_diagonal = true
    }

    id() {
        return [this.link_data.source.data.id, this.link_data.target.data.id]
    }

    render_into(selection) {
        let spawn_point_x = this.link_data.target.x
        let spawn_point_y = this.link_data.target.y

// TODO: remove
//        let spawn_point = this.nodes_layer.viewport.point_spawn_location
//        if (spawn_point) {
//            spawn_point_x = spawn_point[0]
//            spawn_point_y = spawn_point[1]
//        }

        let coords = this.nodes_layer.viewport.scale_to_zoom({x: spawn_point_x, y: spawn_point_y})

        if (this.use_diagonal) {
            this.selection = selection
                .append("path")
                   .classed("link_element", true)
                   .attr("stroke-width", 2)
                   .attr("fill", "none")
                   .attr("stroke-width", function (d) { return Math.max(4, 2-d.depth);})
                   .style("stroke", "grey")
        } else {
            this.selection = selection.append("line")
                .classed("link_element", true)
                .attr("marker-end", "url(#triangle)")
                .attr("x1", coords.x)
                .attr("y1", coords.y)
                .attr("x2", coords.x)
                .attr("y2", coords.y)
                .attr("stroke-width", function (d) { return Math.max(1, 2-d.depth);})
                .style("stroke", "grey")
            }
    }


    update_position() {
        if (this.selection.attr("transit") > 0) {
            return
        }

        let source = this.link_data.source
        let target = this.link_data.target

        if (this.link_data.source.data.current_positioning.hide_node_link) {
            this.selection.attr("opacity", 0)
            return
        }
        this.selection.attr("opacity", 1)

        let x1 = source.data.target_coords.x
        let y1 = source.data.target_coords.y
        let x2 = target.data.target_coords.x
        let y2 = target.data.target_coords.y

        if (this.use_diagonal) {
            this.add_optional_transition(this.selection).attr("d", (d) => this.diagonal_line(x1,y1,x2,y2))
        }
        else {
            this.add_optional_transition(this.selection)
                    .attr("x1", x1)
                    .attr("y1", y1)
                    .attr("x2", x2)
                    .attr("y2", y2)
       }
    }

    // Creates a curved (diagonal) path from parent to the child nodes
    diagonal_line(source_x, source_y, target_x, target_y) {
        let s = {}
        let d = {}
        s.y = source_x
        s.x = source_y
        d.y = target_x
        d.x = target_y

        let path = `M ${s.y} ${s.x}
                C ${(s.y + d.y) / 2} ${s.x},
                  ${(s.y + d.y) / 2} ${d.x},
                  ${d.y} ${d.x}`

        return path
    }

    add_optional_transition(selection) {
        let source = this.link_data.source
        let target = this.link_data.target
        if ((!source.use_transition && !target.use_transition) || this.viewport.layout_manager.dragging)
            return selection

        return node_visualization_utils.DefaultTransition.add_transition(selection.attr("transit", 100)).attr("transit", 0)
    }
}


export class LayeredNodesLayer extends node_visualization_viewport_utils.LayeredLayerBase {
    id() {
        return "nodes"
    }

    name() {
        return "Nodes Layer"
    }

    constructor(viewport) {
        super(viewport)
        this.last_scale = 1
        // Node instances by id
        this.node_instances = {}
        // NodeLink instances
        this.link_instances = {}

        this.nodes_selection = null
        this.links_selection = null
        this.popup_menu_selection = null
    }

    setup() {
        // Nodes/Links drawn on screen
        this.links_selection = this.selection.append("g")
                                .attr("name", "viewport_layered_links")
                                .attr("id", "links")
        this.nodes_selection = this.selection.append("g")
                                .attr("name", "viewport_layered_nodes")
                                .attr("id", "nodes")

    }

    zoomed() {
        let transform_text = "translate(" + this.viewport.last_zoom.x + "," + this.viewport.last_zoom.y + ")"
        this.selection.attr("transform", transform_text)

        for (let idx in this.node_instances)
            this.node_instances[idx].update_quickinfo_position()

        if (this.last_scale != this.viewport.last_zoom.k)
            this.update_gui(true)
        this.last_scale = this.viewport.last_zoom.k
    }

    update_data() {
        this._update_links()
        this._update_nodes()
    }

    _update_nodes() {
        let visible_nodes = this.viewport.get_all_nodes().filter(d=>!d.data.invisible)
        let nodes_selection = this.nodes_selection.selectAll(".node_element").data(visible_nodes, d=>d.data.id)

        // Create new nodes
        nodes_selection.enter().each((node_data, idx, node_list)=>this._create_node(node_data, d3.select(node_list[idx])))
        // Existing nodes: Update bound data in all nodes
        nodes_selection.each((node_data, idx, node_list)=>this._update_node(node_data, d3.select(node_list[idx])))
        // Remove obsolete nodes
        nodes_selection.exit().each(node_data=>this._remove_node(node_data)).remove()
    }

    _update_links() {
        let links = this.viewport.get_all_links()
        let links_selection = this.links_selection.selectAll(".link_element").data(links, d=>[d.source.data.id, d.target.data.id])
        links_selection.enter().each((link_data, idx, links) => this._create_link(link_data, d3.select(links[idx])))
        links_selection.each((link_data, idx, links)=>this._update_link(link_data, d3.select(links[idx])))
        links_selection.exit().each(link_data=>this._remove_link(link_data)).remove()
    }

    _create_node(node_data, selection) {
        let new_node = null;
        if (node_data.data.node_type == "bi_leaf")
            new_node = new BILeafNode(this, node_data)
        else if (node_data.data.node_type == "bi_aggregator")
            new_node = new BIAggregatorNode(this, node_data)
        else
            new_node = new GenericNode(this, node_data)
        this.node_instances[new_node.id()] = new_node
        new_node.render_into(selection)
    }

    _update_node(node_data, selection) {
       selection.selectAll("*").each(function(d) {
           d3.select(this).datum(node_data)
       })
       this.node_instances[node_data.data.id].update_node_data(node_data, selection)
    }

    _remove_node(node_data) {
        delete this.node_instances[node_data.data.id];
    }

    _create_link(link_data, selection) {
        let new_link = new NodeLink(this, link_data)
        this.link_instances[new_link.id()] = new_link
        new_link.render_into(selection)
    }

    _update_link(link_data, selection) {
        selection.selectAll("*").each(function(d) {
            d3.select(this).datum(node_data)
        })
        // TODO: provide a function within the link instance to update its data
        this.link_instances[[link_data.source.data.id, link_data.target.data.id]].link_data = link_data
    }

    _remove_link(link_data) {
        delete this.link_instances[[link_data.source.data.id, link_data.target.data.id]]
    }

    update_gui(force=false) {
        this._update_position_of_context_menu()
        if (!force && this.viewport.layout_manager.force_style.simulation.alpha() < 0.10) {
            return
        }

        for (let idx in this.node_instances)
            this.node_instances[idx].update_position()

        for (let idx in this.link_instances)
            this.link_instances[idx].update_position()

        // Disable node transitions after each update step
        // TODO: check this
        for (let idx in this.node_instances)
            this.node_instances[idx].node.use_transition = false
    }

    render_context_menu(node_instance) {
        if (!this.viewport.layout_manager.edit_layout && !node_instance)
            return // Nothing to show

        let node = null
        let coords = {}
        if (node_instance) {
            node = node_instance.node
            coords = node
        } else {
            let last_zoom = this.viewport.last_zoom
            coords = {x: (d3.event.layerX - last_zoom.x) / last_zoom.k, y: (d3.event.layerY - last_zoom.y) / last_zoom.k}
        }

        d3.event.preventDefault()
        d3.event.stopPropagation()

        // TODO: remove this, apply general update pattern..
        this.div_selection.selectAll("#popup_menu").remove()

        // Create menu
        this.popup_menu_selection = this.div_selection.selectAll("#popup_menu").data([coords])
        this.popup_menu_selection = this.popup_menu_selection.enter().append("div")
                            .attr("id", "popup_menu")
                            .style("pointer-events", "all")
                            .style("position", "absolute")
                              .classed("popup_menu", true)
                            .merge(this.popup_menu_selection)

        // Setup ul
        let content = this.popup_menu_selection.selectAll(".content ul").data([null])
        content = content.enter().append("div")
                                   .classed("content", true)
                                 .append("ul")
                                 .merge(content)

        // Create li for each item
        let elements = []
        if (this.viewport.layout_manager.edit_layout) {
            // Add elements layout manager
            this._add_elements_to_context_menu(content, "layouting", this.viewport.layout_manager.get_context_menu_elements(node))
            // TODO: apply GUP
            if (node_instance)
                content.append("li").append("hr")
        }

        if (node_instance)
            // Add elements from node
            this._add_elements_to_context_menu(content, "node", node_instance.get_context_menu_elements())

        this._update_position_of_context_menu()
    }

    _add_elements_to_context_menu(content, element_source, elements) {
        let links = content.selectAll("li" + "." + element_source).data(elements)
        links.exit().remove()

        links = links.enter().append("li")
                    .classed(element_source, true)
                .append("a")
                    .classed("noselect", true)

        // Add optional href
        links.each((d, idx, nodes)=> {if (d.href) {
            d3.select(nodes[idx]).attr("href", d.href).on("click",
                ()=>this.remove_context_menu()
            )
        }})

        // Add optional img
        links.each(function(d) {if (d.img) {
            d3.select(this).append("img").classed("icon", true).attr("src", d.img)}
        })

        // Add text
        links.each(function(d) {d3.select(this).append("div").style("display", "inline-block").text(d.text)})

        // Add optional click handler
        links.each((d,idx,nodes)=>{
            if (d.on) {
                d3.select(nodes[idx]).on("click", d=>{
                    d.on()
                    this.remove_context_menu()
                })
            }
        })
    }

    _update_position_of_context_menu() {
        if (this.popup_menu_selection == null)
            return

        // Search menu
        let popup_menu = this.popup_menu_selection
        if (popup_menu.empty())
            return

        // Set position
        let old_coords = popup_menu.datum()

        let new_coords = this.viewport.translate_to_zoom(old_coords)

        popup_menu.style("left", new_coords.x + "px")
                  .style("top", new_coords.y + "px")
    }

    remove_context_menu() {
        this.div_selection.select("#popup_menu").remove()
    }
}
