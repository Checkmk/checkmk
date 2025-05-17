/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import {AlertOverview} from "./cmk_alert_overview";
import {BarplotFigure} from "./cmk_barplot";
import {figure_registry} from "./cmk_figures";
import {GaugeFigure} from "./cmk_gauge";
import {InventoryFigure} from "./cmk_inventory";
import {SiteOverview} from "./cmk_site_overview";
import {StateFigure, StateHostFigure} from "./cmk_state";
import {HostStateSummary, ServiceStateSummary} from "./cmk_state_summary";
import {EventStats, HostStats, ServiceStats} from "./cmk_stats";
import {TableFigure} from "./cmk_table";
import {AverageScatterplotFigure} from "./timeseries/average_scatterplot_figure";
import {CmkGraphShifter} from "./timeseries/cmk_graph_shifter";
import {CmkGraphTimeseriesFigure} from "./timeseries/cmk_graph_timeseries_figure";
import {TimeseriesFigure} from "./timeseries/cmk_timeseries";
import {SingleMetricFigure} from "./timeseries/single_metric_figure";
import {PieChartFigure} from "@/modules/figures/cmk_pie_chart";
import {HorizontalBarFigure} from "@/modules/figures/cmk_horizontal_bar";

export function register() {
    figure_registry.register(TableFigure);
    figure_registry.register(HostStats);
    figure_registry.register(ServiceStats);
    figure_registry.register(EventStats);
    figure_registry.register(AlertOverview);
    figure_registry.register(BarplotFigure);
    figure_registry.register(HorizontalBarFigure);
    figure_registry.register(GaugeFigure);
    figure_registry.register(PieChartFigure);
    figure_registry.register(InventoryFigure);
    figure_registry.register(SiteOverview);
    figure_registry.register(StateFigure);
    figure_registry.register(StateHostFigure);
    figure_registry.register(HostStateSummary);
    figure_registry.register(ServiceStateSummary);
    figure_registry.register(TimeseriesFigure);
    figure_registry.register(AverageScatterplotFigure);
    figure_registry.register(SingleMetricFigure);
    figure_registry.register(CmkGraphTimeseriesFigure);
    figure_registry.register(CmkGraphShifter);
}
