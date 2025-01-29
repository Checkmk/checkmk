/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import type {Dimension} from "crossfilter2";
import crossfilter from "crossfilter2";
import type {BaseType, Selection} from "d3";
import {select as d3select} from "d3";
import type {DataTableWidget} from "dc";
import $ from "jquery";

import {DCTableFigure} from "@/modules/figures/cmk_dc_table";
import {FigureBase} from "@/modules/figures/cmk_figures";
import type {FigureData} from "@/modules/figures/figure_types";

import {
    add_classes_to_trs,
    add_columns_classes_to_nodes,
    ifid_dep,
} from "./ntop_utils";

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
    _dc_table!: DCTableFigure<FlowDashletData>;
    constructor(div_selector: string) {
        super(div_selector);
        this._post_url = "ajax_ntop_flows.py";
        this._default_params_dict = {};
    }

    override initialize() {
        this._div_selection.classed("ntop_flows", true);
        this._crossfilter = crossfilter();
        this._dimension = this._crossfilter.dimension(d => d);

        const url_params = new URLSearchParams(this._default_params_dict);
        this._post_body = url_params.toString();
        this._filter_choices = {
            applications: [],
            categories: [],
            protocols: [],
        };
        this._setup_dc_table(this._div_selection);
        this._setup_data_update();
        this._div_selection.classed(ifid_dep, true);
    }

    getEmptyData() {
        return {} as FlowDashletData;
    }

    set_ids(ifid: string, vlanid: string) {
        this._ifid = ifid;
        this._vlanid = vlanid;
        this._update_post_body_and_force_update();
    }

    _setup_dc_table(
        selection: Selection<HTMLDivElement, unknown, BaseType, unknown>,
    ) {
        const div_id = "flows_dashlet";
        selection.append("div").attr("id", div_id);

        this._dc_table = new DCTableFigure("#" + div_id, "flows");

        // WIP: add as first element before paging
        this._setup_fetch_filters();
        this._dc_table.crossfilter(this._crossfilter);
        this._dc_table.dimension(this._dimension);
        this._dc_table.columns(this._get_columns());
        this._dc_table.sort_by(d => d.date);
        this._dc_table.initialize();
        this._dc_table
            .get_dc_chart()
            .on("renderlet", chart => this._update_css_classes(chart));
        this._dc_table.subscribe_post_render_hook(() => {
            this.remove_loading_image();
        });
    }

    _update_css_classes(chart: DataTableWidget) {
        add_classes_to_trs(chart);

        const div_bar = chart
            .selectAll("tr")
            .selectAll("div.progress")
            .classed("progress", false)
            .classed("breakdown_bar", true);
        div_bar
            .select("div.bg-warning")
            .classed("progress-bar", false)
            .classed("bg-warning", false)
            .classed("bytes_sent", true);
        div_bar
            .select("div.bg-info")
            .classed("progress-bar", false)
            .classed("bg-info", false)
            .classed("bytes_rcvd", true);

        add_columns_classes_to_nodes(chart, this._get_columns());
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
        const filter_divs = this._dc_table._div_options
            .selectAll("div.filters")
            .data([null])
            .join("div")
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

    _get_columns(): NtopColumn[] {
        return [
            {
                label: "",
                format: (d: FlowData) => d.url_key,
                classes: ["key"],
            },
            {
                label: "Application",
                format: (d: FlowData) => d.url_ndpi,
                classes: ["application"],
            },
            {
                label: "Protocol",
                format: (d: FlowData) => d.protocol,
                classes: ["protocol"],
            },
            {
                label: "Client",
                format: (d: FlowData) => d.url_client,
                classes: ["client"],
            },
            {
                label: "Server",
                format: (d: FlowData) => d.url_server,
                classes: ["server"],
            },
            {
                label: "Duration",
                format: (d: FlowData) => d.duration,
                classes: ["duration", "number"],
            },
            {
                label: "Score",
                format: (d: FlowData) => d.score,
                classes: ["score", "number"],
            },
            {
                label: "Breakdown",
                format: (d: FlowData) => d.breakdown,
                classes: ["breakdown"],
            },
            {
                label: "Actual Thpt",
                format: (d: FlowData) => d.throughput,
                classes: ["throughput", "number"],
            },
            {
                label: "Total Bytes",
                format: (d: FlowData) => d.bytes,
                classes: ["bytes", "number"],
            },
        ];
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
        this._crossfilter.add(data.flows);

        // Update filters
        this._update_filter_choices(data.filter_choices);

        // Update table
        //TODO: this is a data typing problem see cmk_figures.ts
        // this type is unexpected which might lead to typing errors
        //@ts-ignore
        this._dc_table.process_data(data.flows);
    }
}
