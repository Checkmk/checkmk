/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import type {Dimension} from "crossfilter2";
import type {BaseType, Quadtree, Selection} from "d3";
import {
    area,
    color as d3_Color,
    curveLinear,
    line,
    max,
    min,
    quadtree,
    select,
} from "d3";

import type {
    AreaPlotPlotDefinition,
    BarPlotPlotDefinition,
    Domain,
    DrawSubplotStyles,
    LinePlotPlotDefinition,
    ScatterPlotPlotDefinition,
    SingleValuePlotDefinition,
    SubPlotPlotDefinition,
    TimeseriesFigureDataData,
} from "@/modules/figures/cmk_enterprise_figure_types";
import {
    adjust_domain,
    background_status_component,
    calculate_domain,
    getIn,
    metric_value_component,
    metric_value_component_options_big_centered_text,
    renderable_value,
    state_component,
    svc_status_css,
} from "@/modules/figures/cmk_figures_utils";
import type {
    SubplotDataData,
    TransformedData,
} from "@/modules/figures/figure_types";

import type {SubplotSubs, TimeseriesFigure} from "./cmk_timeseries";
import {SubPlotFactory} from "./sub_plot_factory";

// Base class for all SubPlots
// It renders its data into a <g> provided by the renderer instance
export class SubPlot<PD extends SubPlotPlotDefinition = SubPlotPlotDefinition> {
    definition: PD | null;
    _renderer: TimeseriesFigure | null;
    _dimension: Dimension<any, any> | null;
    transformed_data: TransformedData[];
    stack_values: null | number[];
    main_g: Selection<SVGGElement, unknown, BaseType, unknown> | null;
    svg: Selection<SVGSVGElement, unknown, BaseType, unknown> | null;
    marked_for_removal: boolean | undefined;

    constructor(definition: PD | null) {
        this.definition = definition;
        this._renderer = null; // Graph which renders this plot
        this._dimension = null; // The crossfilter dimension (x_axis)
        this.transformed_data = []; // data shifted/scaled by subplot definition

        this.stack_values = null; // timestamp/value pairs provided by the target plot

        this.main_g = null; // toplevel g, contains svg/canvas elements
        this.svg = null; // svg content
        return this;
    }

    _get_css(prop: string, tag: string, classes: string[]) {
        const obj = this.svg!.append(tag);
        classes.forEach(cls => obj.classed(cls, true));
        const css = obj.style(prop);
        obj.remove();
        return css;
    }

    renderer(renderer: TimeseriesFigure) {
        if (!arguments.length) {
            return this._renderer;
        }
        this._renderer = renderer;
        this.prepare_render();
        return this;
    }

    remove() {
        this.main_g!.transition().duration(1000).style("opacity", 0).remove();
    }

    get_color() {
        if (this.definition!.color) return d3_Color(this.definition!.color);
        return;
    }

    get_opacity(): number {
        if (this.definition!.opacity) return this.definition!.opacity;
        return 1;
    }

    dimension(dimension: Dimension<any, any>) {
        if (!arguments.length) {
            return this._dimension;
        }
        this._dimension = dimension;
        return this;
    }

    get_domains(): Domain | undefined {
        // Return the x/y domain boundaries
        if (this.definition!.is_scalar) return;

        return {
            x: [
                // @ts-ignore
                min(this.transformed_data, d => d.date),
                // @ts-ignore
                max(this.transformed_data, d => d.date),
            ],
            // @ts-ignore
            y: [0, max(this.transformed_data, d => d.value)],
        };
    }

    get_legend_data(start: number, end: number): SubplotDataData {
        // Returns the currently shown x/y domain boundaries
        if (this.definition!.is_scalar) return {data: this.transformed_data};

        const data = this.transformed_data.filter(d => {
            return d.timestamp >= start && d.timestamp <= end;
        });

        const value_accessor =
            this.definition!.stack_on && this.definition!.stack_values
                ? "unstacked_value"
                : "value";
        return {
            // @ts-ignore
            x: [min(data, d => d.date), max(data, d => d.date)],
            // @ts-ignore
            y: [0, max(data, d => d[value_accessor])],
            data: data,
        };
    }

    prepare_render() {
        const plot_size = this._renderer!.plot_size;

        // The subplot main_g contains all graphical components for this subplot
        // @ts-ignore
        this.main_g = this._renderer!.g.selectAll(
            "g.subplot_main_g." + this.definition!.id,
        )
            .data([null])
            .join("g")
            .classed("subplot_main_g", true)
            .classed(this.definition!.id, true);

        if (this.definition!.css_classes)
            this.main_g!.classed(this.definition!.css_classes.join(" "), true);

        // Default drawing area
        // @ts-ignore
        this.svg = this.main_g!.selectAll("svg.subplot")
            .data([null])
            .join("svg")
            .attr("width", Math.max(0.0, plot_size.width))
            .attr("height", Math.max(0.0, plot_size.height))
            .classed("subplot", true);
    }

    // Currently unused. Handles the main_g of SubPlots between different TimeseriesFigure instances
    migrate_to(other_renderer: TimeseriesFigure) {
        let delta: null | {x: number; y: number} = null;
        if (this._renderer) {
            this._renderer.remove_plot(this);
            const old_box = this._renderer._div_selection
                .node()!
                .getBoundingClientRect();
            const new_box = other_renderer._div_selection
                .node()!
                .getBoundingClientRect();
            delta = {x: old_box.x - new_box.x, y: old_box.top - new_box.top};
        }
        other_renderer.add_plot(this);
        if (delta) {
            other_renderer.g
                .select(".subplot_main_g." + this.definition!.id)
                .attr("transform", "translate(" + delta.x + "," + delta.y + ")")
                .transition()
                .duration(2500)
                .attr("transform", "translate(0,0) scale(1)");
        }

        // TODO: Refactor, introduces dashlet dependency
        const dashlet = select(
            other_renderer._div_selection.node()!.closest(".dashlet"),
        );
        if (!dashlet.empty())
            dashlet
                .style("z-index", 1000)
                .transition()
                .duration(2000)
                .style("z-index", 0);

        other_renderer.remove_loading_image();
        other_renderer.update_gui();
    }

    get_coord_shifts() {
        const shift_seconds = this.definition!.shift_seconds || 0;
        const shift_y = this.definition!.shift_y || 0;
        const scale_y = this.definition!.scale_y || 1;
        return [shift_seconds, shift_y, scale_y];
    }

    update_transformed_data() {
        const shifts = this.get_coord_shifts();
        const shift_second = shifts[0];
        const shift_y = shifts[1];
        const scale_y = shifts[2];

        let data = this._dimension!.top(Infinity);
        data = data.filter(d => d.tag == this.definition!.use_tags[0]);
        //let data = this._dimension.filter(d=>d.tag == this.definition.use_tags[0]).top(Infinity);
        //this._dimension.filterAll();

        // Create a deepcopy
        this.transformed_data = JSON.parse(JSON.stringify(data));
        this.transformed_data.forEach(point => {
            point.timestamp += shift_second;
            point.date = new Date(point.timestamp * 1000);
        });

        if (shift_y != 0)
            this.transformed_data.forEach(point => {
                point.value += shift_y;
            });

        if (scale_y != 1)
            this.transformed_data.forEach(point => {
                point.value *= scale_y;
            });

        if (this.stack_values != null)
            this.transformed_data.forEach(point => {
                point.unstacked_value = point.value;
                point.value += this.stack_values![point.timestamp] || 0;
            });
    }

    ident(): string {
        throw Error("Method not implemented");
    }
}

function line_draw_fn(subplot: SubplotSubs) {
    return (
        line()
            .curve(curveLinear)
            // @ts-ignore
            .x(d => subplot._renderer.scale_x(d.date))
            // @ts-ignore
            .y(d => subplot._renderer.scale_y(d.value))
    );
}

function area_draw_fn(subplot: SubplotSubs) {
    const shift_y = subplot.get_coord_shifts()[1];
    const base = subplot._renderer!.scale_y(shift_y);
    return (
        area()
            .curve(curveLinear)
            // @ts-ignore
            .x(d => subplot._renderer.scale_x(d.date))
            // @ts-ignore
            .y1(d => subplot._renderer.scale_y(d.value))
            .y0(d => {
                if (subplot.stack_values != null)
                    return subplot._renderer!.scale_y(
                        // @ts-ignore
                        subplot.stack_values[d.timestamp] || 0,
                    );
                else return base;
            })
    );
}

function graph_data_path(
    subplot: SubplotSubs,
    path_type: string,
    status_cls: string,
) {
    return subplot
        .svg!.selectAll("g.graph_data path." + path_type)
        .data([subplot.transformed_data])
        .join(enter =>
            enter.append("g").classed("graph_data", true).append("path"),
        )
        .attr("class", `${path_type}${status_cls ? " " + status_cls : ""}`)
        .classed((subplot.definition!.css_classes || []).join(" "), true);
}

function draw_subplot(
    subplot: SubplotSubs,
    path_type: string,
    status_cls: string,
    styles: DrawSubplotStyles,
) {
    const path = graph_data_path(subplot, path_type, status_cls);
    const path_fn = (path_type === "line" ? line_draw_fn : area_draw_fn)(
        subplot,
    );

    const plot = subplot
        ._renderer!.transition(path)
        .attr("d", (d: [number, number][] | Iterable<[number, number]>) =>
            path_fn(d),
        );
    if (!status_cls)
        Object.entries(styles).forEach(([property, value]) =>
            plot.style(property, value),
        );
}

// Renders a single uninterrupted line
export class LinePlot extends SubPlot<LinePlotPlotDefinition> {
    override ident() {
        return "line";
    }

    render() {
        draw_subplot(this, "line", "", {
            fill: "none",
            opacity: this.get_opacity() || 1,
            stroke: this.get_color(),
            "stroke-width": this.definition!.stroke_width || 2,
        });
    }

    override get_color() {
        const color = SubPlot.prototype.get_color.call(this);
        const classes = (this.definition!.css_classes || []).concat("line");
        return color != undefined
            ? color
            : d3_Color(this._get_css("stroke", "path", classes));
    }
}

// Renders an uninterrupted area
export class AreaPlot extends SubPlot<AreaPlotPlotDefinition> {
    override ident() {
        return "area";
    }

    render() {
        const color = this.get_color();
        const svc_status_display = getIn(this, "definition", "status_display");
        let status_cls = svc_status_css("background", svc_status_display);
        // Give svcstate class default, when stautus in plot_def, otherwise plot_def style overtakes
        if (svc_status_display && !status_cls) status_cls = "svcstate";

        draw_subplot(this, "area", status_cls, {
            fill: color,
            opacity: this.get_opacity(),
        });
        if (this.definition!.style === "with_topline")
            draw_subplot(this, "line", status_cls, {
                "stroke-width": this.definition!.stroke_width || 2,
                fill: "none",
                stroke: color,
            });
    }

    override get_color() {
        const color = SubPlot.prototype.get_color.call(this);
        const classes = (this.definition!.css_classes || []).concat("area");
        return color != undefined
            ? color
            : d3_Color(this._get_css("fill", "path", classes));
    }

    override get_opacity() {
        const opacity = this.definition!.opacity;
        const classes = (this.definition!.css_classes || []).concat("area");
        return opacity != undefined
            ? opacity
            : Number(this._get_css("opacity", "path", classes));
    }
}

// Renders multiple bars, each based on date->end_date
export class BarPlot extends SubPlot<BarPlotPlotDefinition> {
    _bars!: Selection<SVGRectElement, TransformedData, SVGSVGElement, unknown>;

    override ident() {
        return "bar";
    }

    render() {
        const plot_size = this._renderer!.plot_size;
        const bars = this.svg!.selectAll<SVGRectElement, unknown>(
            "rect.bar",
        ).data(this.transformed_data);
        bars.exit().remove();

        const classes = this.definition!.css_classes || [];
        const bar_spacing = classes.includes("barbar_chart") ? 2 : 4;
        const css_classes = classes.concat("bar").join(" ");

        this._bars = bars
            .enter()
            .append("a")
            .attr("xlink:href", d => d.url!)
            .append("rect")
            // Add new bars
            .each((_d: TransformedData, idx: number, nodes) =>
                this._renderer!.tooltip_generator.add_support(nodes[idx]),
            )
            .classed("bar", true)
            .attr("y", plot_size.height)
            .merge(bars)
            // Update new and existing bars
            .attr("x", d => this._renderer!.scale_x(d.date))
            .attr(
                "width",
                (d: TransformedData) =>
                    this._renderer!.scale_x(
                        new Date(d.ending_timestamp! * 1000),
                    ) -
                    this._renderer!.scale_x(d.date) -
                    bar_spacing,
            )
            .attr("class", css_classes);

        this._renderer!.transition(this._bars)
            .style("opacity", this.get_opacity())
            .attr("fill", this.get_color())
            .attr("rx", 2)
            .attr(
                "y",
                (d: TransformedData) => this._renderer!.scale_y(d.value) - 1,
            )
            .attr("height", (d: TimeseriesFigureDataData) => {
                let y_base = 0;
                if (this.stack_values != null)
                    y_base = this.stack_values[d.timestamp] || 0;
                return (
                    plot_size.height -
                    this._renderer!.scale_y(d.value - y_base) +
                    1
                );
            });
    }

    override get_color() {
        const color = SubPlot.prototype.get_color.call(this);
        const classes = (this.definition!.css_classes || []).concat("bar");
        return color != undefined
            ? color
            : d3_Color(this._get_css("fill", "rect", classes));
    }
}

// Renders a single value
// Per default, the latest timestamp of the given timeline is used
export class SingleValuePlot extends SubPlot<SingleValuePlotDefinition> {
    override ident() {
        return "single_value";
    }

    render() {
        const domain = adjust_domain(
            calculate_domain(this.transformed_data),
            this.definition!.metric.bounds,
        );

        const last_value = this.transformed_data.find(
            element => element.last_value,
        );
        const value = renderable_value(last_value, domain, this.definition);

        const plot_size = this._renderer!.plot_size;
        const svc_status_display = getIn(this, "definition", "status_display");

        const background_status_cls = svc_status_css(
            "background",
            svc_status_display,
        );
        const label_paint_style = getIn(svc_status_display, "paint");
        const label_status_cls = svc_status_css(
            label_paint_style,
            svc_status_display,
        );
        const state_font_size = 14;
        const state_is_visible = label_paint_style && label_status_cls;

        background_status_component(this.svg!, {
            size: {
                width: plot_size.width,
                height: plot_size.height,
            },
            css_class: background_status_cls,
            visible: background_status_cls !== "",
        });

        state_component(this._renderer!, {
            visible: state_is_visible,
            label: svc_status_display.msg,
            css_class: label_status_cls,
            font_size: state_font_size,
        });

        metric_value_component(this.svg!, {
            value: value,
            ...metric_value_component_options_big_centered_text(plot_size, {
                position: {
                    y:
                        (plot_size.height -
                            (state_is_visible ? 1.5 * state_font_size : 0)) /
                        2,
                },
            }),
        });
    }

    override get_color() {
        return d3_Color("white");
    }
}

// Provides quadtree to find points on canvas
export class ScatterPlot extends SubPlot<ScatterPlotPlotDefinition> {
    quadtree: null | Quadtree<TransformedData>;
    canvas: null | Selection<
        HTMLCanvasElement,
        {width: number; height: number},
        BaseType,
        null
    >;
    _last_canvas_size!: {width: number; height: number};

    override ident() {
        return "scatterplot";
    }

    constructor(definition: ScatterPlotPlotDefinition) {
        super(definition);
        this.quadtree = null;
        this.canvas = null;
        return this;
    }

    override prepare_render() {
        SubPlot.prototype.prepare_render.call(this);
        const plot_size = this._renderer!.plot_size;
        const fo = this.main_g!.selectAll("foreignObject.canvas_object")
            .data([plot_size])
            .join("foreignObject")
            .style("pointer-events", "none")
            .classed("canvas_object", true)
            .attr("width", d => d.width)
            .attr("height", d => d.height);

        const body = fo
            .selectAll("xhtml")
            .data([null])
            .join("xhtml")
            .style("margin", "0px");

        this.canvas = body
            .selectAll<HTMLCanvasElement, unknown>("canvas")
            .data([plot_size])
            .join("canvas")
            .classed("subplot", true)
            .attr("x", 0)
            .attr("y", 0)
            .attr("width", d => d.width)
            .attr("height", d => d.height);
    }

    render() {
        const scale_x = this._renderer!.scale_x;
        const scale_y = this._renderer!.scale_y;
        this.transformed_data.forEach(point => {
            point.scaled_x = scale_x(point.date);
            point.scaled_y = scale_y(point.value);
        });

        this.quadtree = quadtree<TransformedData>()
            .x(d => d.scaled_x)
            .y(d => d.scaled_y)
            .addAll(this.transformed_data);
        this.redraw_canvas();
    }

    redraw_canvas() {
        const plot_size = this._renderer!.plot_size;
        const ctx = this.canvas!.node()!.getContext("2d");
        if (!this._last_canvas_size) this._last_canvas_size = plot_size;

        ctx!.clearRect(
            -1,
            -1,
            this._last_canvas_size.width + 2,
            this._last_canvas_size.height + 2,
        );
        const canvas_data = ctx!.getImageData(
            0,
            0,
            plot_size.width,
            plot_size.height,
        );

        const color = this.get_color();
        // @ts-ignore
        const r = color.r;
        // @ts-ignore
        const b = color.b;
        // @ts-ignore
        const g = color.g;
        this.transformed_data.forEach(point => {
            if (point.scaled_x > plot_size.width || point.scaled_x < 0) return;
            const index =
                (Math.trunc(point.scaled_x) +
                    Math.trunc(point.scaled_y) * plot_size.width) *
                4;
            canvas_data.data[index] = r;
            canvas_data.data[index + 1] = g;
            canvas_data.data[index + 2] = b;
            canvas_data.data[index + 3] = 255;
        });
        ctx!.putImageData(canvas_data, 0, 0);
        this._last_canvas_size = plot_size;
    }

    override get_color() {
        const color = SubPlot.prototype.get_color.call(this);
        return color != undefined
            ? color
            : d3_Color(this._get_css("fill", "circle", ["scatterdot"]));
    }
}

export const subplot_factory = new SubPlotFactory(); // Renders scatterplot points on a canvas
subplot_factory.register(LinePlot);
subplot_factory.register(AreaPlot);
subplot_factory.register(ScatterPlot);
subplot_factory.register(BarPlot);
subplot_factory.register(SingleValuePlot);
