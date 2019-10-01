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

export class LayeredLayerBase {
    constructor(viewport, enabled=true) {
        this.toggleable = false
        this.enabled = enabled
        this.viewport = viewport
        this.selection = null
    }


    // Initialize GUI elements and objects
    // Does not process/store any external data

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

        if (this.selection) {
            this.selection.selectAll("*").remove()
            this.selection = null
        }

        if (this.div_selection) {
            this.div_selection.selectAll("*").remove()
            this.div_selection = null
        }
    }

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

export class LayeredOverlayBase extends LayeredLayerBase {
    constructor(viewport, enabled=true) {
        super(viewport, enabled)
        this.toggleable = true
    }
}
