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

export class ToolbarPluginBase extends Object {
    static id() {}

    constructor(description, main_instance) {
        super()
        this.main_instance = main_instance
        this.description = description
        this.active = false
        this.togglebutton_selection = null
        this.content_selection = null
    }

    setup_selections(togglebutton_selection, content_selection) {
        this.togglebutton_selection = togglebutton_selection
        this.content_selection = content_selection
    }

    has_content_selection() {
        return this.content_selection != null
    }

    toggle_active() {
        this.active = !this.active
        this.update_active_state()
    }

    update_active_state() {
        if (!this.active) {
            if (this.togglebutton_selection) {
                this.togglebutton_selection.classed("up", true)
                this.togglebutton_selection.classed("down", false)
            }
            this.disable_actions()
            this.remove()
        }
        else {
            if (this.togglebutton_selection) {
                this.togglebutton_selection.classed("up", false)
                this.togglebutton_selection.classed("down", true)
            }
            this.enable_actions()
            this.render_content()
        }
    }

    remove() {
        this.content_selection.selectAll("*").remove()
    }

    has_toggle_button() {
        return true
    }

    render_togglebutton() {}

    render_content() {}

    description() {
        return this.description
    }

    enable() {
        this.active = true
        this.enable_actions()
    }

    enable_actions() {}

    disable() {
        this.active = false
        this.disable_actions()
    }

    disable_actions() {}
}

