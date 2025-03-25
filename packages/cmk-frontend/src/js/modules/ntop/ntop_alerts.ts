/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import crossfilter from "crossfilter2";
import type {BaseType, Selection} from "d3";
import {
    scaleLinear,
    scaleTime,
    select,
    selectAll,
    timeDay,
    timeDays,
    timeFormat,
} from "d3";
import type {DataTableWidget} from "dc";
import {barChart, redrawAll} from "dc";
import $ from "jquery";

import {DCTableFigure} from "@/modules/figures/cmk_dc_table";
import {FigureBase} from "@/modules/figures/cmk_figures";
import {Tab, TabsBar} from "@/modules/figures/cmk_tabs";
import type {FigureData} from "@/modules/figures/figure_types";
import {
    fmt_number_with_precision,
    SIUnitPrefixes,
} from "@/modules/number_format";

import type {FlowDashletDataChoice, NtopColumn} from "./ntop_flows";
import {
    add_classes_to_trs,
    add_columns_classes_to_nodes,
    ifid_dep,
    seconds_to_time,
} from "./ntop_utils";

export class NtopAlertsTabBar extends TabsBar {
    constructor(div_selector: string) {
        super(div_selector);
    }

    override _get_tab_entries() {
        return [EngagedAlertsTab, PastAlertsTab, FlowAlertsTab];
    }

    //TODO: this method is overwritten in the subclasses of TabsBar but doesn't
    // always have a matching signature which leads to a TS2416 error so it might
    // be necessary to create a consistent signature or find another solution
    // @ts-ignore
    initialize(ifid: string) {
        TabsBar.prototype.initialize.call(this);
        this._activate_tab(this.get_tab_by_id("engaged_alerts_tab"));
        selectAll<any, ABCAlertsPage>("." + ifid_dep)
            .data()
            .forEach(o => o.set_ids(ifid));
    }

    _show_error_info(error_info: string) {
        console.log("data fetch error " + error_info);
    }
}

type ABCAlertsFilteredChoices = FlowDashletDataChoice;
type ABCAlertsTimeSeries = [string, number][];

interface ABCAlertsPageData extends FigureData {
    ntop_link: string;
    alerts: Alert[];
    filter_choices: ABCAlertsFilteredChoices[];
    time_series: ABCAlertsTimeSeries;
    number_of_alerts: number;
}

// Base class for all alert tables
abstract class ABCAlertsPage extends FigureBase<ABCAlertsPageData> {
    _filter_choices: ABCAlertsFilteredChoices[];
    _crossfilter_time!: crossfilter.Crossfilter<any>;
    _date_dimension!: crossfilter.Dimension<any, any>;
    _hour_dimension!: crossfilter.Dimension<any, any>;
    _table_details!: DCTableFigure<ABCAlertsPageData>;
    _ifid!: string | null;
    _vlanid!: string | null;
    _fetch_filters!: Record<string, string>;
    current_ntophost: any;
    _filtered_date!: null | any[];
    _filtered_hours!: null | any[];
    url_param!: string;
    constructor(div_selector: string) {
        super(div_selector);
        this._filter_choices = [];
    }

    override initialize(_with_debugging?: boolean) {
        this._crossfilter_time = crossfilter();

        // Date and hour filters
        this._date_dimension = this._crossfilter_time.dimension(d => d.date);
        this._hour_dimension = this._crossfilter_time.dimension(d => {
            return d.date.getHours() + d.date.getMinutes() / 60;
        });
        this._setup_time_based_filters(
            this._div_selection
                .append("div")
                .classed("time_filters " + this.page_id(), true),
        );

        // Fetch filters
        this._setup_fetch_filters(
            this._div_selection
                .append("div")
                .classed("fetch_filters " + this.page_id(), true),
        );

        const div_description = this._div_selection
            .append("div")
            .classed("description_filter " + this.page_id(), true);
        const div_status = this._div_selection
            .append("div")
            .classed("status " + this.page_id(), true);
        this._div_selection
            .append("div")
            .classed("warning " + this.page_id(), true)
            .style("display", "none")
            .html(
                "<b>Note: </b> When using both day and hour filters, only the selected hours of the last day will be evaluated.",
            );
        this._div_selection
            .append("div")
            .classed("details " + this.page_id(), true);

        // Table with details
        this._table_details = new DCTableFigure(
            "div.details." + this.page_id(),
            null,
        );
        this._table_details.subscribe_data_pre_processor_hook(data =>
            this._convert_alert_details_to_dc_table_format(data),
        );

        this._table_details.subscribe_post_render_hook(() => {
            this._div_selection
                .selectAll("div.status")
                .classed("loading_img_icon", false)
                .select("label");
        });

        this._table_details.activate_dynamic_paging();
        this._table_details.crossfilter(crossfilter());
        this._table_details.columns(this._get_columns());
        this._table_details.initialize();

        // Description filter
        this._setup_description_filter(div_description);
        this._setup_status_text(div_status);

        // CSS adjustments, TODO: check usage
        this._table_details
            .get_dc_chart()
            .on("postRedraw", chart => this._update_cells(chart));
        this._table_details
            .get_dc_chart()
            .on("renderlet", chart => this._update_css_classes(chart));

        // Parameters used for url generation
        this._ifid = null;
        this._vlanid = null;
        this._fetch_filters = {};

        this._div_selection = this._div_selection.classed(ifid_dep, true);
        this._div_selection.datum(this);
    }

    getEmptyData() {
        return {
            data: [],
            plot_definitions: [],
            ntop_link: "",
            alerts: [],
            filter_choices: [],
            time_series: [],
            number_of_alerts: 0,
        };
    }

    _convert_alert_details_to_dc_table_format(data: ABCAlertsPageData) {
        data.alerts.forEach(function (d, i) {
            d.index = i;
            // @ts-ignore
            d.date = new Date(1000 * d.date);
        });
        return {
            data: data.alerts,
            length: data.number_of_alerts,
        };
    }

    page_id() {
        return "";
    }

    update_post_body() {
        const parameters = this.get_url_search_parameters();
        // The post body of this function is always only responsible for the timeseries graphs
        parameters.append("timeseries_only", "1");
        this._post_body = parameters.toString();
    }

    get_url_search_parameters() {
        const parameters = new URLSearchParams();
        const params = Object.assign(
            {ifid: this._ifid, vlanid: this._vlanid},
            this._fetch_filters,
            this._get_time_filter_params(),
            this.current_ntophost == undefined
                ? {}
                : {host: this.current_ntophost},
        );
        Object.keys(params).forEach(key => {
            parameters.append(key, params[key]);
        });
        return parameters;
    }

    set_ids(ifid: string, vlanid = "0") {
        this._ifid = ifid;
        this._vlanid = vlanid;
        this.update_post_body();
        this.scheduler.force_update();
    }

    _setup_time_based_filters(
        selection: Selection<HTMLDivElement, unknown, BaseType, unknown>,
    ) {
        // These parameters -may- include activated filters
        this._filtered_date = null;
        this._filtered_hours = null;
        const table = selection
            // @ts-ignore
            .append("table", "div.paging")
            .classed("filter_graphs", true);
        table
            .append("tr")
            .selectAll("td")
            .data(["day", "hour"])
            .join("td")
            .text(d => "Filter by " + d);
        const graphs_row = table.append("tr");
        this._setup_date_filter(graphs_row.append("td"));
        this._setup_hour_filter(graphs_row.append("td"));
    }

    _update_filter_choices(filter_choices: FlowDashletDataChoice[]) {
        this._filter_choices = filter_choices;
        this._setup_fetch_filters(
            this._div_selection.select("div.fetch_filters." + this.page_id()),
        );
    }

    _setup_fetch_filters(
        selection: Selection<HTMLDivElement, unknown, BaseType, unknown>,
    ) {
        const dropdowns = selection
            .selectAll("div.dropdown")
            .data(this._filter_choices)
            .join("div")
            .style("display", "inline-block")
            .classed("dropdown", true);
        dropdowns
            .selectAll("label")
            .data(d => [d])
            .join("label")
            .text(d => d.group);
        const select = dropdowns
            .selectAll("select")
            .data(d => [d])
            .join("select")
            .attr("class", "filter alerts select2-enable");

        select
            .selectAll("option")
            .data(d => d.choices)
            .join(enter =>
                enter
                    .append("option")
                    .property("value", d => "" + d.id)
                    .text(d => d.name),
            );

        const elements = $("div.dropdown").find(".select2-enable");
        const select2 = elements.select2({
            dropdownAutoWidth: true,
            minimumResultsForSearch: 5,
        });
        select2.on("select2:select", event => {
            this._fetch_filters_changed(event);
        });
    }

    _fetch_filters_changed(event: Event) {
        if (event.target == null) return;
        const selectTarget = event.target as HTMLSelectElement;
        const target = select<HTMLSelectElement, ABCAlertsPage>(selectTarget);
        this._fetch_filters = {};
        //@ts-ignore
        if (selectTarget.value != -1)
            this._fetch_filters[target.datum().url_param] = selectTarget.value;
        this.update_post_body();

        // Reset all other filters
        const selected_index = selectTarget.selectedIndex;
        this._div_selection
            .selectAll("select.filter.alerts option")
            .property("selected", false);
        selectTarget.selectedIndex = selected_index;
        this.show_loading_image();
        this._table_details.reset();
        this.scheduler.force_update();
    }

    _setup_date_filter(
        selection: Selection<HTMLTableCellElement, unknown, BaseType, unknown>,
    ) {
        const div_id = this.page_id() + "_date_filter";
        selection
            .append("div")
            .attr("id", div_id)
            .classed("date_filter", true)
            .style("display", "inline");
        const date_group = this._date_dimension
            .group(d => {
                return timeDay.floor(d);
            })
            .reduceSum(d => d.count);
        const date_chart = barChart("#" + div_id, this.page_id());
        const now = new Date();
        const chart_x_domain = [
            new Date((now.getTime() / 1000 - 31 * 86400) * 1000),
            now,
        ];
        date_chart
            .width(500)
            .height(120)
            .dimension(this._date_dimension)
            .group(date_group)
            .margins({left: 30, top: 5, right: 20, bottom: 20})
            .x(scaleTime().domain(chart_x_domain))
            // @ts-ignore
            .xUnits(timeDays)
            // @ts-ignore
            .colors(() => {
                return "#767d84c2";
            })
            .elasticY(true)
            .on("postRedraw", () => {
                const filter_params = this._get_time_filter_params();
                this._div_selection
                    .select("div.status")
                    .classed("loading_img_icon", true)
                    .select("label")
                    .text(this._compute_status_text(filter_params));

                if (
                    filter_params.hour_start != undefined &&
                    filter_params.date_start != undefined
                ) {
                    this._div_selection
                        .select("div.warning")
                        .style("display", "block");
                } else {
                    this._div_selection
                        .select("div.warning")
                        .style("display", "none");
                }
                const parameters = this.get_url_search_parameters();
                parameters.append("details_only", "1");
                parameters.append("offset", "0");
                this._table_details.set_post_url_and_body(
                    this._post_url,
                    parameters.toString(),
                );
                this._table_details.scheduler.force_update();
            });
        date_chart
            .yAxis()
            .ticks(5)
            .tickFormat(d => {
                return fmt_number_with_precision(d, SIUnitPrefixes, 0);
            });

        date_chart.on("filtered", (date_chart, _filter) => {
            this._filtered_date = date_chart.filters();
        });
        date_chart
            .xAxis()
            .ticks(5)
            .tickFormat(d => {
                if (d.getMonth() === 0 && d.getDate() === 1)
                    return timeFormat("%Y")(d);
                else if (d.getHours() === 0 && d.getMinutes() === 0)
                    return timeFormat("%m-%d")(d);
                return timeFormat("%H:%M")(d);
            });
        date_chart.render();
    }

    _compute_status_text(filter_params: Record<string, number>) {
        function _format_date(
            timestamp: number,
            skip_date = false,
            skip_hours = false,
        ) {
            const date = new Date(timestamp * 1000);
            let response = "";
            if (!skip_date)
                response +=
                    date.getFullYear() +
                    "/" +
                    (date.getMonth() + 1) +
                    "/" +
                    (date.getDate() + 1) +
                    " ";
            if (!skip_hours) {
                response +=
                    ("0" + date.getHours()).slice(-2) +
                    ":" +
                    ("0" + date.getMinutes()).slice(-2);
            }
            return response;
        }
        function _format_absolute_hour(hour_number: number) {
            const timezoneOffset = new Date().getTimezoneOffset();
            hour_number = Math.trunc(hour_number) * 60 - timezoneOffset;
            return (
                ("00" + Math.floor(hour_number / 60)).slice(-2) +
                ":" +
                ("00" + (hour_number % 60)).slice(-2)
            );
        }

        let status_text = "Alert details";
        if (
            filter_params.date_start != undefined &&
            filter_params.hour_start == undefined
        ) {
            status_text +=
                " from " +
                _format_date(filter_params.date_start) +
                " to " +
                _format_date(filter_params.date_end);
        } else if (filter_params.hour_start != undefined) {
            const day_string =
                filter_params.date_end != undefined
                    ? " on " + _format_date(filter_params.date_end, false, true)
                    : " today";
            status_text +=
                " from " +
                _format_absolute_hour(filter_params.hour_start) +
                " to " +
                _format_absolute_hour(filter_params.hour_end) +
                day_string;
        } else status_text += " from last 31 days";

        return status_text;
    }

    _get_time_filter_params() {
        const filter_params: Record<string, number> = {};
        const hour_filter = this._filtered_hours;
        const timezoneOffset = new Date().getTimezoneOffset() / 60;
        if (hour_filter && hour_filter.length == 1) {
            filter_params["hour_start"] = hour_filter[0][0] + timezoneOffset;
            filter_params["hour_end"] = hour_filter[0][1] + timezoneOffset;
        }

        const date_filter: Date[][] = this._filtered_date!;

        if (Array.isArray(date_filter) && date_filter.length === 1) {
            filter_params["date_start"] = Math.trunc(
                date_filter[0][0].getTime() / 1000,
            );
            filter_params["date_end"] = Math.trunc(
                date_filter[0][1].getTime() / 1000,
            );
        }
        return filter_params;
    }

    _setup_hour_filter(
        selection: Selection<HTMLTableCellElement, unknown, BaseType, unknown>,
    ) {
        const div_id = this.page_id() + "_time_filter";
        selection
            .append("div")
            .attr("id", div_id)
            .classed("date_filter", true)
            .style("display", "inline");
        const hour_group = this._hour_dimension
            .group(d => {
                return Math.floor(d);
            })
            .reduceSum(d => d.count);
        const hour_chart = barChart("#" + div_id, this.page_id())
            .width(500)
            .height(120)
            .centerBar(true)
            .dimension(this._hour_dimension)
            .group(hour_group)
            .margins({left: 30, top: 5, right: 20, bottom: 20})
            .x(
                scaleLinear()
                    .domain([0, 24])
                    .rangeRound([0, 10 * 24]),
            )
            // @ts-ignore
            .colors(() => {
                return "#767d84c2";
            })
            .elasticY(true);
        hour_chart.on("filtered", (hour_chart, _filter) => {
            this._filtered_hours = hour_chart.filters();
        });
        hour_chart
            .yAxis()
            .ticks(5)
            .tickFormat(d => {
                return fmt_number_with_precision(d, SIUnitPrefixes, 0);
            });
        hour_chart.render();
    }

    // eslint-disable-next-line @typescript-eslint/no-empty-function, @typescript-eslint/no-unused-vars
    _setup_details_table(_selector: string) {}

    _setup_description_filter(
        selection: Selection<HTMLDivElement, unknown, BaseType, unknown>,
    ) {
        selection.append("label").text("Filter details by description");
        const msg_dimension = this._table_details
            // @ts-ignore
            .crossfilter()!
            .dimension(d => d.msg);
        selection
            .append("input")
            .attr("type", "text")
            .classed("msg_filter", true)
            .on("input", (event: Event) => {
                const target = select(event.target as HTMLInputElement);
                const filter = target.property("value");
                msg_dimension.filter(d => {
                    //@ts-ignore
                    return d.toLowerCase().includes(filter.toLowerCase());
                });
                this._table_details.update_gui();
            });
    }

    _setup_status_text(
        selection: Selection<HTMLDivElement, unknown, BaseType, unknown>,
    ) {
        selection.classed("status", true).append("label");
    }

    _update_css_classes(chart: DataTableWidget) {
        add_classes_to_trs(chart);
    }

    _update_cells(chart: DataTableWidget) {
        this._update_severity(chart);
        // TODO: deactivated for now
        // make sure to reactivate if this feature gets implemented properly
        //this._update_actions(chart);
    }

    _update_severity(chart: DataTableWidget) {
        add_columns_classes_to_nodes(chart, this._get_columns());

        const state_mapping = new Map<string, string>([
            ["error", "state2"],
            ["emergency", "state2"],
            ["critical", "state2"],
            ["warning", "state1"],
            ["notice", "state0"],
            ["debug", "state0"],
            ["info", "state0"],
            ["none", "state3"],
        ]);
        // Add state class to severity
        chart.selectAll("td.severity").each((d, idx, nodes) => {
            const label = select(nodes[idx]).select("label");
            label.classed("badge", true);
            const state = state_mapping.get(d.severity.toLowerCase());
            if (state) label.classed(state, true);
        });
    }

    override update_data(data: ABCAlertsPageData) {
        FigureBase.prototype.update_data.call(this, data);
        const time: {date: Date; count: number}[] = [];
        data.time_series.forEach(entry => {
            time.push({
                //@ts-ignore
                date: new Date(entry[0] * 1000),
                count: entry[1],
            });
        });

        // Update filters
        this._update_filter_choices(data.filter_choices);
        this._crossfilter_time.remove(() => true);
        this._crossfilter_time.add(time);
        this._table_details.set_paging_maximum(data.number_of_alerts);
        this._table_details.update_gui();
    }

    override update_gui() {
        redrawAll(this.page_id());
    }

    abstract _get_columns(): NtopColumn[];
}

// Base class for all alert tabs
export abstract class ABCAlertsTab<
    Page extends ABCAlertsPage = ABCAlertsPage,
> extends Tab {
    _page_class: null | (new (div_selector: string) => Page);
    _alerts_page!: Page;
    constructor(tabs_bar: TabsBar) {
        super(tabs_bar);
        this._page_class = null;
        this._tab_selection.classed("ntop_alerts", true);
    }

    initialize() {
        const div_id = this.tab_id() + "_alerts_table";
        this._tab_selection.append("div").attr("id", div_id);
        //TODO: this might be an error since ABCAlertsPage and its subclasses has
        // only one parameter in the constructor
        //@ts-ignore
        this._alerts_page = new this._page_class!("#" + div_id, this.tab_id());
        this._alerts_page.initialize();
    }

    // eslint-disable-next-line @typescript-eslint/no-empty-function
    activate() {}

    // eslint-disable-next-line @typescript-eslint/no-empty-function
    deactivate() {}
}

//   .-Engaged------------------------------------------------------------.
//   |              _____                                  _              |
//   |             | ____|_ __   __ _  __ _  __ _  ___  __| |             |
//   |             |  _| | '_ \ / _` |/ _` |/ _` |/ _ \/ _` |             |
//   |             | |___| | | | (_| | (_| | (_| |  __/ (_| |             |
//   |             |_____|_| |_|\__, |\__,_|\__, |\___|\__,_|             |
//   |                          |___/       |___/                         |
//   +--------------------------------------------------------------------+
export class EngagedAlertsTab extends ABCAlertsTab<EngagedAlertsPage> {
    constructor(tabs_bar: TabsBar) {
        super(tabs_bar);
        this._page_class = EngagedAlertsPage;
    }

    tab_id() {
        return "engaged_alerts_tab";
    }

    name() {
        return "Engaged Host";
    }
}

//cmk.gui.cee.ntop.connector.NtopAPIv2._build_alert_msg
export interface Alert {
    index: number; //created in JS
    entity: string;
    duration: number;
    count: number;
    msg: string;
    date: string;
    entity_val: string;
    drilldown: null; // Not used
    type: string;
    severity: string;
    score: string;
    needs_id_transform: boolean;
}

class EngagedAlertsPage extends ABCAlertsPage {
    constructor(div_selector: string) {
        super(div_selector);
        this._post_url = "ajax_ntop_engaged_alerts.py";
    }

    override page_id() {
        return "engaged_alerts";
    }

    override initialize(with_debugging?: boolean) {
        super.initialize(with_debugging);
        this.subscribe_data_pre_processor_hook(data => {
            const days: Record<string, number> = {};
            const timeseries_data: [number, number][] = [];
            data.alerts.forEach((alert: Alert) => {
                if (this._filter_entity(alert.entity_val)) return;
                const start_timestamp = alert.date;
                days[start_timestamp] = (days[start_timestamp] || 0) + 1;
            });
            for (const start_timestamp in days) {
                timeseries_data.push([
                    parseInt(start_timestamp),
                    days[start_timestamp],
                ]);
            }
            return {
                time_series: timeseries_data,
                filter_choices: data.filter_choices,
                ntop_link: data.ntop_link,
                number_of_alerts: data.number_of_alerts,
            };
        });
    }

    _filter_entity(_entity_val: string) {
        return false;
    }

    _get_columns() {
        return [
            {
                label: "Date",
                format: (d: Alert) => {
                    return (
                        //@ts-ignore
                        d.date.toLocaleDateString("de") +
                        " " +
                        //@ts-ignore
                        d.date.toLocaleTimeString("de")
                    );
                },
                classes: ["date", "number"],
            },
            {
                label: "Duration",
                format: (d: Alert) => {
                    return seconds_to_time(d.duration);
                },
                classes: ["duration", "number"],
            },
            {
                label: "Severity",
                format: (d: Alert) => {
                    return "<label>" + d.severity + "</label>";
                },
                classes: ["severity"],
            },
            {
                label: "Alert type",
                format: (d: Alert) => d.type,
                classes: ["alert_type"],
            },
            // TODO: deactivated for now
            // make sure to reactivate if this feature gets implemented properly
            //{
            //    label: "Drilldown",
            //    format: ()=>{return "Drilldown Link";},
            //    classes: ["drilldown"]
            //},
            {
                label: "Description",
                format: (d: Alert) => d.msg,
                classes: ["description"],
            },
            // TODO: deactivated for now
            // make sure to reactivate if this feature gets implemented properly
            //{
            //    label: "Actions",
            //    format: ()=>"",
            //    classes: ["actions"]
            //},
        ];
    }
}

//   .-Past---------------------------------------------------------------.
//   |                         ____           _                           |
//   |                        |  _ \ __ _ ___| |_                         |
//   |                        | |_) / _` / __| __|                        |
//   |                        |  __/ (_| \__ \ |_                         |
//   |                        |_|   \__,_|___/\__|                        |
//   |                                                                    |
//   +--------------------------------------------------------------------+
export class PastAlertsTab extends ABCAlertsTab {
    constructor(tabs_bar: TabsBar) {
        super(tabs_bar);
        this._page_class = PastAlertsPage;
    }

    tab_id() {
        return "past_alerts_tab";
    }

    name() {
        return "Past Host";
    }
}

class PastAlertsPage extends ABCAlertsPage {
    constructor(div_selector: string) {
        super(div_selector);
        this._post_url = "ajax_ntop_past_alerts.py";
    }

    override page_id() {
        return "past_alerts";
    }

    _get_columns() {
        return [
            {
                label: "Date",
                format: (d: Alert) => {
                    return (
                        //@ts-ignore
                        d.date.toLocaleDateString("de") +
                        " " +
                        //@ts-ignore
                        d.date.toLocaleTimeString("de")
                    );
                },
                classes: ["date", "number"],
            },
            {
                label: "Duration",
                format: (d: Alert) => {
                    return seconds_to_time(d.duration);
                },
                classes: ["duration", "number"],
            },
            {
                label: "Severity",
                format: (d: Alert) => {
                    return "<label>" + d.severity + "</label>";
                },
                classes: ["severity"],
            },
            {
                label: "Alert type",
                format: (d: Alert) => d.type,
                classes: ["alert_type"],
            },
            // TODO: deactivated for now
            // make sure to reactivate if this feature gets implemented properly
            //{
            //    label: "Drilldown",
            //    format: ()=>{
            //        return "<img src=themes/facelift/images/icon_zoom.png>";
            //    },
            //    classes: ["drilldown"]
            //},
            {
                label: "Description",
                format: (d: Alert) => d.msg,
                classes: ["description"],
            },
            // TODO: deactivated for now
            // make sure to reactivate if this feature gets implemented properly
            //{
            //    label: "Actions",
            //    format: ()=>"",
            //    classes: ["actions"]
            //},
        ];
    }
}

//   .-Flows--------------------------------------------------------------.
//   |                      _____ _                                       |
//   |                     |  ___| | _____      _____                     |
//   |                     | |_  | |/ _ \ \ /\ / / __|                    |
//   |                     |  _| | | (_) \ V  V /\__ \                    |
//   |                     |_|   |_|\___/ \_/\_/ |___/                    |
//   |                                                                    |
//   +--------------------------------------------------------------------+

export class FlowAlertsTab extends ABCAlertsTab {
    constructor(tabs_bar: TabsBar) {
        super(tabs_bar);
        this._page_class = FlowAlertsPage;
    }

    tab_id() {
        return "flow_alerts_tab";
    }

    name() {
        return "Past Flow";
    }
}

class FlowAlertsPage extends ABCAlertsPage {
    constructor(div_selector: string) {
        super(div_selector);
        this._post_url = "ajax_ntop_flow_alerts.py";
    }

    override page_id() {
        return "flow_alerts";
    }

    _get_columns() {
        return [
            {
                label: "Date",
                format: (d: Alert) => {
                    return (
                        //@ts-ignore
                        d.date.toLocaleDateString("de") +
                        " " +
                        //@ts-ignore
                        d.date.toLocaleTimeString("de")
                    );
                },
                classes: ["date", "number"],
            },
            {
                label: "Severity",
                format: (d: Alert) => {
                    return "<label>" + d.severity + "</label>";
                },
                classes: ["severity"],
            },
            {
                label: "Alert type",
                format: (d: Alert) => d.type,
                classes: ["alert_type"],
            },
            {
                label: "Score",
                format: (d: Alert) => d.score,
                classes: ["score", "number"],
            },
            {
                label: "Description",
                format: (d: Alert) => d.msg,
                classes: ["description"],
            },
            // TODO: deactivated for now
            // make sure to reactivate if this feature gets implemented properly
            //{
            //    label: "Actions",
            //    format: ()=>"",
            //    classes: ["actions"]
            //},
        ];
    }
}
