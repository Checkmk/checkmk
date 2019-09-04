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

import * as node_visualization_layout from "node_visualization_layout"


export class LayoutStyleFactory {
    constructor(layout_manager) {
        this.layout_manager = layout_manager
        this.style_templates = {}
        this.load_styles()
    }

    load_styles() {
        LayoutStyleFactory.style_classes.forEach(style=>{
            this.style_templates[style.prototype.type()] = style
        })
    }

    get_styles(){
        return this.style_templates
    }

    get_style_class(style_config) {
        return this.style_templates[style_config.type]
    }

    // Creates a style instance with the given style_config
    instantiate_style(style_config, node, selection) {
        return new (this.get_style_class(style_config))(this.layout_manager, style_config, node, selection)
    }

    instantiate_style_name(style_name, node, selection) {
        return this.instantiate_style({type: style_name}, node, selection)
    }

    instantiate_style_class(style_class, node, selection) {
        return this.instantiate_style({type: style_class.prototype.type()}, node, selection)
    }
}

LayoutStyleFactory.style_classes = []
