/**
 * Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

//   .-Toolbar------------------------------------------------------------.
//   |                 _____           _ _                                |
//   |                |_   _|__   ___ | | |__   __ _ _ __                 |
//   |                  | |/ _ \ / _ \| | '_ \ / _` | '__|                |
//   |                  | | (_) | (_) | | |_) | (_| | |                   |
//   |                  |_|\___/ \___/|_|_.__/ \__,_|_|                   |
//   |                                                                    |
//   +--------------------------------------------------------------------+

import {SearchAggregationsPlugin} from "nodevis/search";
import {ToolbarPluginBase} from "nodevis/toolbar_utils";
import {d3SelectionDiv, NodevisWorld} from "nodevis/type_defs";

export class Toolbar {
    _world: NodevisWorld;
    _div_selection: d3SelectionDiv;
    _toolbar_plugins = {};
    _plugin_contents_selection: d3SelectionDiv;
    _plugin_controls_selection: d3SelectionDiv;
    _plugin_buttons_selection: d3SelectionDiv;
    _plugin_custom_elements_selection: d3SelectionDiv;

    constructor(world: NodevisWorld, selection: d3SelectionDiv) {
        selection.attr("id", "toolbar").style("width", "100%");
        this._world = world;
        this._div_selection = selection;
        this._plugin_contents_selection = this._div_selection
            .append("div")
            .attr("id", "content");
        this._plugin_controls_selection = this._div_selection
            .append("div")
            .attr("id", "toolbar_controls");
        this._plugin_buttons_selection = this._plugin_controls_selection
            .append("div")
            .attr("id", "togglebuttons");
        this._plugin_custom_elements_selection = this._plugin_controls_selection
            .append("div")
            .attr("id", "custom");
    }

    setup_world_components() {
        this._setup_toolbar_plugins();
    }

    _setup_toolbar_plugins(): void {
        this._register_toolbar_plugin(SearchAggregationsPlugin);
    }

    _register_toolbar_plugin(toolbar_plugin: typeof ToolbarPluginBase): void {
        // @ts-ignore
        const instance = toolbar_plugin.instantiate(this._world);
        if (instance.id() in this._toolbar_plugins) return;
        this.add_toolbar_plugin_instance(instance);
    }

    add_toolbar_plugin_instance(
        toolbar_plugin_instance: ToolbarPluginBase
    ): void {
        this._toolbar_plugins[toolbar_plugin_instance.id()] =
            toolbar_plugin_instance;
    }

    update_toolbar_plugins(): void {
        const plugin_ids = Object.keys(this._toolbar_plugins);
        plugin_ids.sort((a: string, b: string) => {
            return this._toolbar_plugins[a].sort_index <
                this._toolbar_plugins[b].sort_index
                ? -1
                : 1;
        });

        plugin_ids.forEach(plugin_id => {
            const plugin = this._toolbar_plugins[plugin_id];
            if (!plugin.content_selection) {
                const content_selection = this._plugin_contents_selection
                    .append("div")
                    .attr("id", plugin_id);
                if (plugin.has_toggle_button()) {
                    const button_selection = this._plugin_buttons_selection
                        .append("div")
                        .attr("id", "togglebutton_" + plugin_id)
                        .classed("togglebutton", true)
                        .classed("noselect", true)
                        .classed("on", true)
                        .classed("down", !plugin.active)
                        .classed("up", plugin.active)
                        .on("click", () => this.toggle_plugin(plugin));
                    plugin.render_togglebutton(button_selection);
                }
                plugin.setup_selections(content_selection);
            }
            this.set_plugin_state(plugin, plugin.active);
        });
    }

    toggle_plugin(plugin: ToolbarPluginBase): void {
        this.set_plugin_state(plugin, !plugin.active);
    }

    set_plugin_state(plugin: ToolbarPluginBase, is_active: boolean): void {
        const plugin_button = this._plugin_buttons_selection.select(
            "#togglebutton_" + plugin.id()
        );
        plugin_button.classed("up", !is_active);
        plugin_button.classed("down", is_active);
        if (is_active == true) {
            plugin.enable();
            plugin.render_content();
        } else {
            plugin.disable();
        }
    }

    get_plugin(plugin_id: string): ToolbarPluginBase {
        return this._toolbar_plugins[plugin_id];
    }
}
