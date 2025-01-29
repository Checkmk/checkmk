/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import type {BaseType, Path, Selection} from "d3";
import {extent, path, select} from "d3";

import type {FigureBase} from "./cmk_figures";
import type {
    Bounds,
    Domain,
    ElementSize,
    FigureData,
    Levels,
    TransformedData,
} from "./figure_types";
import type {Scheduler} from "./multi_data_fetcher";

/**
 * Draw an individual shape
 *
 * @callback pathCallback
 * @param {path} path - d3 path object to draw a shape with, it is filled with color to reflect the status.
 */

interface BackgroundStatueOptions {
    size?: {width: number; height: number};
    path_callback?: (path: Path) => void;
    css_class: string;
    visible: boolean;
}

/**
 * Component to draw a background color on a dashlet
 * @param {selection} selection - d3 object to draw on
 * @param {Object} options - Configuration of the background
 * @param {Object} options.size - When path_callback is not given draw a rect
 * @param {number} options.size.height - Height of the background rect
 * @param {number} options.size.width - Width of the background rect
 * @param {pathCallback} options.path_callback - Draw individual shape instead of rect
 * @param {string} options.css_class - Css classes to append to the background
 * @param {boolean} options.visible - Whether to draw the background at all
 */
export function background_status_component<GType extends BaseType, Data>(
    selection: Selection<GType, Data, BaseType, unknown>,
    options: BackgroundStatueOptions,
) {
    const data = options.visible ? [null] : [];

    const path_callback =
        options.path_callback ||
        function (path) {
            path.rect(0, 0, options.size!.width, options.size!.height);
        };

    const background_path = path();
    path_callback(background_path);

    selection
        .selectAll("path.status_background")
        .data(data)
        .join(enter => enter.insert("path", ":first-child"))
        .attr("class", `status_background ${options.css_class}`)
        .attr("d", background_path.toString());
}

interface MetricValueComponentOptions {
    font_size?: number;
    visible?: boolean;
    value: {
        url: string;
        unit?: string;
        value?: string;
    };
    position: {x: number; y: number};
}

export function calculate_domain(data: TransformedData[]): [number, number] {
    // @ts-ignore
    const [lower, upper] = extent(data, d => d.value);
    // @ts-ignore
    return [lower + upper * (1 - 1 / 0.95), upper / 0.95];
}

export function adjust_domain(domain: Domain, metrics: any): Domain {
    let [dmin, dmax] = domain;

    if (metrics.max != null && metrics.max <= dmax) dmax = metrics.max;
    if (metrics.min != null && dmin <= metrics.min) dmin = metrics.min;
    return [dmin, dmax];
}

export function clamp(value: number, domain: Domain) {
    return Math.min(Math.max(value, domain[0]), domain[1]);
}

export function make_levels(
    domain: Domain,
    bounds: Bounds,
): [Levels, Levels, Levels] | [] {
    let dmin = domain[0];
    const dmax = domain[1];
    if (bounds.warn == null || bounds.crit == null) return [];

    if (bounds.warn >= dmax) bounds.warn = dmax;
    if (bounds.crit >= dmax) bounds.crit = dmax;
    if (bounds.warn <= dmin) dmin = bounds.warn;

    return [
        {from: bounds.crit, to: dmax, style: "metricstate state2"},
        {
            from: bounds.warn,
            to: bounds.crit,
            style: "metricstate state1",
        },
        {from: dmin, to: bounds.warn, style: "metricstate state0"},
    ];
}

/**
 * Component to draw a big centered value on a dashlet
 * @param {selection} selection - d3 object to draw on
 * @param {Object} options - Configuration of the value
 * @param {Object} options.value - Configuration of the text to draw
 * @param {string} options.value.url - When given, add a link to the text
 * @param {string} options.value.unit - Append a unit to the value. e.g. '%'
 * @param {string} options.value.value - Text to display
 * @param {Object} options.position - Where to draw the Text
 * @param {number} options.position.x - X position relative to the center of the text
 * @param {number} options.position.y - Y position relative to the baseline of the text
 * @param {number} options.font_size - Size of the font, clamped to [12, 50]
 * @param {boolean} options.visible - Whether to draw the value at all
 */
export function metric_value_component<GType extends BaseType, Data>(
    selection: Selection<GType, Data, BaseType, unknown>,
    options: MetricValueComponentOptions,
) {
    const font_size = clamp(options.font_size!, [12, 50]);
    const data = options.visible ? [options.value] : [];

    const link = selection
        .selectAll("a.single_value")
        .data(data)
        .join("a")
        .classed("single_value", true)
        .attr("xlink:href", d => d.url || null);
    const text = link
        .selectAll("text")
        .data(d => [d])
        .join("text")
        .text(d => String(d.value))
        .attr("x", options.position.x)
        .attr("y", options.position.y)
        .attr("text-anchor", "middle")
        .attr("dominant-baseline", "central")
        .style("font-weight", "bold")
        .style("font-size", font_size + "px");

    const unit = text
        .selectAll("tspan")
        .data(d => (d.unit ? [d] : []))
        .join("tspan")
        .style("font-size", font_size / 2 + "px")
        .style("font-weight", "lighter")
        .text(d => String(d.unit));
    if (options.value.unit !== "%") {
        unit.attr("dx", font_size / 6 + "px").attr("dy", font_size / 8 + "px");
    }
}

interface BigCenteredTextOptions {
    font_size?: number;
    visible?: boolean;
    position?: {y?: number};
}

/**
 * Function to provide default options for metric_value_component
 * @param {Object} size - Size of container to draw to
 * @param {number} size.width - Width of container
 * @param {number} size.height - Height of container
 * @param {Object} options - Configuration the values
 * @param {number} options.font_size - Overwrite auto font_size (calculated by size)
 * @param {boolean} options.visible - Overwrite auto visible (true)
 * @param {Object} options.position - Overwrite a position value
 * @param {number} options.position.y - Overwrite y position
 *
 * The function provides the following options in the result:
 * * position
 * * font_size
 * * visible
 */
export function metric_value_component_options_big_centered_text(
    size: ElementSize,
    options: BigCenteredTextOptions,
) {
    if (options == undefined) {
        options = {};
    }

    let font_size = Math.min(size.width / 5, (size.height * 2) / 3);
    if (options.font_size !== undefined) {
        font_size = options.font_size;
    }

    let visible = true;
    if (options.visible !== undefined) {
        visible = options.visible;
    }

    const position_x = size.width / 2;

    let position_y = size.height / 2;
    if (options.position !== undefined && options.position.y !== undefined) {
        position_y = options.position.y;
    }

    return {
        position: {
            x: position_x,
            y: position_y,
        },
        font_size: font_size,
        visible: visible,
    };
}

interface StateComponentOptions {
    css_class: string;
    label: string;
    visible: boolean;
    font_size?: number;
}

/**
 * Component to draw a label at the bottom of the dashlet
 * @param {FigureBase} figurebase - Draw label on this dashlet
 * @param {Object} options - Configuration of the label
 * @param {string} options.label - Text to draw in the label
 * @param {string} options.css_class - Css classes to append to the label
 * @param {boolean} options.visible - Whether to draw the label at all
 * @param {string} options.font_size - Optional font size
 */
// Figure which inherited from FigureBase. Needs access to svg and size
export function state_component(
    figurebase: FigureBase<FigureData>,
    options: StateComponentOptions,
) {
    // TODO: use figurebase.svg as first parameter and move size to options
    if (!options.visible) {
        figurebase.svg!.selectAll(".state_component").remove();
        return;
    }
    //hard fix for the moment
    const font_size = options.font_size ? options.font_size : 14;
    const state_component = figurebase
        .svg!.selectAll(".state_component")
        .data([options])
        .join("g")
        .classed("state_component", true)
        .attr(
            "transform",
            "translate(" +
                (figurebase.figure_size.width - font_size * 8) / 2 +
                ", " +
                (figurebase.figure_size.height - font_size * 2) +
                ")",
        );
    state_component
        .selectAll("rect.status_label")
        .data(d => [d])
        .join("rect")
        .attr("class", d => `status_label ${d.css_class}`)
        // status_label css class is also defined for WATO and not encapsulated
        // it predifines other sizes, we use thus style instead of attr for size
        // to override that
        .style("width", font_size * 8)
        .style("height", font_size * 1.5)
        .attr("rx", 2);

    state_component
        .selectAll("text")
        .data(d => [d])
        .join("text")
        .attr("text-anchor", "middle")
        .attr("dx", font_size * 4)
        .attr("dy", font_size * 1.1)
        .style("font-size", font_size + "px")
        .style("fill", "black")
        .style("font-weight", "bold")
        .text(d => d.label);
} // Adhoc hack to extract the unit from a formatted string, which has units
export function getIn(object: any, ...args: any[]) {
    return args.reduce((obj, level) => obj && obj[level], object);
}

export function get_function(render_string: string) {
    return new Function(`"use strict"; return ${render_string}`)();
}

export function plot_render_function(plot: any) {
    const js_render = getIn(plot, "metric", "unit", "js_render");
    if (js_render) return get_function(js_render);
    //TODO: replace this function from string with a better solution
    return get_function(
        "function(v) { return cmk.number_format.fmt_number_with_precision(v, cmk.number_format.SIUnitPrefixes, 2, true); }",
    );
}

export function svc_status_css(paint: string, params: any) {
    const status_cls =
        getIn(params, "paint") === paint ? getIn(params, "css") || "" : "";
    if (status_cls.endsWith("0") && getIn(params, "status") === "not_ok")
        return "";
    return status_cls;
}

export function renderable_value(value: any, _domain: Domain, plot: any) {
    const formatter = plot_render_function(plot);
    return {
        ...split_unit(formatter(value.value)),
        url: value.url || "",
    };
}

// Once we migrate metric system to the frontend drop this
export function split_unit(formatted_value?: string) {
    if (!formatted_value) return {};
    // Separated by space, most rendered quantities
    const splitted_text = formatted_value.split(" ");
    if (splitted_text.length == 2)
        return {value: splitted_text[0], unit: splitted_text[1]};

    // Percentages have no space
    if (formatted_value.endsWith("%"))
        return {value: formatted_value.slice(0, -1), unit: "%"};

    // It's a counter, unitless
    return {value: formatted_value, unit: ""};
}

export function getEmptyBasicFigureData(): FigureData {
    return {data: [], plot_definitions: []};
}

/**
 * Component to realize the css property text-overflow: ellipsis for svg text elements
 * @param node - text/tspan element
 * @param {number} width - Max width for the text/tspan element
 * @param {number} padding - Padding for the text/tspan element
 */
export function svg_text_overflow_ellipsis(
    node: SVGTextElement | SVGTSpanElement,
    width: number,
    padding: number,
) {
    let length = node.getComputedTextLength();
    if (length <= width - padding) return;

    const node_sel = select(node);
    let text = node_sel.text();
    select(node.parentNode as HTMLElement)
        .selectAll("title")
        .data(() => [text])
        .join("title")
        .text(d => d)
        .classed("svg_text_tooltip", true);

    while (length > width - padding && text.length > 0) {
        text = text.slice(0, -1);
        node_sel.text(text + "...");
        length = node.getComputedTextLength();
    }
    node_sel.attr("x", padding).attr("text-anchor", "left");
}

export function add_scheduler_debugging<GType extends BaseType, Data>(
    selection: Selection<GType, Data, BaseType, unknown>,
    scheduler: Scheduler,
) {
    const debugging = selection.append("div");
    // Stop button
    debugging
        .append("input")
        .attr("type", "button")
        .attr("value", "Stop")
        .on("click", () => scheduler.disable());
    // Start button
    debugging
        .append("input")
        .attr("type", "button")
        .attr("value", "Start")
        .on("click", () => scheduler.enable());
    // Suspend 5 seconds
    debugging
        .append("input")
        .attr("type", "button")
        .attr("value", "Suspend 5 seconds")
        .on("click", () => scheduler.suspend_for(5));
    // Force update
    debugging
        .append("input")
        .attr("type", "button")
        .attr("value", "Force")
        .on("click", () => scheduler.force_update());
}
