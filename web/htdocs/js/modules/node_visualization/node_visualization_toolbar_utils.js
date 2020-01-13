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
        this.content_selection = null
    }

    setup_selections(content_selection) {
        this.content_selection = content_selection
    }


    has_toggle_button() {
        return true
    }

    render_togglebutton() {}


    description() {
        return this.description
    }

    enable() {
        this.active = true
        this.enable_actions()
        this.render_content()
    }

    enable_actions() {}

    render_content() {}

    disable() {
        this.active = false
        this.disable_actions()
        this.remove_content()
    }

    disable_actions() {}

    remove_content() {
        if (this.content_selection)
            this.content_selection.selectAll("*").remove()
    }
}

