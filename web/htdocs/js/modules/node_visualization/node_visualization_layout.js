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

export class NodeVisualizationLayout {
    constructor(viewport, id) {
        this.id = id
        this.viewport = viewport
        this.reference_size = {}
        this.style_configs = []
        this.overlay_config = {}
        this.line_config = {"style": "round"}
    }

    save_style(style_config) {
        this.style_configs.push(style_config)
    }

    clear_styles() {
        this.style_configs = []
    }

    remove_style(style_instance) {
        let idx = this.style_configs.indexOf(style_instance.style_config)
        this.style_configs.splice(idx, 1)
    }

    serialize() {
        return {
            reference_size: this.reference_size,
            style_configs: this.style_configs,
            overlay_config: this.overlay_config,
            line_config: this.line_config,
        }
    }

    deserialize(data) {
        this.reference_size = data.reference_size
        this.style_configs  = data.style_configs
        this.overlay_config = data.overlay_config
        this.line_config = data.line_config
    }
}
