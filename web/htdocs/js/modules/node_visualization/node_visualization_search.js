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

import * as d3 from "d3"
import * as node_visualization_toolbar_utils from "node_visualization_toolbar_utils"


export class SearchAggregationsPlugin extends node_visualization_toolbar_utils.ToolbarPluginBase {
    id() {
        return "bi_search_aggregations"
    }

    constructor(main_instance) {
        super("Search aggr", main_instance)
        this.search_node_text = ""
        this.active = true
    }

    has_toggle_button() {
        return false
    }

    render_content() {
        this.content_selection.selectAll(".toolbar_search").data([null]).enter().append("div")
                .classed("box", true)
                .classed("toolbar_search", true)
                .append("input").on("input", () => this.updated_search_node_text())
                      .classed("search_node", true)
                      .attr("placeholder", "Search node")
                      .attr("value", this.search_node_text);
    }

    updated_search_node_text() {
        this.set_search_node_text(d3.select(d3.event.target).property("value"))
        this.start_node_search()
    }

    set_search_node_text(text) {
        this.search_node_text = text
    }

    start_node_search() {
        if (this.search_node_text == "") {
            this.main_instance.infobox.feed_data([])
            return
        }

        let results = []
        let search_node_text_lower = this.search_node_text.trim().toLowerCase()
        this.main_instance.viewport.current_viewport.get_all_nodes().forEach(node=>{
            if (node.data.name.toLowerCase().search(search_node_text_lower) != -1) {
                results.push({"name": node.data.name, "state": node.data.state})
            }
        })

        let data = []
        data.datasource = this.id()
        data.type = "node"
        data.entries = results
        this.main_instance.infobox.feed_data(data)
    }
}

