import * as d3 from "d3";

import * as node_visualization_layouting_utils from "node_visualization_layouting_utils"
import * as node_visualization_layout from "node_visualization_layout";
import * as node_visualization_utils from "node_visualization_utils"

export class AbstractLayoutStyle {
    constructor(layout_manager, style_config, node, selection) {
        this._layout_manager = layout_manager
        // Contains all configurable options for this style
        this.style_config = style_config
        // The selection for the styles graphical overlays
        this.selection = selection

        // Root node for this style
        this.style_root_node = node
        if (this.style_root_node) {
            // Chunk this root node resides in
            if (this.style_config.position) {
                let coords = this.style_root_node.data.chunk.coords
                this.style_root_node.x = (style_config.position.x / 100 * coords.width)  + coords.x
                this.style_root_node.y = (style_config.position.y / 100 * coords.height) + coords.y
            }
        }

        // Apply missing default values to options
        this._initialize_style_config()

        // Default options lookup
        this._default_options = {}
        let style_options = this.get_style_options()
        style_options.forEach(option=>{
            this._default_options[option.id] = option.values.default
        })

        // If set, suppresses translationn of style_node offsets
        this._style_translated = false

        // Coords [x,y] for each node in this style
        this._vertices = []
    }

    _initialize_style_config() {
        if (this.style_config.options == null) {
            this.style_config.options = {}
        }

        // options
        this.get_style_options().forEach(option=>{
            if (this.style_config.options[option.id] == null)
                this.style_config.options[option.id] = option.values.default
        })

        // matcher
        let matcher = this.get_matcher()
        if (matcher)
            this.style_config.matcher = matcher

        // position
        if (this.style_root_node && !this.style_config.position)
            this.style_config.position = this._layout_manager.get_viewport_percentage_of_node(this.style_root_node)
    }

    id() {
        return this.compute_id(this.style_root_node)
    }

    compute_id(node) {
        return this.type() + "_" + node.data.id
    }

    get_style_options() {
        return []
    }

    render_options(into_selection) {
        this.options_selection = into_selection
        this._update_options_in_input_field()
    }


    _update_options_in_input_field() {
        if (!this.options_selection)
            return

        let style_options = this.get_style_options()
        if (style_options.length == 0)
            return

        this.options_selection.selectAll("#styleoptions_headline").data([null]).enter()
                .append("h4")
                    .attr("id", "styleoptions_headline")
                    .text("Options")

        let table = this.options_selection.selectAll("table").data([null])
        table = table.enter().append("table").merge(table)

        let rows = table.selectAll("tr").data(style_options)

        let rows_enter = rows.enter().append("tr")
        rows_enter.append("td").text(d=>d.text)
                            .classed("style_infotext", true)
        rows_enter.append("td").append("input")
                            .classed("range", true)
                            .attr("id", d=>d.id)
                            .attr("type", "range")
                            .attr("step", 1)
                            .attr("min", d=>d.values.min)
                            .attr("max", d=>d.values.max)
                            .on("input", ()=>{
                                this._layout_manager.dragging = true
                                this.option_changed_in_input_field()
                                this.changed_options()
                            })
                            .on("change", ()=>{
                                this._layout_manager.dragging = false
                            })
        rows_enter.append("td").classed("text", true)
        rows = rows_enter.merge(rows)
        rows.select("td input.range").property("value",d=>d.value)
        rows.select("td.text").text(d=>d.value)

        this.options_selection.selectAll("input.reset_options").data([null]).enter()
                             .append("input")
                               .attr("type", "button")
                               .classed("button", true)
                               .classed("reset_options", true)
                               .attr("value", "Reset default values")
                               .on("click", d=>{
                                    this.reset_default_options()
                                })
        this.options_selection.selectAll("div.clear_float").data([null]).enter()
                            .append("div")
                            .classed("clear_float", true)
                            .style("clear", "right")
    }

    reset_default_options() {
        let style_options = this.get_style_options()
            for (let idx in style_options) {
                let option = style_options[idx]
                this.style_config.options[option.id] = option.values.default
            }
        this.changed_options()
    }

    option_changed_in_input_field() {
        let style_options = this.get_style_options()
        for (let idx in style_options) {
            let option = style_options[idx]
            this.style_config.options[option.id] = +this.options_selection.select("#" + option.id).property("value")
        }
    }

    changed_options() {
        this._update_options_in_input_field()
        this.force_style_translation()
        this.translate_coords()

        this.update_data()
        this._layout_manager.compute_node_positions()

        this._layout_manager.viewport.update_data_of_layers()
        this._layout_manager.viewport.update_gui_of_layers()
    }

    style_color() {}

    type() {}

    description() {}

    set_matcher(matcher) {
        this.style_config.matcher = matcher
    }

    get_matcher() {
        let matcher_conditions= {}

        if (this.style_root_node.data.node_type == "bi_aggregator" ||
            this.style_root_node.data.node_type == "bi_leaf") {

            // Match by aggr_path: The path of rule_ids up to the node
            matcher_conditions.aggr_path_id = {value: this.style_root_node.data.aggr_path_id.join("#")}
            matcher_conditions.aggr_path_name = {value: this.style_root_node.data.aggr_path_name.join("#")}

            if (this.style_root_node.data.node_type == "bi_aggregator") {
                // Aggregator: Match by rule_id
                matcher_conditions.rule_id = {value: this.style_root_node.data.rule_id.rule}
                matcher_conditions.rule_name = {value: this.style_root_node.data.name}
            } else {
                // End node: Match by hostname or service
                matcher_conditions.hostname = {value: this.style_root_node.data.hostname}
                matcher_conditions.service = {value: this.style_root_node.data.service}
            }
        } else {
            // Generic node
            matcher_conditions.hostname = {value: this.style_root_node.data.hostname}
        }

        // Override default options with user customized settings.
        // May disable match types and modify match texts
        for (let idx in this.style_config.matcher) {
            matcher_conditions[idx] = this.style_config.matcher[idx]
        }
        return matcher_conditions
    }

    get_aggregation_path(node) {
        let path = []
        if (node.parent)
             path = path.concat(this.get_aggregation_path(node.parent))
        if (node.data.aggr_path)
            path.push(node.data.aggr_path)
        return path
    }

    update_style_indicator(indicator_shown) {
        let style_indicator = this.style_root_node.selection.selectAll("circle.style_indicator").data([this])

        if (!indicator_shown) {
            style_indicator = style_indicator.merge(style_indicator)
            style_indicator.remove()
        }

        style_indicator = style_indicator.enter().append("circle").classed("style_indicator", true)
                            .attr("pointer-events", "none")
                            .attr("r", 30)
                            .attr("fill", d=>d.style_color())
                            .attr("opacity", 0.5)
                            .merge(style_indicator)
    }


    // positioning_weight of the layout positioning
    // If multiple positioning forces are applied to one node, the one with the highest positioning_weight wins
    positioning_weight() {
        return 0
    }

    force_style_translation() {
        this._style_translated = false
    }

    zoomed() {}

    update_data() {}

    update_gui() {}

    fix_node(node) {
        let force = this.get_default_node_force(node)
        force.fx = node.x
        force.fy = node.y
        force.use_transition = true
    }

    get_default_node_force(node) {
        return this._layout_manager.get_node_positioning(node)[this.id()] = {weight: this.positioning_weight()}
    }

    // Computes offsets use for node translate
    _compute_node_offsets() {}

    // Translates the nodes by the computed offsets
    translate_coords() {}

    remove() {
        delete this.style_root_node.data.node_positioning[this.id()]
        // TODO: might get added/removed on the same call..
        this.get_div_selection().remove()
        this.update_style_indicator(false)
    }

    add_option_icons(coords, elements) {
        for (let idx in elements) {
            let element = elements[idx]
            let img = this.get_div_selection().selectAll("img." + element.type).data([element], d=>d.node.data.id)
            img = img.enter().append("img")
                                .classed(element.type, true)
                                .classed("layouting_icon", true)
                                .classed("box", true)
                                .attr("src", element.image)
                                .style("background", "white")
                                .style("opacity", "0.7")
                                .style("position", "absolute")
                                .style("pointer-events", "all")
                                .each((d, idx, nodes)=>{
                                    if (d.call)
                                        d3.select(nodes[idx]).call(d.call)
                                })
                                .each((d, idx, nodes)=>{
                                    if (d.onclick)
                                        d3.select(nodes[idx]).on("click", d.onclick)
                                })
                            .merge(img)
            let offset = parseInt(img.style("width"), 10)
            img.style("top", d=>coords.y - 62 + "px")
            img.style("left", d=>coords.x + (idx * (offset + 12)) + "px")
        }
    }

    get_div_selection() {
        let div_selection = this._layout_manager.div_selection.selectAll("div.hierarchy").data([this.id()])
        return div_selection.enter().append("div").classed("hierarchy", true).merge(div_selection)
    }

    add_enclosing_hull(into_selection, vertices) {
        if (vertices.length < 2) {
            into_selection.selectAll("path.style_overlay").remove()
            return
        }

        let boundary = 30
        let hull_vertices = []
        vertices.forEach(entry=>{
            hull_vertices.push([entry[0]+boundary, entry[1]+boundary])
            hull_vertices.push([entry[0]-boundary, entry[1]-boundary])
            hull_vertices.push([entry[0]+boundary, entry[1]-boundary])
            hull_vertices.push([entry[0]-boundary, entry[1]+boundary])
        })
        let hull = into_selection.selectAll("path.style_overlay").data([d3.polygonHull(hull_vertices)])
        hull = hull.enter().append("path")
                    .classed("style_overlay", true)
                    .style("vector-effect", "non-scaling-stroke")
                    .style("stroke", "black")
                    .style("stroke-width", "4px")
                    .attr("pointer-events", "none")
                .merge(hull)
        hull.interrupt()
        this.add_optional_transition(hull.attr("d", function(d) {return "M" + d.join("L") + "Z";}));
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

export class LayoutStyleForce extends AbstractLayoutStyle {
    type() {
        return "force"
    }

    description() {
        return "Free-Floating style"
    }

    style_color() {
        return "#F0F8FF"
    }

    compute_id(node) {
        return "force"
    }

    id() {
        return "force"
    }

    constructor(layout_manager, style_config, node, selection) {
        super(layout_manager, style_config, node, selection)
        this.simulation = d3.forceSimulation();
        this.simulation.alphaMin(0.10)
// TODO: determine best alphaDecay
//        this.simulation.alphaDecay(0.01)
        this._setup_forces()
    }

    get_matcher() {}

    get_style_options() {
        return [{id: "center_force", values: {default: 5, min: 0, max: 100},
                 text: "Center force strength", value: this.style_config.options.center_force},
                {id: "maxdistance", values: {default: 800, min: 10, max: 2000},
                 text: "Max force distance", value: this.style_config.options.maxdistance},
                {id: "force_node", values: {default: -300, min: -1000, max: 50},
                 text: "Repulsion force leaf", value: this.style_config.options.force_node},
                {id: "force_aggregator", values: {default: -300, min: -1000, max: 50},
                 text: "Repulsion force branch", value: this.style_config.options.force_aggregator},
                {id: "link_force_node", values: {default: 30, min: -10, max: 300},
                 text: "Link distance leaf", value: this.style_config.options.link_force_node},
                {id: "link_force_aggregator", values: {default: 30, min: -10, max: 300},
                 text: "Link distance branches", value: this.style_config.options.link_force_aggregator},
                {id: "link_strength", values: {default: 30, min: 0, max: 300},
                 text: "Link strength", value: this.style_config.options.link_strength},
                {id: "collision_force_node", values: {default: 15, min: 0, max: 150},
                 text: "Collision box leaf", value: this.style_config.options.collision_force_node},
                {id: "collision_force_aggregator", values: {default: 15, min:0, max:150},
                 text: "Collision box branch", value: this.style_config.options.collision_force_aggregator}]
    }

    // TODO: remove with base functionality
    get_config() {
        return {
            type: this.type(),
            options: this.style_config.options
        }
    }

    size_changed() {
        this._update_center_force()
        this.restart_with_alpha(0.5)
    }

    _setup_forces() {
        // Gravity
        let charge_force = d3.forceManyBody().strength((d) => {
            if (d.force != null) {
                return d.force;
            }
            if (d._children)
                return this.style_config.options.force_aggregator
            else
                return this.style_config.options.force_node})
                    .distanceMax(this.style_config.options.maxdistance)
        this.simulation.force("charge_force", charge_force)

        // Collision
        let collide_force = d3.forceCollide(d=>{
                if (d.data.collision_force != null) {
                    return d.data.collision_force;
                }
                if (d._children)
                    return this.style_config.options.collision_force_aggregator
                else
                    return this.style_config.options.collision_force_node
        })
        this.simulation.force("collide", collide_force)
    }

    _update_center_force() {
        let hierarchy_list = this._layout_manager.viewport.get_hierarchy_list()
        if (hierarchy_list.length == 0)
            return

        this.forceX = d3.forceX(d=>{
                return d.data.chunk.coords.x + d.data.chunk.coords.width/2
        }).strength(d=>{
                if (d.parent != null)
                    this.style_config.options.center_force / 300
                return this.style_config.options.center_force / 100})
        this.forceY = d3.forceY(d=>{
                return d.data.chunk.coords.y + d.data.chunk.coords.height/2
        }).strength(d=>{
                if (d.parent != null)
                    this.style_config.options.center_force / 300
                return this.style_config.options.center_force / 100})
        this.simulation.force("x", this.forceX)
        this.simulation.force("y", this.forceY)
    }

    update_data() {
        // TODO: use links based on get_all_links
        let all_nodes = []
        let all_links = []
        this._update_center_force()
        this._layout_manager.viewport.get_hierarchy_list().forEach(partition=>{
            all_nodes = all_nodes.concat(partition.nodes)
            partition.nodes.slice(1).forEach(node=>{
                if (node.data.invisible)
                    return
            })
        })
        this.simulation.nodes(all_nodes)

        all_links = this._layout_manager.viewport.get_all_links()

        // Links
        let link_force = d3.forceLink(all_links)
                            .id(function (d) {return d.data.id})
                            .distance(d=>{
                                if (d.source._children)
                                    return this.style_config.options.link_force_aggregator
                                else
                                    return this.style_config.options.link_force_node})
//                            .strength(this.style_config.options.link_strength/10)
        this.simulation.force("links", link_force);
        this.restart_with_alpha(0.7)
        this.simulation.on("tick", () => this.tick_called())
    }

    tick_called() {
            let update_start = window.performance.now()
            this._layout_manager.viewport.update_gui_of_layers()
            tick_duration = window.performance.now() - update_start
    }

    restart_with_alpha(alpha) {
        if (this.simulation.alpha() < 0.12)
            this.simulation.restart();
        this.simulation.alpha(alpha);
    }
}

export let tick_count = 0
export let tick_duration = 0

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
        return 10 + parseInt(this.style_root_node.depth)
    }

    remove() {
        this.get_div_selection().remove()
        AbstractLayoutStyle.prototype.remove.call(this)
        this._cleanup_style_node_positioning()
    }

    _cleanup_style_node_positioning() {
        if (this.style_root_node) {
            this.style_root_node.descendants().forEach(node=>{
                delete node.data.node_positioning[this.id()]
            })
        }
    }

    update_data() {
        this.selection.attr("transform", this._layout_manager.viewport.last_zoom)
        this.use_transition = true

        this._cleanup_style_node_positioning()

        // Remove nodes not belonging to this style
        this._set_hierarchy_filter(this.style_root_node, true)
        this.filtered_descendants = this.style_root_node.descendants()

        // Determine max_depth, used by text positioning
        this.max_depth = 1
        this.filtered_descendants.forEach(node => {this.max_depth = Math.max(this.max_depth, node.depth)})

        // Save old coords
        let old_coords = {}
        this.filtered_descendants.forEach(node=>{
            old_coords[node.data.id] = {x: node.x, y: node.y}
        })

        // Layout type specific computation
        this._compute_node_offsets()
        this.force_style_translation()

        this._reset_hierarchy_filter(this.style_root_node)

        // Reapply old coords
        this.filtered_descendants.forEach(node=>{
            node.x = old_coords[node.data.id].x
            node.y = old_coords[node.data.id].y
        })

        // Fixate this.style_root_node till the layout gets applied
        // Otherwise the force layout tends to move this.style_root_node
        this.fix_node(this.style_root_node)
    }


    // Removes nodes (and their childs) with other explicit styles set
    _set_hierarchy_filter(node, first_node=false) {
        if (!first_node && node.data.use_style)
            return []

        if (node.children) {
            node.children_backup = node.children
            node.children = []
            for (let idx in node.children_backup) {
                let child_node = node.children_backup[idx]
                node.children = node.children.concat(this._set_hierarchy_filter(child_node))
            }
            if (node.children.length == 0)
                delete node.children
        }
        return [node]
    }

    _reset_hierarchy_filter(node) {
        if (!node.children_backup)
            return

        for (let idx in node.children_backup)
            this._reset_hierarchy_filter(node.children_backup[idx])

        node.children = node.children_backup
        delete node.children_backup
    }

    zoomed() {
        this.selection.attr("transform", this._layout_manager.viewport.last_zoom)
        // Update style overlays which depend on zoom
        this.generate_overlay()
    }

    get_drag_callback(drag_function) {
        return d3.drag().on("start.drag", ()=> this.drag_start())
                        .on("drag.drag", ()=>{drag_function(), this.changed_options()})
                        .on("end.drag", ()=> this.drag_end())
    }

    drag_start() {
        this.drag_start_info = {}
        this.drag_start_info.start_coords = d3.mouse(this.selection.node())
        this.drag_start_info.options = JSON.parse(JSON.stringify(this.style_config.options))
        this._layout_manager.toolbar_plugin.layout_style_configuration.update_current_style(this)
        this._layout_manager.dragging = true
    }

    change_rotation() {
        let coords = d3.mouse(this.selection.node())
        let offset = ((this.drag_start_info.start_coords[1] - coords[1]) * this._layout_manager.viewport.last_zoom.k) % 360
        let rotation = (this.drag_start_info.options.rotation + offset) % 360
        if (rotation < 0)
            rotation += 360

        this.style_config.options.rotation = parseInt(rotation)
        this.force_style_translation()
    }

    drag_end() {
        this._layout_manager.dragging = false
    }

    add_optional_transition(selection_with_node_data) {
        if (!this._layout_manager.dragging) {
            return selection_with_node_data.transition().duration(node_visualization_utils.DefaultTransition.duration())
        }
        return selection_with_node_data
    }
}


export class LayoutStyleHierarchy extends LayoutStyleHierarchyBase {
    constructor(layout_manager, style_config, node, selection) {
        super(layout_manager, style_config, node, selection)
    }

    type() {
        return "hierarchy"
    }

    description() {
        return "Hierarchical style"
    }

    style_color() {
        return "#98FB98"
    }

    get_style_options() {
        return [{id: "rotation", values: {default: 270, min: 0, max: 359}, text: "Rotation", value: this.style_config.options.rotation},
                {id: "layer_height", values: {default: 80, min: 20, max: 500}, text: "Layer height", value: this.style_config.options.layer_height},
                {id: "node_size", values: {default: 25, min: 15, max: 100}, text: "Node size", value: this.style_config.options.node_size}]
    }

    _compute_node_offsets() {
        let coords = this.get_hierarchy_size()
        d3.tree().nodeSize([this.style_config.options.node_size,
                                                                this.style_config.options.layer_height])(this.style_root_node)

        this._node_positions = []
        for (let idx in this.filtered_descendants) {
            let node = this.filtered_descendants[idx]
            this._node_positions.push([node.x - this.style_root_node.x, node.y - this.style_root_node.y])
        }
    }

    translate_coords() {
        let nodes = this.filtered_descendants
        let coords = this.get_hierarchy_size()

        if (this._style_translated) {
            return
        }

        let rad = this.style_config.options.rotation  / 180 * Math.PI

        let cos_x = Math.cos(rad)
        let sin_x = Math.sin(rad)
        let text_positioning = this.get_text_positioning(rad)

        this._vertices = []
        for (let idx in nodes) {
            let node = nodes[idx]

            let node_positioning = this._layout_manager.get_node_positioning(nodes[idx])

            let force = this.get_default_node_force(node)
            let node_position = this._node_positions[idx]
            let node_coords = {
                y: node_position[0] * cos_x - node_position[1] * sin_x,
                x: node_position[0] * sin_x + node_position[1] * cos_x,
            }
            force.fx = coords.x + node_coords.x
            force.fy = coords.y + node_coords.y
            force.use_transition = this.use_transition
            nodes[idx].force = -500

            this._vertices.push([force.fx, force.fy])
            force.text_positioning = text_positioning
        }

        this.generate_overlay()

        this._style_translated = true
        this.use_transition = false
    }

    generate_overlay() {
        if (!this._layout_manager.edit_layout)
            return

        this.add_enclosing_hull(this.selection, this._vertices)
        let elements = [
            {node: this.style_root_node, type: "scale",  image: "images/icons/icons8-resize-filled-48.png", call: this.get_drag_callback(()=>this.resize_layer_drag())},
            {node: this.style_root_node, type: "rotation", image: "images/icons/icons8-rotate-left-48.png", call: this.get_drag_callback(()=>this.change_rotation())}
        ]
        let coords = this._layout_manager.viewport.translate_to_zoom({x: this.style_root_node.x, y: this.style_root_node.y})
        this.add_option_icons(coords, elements)
    }


    get_text_positioning(rad) {
        rad = rad / 2
        if (rad > 3/4 * Math.PI)
            rad = rad - Math.PI

        let rotate = - rad / Math.PI * 180

        let anchor_options = ["start", "end"]
        let boundary = 9/32 * Math.PI

        let left_side = rad > boundary && rad < Math.PI - boundary

        let distance = 20
        let x = Math.cos(-rad * 2) * distance
        let y = Math.sin(-rad * 2) * distance

        if (rad > Math.PI - boundary) {
            rotate += 180
        }
        else if (left_side) {
            rotate += 90
            anchor_options = ["end", "start"]
        }

        let text_anchor = anchor_options[0]
        let transform_text = "translate(" + x + "," + y + ") rotate(" + rotate + ")"
        return (selection)=>{
            selection.attr("transform", transform_text)
                     .attr("text-anchor", text_anchor)
        }
    }

    resize_layer_drag() {
        let rotation_rad = this.style_config.options.rotation / 180 * Math.PI
        let coords = d3.mouse(this.selection.node())
        let offset_y = (this.drag_start_info.start_coords[0] - coords[0])
        let offset_x = (this.drag_start_info.start_coords[1] - coords[1])


        let dx_scale = (100+(Math.cos(-rotation_rad) * offset_x - Math.sin(-rotation_rad) * offset_y))/100
        let dy_scale = (100-(Math.cos(-rotation_rad) * offset_y + Math.sin(-rotation_rad) * offset_x))/100

        let node_size = this.drag_start_info.options.node_size * dx_scale
        let layer_height  = this.drag_start_info.options.layer_height * dy_scale

        this.style_config.options.node_size = parseInt(Math.max(this._default_options.node_size/2, Math.min(this._default_options.node_size * 8, node_size)))
        this.style_config.options.layer_height = parseInt(Math.max(this._default_options.layer_height/2, Math.min(this._default_options.layer_height * 8, layer_height)))
    }

    get_hierarchy_size() {
        let max_elements_per_layer = {}

        this.filtered_descendants.forEach(node => {
                if (node.children == null)
                    return
                if (max_elements_per_layer[node.depth] == null)
                    max_elements_per_layer[node.depth] = 0

                max_elements_per_layer[node.depth] += node.children.length
//                max_elements_per_layer = Math.max(max_elements_per_layer, node.children.length)})
        })
        this.layer_count = this.max_depth - this.style_root_node.depth + 2

        let highest_density = 0
        for (let idx in max_elements_per_layer)
            highest_density = Math.max(highest_density, max_elements_per_layer[idx])

        let width = highest_density * this.style_config.options.node_size
        let height = this.layer_count * this.style_config.options.layer_height

        let coords = {}
        coords.x = +this.style_root_node.x
        coords.y = +this.style_root_node.y
        coords.width = width
        coords.height = height
        return coords
    }
}



export class LayoutStyleRadial extends LayoutStyleHierarchyBase {
    type() {
        return "radial"
    }

    description() {
        return "Radial style"
    }

    style_color() {
        return "#4682B4"
    }

    get_style_options() {
        return [{id: "radius",   values: {default: 120, min: 30, max: 300}, text: "Radius", value: this.style_config.options.radius},
                {id: "rotation", values: {default: 0, min: 0, max: 359}, text: "Rotation", value: this.style_config.options.rotation},
                {id: "degree",   values: {default: 360, min: 10, max: 360}, text: "Degree", value: this.style_config.options.degree}]
    }

    _compute_node_offsets() {
        let radius = this.style_config.options.radius * (this.max_depth - this.style_root_node.depth + 1)
        let rotation_rad = this.style_config.options.rotation / 360 * 2 * Math.PI
        let tree = d3.cluster().size([(this.style_config.options.degree/360 * 2*Math.PI), radius])
        tree(this.style_root_node)
        this.style_root_node_offsets = []

        for (let idx in this.filtered_descendants) {
            let node = this.filtered_descendants[idx]
            let radius_reduction = 0
            if (!node.children) {
                radius_reduction = this.style_config.options.radius * 1
            }

            let x = Math.cos(node.x + rotation_rad) * (node.y - radius_reduction)
            let y = -Math.sin(node.x + rotation_rad) * (node.y - radius_reduction)
            this.style_root_node_offsets.push([node, x, y, (node.x + rotation_rad) % (2 * Math.PI)])
        }
    }

    translate_coords() {
        if (this._style_translated) {
            return
        }

        let offsets = {}
        offsets.x = this.style_root_node.x
        offsets.y = this.style_root_node.y

        for (let idx in this.style_root_node_offsets) {
            let entry = this.style_root_node_offsets[idx]
            let node = entry[0]
            let x = entry[1]
            let y = entry[2]
            let node_rad = entry[3]

            let node_positioning = this._layout_manager.get_node_positioning(node)
            let force = node_positioning[this.id()] = {}

            force.weight = this.positioning_weight()
            let node_coords = {}
            node_coords.x = offsets.x + x
            node_coords.y = offsets.y + y

            force.fx = node_coords.x
            force.fy = node_coords.y

            if (node != this.style_root_node)
                force.text_positioning = this.get_text_positioning(entry)

            force.use_transition = this.use_transition
            this.filtered_descendants[idx].force = -500

        }

        this.generate_overlay()
        this.use_transition = false
        this._style_translated = true
    }

    get_text_positioning(entry) {
        let node = entry[0]
        let node_rad = entry[3]

        if (this.style_root_node == node)
            return

        this.layer_count = this.max_depth - this.style_root_node.depth + 1
        let rotate = -node_rad / Math.PI * 180

        let anchor_options = ["start", "end"]
        let is_circle_left_side = node_rad > Math.PI/2 && node_rad < 3/2 * Math.PI
        if (is_circle_left_side) {
            rotate += 180
            anchor_options = ["end", "start"]
        }


        let x = Math.cos(-node_rad) * 12
        let y = Math.sin(-node_rad) * 12
        let toggle_text_anchor = node.height > 0

        let text_anchor = anchor_options[0]
        if (toggle_text_anchor) {
            x = -x
            y = -y
            text_anchor = anchor_options[1]
        }

        let transform_text = "translate(" + x + "," + y + ") rotate(" + rotate + ")"
        return (selection)=>{
            selection.attr("transform", transform_text)
                     .attr("text-anchor", text_anchor)
        }
    }

    generate_overlay() {
        if (!this._layout_manager.edit_layout)
            return
        let degree = Math.min(360, Math.max(0, this.style_config.options.degree))
        let end_angle = degree / 360 * 2 * Math.PI

        let arc = d3.arc()
                    .innerRadius(25)
                    .outerRadius(this.style_config.options.radius * (this.max_depth - this.style_root_node.depth + 1))
                    .startAngle(2*Math.PI - end_angle + Math.PI/2)
                    .endAngle(2*Math.PI + Math.PI/2)

        // TODO: remove translation overlay
        let translation_overlay = this.selection.selectAll("g.translation_overlay").data([null])
        translation_overlay = translation_overlay.enter().append("g")
                                      .classed("translation_overlay", true)
                                    .merge(translation_overlay)

        let rotation_overlay = translation_overlay.selectAll("g.rotation_overlay").data([null])
        rotation_overlay = rotation_overlay.enter().append("g")
                                      .classed("rotation_overlay", true)
                                    .merge(rotation_overlay)
        translation_overlay.attr("transform", "translate(" + this.style_root_node.x + "," + this.style_root_node.y + ")")
        rotation_overlay.attr("transform", "rotate(" + (-this.style_config.options.rotation) +")")

        // Arc
        let path = rotation_overlay.selectAll("path").data([null])
        path = path.enter().append("path")
                    .classed("style_overlay", true)
                    .style("vector-effect", "non-scaling-stroke")
                    .attr("pointer-events", "none")
            .merge(path)
        this.add_optional_transition(path).attr("d", arc)


        // Icons
        let elements = [
            {node: this.style_root_node, type: "radius", image: "images/icons/icons8-resize-filled-48.png",
             call: this.get_drag_callback(()=>this.change_radius())
            },
            {node: this.style_root_node, type: "rotation", image: "images/icons/icons8-rotate-left-48.png",
             call: this.get_drag_callback(()=>this.change_rotation())
            },
            {node: this.style_root_node, type: "degree", image: "images/icons/icons8-pie-chart-filled-48.png",
             call: this.get_drag_callback(()=>this.change_degree())
            }
        ]
        let coords = this._layout_manager.viewport.translate_to_zoom({x: this.style_root_node.x, y: this.style_root_node.y})
        this.add_option_icons(coords, elements)
    }

    change_radius() {
        this._layout_manager.toolbar_plugin.layout_style_configuration.update_current_style(this)
        let coords = d3.mouse(this.selection.node())
        let offset_x = (this.drag_start_info.start_coords[1] - coords[1]) * this._layout_manager.viewport.last_zoom.k
        this.style_config.options.radius = parseInt(Math.min(500, Math.max(10, this.drag_start_info.options.radius + offset_x)))

        // TODO: check this
        this._layout_manager.viewport.update_data_of_layers()
    }

    change_degree() {
        this._layout_manager.toolbar_plugin.layout_style_configuration.update_current_style(this)
        let coords = d3.mouse(this.selection.node())

        let offset_x = (this.drag_start_info.start_coords[1] - coords[1]) * 2 * this._layout_manager.viewport.last_zoom.k
        let degree = parseInt(Math.min(360, Math.max(10, this.drag_start_info.options.degree + offset_x)))
        this.style_config.options.degree = degree
        // TODO: check this
        this._layout_manager.viewport.update_data_of_layers()
    }
}


export class LayoutStyleFixed extends AbstractLayoutStyle {
    type() {
        return "fixed"
    }

    description() {
        return "Fixed position style"
    }

    style_color() {
        return "Burlywood"
    }

    positioning_weight() {
        return 100;
    }

    update_data() {
        this.fix_node(this.style_root_node)
    }
}

export class LayoutStyleBlock extends LayoutStyleHierarchyBase {
    type() {
        return "block"
    }

    description() {
        return "Leaf-Nodes Boxed style"
    }

    style_color() {
        return "#FF6347"
    }

    _compute_node_offsets() {
        if (!this.style_root_node.children)
            return


        let node_width = 50
        let width = parseInt(Math.sqrt(this.style_root_node.children.length)) * node_width
        let max_cols = parseInt(width/node_width)

        this.style_root_node_offsets = []
        for (let idx in this.style_root_node.children) {
            let node = this.style_root_node.children[idx]
            if (node._children)
                continue
            let row_no = parseInt(idx / max_cols) + 1
            let col_no = idx % max_cols + 1
            this.style_root_node_offsets.push([node, -width/2 + node_width/2 + col_no * node_width, row_no * node_width/2])
        }
    }

    translate_coords() {
        if (!this.style_root_node.children)
            return

        if (this._style_translated) {
            return
        }

        let node_positioning = this._layout_manager.get_node_positioning(this.style_root_node)
        let force = node_positioning[this.id()] = {}
        force.weight = this.positioning_weight()
        force.fx = this.style_root_node.x
        force.fy = this.style_root_node.y

        this._vertices = []
        this._vertices.push([this.style_root_node.x, this.style_root_node.y])

        for (let idx in this.style_root_node_offsets) {
            let entry = this.style_root_node_offsets[idx]
            let node = entry[0]
            let x = entry[1]
            let y = entry[2]
            let node_positioning = this._layout_manager.get_node_positioning(node)
            let force = node_positioning[this.id()] = {}

            force.weight = this.positioning_weight()
            let node_coords = {}
            node_coords.x = this.style_root_node.x + x
            node_coords.y = this.style_root_node.y + y

            force.fx = node_coords.x
            force.fy = node_coords.y

            this._vertices.push([force.fx, force.fy])

            force.use_transition = this.use_transition
            force.text_positioning = (selection, radius)=>selection.attr("transform", "translate("+(radius)+","+(radius+4)+") rotate(45)")
            force.hide_node_link = true
            node.force = -500
        }

        this.generate_overlay()
        this.use_transition = false
        this._style_translated = true
        return true
    }

    update_gui() {
        this.generate_overlay()
    }

    generate_overlay() {
        if (this._vertices.length < 2)
            return

        // Remove the style_root_node
        let boundary = 10
        let hull_vertices = []
        for (let idx in this._vertices) {
            if (idx == 0)
                continue
            let entry = this._vertices[idx]
            hull_vertices.push([entry[0]+boundary, entry[1]+boundary])
            hull_vertices.push([entry[0]-boundary, entry[1]-boundary])
            hull_vertices.push([entry[0]+boundary, entry[1]-boundary])
            hull_vertices.push([entry[0]-boundary, entry[1]+boundary])
        }
        let hull = this.selection.selectAll("path.children_boundary").data([d3.polygonHull(hull_vertices)])
        hull = hull.enter().append("path")
                    .classed("children_boundary", true)
                    .style("vector-effect", "non-scaling-stroke")
                    .style("fill", "none")
                    .style("stroke", "grey")
                    .style("stroke-width", "2px")
                    .attr("stroke-linejoin", "round")
                    .attr("pointer-events", "none")
                .merge(hull)
        hull.interrupt()
        this.add_optional_transition(hull.attr("d", function(d) {return "M" + d.join("L") + "Z";}));

        let connection_line = this.selection.selectAll("line.root_children_connection").data([null])
        connection_line.enter().append("line")
                .classed("root_children_connection", true)
                .style("vector-effect", "non-scaling-stroke")
                .attr("stroke", "grey")
                .attr("stroke-width", d=>{return Math.max(1, 2-this.style_root_node.depth)})
              .merge(connection_line)
                .attr("x1", this.style_root_node.x)
                .attr("y1", this.style_root_node.y)
                .attr("x2", this.style_root_node.x)
                .attr("y2", this.style_root_node.y + 15)
    }
}

// TODO: move this from global scope into setup components in LayoutManager?
node_visualization_layouting_utils.LayoutStyleFactory.style_classes.push(LayoutStyleForce)
node_visualization_layouting_utils.LayoutStyleFactory.style_classes.push(LayoutStyleHierarchy)
node_visualization_layouting_utils.LayoutStyleFactory.style_classes.push(LayoutStyleRadial)
node_visualization_layouting_utils.LayoutStyleFactory.style_classes.push(LayoutStyleFixed)
node_visualization_layouting_utils.LayoutStyleFactory.style_classes.push(LayoutStyleBlock)
