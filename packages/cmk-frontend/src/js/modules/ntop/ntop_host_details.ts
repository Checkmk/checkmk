/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

/*eslint no-undef: "off"*/
import crossfilter from "crossfilter2";
import type {Selection} from "d3";
import {ascending, select, selectAll} from "d3";
import type {DataTableWidget, PieChart, RowChart} from "dc";
import {pieChart, redrawAll, renderAll, rowChart} from "dc";

import {DCTableFigure} from "@/modules/figures/cmk_dc_table";
import type {FigureBase} from "@/modules/figures/cmk_figures";
import {figure_registry} from "@/modules/figures/cmk_figures";
import {TableFigure} from "@/modules/figures/cmk_table";
import {Tab, TabsBar} from "@/modules/figures/cmk_tabs";
import type {FigureData} from "@/modules/figures/figure_types";
import {MultiDataFetcher} from "@/modules/figures/multi_data_fetcher";

import type {ABCAlertsTab, Alert} from "./ntop_alerts";
import {EngagedAlertsTab, FlowAlertsTab, PastAlertsTab} from "./ntop_alerts";
import {FlowsDashlet} from "./ntop_flows";
import type {
    ApplicationTabData,
    HostTabData,
    PacketsTabData,
    PeersTabData,
    PortsTabData,
    TopPeerProtocol,
    TrafficTabData,
} from "./ntop_types";
import {
    add_classes_to_trs,
    add_columns_classes_to_nodes,
    bytes_to_volume,
    ifid_dep,
} from "./ntop_utils";

function _add_item_link(tab_instance: Tab) {
    // Create link to ntop and hide it until we have a valid link from the backend
    tab_instance._link_item = tab_instance._tab_selection
        .append("div")
        .append("a")
        .attr("target", "_blank")
        .classed("link_to_ntop_host", true);

    tab_instance._link_item.style("display", "none");
    tab_instance._link_item.text("View data in ntopng");
}

function update_item_link(tab_instance: Tab, link: string) {
    tab_instance._link_item.style("display", null);
    tab_instance._link_item.attr("href", link);
}

export class HostTabs extends TabsBar {
    current_ntophost!: string;

    override _get_tab_entries(): (
        | (new (tabs_bar: HostTabs) => NtopTab)
        | (new (tabs_bar: TabsBar) => Tab)
    )[] {
        return [
            HostTab,
            TrafficTab,
            PacketsTab,
            PortsTab,
            PeersTab,
            ApplicationsTab,
            NtophostFlowsTab,
            NtophostEngagedAlertsTab,
            NtophostPastAlertsTab,
            NtophostFlowAlertsTab,
        ];
    }

    override initialize(tab: string, ifid: string, vlanid: string) {
        TabsBar.prototype.initialize.call(this);
        ["engaged_alerts_tab", "past_alerts_tab", "flow_alerts_tab"].forEach(
            tab_id =>
                ((
                    this.get_tab_by_id(tab_id) as ABCAlertsTab
                )._alerts_page.current_ntophost = this.current_ntophost),
        );
        selectAll("." + ifid_dep)
            .data()
            // @ts-ignore
            .forEach(o => o.set_ids(ifid, vlanid));
        this._activate_tab(this.get_tab_by_id(tab));
    }

    set_current_ntophost(value: string) {
        this.current_ntophost = value;
    }

    get_current_ntophost_uri_dict() {
        return {host: this.current_ntophost};
    }

    _show_error_info(error_info: string) {
        console.log("Error fetching data:" + error_info);
    }
}

abstract class NtopTab extends Tab<HostTabs> {
    _multi_data_fetcher: MultiDataFetcher;
    _figures: Record<string, FigureBase<FigureData>>;
    _dc_figures: Record<string, any>;
    _ifid: string;
    _vlanid!: string;
    post_url!: string;

    constructor(tabs_bar: HostTabs) {
        super(tabs_bar);
        this._multi_data_fetcher = new MultiDataFetcher();
        this._figures = {}; // figures from cmk
        this._dc_figures = {}; // figures from dc_library
        this._tab_selection.classed("ntop ntop_host " + ifid_dep, true);
        //@ts-ignore
        this._ifid = tabs_bar.current_ifid;
        _add_item_link(this);
    }

    update_post_body() {
        this._multi_data_fetcher.reset();
        this._multi_data_fetcher.add_fetch_operation(
            this.post_url,
            this.get_post_body(),
            120,
        );
        this._multi_data_fetcher.subscribe_hook(
            this.post_url,
            this.get_post_body(),
            data => this._update_data(data),
        );
    }

    set_ids(ifid: string, vlanid: string) {
        this._ifid = ifid;
        this._vlanid = vlanid;
        this.update_post_body();
    }

    get_post_body() {
        const url_params = new URLSearchParams(
            Object.assign(
                {},
                this._tabs_bar.get_current_ntophost_uri_dict(),
                this.get_current_ifid_uri_dict(),
                this.get_current_vlanid_uri_dict(),
            ),
        );
        return url_params.toString();
    }

    get_current_ifid_uri_dict() {
        return {ifid: this._ifid};
    }

    get_current_vlanid_uri_dict() {
        return {vlanid: this._vlanid};
    }

    // eslint-disable-next-line @typescript-eslint/no-empty-function
    initialize() {}

    activate() {
        for (const figure_id in this._figures) {
            this._figures[figure_id].scheduler.enable();
            this._figures[figure_id].scheduler.update_if_older_than(5);
        }
        this._multi_data_fetcher.scheduler.enable();
        this._multi_data_fetcher.scheduler.update_if_older_than(5);
    }

    deactivate() {
        for (const figure_id in this._figures) {
            this._figures[figure_id].scheduler.disable();
        }
        this._multi_data_fetcher.scheduler.disable();
    }

    _update_data(_data: any) {
        throw new Error("not implemented in base class!");
    }
}

export class HostTab extends NtopTab {
    tab_id() {
        return "host_tab";
    }

    name() {
        return "Host";
    }

    override initialize() {
        const div_id = "host_data";
        this._tab_selection.append("div").attr("id", div_id);
        const table_figure_class = figure_registry.get_figure("table");
        const table_figure = new table_figure_class("#" + div_id);
        this.post_url = "ajax_ntop_host_stats.py";
        table_figure.set_post_url_and_body(this.post_url, this.get_post_body());
        table_figure.scheduler.set_update_interval(60);
        table_figure.subscribe_post_render_hook(data =>
            this._update_next_post_url(data),
        );
        table_figure.initialize(false);

        this._figures["host_data"] = table_figure;
    }

    override update_post_body() {
        this._figures["host_data"].set_post_url_and_body(
            this.post_url,
            this.get_post_body(),
        );
    }

    _update_next_post_url(data: HostTabData) {
        update_item_link(this, data["ntop_link"]);
        this._figures["host_data"].set_post_url_and_body(
            this.post_url,
            this.get_post_body() +
                "&_previous_data=" +
                JSON.stringify(data["meta"]["data"]),
        );
    }
}

class TrafficTab extends NtopTab {
    _table_figures!: TableFigure;
    _table_stats!: TableFigure;

    tab_id() {
        return "traffic_tab";
    }

    name() {
        return "Traffic";
    }

    override initialize() {
        this.post_url = "ajax_ntop_host_traffic.py";
        const post_body = this.get_post_body();
        this._multi_data_fetcher.add_fetch_operation(
            this.post_url,
            post_body,
            120,
        );
        this._multi_data_fetcher.subscribe_hook(
            this.post_url,
            post_body,
            data => this._update_data(data),
        );

        // One table for the figures
        let div_id = "ntop_host_traffic_overview";
        this._tab_selection.append("div").attr("id", div_id);
        this._table_figures = new TableFigure("#" + div_id);
        this._table_figures.initialize();

        // separate table for the traffic breakdown
        div_id = "ntop_host_traffic_breakdown";
        this._tab_selection.append("div").attr("id", div_id);
        this._table_stats = new TableFigure("#" + div_id);
        this._table_stats.initialize();
    }

    override _update_data(data: TrafficTabData) {
        this._table_figures.process_data(data["table_overview"]);
        this._table_stats.process_data(data["table_breakdown"]);

        //_update_dc_graphs_in_selection(this._table_figures._div_selection, this.tab_id());
        redrawAll(this.tab_id());

        update_item_link(this, data["ntop_link"]);
    }
}

class PacketsTab extends NtopTab {
    tab_id() {
        return "packets_tab";
    }

    name() {
        return "Packets";
    }

    override initialize() {
        this._tab_selection.append("div").attr("id", "table_packets");
        const table_figure_class = figure_registry.get_figure("table");
        const table = new table_figure_class("#table_packets");
        table.initialize(false);
        this._figures["table_packets"] = table;

        this.post_url = "ajax_ntop_host_packets.py";
        const post_body = this.get_post_body();
        this._multi_data_fetcher.add_fetch_operation(
            this.post_url,
            post_body,
            120,
        );
        this._multi_data_fetcher.subscribe_hook(
            this.post_url,
            post_body,
            data => this._update_data(data),
        );
    }

    override _update_data(data?: PacketsTabData) {
        if (data == undefined) return;
        this._figures["table_packets"].process_data(data["table_packets"]);

        redrawAll(this.tab_id());
        update_item_link(this, data["ntop_link"]);
    }
}

class PortsTab extends NtopTab {
    _table_ports!: TableFigure;

    tab_id() {
        return "ports_tab";
    }

    name() {
        return "Ports";
    }

    override initialize() {
        const div_id = "ntop_host_ports";
        this._tab_selection.append("div").attr("id", div_id);
        this._table_ports = new TableFigure("#" + div_id);
        this._table_ports.initialize();

        this.post_url = "ajax_ntop_host_ports.py";
        const post_body = this.get_post_body();
        this._multi_data_fetcher.add_fetch_operation(
            this.post_url,
            post_body,
            120,
        );
        this._multi_data_fetcher.subscribe_hook(
            this.post_url,
            post_body,
            data => this._update_data(data),
        );
    }

    override _update_data(data: PortsTabData) {
        this._table_ports.process_data(data["table_ports"]);
        redrawAll(this.tab_id());
        update_item_link(this, data["ntop_link"]);
    }
}

class PeersTab extends NtopTab {
    _filter_dimensions: Record<any, any>;
    _filters: Record<any, any>;
    _crossfilter!: crossfilter.Crossfilter<any>;
    _host_chart!: RowChart;
    _name_dimension!: crossfilter.Dimension<any, any>;
    _traffic_per_host!: crossfilter.Group<
        any,
        crossfilter.NaturallyOrderedValue,
        unknown
    >;
    _pie_chart!: PieChart;
    _pie_dimension!: crossfilter.Dimension<any, any>;
    _pie_group!: crossfilter.Group<any, any, any>;
    _table_stats!: DCTableFigure;

    constructor(tabs_bar: HostTabs) {
        super(tabs_bar);
        this._multi_data_fetcher = new MultiDataFetcher();

        // Filtered elements for the crossfilter dimension
        this._filter_dimensions = {};
        this._filters = {};
    }

    tab_id() {
        return "peers_tab";
    }

    name() {
        return "Peers";
    }

    override initialize() {
        // TODO: requires cleanup. this code is still from the prototype version

        // Uses flex layout
        const div_graphs = this._tab_selection
            .append("div")
            .style("display", "flex")
            .style("flex-wrap", "wrap");

        // Create main divs
        div_graphs
            .selectAll("div.main_component")
            .data(["bar", "pie"])
            .enter()
            .append("div")
            .classed("main_component", true)
            .attr("id", d => d);

        div_graphs
            .selectAll("div#bar")
            .style("display", "flex")
            .style("flex-wrap", "wrap")
            .style("justify-content", "center")
            .style("align-content", "center")
            .style("width", "550px")
            .style("height", "400px")
            .append("div")
            .attr("id", "peers_bar");

        div_graphs
            .selectAll("div#pie")
            .style("display", "flex")
            .style("flex-wrap", "wrap")
            .style("justify-content", "center")
            .style("align-content", "center")
            .style("width", "400px")
            .style("height", "400px")
            .append("div")
            .attr("id", "peers_pie");

        this.post_url = "ajax_ntop_host_top_peers_protocols.py";
        const post_body = this.get_post_body();
        this._multi_data_fetcher.add_fetch_operation(
            this.post_url,
            post_body,
            120,
        );
        this._multi_data_fetcher.subscribe_hook(
            this.post_url,
            post_body,
            data => this._update_data(data),
        );

        // crossfilter is globally defined
        this._crossfilter = crossfilter();

        // Host chart
        this._host_chart = rowChart("#peers_bar", this.tab_id());
        this._name_dimension = this._crossfilter.dimension(function (d) {
            return d.name;
        });
        this._traffic_per_host = this._name_dimension
            .group()
            .reduceSum(function (d) {
                return +d.traffic;
            });
        this._host_chart
            .width(500)
            .height(300)
            .elasticX(true)
            .dimension(this._name_dimension)
            .group(this._traffic_per_host);
        // Tooltip
        this._host_chart.title(function (d) {
            return "Host " + d.key + ": " + bytes_to_volume(d.value);
        });

        this._host_chart
            .xAxis()
            .tickFormat(function (v) {
                if (v < 1024) return v.toFixed(2);
                else return bytes_to_volume(v);
            })
            .ticks(5);

        // Protocol chart
        this._pie_chart = pieChart("#peers_pie", this.tab_id());
        this._pie_dimension = this._crossfilter.dimension(d => d.l7proto);
        this._pie_group = this._pie_dimension.group().reduceSum(d => d.traffic);
        this._pie_chart
            .width(550)
            .height(300)
            .dimension(this._pie_dimension)
            .radius(350)
            .innerRadius(60)
            .externalRadiusPadding(40)
            .minAngleForLabel(0.5)
            .externalLabels(25)
            .group(this._pie_group);

        // Table
        const name_dimension = this._crossfilter.dimension(d => d.name);
        renderAll(this.tab_id());

        // Table
        const div_id = "peers_table";
        this._tab_selection.append("div").attr("id", div_id);
        this._table_stats = new DCTableFigure("#" + div_id, this.tab_id());
        this._table_stats.crossfilter(this._crossfilter);
        this._table_stats.dimension(name_dimension);
        this._table_stats.columns(this._get_columns());
        this._table_stats.sort_by(d => {
            return d.name;
        });
        this._table_stats.initialize();
        this._table_stats
            .get_dc_chart()
            .on("renderlet", chart => this._update_css_classes(chart));
        this._table_stats.get_dc_chart().order(ascending);
    }

    override _update_data(data?: PeersTabData) {
        if (data === undefined) return;

        const data_stats = data["stats"];
        // @ts-ignore
        if (data_stats == []) return;
        this._crossfilter.remove(() => true);
        this._crossfilter.add(data_stats);
        redrawAll(this.tab_id());
        this._table_stats.remove_loading_image();

        update_item_link(this, data["ntop_link"]);
    }

    _update_css_classes(chart: DataTableWidget) {
        add_classes_to_trs(chart);
        add_columns_classes_to_nodes(chart, this._get_columns());
    }

    _get_columns() {
        return [
            {
                label: "Host",
                format: (d: TopPeerProtocol) => d.host_url,
                classes: ["host"],
            },
            {
                label: "IP Address",
                format: (d: TopPeerProtocol) => d.host,
                classes: ["host"],
            },
            {
                label: "Application",
                format: (d: TopPeerProtocol) => d.l7proto_url,
                classes: ["application"],
            },
            {
                label: "Traffic",
                format: (d: TopPeerProtocol) => d.traffic_hr,
                classes: ["traffic", "number"],
            },
            {
                // insert an empty column at the end for large screens
                label: "",
                format: () => "",
                classes: ["empty"],
            },
        ];
    }
}

class ApplicationsTab extends NtopTab {
    _table!: TableFigure;
    _nav!: Selection<HTMLElement, any, HTMLElement, any>;
    _li!: Selection<HTMLLIElement, any, HTMLElement, any>;
    _subtab_applications!: Selection<HTMLDivElement, any, HTMLElement, any>;
    _subtab_categories!: Selection<HTMLDivElement, any, HTMLElement, any>;
    _table_applications!: TableFigure;
    _table_categories!: TableFigure;

    tab_id() {
        return "applications_tab";
    }

    name() {
        return "Apps";
    }

    override initialize() {
        // overview
        let div_id = "ntop_host_apps_overview";
        this._tab_selection.append("div").attr("id", div_id);

        this._table = new TableFigure("#" + div_id);
        this._table.initialize();

        // tab navigation
        this._nav = this._tab_selection
            .append("nav")
            .classed("main-navigation", true)
            .style("display", "none");
        const ul = this._nav.append("ul");
        this._li = ul
            .selectAll("li")
            .data(["Applications", "Categories"])
            .enter()
            .append("li")
            .classed("noselect", true)
            .text(d => d)
            .attr("id", d => d.toLowerCase())
            .on("click", d => {
                this._switch_subtab(d);
            });
        ul.selectAll("li#applications").classed("active", true);

        const tab_content = this._tab_selection
            .append("div")
            .attr("id", "tab_content");
        this._subtab_applications = tab_content
            .append("div")
            .attr("id", "applications")
            .classed("subtab", true);
        this._subtab_categories = tab_content
            .append("div")
            .attr("id", "categories")
            .classed("subtab", true)
            .style("display", "none");

        // applications table
        div_id = "ntop_host_apps_applications";
        this._subtab_applications.append("div").attr("id", div_id);
        this._table_applications = new TableFigure("#" + div_id);
        this._table_applications.initialize();

        // categories table
        div_id = "ntop_host_apps_categories";
        this._subtab_categories.append("div").attr("id", div_id);
        this._table_categories = new TableFigure("#" + div_id);
        this._table_categories.initialize();

        this.post_url = "ajax_ntop_host_applications.py";
        const post_body = this.get_post_body();
        this._multi_data_fetcher.add_fetch_operation(
            this.post_url,
            post_body,
            120,
        );
        this._multi_data_fetcher.subscribe_hook(
            this.post_url,
            post_body,
            data => {
                this._update_data(data);
                this._update_gui();
            },
        );
    }

    _switch_subtab(activate_id: string) {
        //@ts-ignore
        const activate_id_str = activate_id.target.id.toLowerCase();
        this._li.classed("active", d => {
            return d.toLowerCase() == activate_id_str;
        });
        this._tab_selection
            .selectAll("div.subtab")
            .style("display", (_d, idx, nodes) => {
                const div = select(nodes[idx]);
                if (div.attr("id") == activate_id_str) return null;
                else return "none";
            });
    }

    override _update_data(data: ApplicationTabData) {
        this._nav.style("display", "");
        this._table.process_data(data["table_apps_overview"]);
        this._table_applications.process_data(data["table_apps_applications"]);
        this._table_categories.process_data(data["table_apps_categories"]);
        redrawAll(this.tab_id());

        update_item_link(this, data["ntop_link"]);
    }

    _update_gui() {
        for (const table_obj of [
            this._table_applications,
            this._table_categories,
        ]) {
            table_obj._table.select("tr").classed("header", true);
        }
    }
}

class NtophostFlowsTab extends NtopTab {
    _flows_dashlet!: FlowsDashlet;

    tab_id() {
        return "flows_tab";
    }

    name() {
        return "Flows";
    }

    override initialize() {
        const div_id = "ntop_host_flows";
        this._tab_selection.append("div").attr("id", div_id);
        this._flows_dashlet = new FlowsDashlet("#" + div_id);
        this._flows_dashlet._default_params_dict =
            this._tabs_bar.get_current_ntophost_uri_dict();
        this._flows_dashlet.initialize();
        // The FlowsTab has the FlowsDashlet embedded which must also runs standalone.
        // Therefore the ifid will be injected there and we need to remove the class
        // (derived from NtopTab) here.
        this._tab_selection.classed(ifid_dep, false);
    }
}

class NtophostPastAlertsTab extends PastAlertsTab {
    override tab_id() {
        return "past_alerts_tab";
    }

    override name() {
        return "Past Host";
    }

    override initialize() {
        PastAlertsTab.prototype.initialize.call(this);
        _initialize_alerts_tab(this);
    }
}

class NtophostEngagedAlertsTab extends EngagedAlertsTab {
    override tab_id() {
        return "engaged_alerts_tab";
    }
    override name() {
        return "Engaged Host";
    }

    override initialize() {
        EngagedAlertsTab.prototype.initialize.call(this);
        _initialize_alerts_tab(this);
        this._alerts_page._filter_entity = entity_val => {
            return this._filter_entity(entity_val, this);
        };
    }

    _filter_entity(
        entity_val: string,
        this_reference: NtophostEngagedAlertsTab,
    ) {
        return (
            entity_val.indexOf(
                (<HostTabs>this_reference._tabs_bar).current_ntophost,
            ) == -1
        );
    }
}

class NtophostFlowAlertsTab extends FlowAlertsTab {
    override tab_id() {
        return "flow_alerts_tab";
    }

    override name() {
        return "Past Flow";
    }

    override initialize() {
        FlowAlertsTab.prototype.initialize.call(this);
        _initialize_alerts_tab(this);
    }
}

function _initialize_alerts_tab(instance: ABCAlertsTab) {
    const dimension = instance._alerts_page._table_details
        // @ts-ignore
        .crossfilter()!
        .dimension(d => d);
    dimension.filter(d => {
        return (
            (d as unknown as Alert).msg.indexOf(
                (<HostTabs>instance._tabs_bar).current_ntophost,
            ) != -1
        );
    });
    _add_item_link(instance);
    instance._alerts_page.subscribe_post_render_hook(data =>
        update_item_link(instance, data["ntop_link"]),
    );
}
