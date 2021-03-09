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

export function log(level, info) {
    if (level < 4)
        console.log(...Array.from(arguments))
}

export class DefaultTransition {
    static duration() {
        return 500;
    }

    static add_transition(selection) {
        return selection.transition().duration(DefaultTransition.duration())
    }
}

// Stores layers and maintains their correct order
class LayerRegistry {
    constructor() {
        this._layers = []
    }

    register(layer_class, sort_index) {
        this._layers.push([layer_class, sort_index])
        this._layers.sort(function (a, b) {
            if (a[1] > b[1])
                return 1
            if (a[1] < b[1])
                return -1
            return 0
        })
    }

    get_layers() {
        return this._layers
    }
}
export let layer_registry = new LayerRegistry()


// Stores node visualization classes
class NodeTypeClassRegistry {
    constructor() {
        this._node_classes = {}
    }

    register(node_class) {
        this._node_classes[node_class.id()] = node_class
    }

    get_node_class(class_id) {
        return this._node_classes[class_id]
    }
}
export let node_type_class_registry = new NodeTypeClassRegistry()


export class NodeMatcher {
    constructor(hierarchy_list) {
        this.hierarchy_list = hierarchy_list
    }

    find_node(matcher) {
        let nodes_to_check = []

        if (matcher.rule_id)
            nodes_to_check =  this._get_aggregator_nodes()
        else if(matcher.hostname || matcher.service)
            nodes_to_check =  this._get_leaf_nodes()
        else
            nodes_to_check =  this._get_all_nodes()

        for (let idx in nodes_to_check) {
            let node = nodes_to_check[idx]
            if (this._match_node(matcher, node))
                return node
        }
    }

    _get_all_nodes() {
        let all_nodes = []
        this.hierarchy_list.forEach(partition=>{
            all_nodes = all_nodes.concat(partition.nodes)
        })
        return all_nodes
    }

    _get_aggregator_nodes() {
        let aggregator_nodes = []
        this.hierarchy_list.forEach(partition=>{
            partition.nodes.forEach(node=>{
                if (node.children)
                    aggregator_nodes.push(node)
            })
        })
        return aggregator_nodes
    }

    _get_leaf_nodes() {
        let leaf_nodes = []
        this.hierarchy_list.forEach(partition=>{
            partition.nodes.forEach(node=>{
                if (!node._children)
                    leaf_nodes.push(node)
            })
        })
        return leaf_nodes
    }

    _match_node(matcher, node) {
        // Basic matches
        let elements = ["hostname", "service"]
        for (let idx in elements) {
            let match_type = elements[idx]
            if (matcher[match_type] && !matcher[match_type].disabled && node.data[match_type] != matcher[match_type].value)
                return false
        }

        // List matches
        elements = ["aggr_path_id", "aggr_path_name"]
        for (let idx in elements) {
            let match_type = elements[idx]
            if (!matcher[match_type])
                continue

            if (matcher[match_type].disabled)
                continue

            if (JSON.stringify(matcher[match_type].value) != JSON.stringify(node.data[match_type]))
                return false
        }

        // Complex matches
        if (matcher.rule_id && !matcher.rule_id.disabled && node.data.rule_id.rule != matcher.rule_id.value)
            return false

        // Complex matches
        if (matcher.rule_name && !matcher.rule_name.disabled && node.data.name != matcher.rule_name.value)
            return false


        return node
    }
}

export function get_bounding_rect(list_of_coords) {
    let rect = {
        x_min:  10000,
        x_max: -10000,
        y_min:  10000,
        y_max: -10000,
    }

    list_of_coords.forEach(coord=>{
        rect.x_min = Math.min(coord.x, rect.x_min)
        rect.y_min = Math.min(coord.y, rect.y_min)
        rect.x_max = Math.max(coord.x, rect.x_max)
        rect.y_max = Math.max(coord.y, rect.y_max)
    })
    rect.width = rect.x_max - rect.x_min
    rect.height = rect.y_max - rect.y_min
    return rect
}

export function get_bounding_rect_of_rotated_vertices(vertices, rotation_in_rad) {
    // TODO: check this
    // Vertices with less than 3 elements will fail
    if (vertices.length < 3)
        return {
            x_min: vertices[0].x,
            x_max: vertices[0].x+10,
            y_min: vertices[0].y,
            y_max: vertices[0].y+10,
            width: 10,
            height: 10}

    let cos_x = Math.cos(rotation_in_rad)
    let sin_x = Math.sin(rotation_in_rad)
    let rotated_vertices = []
    vertices.forEach(coords=>{
        rotated_vertices.push({
            x: cos_x * coords.x + sin_x * coords.y,
            y: cos_x * coords.y + sin_x * coords.x,
        })
    })
    return get_bounding_rect(rotated_vertices)
}


