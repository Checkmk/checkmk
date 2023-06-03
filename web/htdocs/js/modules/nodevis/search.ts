// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

import {
    NodevisWorld,
    SearchResultEntry,
    SearchResults,
} from "nodevis/type_defs";

import {ToolbarPluginBase} from "./toolbar_utils";

export class SearchAggregationsPlugin extends ToolbarPluginBase {
    _search_node_text = "";

    static instantiate(world: NodevisWorld) {
        return new SearchAggregationsPlugin(world, "Search aggregations");
    }

    id() {
        return "bi_search_aggregations";
    }

    has_toggle_button(): boolean {
        return false;
    }

    render_content(): void {
        if (this._div_selection == null) return;

        this._div_selection
            .selectAll(".toolbar_search")
            .data([null])
            .enter()
            .append("div")
            .classed("box", true)
            .classed("toolbar_search", true)
            .append("input")
            .on("input", event => this.updated_search_node_text(event))
            .classed("search_node", true)
            .attr("placeholder", "Search node")
            .attr("value", this._search_node_text);
    }

    updated_search_node_text(event: InputEvent): void {
        const target = event.target;
        if (target == null) return;
        // @ts-ignore
        this.set_search_node_text(target.value);
        this.start_node_search();
    }

    set_search_node_text(text: string): void {
        this._search_node_text = text;
    }

    start_node_search(): void {
        if (this._search_node_text == "") {
            this._world.infobox.feed_data(new SearchResults());
            return;
        }

        const entries: SearchResultEntry[] = [];
        const search_node_text_lower = this._search_node_text
            .trim()
            .toLowerCase();
        this._world.viewport.get_all_nodes().forEach(node => {
            if (
                node.data.name.toLowerCase().search(search_node_text_lower) !=
                -1
            ) {
                entries.push({name: node.data.name, state: node.data.state});
            }
        });

        const data: SearchResults = {
            datasource: this.id(),
            type: "node",
            entries: entries,
        };
        this._world.infobox.feed_data(data);
    }
}
