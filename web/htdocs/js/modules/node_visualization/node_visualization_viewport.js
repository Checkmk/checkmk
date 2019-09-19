// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
// +------------------------------------------------------------------+
//
// This file is part of Check_MK.
// The official homepage is at http://mathias-kettner.de/check_mk.
//
// check_mk is free software;  you can redistribute it and/or modify it
// under the  terms of the  GNU General Public License  as published by
// the Free Software Foundation in version 2.  check_mk is  distributed
// in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
// out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
// PARTICULAR PURPOSE. See the  GNU General Public License for more de-
// tails.  You should have received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

import * as node_visualization_utils from "node_visualization_utils"
import * as node_visualization_datasources from "node_visualization_datasources"
import * as node_visualization_viewport_layers from "node_visualization_viewport_layers"
import * as node_visualization_layouting from "node_visualization_layouting"
import * as d3 from "d3"

// The main viewport
export class Viewport {
    constructor(main_instance) {
        this.main_instance = main_instance;
        this.selection = this.main_instance.get_div_selection().append("div")
                                  .attr("id", "viewport")
                                  .classed("viewport", true);

        this._viewport_plugins = {}
        this.current_viewport = null
        this._load_viewport_plugins()
        this._set_viewport_plugin(LayeredViewportPlugin.id())
        this._current_datasource = null
        window.addEventListener("resize", ()=>this._size_changed())
    }

    _size_changed() {
        if (this.current_viewport)
            this.current_viewport.size_changed()
    }

    _load_viewport_plugins() {
        this._register_viewport_plugin(LayeredViewportPlugin)
    }

    _set_viewport_plugin(plugin_id) {
        this.current_viewport = this._viewport_plugins[plugin_id]
        this.current_viewport.setup(this.selection)
    }

    _register_viewport_plugin(viewport_plugin_class) {
        if (viewport_plugin_class.id() in this._viewport_plugins)
            return
        this._viewport_plugins[viewport_plugin_class.id()] = new viewport_plugin_class(this)

    }

    // Determines the correct viewport plugin for the given daten
    // Since there is only one plugin right now, its quite pointless :)
    show_data(datasource, node_chunk_list) {
        this._current_datasource = datasource
        this.current_viewport.feed_data(node_chunk_list)
    }

    get_current_datasource() {
        return this._current_datasource
    }
}


export class AbstractViewportPlugin {
    static id() {
        return "abstract_viewport_plugin"
    }

    constructor(master_viewport) {
        this._master_viewport = master_viewport
        this.main_instance = this._master_viewport.main_instance
    }

    setup(into_selection) {}

    feed_data(json_data) {}

    get_current_datasource() {
        return this._master_viewport.get_current_datasource()
    }
}


//#.
//#   .-Layered Viewport---------------------------------------------------.
//#   |                _                                  _                |
//#   |               | |    __ _ _   _  ___ _ __ ___  __| |               |
//#   |               | |   / _` | | | |/ _ \ '__/ _ \/ _` |               |
//#   |               | |__| (_| | |_| |  __/ | |  __/ (_| |               |
//#   |               |_____\__,_|\__, |\___|_|  \___|\__,_|               |
//#   |                           |___/                                    |
//#   |           __     ___                                _              |
//#   |           \ \   / (_) _____      ___ __   ___  _ __| |_            |
//#   |            \ \ / /| |/ _ \ \ /\ / / '_ \ / _ \| '__| __|           |
//#   |             \ V / | |  __/\ V  V /| |_) | (_) | |  | |_            |
//#   |              \_/  |_|\___| \_/\_/ | .__/ \___/|_|   \__|           |
//#   |                                   |_|                              |
//#   +--------------------------------------------------------------------+
class LayeredViewportPlugin extends AbstractViewportPlugin {
    id() {
        return "layered_viewport"
    }

    constructor(master_viewport) {
        super(master_viewport)

        this._layers = {} // Layer instances
        this._selections_for_layer = {} // Each layer gets a div and svg selection
        this._node_chunk_list = [] // Node data
        this._margin = {top: 10, right: 10, bottom: 10, left: 10};


        //////////////////////////////////
        // Infos usable by layers
        this.width = 0
        this.height = 0

        this.last_zoom = d3.zoomIdentity
        this.scale_x = null
        this.scale_y = null
        //////////////////////////////////

        this.always_update_layout = false

    }

    setup(into_selection) {
        this.into_selection = into_selection
        this.selection = into_selection.append("div").attr("id", "main_window_layered")

        // Each layer gets a svg and a div domain to render its content
        // Layer structure

        // div#main_window_layered
        //    svg#svg_content 
        //       g#svg_layers
        //          layerA
        //          layerB
        //          layerC
        //    div#div_content 
        //       div#div_layers
        //          layerA
        //          layerB
        //          layerC

        this.svg_content_selection = this.selection.append("svg").attr("width", "100%").attr("height", "100%")
                                                    .attr("id", "svg_content")
                                                    .on("contextmenu", () => {
                                                               d3.event.preventDefault()
                                                               d3.event.stopPropagation()
                                                               // TODO: identify nodes layer (svg/canvas)
                                                               this._layers[node_visualization_viewport_layers.LayeredNodesLayer.prototype.id()].render_context_menu()
                                                    })
                                                    .on("click.remove_context", ()=>this._layers[node_visualization_viewport_layers.LayeredNodesLayer.prototype.id()].remove_context_menu())

        this.div_content_selection = this.selection.append("div").style("position", "absolute")
                                                    .style("width", "100%")
                                                    .style("height", "100%")
                                                    .style("top", "0px")
                                                    .style("left", "0px")
                                                    .style("pointer-events", "none")
                                                    .style("overflow", "hidden")
                                                    .attr("id", "div_content")

        this.svg_layers_selection = this.svg_content_selection.append("g").attr("id", "svg_layers")
        this.div_layers_selection = this.div_content_selection.append("div").attr("id", "div_layers")

        this.main_zoom = d3.zoom()
        this.main_zoom.scaleExtent([0.2, 10]).on("zoom", () => this.zoomed())

        // Disable left click zoom
        this.main_zoom.filter(()=>{return d3.event.button === 0 || d3.event.button === 1})
        this.svg_content_selection.call(this.main_zoom).on("dblclick.zoom", null)

        this.layer_toggle = this.div_layers_selection.append("div").attr("id", "togglebox_choices")

        // Initialize viewport size and scales before loading the layers
        this.size_changed()
        this._load_layers()
        this.size_changed()
    }


    _load_layers() {
        node_visualization_utils.layer_registry.register(node_visualization_layouting.LayoutManagerLayer, 40)

        node_visualization_utils.layer_registry.get_layers().forEach(layer=>{
            let layer_class = layer[0]
            let layer_instance = new layer_class(this)
            this._add_layer(layer_instance)
            if (layer_class == node_visualization_layouting.LayoutManagerLayer)
                this.layout_manager = layer_instance
        })
    }

    _add_layer(layer) {
        this._layers[layer.id()] = layer
        this._selections_for_layer[layer.id()] = {
              svg: this.svg_layers_selection.append("g").attr("id", layer.id()),
              div: this.div_layers_selection.append("div").attr("id", layer.id())
        }

        // Toggleable layers are off by default
        layer.set_enabled(!layer.is_toggleable())
    }

    update_active_overlays() {
        let overlay_config = this.layout_manager.get_overlay_config()
        let active_overlays = {}
        for (let idx in overlay_config) {
            let overlay = overlay_config[idx]
            if (overlay.active == true)
                active_overlays[idx] = true
        }

        // Enable/Disable overlays
        for (let idx in this._layers) {
            let layer = this._layers[idx]
            if (!layer.is_toggleable())
                continue

            let layer_id = layer.id()
            if (active_overlays[layer_id]) {
                if (layer.is_enabled())
                    continue
                this.enable_layer(layer_id)
            } else {
                if (!layer.is_enabled())
                    continue
                this.disable_layer(layer_id)
            }
        }
        this.update_overlay_toggleboxes()
    }

    enable_layer(layer_id) {
        this._layers[layer_id].enable(this._selections_for_layer[layer_id])
    }

    disable_layer(layer_id) {
        this._layers[layer_id].disable()
    }

    get_layers() {
        return this._layers
    }

    get_layer(layer_id) {
        return this._layers[layer_id]
    }

    update_overlay_toggleboxes() {
        if (!this.layout_manager.layout_applier.current_layout_group)
            return
        let configurable_overlays = []
        for (let idx in this._layers) {
            let layer = this._layers[idx]
            let layer_id = layer.id()
            if (layer.toggleable) {
                let overlay_config = this.layout_manager.layout_applier.current_layout_group.overlay_config
                if (!overlay_config[layer_id])
                    continue

                if (overlay_config[layer_id].configurable != true)
                    continue

                configurable_overlays.push({layer: layer, config: overlay_config[layer_id]})
            }
        }

        // Update toggleboxes
        let toggleboxes = this.layer_toggle.selectAll("div.togglebox").data(configurable_overlays, d=>d.layer.id())
        toggleboxes.exit().remove()
        toggleboxes = toggleboxes.enter().append("div").text(d=>d.layer.name())
                        .attr("layer_id", d=>d.layer.id())
                        .classed("box", true)
                        .classed("noselect", true)
                        .classed("togglebox", true)
                        .style("pointer-events", "all")
                        .on("click", ()=>this.toggle_overlay_click())
                        .merge(toggleboxes)
        toggleboxes.classed("enabled", d=>d.config.active)
    }

    toggle_overlay_click() {
        d3.event.stopPropagation()
        let target = d3.select(d3.event.target)
        let layer_id = target.attr("layer_id")

        var new_state =  !this._layers[layer_id].is_enabled()
        target.classed("enabled", new_state)
        if (new_state == true)
            this.enable_layer(layer_id)
        else
            this.disable_layer(layer_id)
    }

    feed_data(data_to_show) {
        this.feed_data_timestamp = Math.floor(new Date().getTime()/1000)
        this.data_to_show = data_to_show

        // TODO: fix marked obsolete handling
        this._node_chunk_list.forEach(node_chunk=>node_chunk.marked_obsolete=true)


        // This is in indicator whether its necessary to reapply all layouts
        this._chunks_changed = false
        this.data_to_show.chunks.forEach(chunk_rawdata=>{
            this._consume_chunk_rawdata(chunk_rawdata)
        })

        this._remove_obsolete_chunks()
        this._arrange_multiple_node_chunks()

        this.update_layers()

        if (this.always_update_layout || this._chunks_changed)
            this.layout_manager.layout_applier.apply_multiple_layouts(this.get_hierarchy_list())
        this.layout_manager.compute_node_positions()

    }

    _consume_chunk_rawdata(chunk_rawdata) {
        // Generates a chunk object which includes the following data
        // {
        //   id:                 ID to identify this chunk
        //   hierarchy:          nodes in hierarchical order
        //   tree:               hierarchy tree
        //   nodes:              nodes as list
        //   links:              links between nodes
        //                       These are either provided in the rawdata or
        //                       automatically computed out of the hierarchy layout
        //   layout:             layout configuration
        // }
        let chunk = {}

        let hierarchy = d3.hierarchy(chunk_rawdata.hierarchy)

        // Initialize default info of each node
        hierarchy.descendants().forEach(node=>{
                node._children = node.children
                node.data.node_positioning = {}
                node.data.transition_info = {}
                node.data.chunk = chunk
        })

        // Compute path and id to identify the nodes
        this._add_aggr_path_and_node_id(hierarchy, {})

        chunk.tree = hierarchy
        chunk.nodes = chunk.tree.descendants()

        // Use layout info
        chunk.layout_settings = chunk_rawdata.layout

        chunk.id = chunk.nodes[0].data.id

        let chunk_links = []
        if (chunk_rawdata.links) {
            // The chunk specified its own links
            chunk_rawdata.links.forEach(link=>{
                chunk_links.push({source: chunk.nodes[link[0]],
                                  target: chunk.nodes[link[1]]})
            })
        } else {
            // Create links out of the hierarchy layout
            chunk.nodes.forEach(node=>{
                if (!node.parent || node.data.invisible)
                    return
                chunk_links.push({source: node, target: node.parent})
            })
        }
        chunk.links = chunk_links
        this.update_node_chunk_list(chunk)
    }

    _remove_obsolete_chunks() {
        let new_chunk_list = []
        this._node_chunk_list.forEach(node_chunk=>{
            if (!node_chunk.marked_obsolete)
                new_chunk_list.push(node_chunk)
            else
                this._chunks_changed = true
        })
        this._node_chunk_list = new_chunk_list
    }

    _add_aggr_path_and_node_id(node, siblings_id_counter) {
        let aggr_path_id = []
        let aggr_path_name = []
        if (node.parent) {
            aggr_path_id = node.parent.data.aggr_path_id.concat([])
            aggr_path_name = node.parent.data.aggr_path_name.concat([])
        }

        let rule_id = node.data.rule_id
        let name = node.data.name
        if (rule_id != null) {
            // Aggregation node
            rule_id = rule_id.rule
            aggr_path_id = aggr_path_id.concat([[rule_id, this._get_siblings_index("rule_id", rule_id, siblings_id_counter)]])
            aggr_path_name = aggr_path_name.concat([[name, this._get_siblings_index("rule_name", name, siblings_id_counter)]])
        }

        node.data.aggr_path_id = aggr_path_id
        node.data.aggr_path_name = aggr_path_name

        let node_id = ""
        node.data.aggr_path_name.forEach(token=>{
            node_id += "#" + token[0] + "#" + token[1]
        })


        if (node.data.hostname)
            node_id += node.data.hostname + "(" + this._get_siblings_index("hostname", node.data.hostname, siblings_id_counter) + ")"
         if (node.data.service)
            node_id += node.data.service + "(" + this._get_siblings_index("service", node.data.service, siblings_id_counter) + ")"
        node.data.id = node_id

        if (node.children) {
            let siblings_id_counter = {}
            node.children.forEach(child=>this._add_aggr_path_and_node_id(child, siblings_id_counter))
        }
    }

    _get_siblings_index(domain, value, siblings_id_counter) {
        if (!siblings_id_counter[domain + "_" + value])
            siblings_id_counter[domain + "_" + value] = []
        siblings_id_counter[domain + "_" + value].push(value)
        return siblings_id_counter[domain + "_" + value].length
    }

    _arrange_multiple_node_chunks() {
        if (this._node_chunk_list.length == 0)
            return

        let partition_hierarchy = {name: "root", children: []}
        this._node_chunk_list.forEach(chunk=>{
            partition_hierarchy.children.push({name: chunk.nodes[0].data.id,
                                               value: chunk.nodes.length})
        })

        let treemap_root = d3.hierarchy(partition_hierarchy)
        treemap_root.sum(d=>d.value)

        d3.treemap().size([parseInt(this.width), parseInt(this.height)])(treemap_root)
        for (let idx in treemap_root.children) {
            let child = treemap_root.children[idx]
            let node_chunk = this._node_chunk_list[idx]
            let coords = {x: child.x0, y: child.y0, width: child.x1 - child.x0, height: child.y1 - child.y0}

            node_chunk.coords = coords
            let rad = 0
            let rad_delta = Math.PI/8

            node_chunk.nodes.forEach(node=>{
                if (node["x"])
                    // This node already has some coordinates
                    return

                let spawn_coords = this._compute_spawn_coords(node_chunk, node)
                node.x = spawn_coords.x + Math.cos(rad) * (30+rad*4)
                node.y = spawn_coords.y + Math.sin(rad) * (30+rad*4)
                rad += rad_delta
            })
        }
    }

    _compute_spawn_coords(node_chunk, node) {
        let linked_nodes = this._find_linked_nodes(node_chunk, node)
        // Try to use the coordinates of active linked nodes
        for (let idx in linked_nodes) {
            let linked_node = linked_nodes[idx]
            if (linked_node.x)
                return {x: linked_node.x, y: linked_node.y}
        }

        // Try to use the coordinates of the parent node
        if (node.parent && node.parent.x) {
            return {x: node.parent.x, y: node.parent.y}
        }

        // Fallback. Spawn at center
        return {x: node_chunk.coords.width/2, y: node_chunk.coords.height/2}
    }

    _find_linked_nodes(node_chunk, node) {
        let linked_nodes = []
        node_chunk.links.forEach(link=>{
            if (node == link.source)
                linked_nodes.push(link.target)
            else if (node == link.target)
                linked_nodes.push(link.source)
        })
        return linked_nodes
    }

    get_all_links() {
        let all_links = []
        this._node_chunk_list.forEach(chunk=>{
            all_links = all_links.concat(chunk.links)
        })
        return all_links
    }

    get_all_nodes() {
        let all_nodes = []
        this._node_chunk_list.forEach(hierarchy=>{
            all_nodes = all_nodes.concat(hierarchy.nodes)
        })
        return all_nodes
    }

    get_hierarchy_list() {
        return this._node_chunk_list
    }

    get_chunk_of_node(node_in_chunk) {
        let root_node = this._get_chunk_root(node_in_chunk)
        for (let idx in this._node_chunk_list) {
           if (this._node_chunk_list[idx].tree == root_node)
               return this._node_chunk_list[idx]
        }
        return null
    }

    _get_chunk_root(node) {
       if (!node.parent)
            return node
       return this._get_chunk_root(node.parent)
    }

    update_node_chunk_list(new_chunk) {
        let chunk_id = new_chunk.tree.data.id
        for (let idx in this._node_chunk_list) {
            let existing_chunk = this._node_chunk_list[idx]
            if (existing_chunk.tree.data.id == chunk_id) {
                let old_node_coords = {}
                existing_chunk.nodes.forEach(node=>{
                    old_node_coords[node.data.id] = {x: node.x, y: node.y}
                })

                if (!this.layout_manager.allow_layout_updates)
                    new_chunk.layout_instance = existing_chunk.layout_instance

                new_chunk.coords = existing_chunk.coords
                new_chunk.nodes.forEach((node, idx)=>{
                    // Reuse computed coordinates from previous chunk data
                    if (old_node_coords[node.data.id]) {
                        node.x = old_node_coords[node.data.id].x
                        node.y = old_node_coords[node.data.id].y
                    }
                    else
                        this._chunks_changed = true
                })
                if (existing_chunk.nodes.length != new_chunk.nodes.length)
                    this._chunks_changed = true
                this._node_chunk_list[idx] = new_chunk
                return
            }
        }

        this._chunks_changed = true
        this._node_chunk_list.push(new_chunk)
    }

    recompute_node_chunk_descendants_and_links(node_chunk) {
        node_chunk.nodes = node_chunk.tree.descendants()

        let chunk_links = []
        node_chunk.nodes.forEach(node=>{
            if (!node.parent || node.data.invisible)
                return
            chunk_links.push({source: node, target: node.parent})
        })
        node_chunk.links = chunk_links
    }

    update_layers() {
        this.update_data_of_layers()
        this.update_gui_of_layers()
    }

    update_data_of_layers() {
        for (var layer_id in this._layers) {
            if (!this._layers[layer_id].is_enabled())
                continue
            node_visualization_utils.log(7, "update data of layer", layer_id)
            this._layers[layer_id].update_data()
        }
    }

    update_gui_of_layers() {
        for (var layer_id in this._layers) {
            if (!this._layers[layer_id].is_enabled())
                continue
            node_visualization_utils.log(7, "update gui of layer", layer_id)
            this._layers[layer_id].update_gui()
        }
    }

    zoomed() {
        if (!this.data_to_show)
            return

        this.last_zoom = d3.event.transform
        this.scale_x.range([0, this.width * d3.event.transform.k])
        this.scale_y.range([0, this.height * d3.event.transform.k])

        for (var layer_id in this._layers) {
            if (!this._layers[layer_id].is_enabled())
                continue
            this._layers[layer_id].zoomed()
            this._layers[layer_id].update_gui()
        }
    }

    // Applies scale and x/y translation
    translate_to_zoom(coords) {
        let translated = this.scale_to_zoom(coords)
        if ("x" in translated)
            translated.x = this.last_zoom.x + translated.x

        if ("y" in translated)
            translated.y = this.last_zoom.y + translated.y

        return translated
    }

    // Applies scale
    scale_to_zoom(coords) {
        let translated = {}
        if ("x" in coords)
            translated.x = this.scale_x(coords.x)

        if ("y" in coords)
            translated.y = this.scale_y(coords.y)

        if (coords.width)
            translated.width = this.scale_x(coords.width)

        if (coords.height)
            translated.height = this.scale_y(coords.height)

        return translated
    }


    size_changed() {
        let rectangle = this.into_selection.node().getBoundingClientRect();
        this.width = rectangle.width - this._margin.left- this._margin.right;
        this.height = rectangle.height - this._margin.top - this._margin.bottom;

        this.scale_x = d3.scaleLinear().domain([0, this.width]).range([0, this.width])
        this.scale_y = d3.scaleLinear().domain([0, this.height]).range([0, this.height])

        this.selection.style("width", (this.width + this._margin.left + this._margin.right) + "px")
                      .style("height", (this.height + this._margin.top + this._margin.bottom) + "px")

        for (var layer_id in this._layers) {
            this._layers[layer_id].size_changed()
        }
    }
}

