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

//   .-Toolbar------------------------------------------------------------.
//   |                 _____           _ _                                |
//   |                |_   _|__   ___ | | |__   __ _ _ __                 |
//   |                  | |/ _ \ / _ \| | '_ \ / _` | '__|                |
//   |                  | | (_) | (_) | | |_) | (_| | |                   |
//   |                  |_|\___/ \___/|_|_.__/ \__,_|_|                   |
//   |                                                                    |
//   +--------------------------------------------------------------------+

import * as node_visualization_search from "node_visualization_search"
import * as node_visualization_datasources from "node_visualization_datasources"

export class Toolbar {
    constructor(main_instance, selection) {
        selection.attr("id", "toolbar")
                 .style("width", "100%")
                 .style("height", "100%");
        this.main_instance = main_instance
        this._selection = selection

        this._toolbar_plugins = {}
        this._plugins_content_selection = this._selection.append("div")
                                                    .attr("id", "content")

        this._plugin_controls_selection = this._selection.append("div")
                                                    .attr("id", "toolbar_controls")
        this._plugin_buttons_selection = this._plugin_controls_selection.append("div")
                                                    .attr("id", "togglebuttons")
        this._plugin_custom_elements_selection = this._plugin_controls_selection.append("div")
                                                    .attr("id", "custom")

        this._setup_toolbar_plugins()
        this.update_toolbar_plugins()

        // Kept for debug purposes. This opens the layout toolbar a second later
        //setTimeout(()=>this._toolbar_plugins["layouting_toolbar"].toggle_active(), 1000)
    }

    _setup_toolbar_plugins() {
        this._register_toolbar_plugin(node_visualization_search.SearchAggregationsPlugin)
    }

    _register_toolbar_plugin(toolbar_plugin_class) {
        if (toolbar_plugin_class.prototype.id() in this._toolbar_plugins)
            return
        this.add_toolbar_plugin_instance(new toolbar_plugin_class(this.main_instance))
    }

    add_toolbar_plugin_instance(toolbar_plugin_instance) {
        this._toolbar_plugins[toolbar_plugin_instance.id()] = toolbar_plugin_instance
    }

    update_toolbar_plugins() {
        let plugin_ids = Object.keys(this._toolbar_plugins)
        plugin_ids.sort((a, b) => {
            return this._toolbar_plugins[a].sort_index < this._toolbar_plugins[b].sort_index
        })

        plugin_ids.forEach(plugin_id=>{
            let plugin = this._toolbar_plugins[plugin_id];
            if (!plugin.content_selection) {
                let content_selection = this._plugins_content_selection.append("div").attr("id", plugin_id);
                if (plugin.has_toggle_button()) {
                    let button_selection = this._plugin_buttons_selection.append("div")
                                                        .attr("id", "togglebutton_" + plugin_id)
                                                        .classed("togglebutton", true)
                                                        .classed("noselect", true)
                                                        .classed("box", true)
                                                        .classed("on", true)
                                                        .classed("down", !plugin.active)
                                                        .classed("up", plugin.active)
                                                        .on("click", ()=>this.toggle_plugin(plugin));
                    plugin.render_togglebutton(button_selection);
                }
                plugin.setup_selections(content_selection);
            }
            this.set_plugin_state(plugin, plugin.active);
        })
    }

    toggle_plugin(plugin) {
        this.set_plugin_state(plugin, !plugin.active);
    }

    set_plugin_state(plugin, is_active) {
        let plugin_button = this._plugin_buttons_selection.select("#togglebutton_" + plugin.id());
        plugin_button.classed("up", !is_active);
        plugin_button.classed("down", is_active);
        if (is_active == true) {
            plugin.enable();
            plugin.render_content();
        } else {
            plugin.disable();
        }
    }

    get_plugin(plugin_id) {
        return this._toolbar_plugins[plugin_id]
    }
}
