// Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

import * as d3 from "d3";
import {d3SelectionDiv, NodevisWorld, SearchResults} from "nodevis/type_defs";
import {DefaultTransition} from "nodevis/utils";

//.
//   .-InfoBox------------------------------------------------------------.
//   |                 ___        __       ____                           |
//   |                |_ _|_ __  / _| ___ | __ )  _____  __               |
//   |                 | || '_ \| |_ / _ \|  _ \ / _ \ \/ /               |
//   |                 | || | | |  _| (_) | |_) | (_) >  <                |
//   |                |___|_| |_|_|  \___/|____/ \___/_/\_\               |
//   |                                                                    |
//   +--------------------------------------------------------------------+

export class InfoBox {
    _div_selection: d3SelectionDiv;
    _content_selection: d3SelectionDiv;
    _formatters: InfoboxNodeFormatter[];
    _world: NodevisWorld;

    constructor(world: NodevisWorld, selection: d3SelectionDiv) {
        this._world = world;
        selection
            .attr("id", "infobox")
            .classed("box", true)
            .style("display", "none");
        this._div_selection = selection;
        this._content_selection = this._div_selection
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
            this._div_selection.style("display", "none");
            return;
        }

        if (this._div_selection.style("display") == "none") {
            this._div_selection.style("display", null);
            DefaultTransition.add_transition(
                this._div_selection.style("opacity", "0")
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
                this._content_selection.style("height", old_height)
            ).style("height", new_height);
        }
    }

    _find_formatter(data): InfoboxNodeFormatter | void {
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
        data: SearchResults
    ): void {
        let entries = data.entries;

        const heading_info = "Matching nodes";
        selection.append("label").text(heading_info);

        // TODO: improve formula to determine max vertical space
        const current_height = this._world.viewport.height;
        const max_entries: number = Math.max(
            (current_height / 24 / 10) * 10,
            10
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
                        " matches shown)"
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
                d3.select(this).classed("state" + d.state, true);
            })
            .on("click", (event, d) => this._zoom_node(d.name))
            .on("mouseover", (event, d) => this._highlight_node(d.name, true))
            .on("mouseout", (event, d) => this._highlight_node(d.name, false));
    }

    _highlight_node(node_id: string, highlight: boolean): void {
        this._world.viewport.get_all_nodes().forEach(node => {
            node.data.selection.classed(
                "focus",
                highlight && node.data.name == node_id
            );
        });
    }

    _zoom_node(node_id: string): void {
        this._world.viewport.get_all_nodes().forEach(node => {
            if (node.data.name == node_id) {
                this._world.viewport.zoom_to_coords(-node.x, -node.y);
                return;
            }
        });
    }
}
