/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import type {Dimension} from "crossfilter2";
import type {ScaleBand, ScaleLinear, Selection} from "d3";
import {axisRight, axisTop, max, range, scaleBand, scaleLinear} from "d3";

import {FigureBase} from "@/modules/figures/cmk_figures";
import {getIn, make_levels} from "@/modules/figures/cmk_figures_utils";
import type {
    BarplotDashletConfig,
    Domain,
    SingleMetricData,
    SingleMetricDataPlotDefinitions,
} from "@/modules/figures/figure_types";
import {domainIntervals, partitionableDomain} from "@/modules/number_format";

//Barplot Figures extends SingleMetricDashlet in python
// see cmk.gui.cee.plugins.dashboard.single_metric.SingleMetricDashlet
export class BarplotFigure extends FigureBase<
    SingleMetricData,
    BarplotDashletConfig
> {
    _time_dimension: Dimension<any, any>;
    _tag_dimension: Dimension<any, string>;
    _plot_definitions: SingleMetricDataPlotDefinitions[];
    bars!: Selection<SVGGElement, unknown, any, any>;
    scale_x!: ScaleLinear<number, number, never>;
    scale_y!: ScaleBand<string>;

    override ident() {
        return "barplot";
    }

    constructor(div_selector: string, fixed_size = null) {
        super(div_selector, fixed_size);
        this.margin = {top: 20, right: 10, bottom: 10, left: 10};

        this._time_dimension = this._crossfilter.dimension(d => d.timestamp);
        this._tag_dimension = this._crossfilter.dimension(d => d.tag);

        this._plot_definitions = [];
    }

    getEmptyData() {
        return {data: [], plot_definitions: [], title: "", title_url: ""};
    }

    override initialize() {
        this.svg = this._div_selection.append("svg").classed("renderer", true);
        this.plot = this.svg.append("g");
        this.bars = this.plot.append("g").classed("bars", true);

        // X axis
        this.scale_x = scaleLinear();
        this.plot
            .append("g")
            .classed("x_axis", true)
            .call(axisTop(this.scale_x));

        // Y axis
        this.scale_y = scaleBand().padding(0.2);
        this.plot
            .append("g")
            .classed("y_axis", true)
            .call(axisRight(this.scale_y));
    }

    override render() {
        if (this._data) this.update_gui();
    }

    override resize() {
        if (this._data.title) {
            this.margin.top = 20 + 24; // 24 from UX project
        } else {
            this.margin.top = 20;
        }
        FigureBase.prototype.resize.call(this);
        this.svg!.attr("width", this.figure_size.width).attr(
            "height",
            this.figure_size.height,
        );
        this.scale_x.range([0, this.plot_size.width]);
        this.scale_y.range([this.plot_size.height, 0]);
        this.plot.attr(
            "transform",
            "translate(" + this.margin.left + "," + this.margin.top + ")",
        );
    }

    _update_plot_definitions(
        plot_definitions: SingleMetricDataPlotDefinitions[],
    ) {
        this._plot_definitions = [];

        // We are only interested in the single_value plot types, they may include metrics info
        plot_definitions.forEach(plot_definition => {
            if (plot_definition.plot_type != "single_value") return;
            this._plot_definitions.push(plot_definition);
        });
    }

    render_grid(ticks: number[]) {
        // Grid
        const height = this.plot_size.height;
        this.plot
            .selectAll<SVGElement, null>("g.grid.vertical")
            .data([null])
            .join("g")
            .classed("grid vertical", true)
            .call(
                // @ts-ignore
                d3
                    .axisTop(this.scale_x)
                    .tickValues(ticks)
                    .tickSize(-height)
                    .tickFormat((_x, _y) => ""),
            );
    }

    override update_gui() {
        const data = this._data;
        this._update_plot_definitions(data.plot_definitions || []);
        if (data.plot_definitions.length == 0) return;
        this._crossfilter.remove(() => true);
        this._time_dimension.filterAll();
        this._crossfilter.add(data.data);

        // We expect, that all of the latest values have the same timestamp
        // Set the time dimension filter to the latest value
        // If this needs to be changed someday, simply iterate over all plot_definitions
        this._time_dimension.filter(
            d => d == this._time_dimension.top(1)[0].timestamp,
        );

        this.resize();
        this.render_title(data.title, data.title_url!);

        const domain = this.render_axis();
        this._render_values(domain);
    }

    render_axis(): Domain {
        const value_labels = this._plot_definitions.map(d => d.label);
        this.scale_y.domain(value_labels);
        const axis_labels = axisRight(this.scale_y);
        // 12 is UX font-height, omit labels when not enough space
        if (value_labels.length >= this.plot_size.height / 12)
            axis_labels.tickFormat((_x, _y) => "");

        this.plot
            .selectAll("g.y_axis")
            .classed("axis", true)
            // @ts-ignore
            .call(axis_labels)
            .selectAll("text")
            .attr("transform", `translate(0,${-this.scale_y.bandwidth() / 2})`);

        const used_tags = this._plot_definitions.map(d => d.use_tags[0]);
        const points = this._tag_dimension
            .filter(d => used_tags.includes(String(d)))
            .top(Infinity);

        const display_range = this._dashlet_spec.display_range;

        const tickcount = Math.max(2, Math.ceil(this.plot_size.width / 85));

        // @ts-ignore
        let x_domain: [number, number] = [0, max(points, d => d.value)];
        if (Array.isArray(display_range) && display_range[0] === "fixed")
            x_domain = display_range[1][1];

        const [min_val, max_val, step] = partitionableDomain(
            x_domain,
            tickcount,
            domainIntervals(
                getIn(this._plot_definitions[0], "metric", "unit", "stepping"),
            ),
        );

        const domain: Domain = [min_val, max_val];
        const tick_vals = range(min_val, max_val, step);

        this.scale_x.domain(domain);
        this._tag_dimension.filterAll();

        const render_function = this.get_scale_render_function();

        this.plot
            .selectAll("g.x_axis")
            .classed("axis", true)
            .style("text-anchor", "start")
            .call(
                // @ts-ignore
                d3
                    .axisTop(this.scale_x)
                    .tickValues(tick_vals)
                    .tickFormat(d => render_function(d).replace(/\.0+\b/, "")),
            );
        this.render_grid(range(min_val, max_val, step / 2));
        return domain;
    }

    _render_values(domain: Domain) {
        const points = this._plot_definitions.map(d => {
            let point = this._tag_dimension
                .filter(tag => tag == d.use_tags[0])
                .top(1)[0];
            if (point === undefined) point = {value: 0};

            const levels = make_levels(domain, d.metric!.bounds);
            point.level_style = levels.length
                ? levels.find(element => point.value < element.to)?.style
                : "metricstate state0";
            return {...d, ...point};
        });
        this.bars
            .selectAll<HTMLAnchorElement, any>("a")
            .data(points, d => d.id)
            .join("a")
            .attr("xlink:href", d => d.url)
            .selectAll("rect.bar")
            .data(d => [d])
            .join("rect")
            .classed("bar", true)
            .attr("y", d => (this.scale_y(d.label) ?? 0) + 6) // 6 is half the default font size. Thus bar stays bellow text
            .attr(
                "height",
                Math.max(Math.min(24, this.scale_y.bandwidth() - 12), 4),
            )
            .attr("width", d => this.scale_x(d.value))
            .attr("rx", 2)
            // @ts-ignore
            .classed(d => d.level_style);

        this._tag_dimension.filterAll();
    }
}
