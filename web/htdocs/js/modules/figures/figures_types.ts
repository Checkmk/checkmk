/* eslint  @typescript-eslint/no-unused-vars: 0, @typescript-eslint/no-empty-interface: 0 */
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
