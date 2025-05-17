/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import type {Dimension} from "crossfilter2";
import crossfilter from "crossfilter2";
import {BaseType, Selection} from "d3";
import {select as d3select} from "d3";
import $ from "jquery";

import {FigureBase} from "@/modules/figures/cmk_figures";
import type {FigureData} from "@/modules/figures/figure_types";

import {ifid_dep} from "./ntop_utils";

interface FilterChoices {
    applications: any[];
    categories: any[];
    protocols: any[];
}

export interface FlowData {
    url_key: string;
    url_ndpi: string;
    protocol: any;
    url_client: string;
    url_server: string;
    duration: string;
    score: string;
    breakdown: string;
    throughput: string;
    bytes: string;
}
export interface FlowDashletDataChoice {
    group: string;
    url_param: string;
    choices: Choice[];
}

export interface NtopColumn<Data = any> {
    label: string;
    format: (d: Data) => string;
    classes: string[];
}

export interface Choice {
    id: string;
    name: string;
}

//FlowDashletData in python is not related at all to FigureData
//it has no data or plot_definition but to keep the structure
//in ts I had to extend it.
interface FlowDashletData extends FigureData {
    flows: FlowData;
    filter_choices: FlowDashletDataChoice[];
}

export class FlowsDashlet extends FigureBase<FlowDashletData> {
    _default_params_dict;
    _dimension!: Dimension<any, any>;
    _filter_choices!: FilterChoices | FlowDashletDataChoice[];
    url_param = "";
    _ifid!: string;
    _vlanid!: string;
    _pagination!: Selection<HTMLDivElement, any, BaseType, any>;
    _table_div!: Selection<HTMLDivElement, any, BaseType, any>;
    _indexDim!: Dimension<any, any>;
    constructor(div_selector: string) {
        super(div_selector);
        this._post_url = "ajax_ntop_flows.py";
        this._default_params_dict = {};
    }

    override initialize() {
        this._div_selection.classed("ntop_flows", true);
        this._crossfilter = crossfilter();
        this._dimension = this._crossfilter.dimension(d => d);
        this._indexDim = this._crossfilter.dimension(d => d.index);

        const url_params = new URLSearchParams(this._default_params_dict);
        this._post_body = url_params.toString();
        this._filter_choices = {
            applications: [],
            categories: [],
            protocols: [],
        };
        this._setup_fetch_filters();
        this._setup_data_update();
        this._div_selection.classed(ifid_dep, true);
        this._pagination = this._div_selection
            .append("div")
            .attr("id", "table_pagination");
        this._table_div = this._div_selection
            .append("div")
            .attr("id", "table_div");
    }

    getEmptyData() {
        return {} as FlowDashletData;
    }

    set_ids(ifid: string, vlanid: string) {
        this._ifid = ifid;
        this._vlanid = vlanid;
        this._update_post_body_and_force_update();
    }

    _update_css_classes() {
        // Update CSS classes for the table
        // Reason: The backend provides some prerendered HTML and we need to modify it further
        this._div_selection.selectAll("a").classed("ntop_link", true);
        const progress_bar = this._div_selection
            .selectAll("tr")
            .selectAll("div.progress")
            .classed("progress", false)
            .classed("breakdown_bar", true);
        progress_bar
            .select("div.bg-warning")
            .classed("progress-bar", false)
            .classed("bg-warning", false)
            .classed("bytes_sent", true);
        progress_bar
            .select("div.bg-info")
            .classed("progress-bar", false)
            .classed("bg-info", false)
            .classed("bytes_rcvd", true);
    }

    _setup_data_update() {
        this.set_post_url_and_body(this._post_url, this._post_body);
        this.scheduler.enable();
        this.scheduler.set_update_interval(600);
    }

    _update_filter_choices(filter_choices: FlowDashletDataChoice[]) {
        this._filter_choices = filter_choices;
        this._setup_fetch_filters();
    }

    _setup_fetch_filters() {
        const filter_divs = this._div_selection
            .selectAll("div.filters")
            .data([null])
            .join("div")
            .style("padding-top", "10px")
            .classed("filters", true);

        const filter_div = filter_divs
            .selectAll("div.filter")
            // @ts-ignore
            .data(this._filter_choices)
            .join(enter =>
                enter
                    .append("div")
                    .attr("class", d => d.group.toLowerCase())
                    .classed("filter", true),
            );

        filter_div
            .selectAll("label")
            .data(d => [d])
            .join("label")
            .text(d => d.group);
        const select = filter_div
            .selectAll("select")
            .data(d => [d])
            .join("select")
            .attr("url_param", d => d.url_param)
            .attr("class", "filter select2-enable");

        select
            .selectAll("option")
            .data(
                d => d.choices,
                // @ts-ignore
                d => d.id,
            )
            .join(enter =>
                enter.append("option").property("value", d => "" + d.id),
            )
            .text(d => d.name);

        const elements = $("div.filters").find(".select2-enable");
        const select2 = elements.select2({
            dropdownAutoWidth: true,
            minimumResultsForSearch: 5,
        });
        select2.on("select2:select", () => {
            this._update_post_body_and_force_update();
        });
    }

    _update_post_body_and_force_update() {
        // add default parameters
        let params = Object.assign({}, this._default_params_dict, {
            ifid: this._ifid,
            vlanid: this._vlanid,
        });
        // add filter parameters
        this._div_selection
            .selectAll<HTMLSelectElement, FlowsDashlet>("select.filter")
            .each((_d, idx, nodes) => {
                const select = d3select<HTMLSelectElement, FlowsDashlet>(
                    nodes[idx],
                );
                const key = select.datum().url_param;
                const value = select.property("value");
                if (value == -1) return;
                params = Object.assign(params, {[key]: value});
            });
        const url_params = new URLSearchParams(params);
        this.show_loading_image();
        this._post_body = url_params.toString();
        this._setup_data_update();
        this.scheduler.force_update();
    }

    override update_data(data: FlowDashletData) {
        // Remove old data
        this._crossfilter.remove(() => true);

        // Add new data
        // @ts-ignore
        const data_with_index = data.flows.map((d, i) => ({...d, index: i}));
        this._crossfilter.add(data_with_index);

        // Update filters
        this._update_filter_choices(data.filter_choices);

        // Update table
        //TODO: this is a data typing problem see cmk_figures.ts
        // this type is unexpected which might lead to typing errors
        //@ts-ignore
        this._render_table();
    }

    _render_table_pagination() {
        const entries = 20;

        const new_row = this._pagination
            .selectAll("table")
            .data([null])
            .enter()
            .append("table")
            .style("width", "260px")
            .style("margin", "10px")
            .style("margin-left", "auto")
            .style("margin-right", "0px")
            .append("tr");
        const current_pagination = new_row
            .append("td")
            .classed("pagination_info", true)
            .style("width", "160px")
            .style("text-align", "right")
            .attr("offset", 0);
        [
            ["<<", 0],
            ["<", -entries],
            [">", entries],
            [">>", Infinity],
        ].forEach(entry => {
            const [text, offset] = entry;
            new_row
                .append("td")
                .classed("navigation noselect", true)
                .style("cursor", "pointer")
                .on("mouseover", (event: MouseEvent) => {
                    d3select(event.target! as HTMLElement).style(
                        "background",
                        "#9c9c9c",
                    );
                })
                .on("mouseout", (event: MouseEvent) => {
                    d3select(event.target! as HTMLElement).style(
                        "background",
                        null,
                    );
                })
                .text(text)
                .attr("offset", offset)
                .on("click", (event: MouseEvent) => {
                    const old_offset = parseInt(
                        current_pagination.attr("offset"),
                    );
                    const delta = d3select(event.target! as HTMLElement).attr(
                        "offset",
                    );
                    var [from, to] = [0, 0];

                    const total_entries = this._crossfilter.all().length;

                    if (delta == "Infinity") {
                        from = Math.floor(total_entries / entries) * entries;
                        to = total_entries;
                    } else {
                        const num_delta = parseInt(delta);
                        if (num_delta == 0) {
                            from = 0;
                            to = entries;
                        } else {
                            from = old_offset + num_delta;
                            if (from < 0) from = 0;
                            if (from > total_entries) from = old_offset;
                            to = from + entries;
                        }
                    }
                    if (to > total_entries) {
                        to = total_entries;
                    }

                    this._indexDim.filterRange([from, to]);
                    current_pagination.attr("offset", from);
                    this._update_pagination_text(current_pagination);
                    this._render_table();
                });
        });
        this._update_pagination_text(current_pagination);
    }

    _update_pagination_text(
        current_pagination: Selection<HTMLTableCellElement, any, BaseType, any>,
    ) {
        if (current_pagination.empty()) return;
        const offset = parseInt(current_pagination.attr("offset"));
        const total_entries = this._crossfilter.all().length;
        const to = Math.min(offset + 20, total_entries);
        current_pagination.text(`${offset} - ${to} of ${total_entries}`);
    }

    _render_table() {
        this._render_table_pagination();
        const table = this._table_div
            .selectAll("table")
            .data([this._crossfilter.allFiltered()])
            .join("table");

        interface Entry {
            header: string;
            ident: string;
            html_field: keyof FlowData | null;
            field_name: keyof FlowData | null;
        }

        const entries: Entry[] = [
            {
                header: "",
                ident: "info",
                html_field: "url_key",
                field_name: null,
            },
            {
                header: "Application",
                ident: "application",
                html_field: "url_ndpi",
                field_name: null,
            },
            {
                header: "Protocol",
                ident: "protocol",
                html_field: null,
                field_name: "protocol",
            },
            {
                header: "Client",
                ident: "url_client",
                html_field: "url_client",
                field_name: null,
            },
            {
                header: "Server",
                ident: "url_server",
                html_field: "url_server",
                field_name: null,
            },
            {
                header: "Duration",
                ident: "duration",
                html_field: null,
                field_name: "duration",
            },
            {
                header: "Score",
                ident: "score",
                html_field: null,
                field_name: "score",
            },
            {
                header: "Breakdown",
                ident: "breakdown",
                html_field: "breakdown",
                field_name: null,
            },
            {
                header: "Actual Thpt",
                ident: "throughput",
                html_field: null,
                field_name: "throughput",
            },
            {
                header: "Total Bytes",
                ident: "bytes",
                html_field: null,
                field_name: "bytes",
            },
        ];

        // Headers, only once
        table
            .selectAll("thead")
            .data([entries])
            .enter()
            .append("thead")
            .append("tr")
            .selectAll("th")
            .data(d => d)
            .join("th")
            .text(d => d.header);

        // Rows
        const rows = table
            .selectAll("tbody")
            .data(d => [d])
            .join("tbody")
            .selectAll("tr")
            .data(d => d)
            .join("tr")
            .attr("class", "table_row");

        entries.forEach(entry => {
            const cell = rows
                .selectAll<HTMLTableCellElement, FlowData>(`td.${entry.ident}`)
                .data(d => [d])
                .join("td")
                .classed(entry.ident, true);
            const html_field = entry.html_field;
            if (html_field !== null) {
                cell.html(d => d[html_field]);
            }

            const field_name = entry.field_name;
            if (field_name !== null) cell.text(d => d[field_name]);
        });

        this._update_css_classes();
    }
}
