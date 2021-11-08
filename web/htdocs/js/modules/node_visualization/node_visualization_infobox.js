// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

import * as d3 from "d3";
import * as node_visualization_datasources from "node_visualization_datasources";
import * as node_visualization_utils from "node_visualization_utils";

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
    constructor(main_instance, selection) {
        this.main_instance = main_instance;
        selection.attr("id", "infobox").classed("box", true).style("display", "none");
        this._selection = selection;

        this._content_selection = this._selection.append("div").attr("id", "content");

        this._formatters = [];
        this._setup_formatters();
    }

    _setup_formatters() {
        this._formatters.push(new InfoboxNodeFormatter(this.main_instance));
    }

    feed_data(data) {
        if (data.entries.length == 0) {
            this._selection.style("display", "none");
            return;
        }

        if (this._selection.style("display") == "none") {
            this._selection.style("display", null);
            node_visualization_utils.DefaultTransition.add_transition(
                this._selection.style("opacity", "0")
            ).style("opacity", "1");
        }

        // Clear infobox
        let old_height = this._content_selection.style("height");
        this._content_selection.selectAll("*").remove();

        let formatter = this._find_formatter(data);
        if (formatter) {
            this._content_selection.style("height", null);
            formatter.render_into_selection(this._content_selection, data);
            let new_height = this._content_selection.style("height");
            node_visualization_utils.DefaultTransition.add_transition(
                this._content_selection.style("height", old_height)
            ).style("height", new_height);
        }
    }

    _find_formatter(data) {
        for (let idx in this._formatters) {
            let formatter = this._formatters[idx];
            if (formatter.supports_data(data)) return formatter;
        }
    }
}

class AbstractInfoboxFormatter {
    constructor(main_instance) {
        this.main_instance = main_instance;
    }

    supports_data(data) {
        return false;
    }

    render_into_selection(selection) {}
}

class InfoboxNodeFormatter extends AbstractInfoboxFormatter {
    supports_data(data) {
        return true;
    }

    render_into_selection(selection, data) {
        let entries = data.entries;

        let heading_info = "Matching nodes";
        selection.append("label").text(heading_info);

        // TODO: improve formula to determine max vertical space
        let max_entries =
            parseInt(this.main_instance.viewport.current_viewport.height / 24 / 10) * 10;
        max_entries = Math.max(max_entries, 10);
        if (entries.length > max_entries) {
            selection.append("br");
            selection
                .append("label")
                .text("(" + max_entries + " of " + entries.length + " matches shown)");
        }

        entries = entries.slice(0, max_entries);
        let table = selection.append("table").attr("id", "rows");
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

    _highlight_node(node_id, highlight) {
        this.main_instance.viewport.current_viewport.get_all_nodes().forEach(node => {
            node.selection.classed("focus", node.data.name == node_id);
        });
    }

    _zoom_node(node_id) {
        this.main_instance.viewport.current_viewport.get_all_nodes().forEach(node => {
            if (node.data.name == node_id) {
                node_visualization_utils.DefaultTransition.add_transition(
                    this.main_instance.viewport.current_viewport.svg_content_selection
                ).call(this.main_instance.viewport.current_viewport.main_zoom.transform, () =>
                    this._transform(node)
                );
                return;
            }
        });
    }

    _transform(node) {
        return d3.zoomIdentity
            .translate(
                this.main_instance.viewport.current_viewport.width / 2,
                this.main_instance.viewport.current_viewport.height / 2
            )
            .scale(this.main_instance.viewport.current_viewport.last_zoom.k)
            .translate(-node.x, -node.y);
    }
}
