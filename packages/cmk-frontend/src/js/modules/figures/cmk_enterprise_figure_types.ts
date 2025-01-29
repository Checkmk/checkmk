/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import type {HSLColor, RGBColor} from "d3";

import type {FigureData} from "@/modules/figures/figure_types";

export interface TimeseriesFigureDataPlotDefinition {
    id: string;
    color: string;
    plot_type: string;
    metric: {
        unit: {
            js_render: string;
        };
    };
    label: string;
    use_tags: string[];
}

export interface TimeseriesFigureDataData {
    date?: Date; //dynamic assignment in JS
    timestamp: number;
    ending_timestamp: number;
    value: number;
    tag: string;
    tooltip: string;
}

export interface TimeseriesFigureData
    extends FigureData<
        TimeseriesFigureDataData,
        TimeseriesFigureDataPlotDefinition
    > {
    zoom_settings?: {lock_zoom_x: boolean; lock_zoom_x_scale: boolean};
    title: string;
    title_url: string;
    data: TimeseriesFigureDataData[];
}

export interface SubPlotPlotDefinition {
    plot_type: string;
    id: string;
    label: string;
    use_tags: string[];
    stack_on?: string;
    is_scalar?: boolean;
    stack_values?: any;
    css_classes?: string[];
    color?: null | string;
    opacity?: number;
    shift_seconds?: number;
    shift_y?: number;
    scale_y?: number;
    is_shift?: boolean;
    hidden?: boolean;
}

export interface SingleValuePlotDefinition extends SubPlotPlotDefinition {
    plot_type: "single_value";
    metric: Record<string, Record<any, any>>;
}

export interface ScatterPlotPlotDefinition extends SubPlotPlotDefinition {
    plot_type: "scatterplot";
    color: string | null;
    metric: Record<string, Record<any, any>>;
}

export interface BarPlotPlotDefinition extends SubPlotPlotDefinition {
    plot_type: "bar";
    css_classes: string[];
}

export interface AreaPlotPlotDefinition extends SubPlotPlotDefinition {
    plot_type: "area";
    metric: Record<string, Record<any, any>>;
    style: string;
    status_display: Record<string, string>;
    color: string;
    opacity: number;
    stroke_width?: number;
}

export interface LinePlotPlotDefinition extends SubPlotPlotDefinition {
    stroke_width?: number;
}

export interface DrawSubplotStyles {
    fill: RGBColor | HSLColor | null | string;
    opacity?: string | number;
    stroke?: RGBColor | HSLColor | null;
    "stroke-width"?: number;
}

export interface Shift {
    shifted_id: string;
    seconds: number;
    color: string;
    label_suffix: string;
}

export interface Domain {
    x: [number, number];
    y: [number, number];
}
