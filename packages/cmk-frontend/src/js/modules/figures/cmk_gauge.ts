/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import type {Dimension} from "crossfilter2";
import type {ScaleLinear} from "d3";
import {arc, histogram, max, range, scaleLinear} from "d3";

import {FigureBase} from "@/modules/figures/cmk_figures";
import {
    add_scheduler_debugging,
    adjust_domain,
    background_status_component,
    calculate_domain,
    clamp,
    getIn,
    make_levels,
    metric_value_component,
    plot_render_function,
    renderable_value,
    state_component,
    svc_status_css,
} from "@/modules/figures/cmk_figures_utils";
import type {
    Domain,
    GaugeDashletConfig,
    Levels,
    SingleMetricData,
    SingleMetricDataPlotDefinitions,
} from "@/modules/figures/figure_types";

// Used for rapid protoyping, bypassing webpack
// var cmk_figures = cmk.figures; /* eslint-disable-line no-undef */
// var d3 = d3; /* eslint-disable-line no-undef */
// var crossfilter = crossfilter; /* eslint-disable-line no-undef */

export class GaugeFigure extends FigureBase<
    SingleMetricData,
    GaugeDashletConfig
> {
    _tag_dimension: any[] | Dimension<any, any>;
    _radius!: number;

    override ident() {
        return "gauge";
    }

    constructor(div_selector: string, fixed_size = null) {
        super(div_selector, fixed_size);
        this._tag_dimension = this._crossfilter.dimension(d => d.tag);
        this.margin = {top: 10, right: 10, bottom: 10, left: 10};
    }

    getEmptyData() {
        return {
            title_url: "",
            title: "",
            data: [],
            plot_definitions: [],
        };
    }

    override initialize(debug?: boolean) {
        if (debug) add_scheduler_debugging(this._div_selection, this.scheduler);
        this.svg = this._div_selection.append("svg");
        this.plot = this.svg.append("g");
    }

    override resize() {
        if (this._data.title) {
            this.margin.top = 10 + 24; // 24 from UX project
        } else {
            this.margin.top = 10;
        }

        FigureBase.prototype.resize.call(this);
        this.svg!.attr("width", this.figure_size.width).attr(
            "height",
            this.figure_size.height,
        );
        this._radius = Math.min(
            this.plot_size.width / 2,
            (3 / 4) * this.plot_size.height,
        );
        this.plot.attr(
            "transform",
            "translate(" +
                (this.plot_size.width / 2 + this.margin.left) +
                ", " +
                (this._radius + this.margin.top) +
                ")",
        );
        this._render_fixed_elements();
    }

    override update_gui() {
        this._crossfilter.remove(() => true);
        this._crossfilter.add(this._data.data);

        let filter_tag: string | null = null;
        if (
            this._data.plot_definitions &&
            this._data.plot_definitions.length > 0
        )
            filter_tag =
                this._data.plot_definitions[
                    this._data.plot_definitions.length - 1
                ].use_tags[0];
        // @ts-ignore
        this._tag_dimension.filter((d: string) => d == filter_tag);

        this.resize();
        this.render();
    }

    override render() {
        this._render_levels();
        this.render_title(this._data.title, this._data.title_url!);
    }

    _render_fixed_elements() {
        const limit = (7 * Math.PI) / 12;
        this.plot
            .selectAll<SVGPathElement, null>("path.gauge_span")
            .data([null])
            .join(enter => enter.append("path").classed("gauge_span", true))
            .attr(
                "d",
                arc<null>()
                    .innerRadius(this._radius * 0.75)
                    .outerRadius(this._radius * 0.85)
                    .startAngle(-limit)
                    .endAngle(limit),
            );
    }

    _render_gauge_range_labels(
        domain: Domain,
        formatter: (nr: number) => string,
    ) {
        const limit = (15 * Math.PI) / 24;
        const label_rad = 0.8 * this._radius;
        const domain_labels = [
            {
                value: formatter(domain[0]),
                y: -label_rad * Math.cos(limit),
                x: label_rad * Math.sin(-limit),
            },
            {
                value: formatter(domain[1]),
                y: -label_rad * Math.cos(limit),
                x: label_rad * Math.sin(limit),
            },
        ];

        this.plot
            .selectAll("text.range")
            .data(domain_labels)
            .join("text")
            .classed("range", true)
            .text(d => d.value)
            .attr("text-anchor", "middle")
            .style("font-size", "8pt")
            .attr("x", d => d.x)
            .attr("y", d => d.y);
    }

    _render_levels() {
        const data = this._crossfilter.allFiltered();
        const plot = this._data.plot_definitions.filter(
            d => d.plot_type == "single_value",
        )[0];
        if (!data.length || !plot || !plot.metric.bounds) {
            this.plot.selectAll("path.level").remove();
            this.plot.selectAll("path.single_value").remove();
            this.plot.selectAll("a.single_value").remove();
            return;
        }

        const display_range = this._dashlet_spec.display_range;

        let domain = adjust_domain(
            //@ts-ignore
            calculate_domain(data),
            plot.metric.bounds,
        );
        if (Array.isArray(display_range) && display_range[0] === "fixed")
            domain = display_range[1][1];

        domain.sort(); // Safeguards against negative number ordering or bad order. Display and clamp need good order
        const formatter = plot_render_function(plot);

        this._render_gauge_range_labels(domain, formatter);

        if (domain[0] === domain[1]) return;
        const limit = (7 * Math.PI) / 12;
        const scale_x = scaleLinear().domain(domain).range([-limit, limit]);
        // this.metric_thresholds_stripe(plot, domain, scale_x);
        // gauge bar
        const last_value = data[data.length - 1];
        const value = renderable_value(last_value, domain, plot);
        this.plot
            .selectAll("path.single_value")
            .data([{...value, value: clamp(last_value.value, domain)}])
            .join("path")
            .attr("class", "single_value")
            .attr(
                "d",
                // @ts-ignore
                d3
                    .arc()
                    .innerRadius(this._radius * 0.75)
                    .outerRadius(this._radius * 0.85)
                    .startAngle(() => -limit)
                    // @ts-ignore
                    .endAngle(d => scale_x(d.value)),
            );

        const svc_status_display = getIn(plot, "status_display");

        const background_status_cls = svc_status_css(
            "background",
            svc_status_display,
        );
        const label_paint_style = getIn(svc_status_display, "paint");
        const label_status_cls = svc_status_css(
            label_paint_style,
            svc_status_display,
        );

        background_status_component(this.plot, {
            path_callback: path =>
                path.arc(
                    0,
                    0,
                    this._radius * 0.69,
                    (-13 * Math.PI) / 12,
                    Math.PI / 12,
                    false,
                ),
            css_class: background_status_cls,
            visible: background_status_cls !== "",
        });
        state_component(this, {
            visible: label_paint_style && label_status_cls,
            label: svc_status_display.msg,
            css_class: label_status_cls,
        });
        metric_value_component(this.plot, {
            value: value,
            position: {
                x: 0,
                y: -this._radius / 10,
            },
            font_size: this._radius / 3,
            visible: true,
        });

        if (data.length > 10) this._render_histogram(domain, data);
    }

    metric_thresholds_stripe(
        plot: SingleMetricDataPlotDefinitions,
        domain: Domain,
        scale_x: ScaleLinear<number, number>,
    ) {
        this.plot
            .selectAll<SVGPathElement, Levels>("path.level")
            .data(make_levels(domain, plot.metric.bounds))
            .join(enter => enter.append("path"))
            .attr("class", d => "level " + d.style)
            .attr(
                "d",
                arc<Levels>()
                    .innerRadius(this._radius * 0.71)
                    .outerRadius(this._radius * 0.73)
                    .startAngle(d => scale_x(d.from))
                    .endAngle(d => scale_x(d.to)),
            )
            .selectAll("title")
            .data(d => [d])
            .join("title")
            .text(d => d.from + " -> " + d.to);
    }
    _render_histogram(domain: Domain, data: any[]) {
        const num_bins = 40;
        const x = scaleLinear().domain([0, num_bins]).range(domain);
        const bins = histogram()
            // @ts-ignore
            .value(d => d.value)
            .thresholds(range(num_bins).map(x))
            // @ts-ignore
            .domain(x.range())(data);

        const record_count = data.length;
        const innerRadius = this._radius * 0.87;
        const bin_scale = scaleLinear()
            // @ts-ignore
            .domain([0, max(bins, d => d.length)])
            .range([innerRadius, this._radius]);
        const limit = (7 * Math.PI) / 12;
        const angle_between_bins = (2 * limit) / bins.length;
        const bin_spacing = angle_between_bins * 0.05;
        this.plot
            .selectAll("path.bin")
            .data(bins)
            .join(enter => enter.append("path").classed("bin", true))
            .attr("fill", "#546679")
            .attr(
                "d",
                // @ts-ignore
                arc()
                    .innerRadius(innerRadius)
                    .outerRadius(
                        // @ts-ignore
                        d => bin_scale(d.length) + (d.length > 0 ? 2 : 0),
                    )
                    .startAngle((_d, idx) => -limit + idx * angle_between_bins)
                    .endAngle(
                        (_d, idx) =>
                            -limit +
                            (idx + 1) * angle_between_bins -
                            bin_spacing,
                    ),
            )
            .selectAll("title")
            .data(d => [d])
            .join("title")
            .text(d => {
                let title = "";
                // @ts-ignore
                if (d.length == 0) return title;
                // @ts-ignore
                title += ((100.0 * d.length) / record_count).toPrecision(3);
                // @ts-ignore
                title += "%: " + d.x0.toPrecision(3);
                // @ts-ignore
                title += " -> " + d.x1.toPrecision(3);
                return title;
            });
    }
}
