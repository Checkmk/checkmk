/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

/* eslint  @typescript-eslint/no-unused-vars: 0, @typescript-eslint/no-empty-interface: 0 */

//TODO: this is kind of code duplication, since the types are defined twice
// in python and typescript, so maybe in the future it would be better to have
// a way to automatically generate them from one sie to another

export interface SubplotDataData {
    x?: [Date | undefined, Date | undefined];
    y?: [number, number | undefined];
    data: TransformedData[];
}

//types from: cmk/gui/cee/plugins/dashboard/site_overview.py
export interface ABCElement {
    type: string;
    title: string;
    tooltip: string;
}

export interface SiteElement extends ABCElement {
    type: "site_element";
    url_add_vars: Record<string, string>;
    total: Part;
    parts: Part[];
}

export interface HostElement extends ABCElement {
    hexagon_config: {
        css_class: string;
        path: string;
        color?: number;
        tooltip: string;
        id: string;
    }[];
    x: number;
    y: number;
    type: "host_element";
    link: string;
    host_css_class: string;
    service_css_class: string;
    has_host_problem: boolean;
    num_services: number;
    num_problems: number;
}

export interface IconElement extends ABCElement {
    type: "icon_element";
    css_class: string;
}

export interface Part {
    title: string;
    css_class: string;
    count: number;
}

export interface SingleMetricDataData {
    tag: string;
    last_value: boolean;
    timestamp: number;
    value: number;
    label: any;
    url: string;
}

export interface SingleMetricDataPlotDefinitions {
    label: any;
    id: string;
    plot_type: string;
    style: string;
    status_display: Record<string, string>;
    use_tags: string[];
    color: string;
    opacity: number;
    metric: Record<string, Record<string, any>>;
}

export interface ElementMargin {
    top: number;
    right: number;
    bottom: number;
    left: number;
}

export interface FigureData<D = any, P = any> {
    //TODO: in all figureBase subclasses data is an array of data or it's not used at all like
    // in case of ntop figures, however, it's in some cases only on element (as type not a single element array)
    // like in HostStateSummary and ServiceStateSummary. This causes typing confusion and possible errors
    // so it might be better to change the structure of the above mentioned classes.
    data: D[] | D;
    plot_definitions: P[];
}

export interface SingleMetricData
    extends FigureData<SingleMetricDataData, SingleMetricDataPlotDefinitions> {
    data: SingleMetricDataData[];
    title: string;
    title_url: string;
}

/*
In cmk_figures there is an attribute called _dashlet_spec which is
a generic type. It's being set by set_dashlt_spec(dashlet) which is
used in python in: cmk/gui/dashboard/dashlet/figure_dashlet.py:149
So in this File there is an attribute of the class ABCDashlet
which inherits Dashlet(T) which is a generic class
and T should be subclass of DashletConfig. So I think ABCDashlet is
the python equivalent of FigureBase regarding _dashlet_spec
*/

//types from: cmk/gui/dashboard/type_defs.py
type DashboardName = string;
type DashletId = number;
type DashletRefreshInterval = boolean | number;
type DashletRefreshAction = string | null;
type DashletSize = [number, number];
type DashletPosition = [number, number];
type InfoName = string;
type SingleInfos = InfoName[];
type FilterName = string;
type FilterHTTPVariables = Record<string, string>;
type VisualContext = Record<FilterName, FilterHTTPVariables>;

interface _DashletConfigMandatory {
    type: string;
}

//cmk/gui/dashboard/type_defs.py:25
//This interface is called DashletConfig in Python but I renamed it to
//FigureBaseDashletSpec to match the naming in Typescript
export interface FigureBaseDashletSpec extends _DashletConfigMandatory {
    single_infos: SingleInfos;
    title: string;
    title_url: string;
    context: VisualContext;
    reload_on_resize: boolean;
    position: DashletPosition;
    size: DashletSize;
    background: boolean;
    show_title: boolean | "transparent";
}

type DisplayRange = ["fixed", any] | "automatic";

export interface BarplotDashletConfig extends SingleMetricDashletConfig {
    display_range: DisplayRange;
}

export interface SingleMetricDashletConfig extends FigureBaseDashletSpec {
    metric: string;
}

type TimerangeValue = [null, number, string, [string, any]];

interface TimeRangeParameters {
    window: TimerangeValue;
    rrd_consolidation: "average" | "min" | "max";
}

type TimeRange = "current" | ["range", TimeRangeParameters];
type StatusDisplay =
    | null
    | ["text", "all" | "not_ok"]
    | ["background", "all" | "not_ok"];

//cmk/gui/cee/plugins/dashboard/single_metric.py:471
export interface SingleGraphDashletConfig extends SingleMetricDashletConfig {
    time_range: TimeRange;
    display_range: DisplayRange;
    toggle_range_display: boolean;
    status_display: StatusDisplay;
}

//cmk/gui/cee/plugins/dashboard/single_metric.py:392
export interface GaugeDashletConfig extends SingleMetricDashletConfig {
    time_range: TimeRange;
    display_range: DisplayRange;
    status_display: StatusDisplay;
}

//cmk.gui.cee.plugins.dashboard.inventory.InventoryDashletConfig
interface InventoryDashletConfig extends FigureBaseDashletSpec {
    inventory_path: string;
}

interface _AlertOverviewDashletConfigMandatory extends FigureBaseDashletSpec {
    time_range: TimerangeValue;
}

//cmk/gui/cee/plugins/dashboard/alert_overview.py:225
interface AlertOverviewDashletConfig
    extends _AlertOverviewDashletConfigMandatory {
    limit_objects: number;
}

type HostStateValue = [0, 1, 2];

interface HostStateSummaryDashletConfig extends FigureBaseDashletSpec {
    state: HostStateValue;
}

type MonitoringStateValue = [0, 1, 2, 3];

//cmk/gui/cee/plugins/dashboard/state_summary.py:338
interface ServiceStateSummaryDashletConfig extends FigureBaseDashletSpec {
    state: MonitoringStateValue;
}

interface StatsDashletConfig extends FigureBaseDashletSpec {}

interface SiteOverviewDashletConfig extends FigureBaseDashletSpec {}

//cmk/gui/cee/plugins/dashboard/status.py:31
interface StateDashletConfig extends FigureBaseDashletSpec {
    status_display: StatusDisplay;
    show_summary: "not_ok" | null;
}

//cmk/gui/cee/plugins/dashboard/average_scatterplot_dashlet.py:286
export interface AverageScatterplotDashletConfig extends FigureBaseDashletSpec {
    metric: string;
    time_range: TimerangeValue;
    metric_color: string | null;
    avg_color: string | null;
    median_color: string | null;
}

export interface ElementSize {
    width: number;
    height: number;
}

export type Levels = {
    from: number;
    to: number;
    style: string;
};

interface _Metric {
    bounds: Bounds;
    unit: any;
}

export interface Bounds {
    warn?: number;
    crit?: number;
    min?: number;
    max?: number;
}

export type Domain = [number, number];

export interface TransformedData {
    label: any;
    scaled_y: number;
    scaled_x: number;
    value: number;
    unstacked_value: number;
    timestamp: number;
    date: Date;
    ending_timestamp?: number;
    url?: string;
    last_value?: number;
    tooltip?: string;
}
