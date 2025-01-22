/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import {select} from "d3";

import {get} from "./texts";
import type {
    d3SelectionDiv,
    NodevisWorld,
    SearchResultEntry,
} from "./type_defs";
import {SearchResults} from "./type_defs";
import {DefaultTransition} from "./utils";

export class SearchNodes {
    _world: NodevisWorld;
    _search_node_text = "";
    _search_result_panel: SearchResultPanel;
    constructor(world: NodevisWorld, search_result_selection: d3SelectionDiv) {
        this._world = world;
        this._setup_search_panel();
        this._search_result_panel = new SearchResultPanel(
            world,
            search_result_selection,
        );
    }

    _setup_search_panel(): void {
        const search_nodes_cell = select("table#page_menu_bar tr")
            .selectAll("td.inpage_search.node_vis")
            .data([null])
            .enter()
            .insert("td", "td.shortcuts")
            .classed("inpage_search node_vis", true);
        const input = search_nodes_cell
            .append("input")
            .on("input", event =>
                this.updated_search_node_text(event.target!.value),
            )
            .attr("type", "text")
            .attr("placeholder", "Find on this page...")
            .attr("value", this._search_node_text);
        search_nodes_cell
            .append("input")
            .attr("type", "button")
            .property("value", "X")
            .on("click", () => {
                input.property("value", "");
                this.updated_search_node_text("");
            });
    }

    updated_search_node_text(value: string): void {
        this.set_search_node_text(value);
        this.start_node_search();
    }

    set_search_node_text(text: string): void {
        this._search_node_text = text;
    }

    start_node_search(): void {
        if (this._search_node_text == "") {
            this._search_result_panel.feed_data(new SearchResults());
            return;
        }

        const entries: SearchResultEntry[] = [];
        const search_node_text_lower = this._search_node_text
            .trim()
            .toLowerCase();
        this._world.viewport.get_all_nodes().forEach(node => {
            if (
                !node.data.invisible &&
                node.data.name.toLowerCase().search(search_node_text_lower) !=
                    -1
            ) {
                entries.push({name: node.data.name, state: node.data.state});
            }
        });

        const data: SearchResults = {
            type: "node",
            entries: entries,
        };
        this._search_result_panel.feed_data(data);
    }
}
export class SearchResultPanel {
    _world: NodevisWorld;
    _search_result_selection: d3SelectionDiv;
    _content_selection: d3SelectionDiv;
    _formatters: InfoboxNodeFormatter[];

    constructor(world: NodevisWorld, search_result_selection: d3SelectionDiv) {
        this._world = world;
        search_result_selection
            .attr("id", "infobox")
            .classed("box", true)
            .style("display", "none");
        this._search_result_selection = search_result_selection;
        this._content_selection = this._search_result_selection
            .append("div")
            .attr("id", "content");
        this._formatters = [];
        this._setup_formatters();
    }

    _setup_formatters(): void {
        this._formatters.push(new InfoboxNodeFormatter(this._world));
    }

    feed_data(data: SearchResults): void {
        if (data.entries.length == 0) {
            this._search_result_selection.style("display", "none");
            return;
        }

        if (this._search_result_selection.style("display") == "none") {
            this._search_result_selection.style("display", null);
            DefaultTransition.add_transition(
                this._search_result_selection.style("opacity", "0"),
            ).style("opacity", "1");
        }

        // Clear infobox
        const old_height = this._content_selection.style("height");
        this._content_selection.selectAll("*").remove();

        const formatter = this._find_formatter(data);
        if (formatter) {
            this._content_selection.style("height", null);
            formatter.render_into_selection(this._content_selection, data);
            const new_height = this._content_selection.style("height");
            DefaultTransition.add_transition(
                this._content_selection.style("height", old_height),
            ).style("height", new_height);
        }
    }

    _find_formatter(data: SearchResults): InfoboxNodeFormatter | void {
        for (const idx in this._formatters) {
            const formatter = this._formatters[idx];
            if (formatter.supports_data(data)) return formatter;
        }
    }
}

class InfoboxNodeFormatter {
    _world: NodevisWorld;

    constructor(world: NodevisWorld) {
        this._world = world;
    }

    supports_data(data: any): boolean {
        if (data) return true;
        return false;
    }

    render_into_selection(
        selection: d3SelectionDiv,
        data: SearchResults,
    ): void {
        let entries = data.entries;

        const heading_info = get("matching_nodes");
        selection.append("label").text(heading_info);

        const current_height = this._world.viewport.get_size().height;
        const max_entries: number = Math.floor(
            Math.max((current_height / 24 / 10) * 10, 10),
        );
        if (entries.length > max_entries) {
            selection.append("br");
            selection
                .append("label")
                .text(
                    "(" +
                        max_entries +
                        " of " +
                        entries.length +
                        " matches shown)",
                );
        }

        entries = entries.slice(0, max_entries);
        const table = selection.append("table").attr("id", "rows");
        table
            .selectAll("tr")
            .data(entries)
            .enter()
            .append("tr")
            .append("td")
            .classed("noselect", true)
            .classed("infobox_entry", true)
            .text(d => d.name)
            .each(function (d) {
                select(this).classed("state" + d.state, true);
            })
            .on("click", (_event: Event, d) => this._zoom_node(d.name))
            .on("mouseover", (_event: Event, d) =>
                this._highlight_node(d.name, true),
            )
            .on("mouseout", (_event: Event, d) =>
                this._highlight_node(d.name, false),
            );
    }

    _highlight_node(node_id: string, highlight: boolean): void {
        const all_nodes = this._world.viewport.get_all_nodes();
        all_nodes.forEach(node => {
            const gui_node = this._world.viewport
                .get_nodes_layer()
                .get_node_by_id(node.data.id);
            if (!gui_node._selection) return;
            gui_node
                .selection()
                .classed("focus", highlight && node.data.name == node_id);
        });
    }

    _zoom_node(node_id: string): void {
        const all_nodes = this._world.viewport.get_all_nodes();
        all_nodes.forEach(node => {
            if (node.data.name == node_id) {
                this._world.viewport.zoom_to_coords(-node.x, -node.y);
                return;
            }
        });
    }
}
