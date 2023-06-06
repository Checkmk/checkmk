/**
 * Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import * as cmk_figures from "cmk_figures";
import { BaseType } from "d3";
import * as d3 from "d3";
import * as d3Hexbin from "d3-hexbin";

interface FigurePart {
    count: number;
    css_class: string;
    title: string;
    url: string;
}
interface FigureResponseData extends cmk_figures.FigureData {
    title: string;
    title_url: string;
    parts: FigurePart[];
    total: FigurePart;
}

interface HexConfig {
    title: string;
    path: string;
    css_class: string;
    tooltip: string;
    count: number;
}

export class HostStats extends cmk_figures.FigureBase<FigureResponseData> {
    _table_div!: d3.Selection<HTMLDivElement, any, BaseType, any>;
    _hexagon_box!: d3.Selection<SVGGElement, unknown, BaseType, unknown>;
    _max_radius!: number;
    _title!: string;
    _title_url!: string;
    ident() {
        return "hoststats";
    }

    getEmptyData(): FigureResponseData {
        return {
            title: "",
            title_url: "",
            data: [],
            plot_definitions: [],
            total: {count: 0, css_class: "", title: "", url: ""},
            parts: [],
        };
    }

    initialize(debug?: boolean) {
        super.initialize(debug);

        this._div_selection.classed("stats_dashlet", true);
        this._table_div = this._div_selection
            .append("div")
            .classed("stats_table", true);
        this.svg = this._div_selection.append("svg");
        // NOTE: for IE11 support we set the attribute here and do not use a CSS class
        this._hexagon_box = this.svg
            .append("g")
            .attr("transform", "translate(60, 95)");
        this._max_radius = 48;
    }

    update_data(data: FigureResponseData) {
        this._title = data.title;
        this._title_url = data.title_url;
        //This assignment changes the type of our Data so it not FigureData but FigureData.Data
        //It's difficult to have a workaround for this...
        this._data = data.data;
    }

    update_gui() {
        if (!this._data || this._data.total.count == 0) return;

        this.resize();
        const parts = this._data.parts;
        const hexbin = d3Hexbin.hexbin();
        const hexagon_config: HexConfig[] = [];

        let largest_element_count = 0;
        for (const element of this._data.parts) {
            if (element.count > largest_element_count)
                largest_element_count = element.count;
        }

        if (this._data.total.count == 0) {
            hexagon_config.push({
                title: "",
                path: hexbin.hexagon(this._max_radius),
                css_class: "empty",
                tooltip: "",
                count: 0,
            });
        } else {
            let sum = this._data.total.count;
            let radius = 0;
            parts.forEach(part => {
                radius =
                    part.count == 0
                        ? 0
                        : (Math.pow(sum, 0.33) /
                              Math.pow(this._data.total.count, 0.33)) *
                          this._max_radius;
                sum -= part.count;

                hexagon_config.push({
                    title: part.title,
                    path: hexbin.hexagon(radius),
                    css_class: part.css_class,
                    tooltip: "",
                    count: part.count,
                });
            });
        }

        // render all hexagons
        this._hexagon_box
            .selectAll("path.hexagon")
            .data(hexagon_config)
            .join(enter => enter.append("path"))
            .attr("d", d => d.path)
            .attr("class", d => "hexagon " + d.css_class);

        // render table
        const table = this._table_div
            .selectAll("table")
            .data([parts.concat(this._data.total)])
            .join("table");
        const rows = table
            .selectAll("tr")
            .data(d => d)
            .join("tr");

        const a = rows.selectAll("td a").data(d => [
            { // count
                text: d.count,
                url: d.url,
                css_class: "count " + d.css_class,
            },
            { // state color
                text: "",
                url: d.url,
                css_class: "box " + d.css_class,
            },
            { // text (state title)
                text: d.title,
                url: d.url,
                css_class: "text",
            },
        ]);
        a.join(enter => enter.append("td").append("a"))
            .attr("class", d => d.css_class)
            .text(d => d.text)
            .attr("href", d => d.url);

        this.render_title(this._title, this._title_url);
    }
}

export class ServiceStats extends HostStats {
    ident() {
        return "servicestats";
    }
}

export class EventStats extends HostStats {
    ident() {
        return "eventstats";
    }
}

cmk_figures.figure_registry.register(HostStats);
cmk_figures.figure_registry.register(ServiceStats);
cmk_figures.figure_registry.register(EventStats);
