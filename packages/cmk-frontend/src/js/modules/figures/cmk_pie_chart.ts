/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import {arc, scaleOrdinal, schemeCategory10, pie, PieArcDatum} from "d3";

import {FigureBase} from "@/modules/figures/cmk_figures";
import {add_scheduler_debugging} from "@/modules/figures/cmk_figures_utils";
import {FigureData} from "@/modules/figures/figure_types";

export interface PieChartData {
    index: number;
    ident: string;
    label: string;
    value: number;
}

export interface PieChartConfig extends FigureData<PieChartData> {
    title: string;
    title_url: string;
}

export class PieChartFigure extends FigureBase<PieChartConfig> {
    _radius!: number;
    _hide_percentile_smaller_than: number;

    override ident() {
        return "pie_chart";
    }

    constructor(div_selector: string, fixed_size = null) {
        super(div_selector, fixed_size);
        this.margin = {top: 10, right: 10, bottom: 10, left: 10};
        this._hide_percentile_smaller_than = 5;
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
    }

    override update_gui() {
        this.resize();
        this.render();
    }

    override render() {
        this.render_title(this._data.title, this._data.title_url!);
        if (!Array.isArray(this._data.data)) return; // invalid data, not a list
        const radius =
            Math.min(this.figure_size.width, this.figure_size.height) / 3;

        const svg = this.svg!.attr("width", this.figure_size.width)
            .attr("height", this.figure_size.height)
            .selectAll("g.pie")
            .data([this._data.data])
            .join("g")
            .classed("pie", true)
            .attr(
                "transform",
                `translate(${this.figure_size.width / 2},${this.figure_size.height / 2})`,
            );

        const arcs = svg
            .selectAll<SVGGElement, PieArcDatum<PieChartData>>("g.arc")
            .data(
                data => pie<PieChartData>().value(d => d.value)(data),
                d => d.data.ident,
            )
            .join("g")
            .classed("arc", true);

        const color = scaleOrdinal(schemeCategory10);
        arcs.selectAll("path")
            .data(d => [d])
            .join("path")
            .transition()
            .attr(
                "d",
                arc<PieArcDatum<PieChartData>>()
                    .innerRadius(radius - 50)
                    .outerRadius(radius),
            )
            .attr("fill", d => {
                return color(d.data.index.toString());
            });

        arcs.selectAll("title")
            .data(d => [d])
            .join("title")
            .text(d =>
                d.data.label
                    .concat(": ")
                    .concat((d.data.value || "").toString()),
            );

        const labelOffset = 30;
        const labelRadius = radius + labelOffset;
        arcs.selectAll("text")
            .data(d => [d])
            .join("text")
            .transition()
            .attr(
                "x",
                d => Math.sin((d.startAngle + d.endAngle) / 2) * labelRadius,
            )
            .attr(
                "y",
                d => -Math.cos((d.startAngle + d.endAngle) / 2) * labelRadius,
            )
            .attr("text-anchor", "middle")
            .attr("alignment-baseline", "middle")
            .attr("font-size", "12px")
            .text(d => {
                if (
                    (d.endAngle - d.startAngle) / (2 * Math.PI) <
                    this._hide_percentile_smaller_than / 100
                )
                    return "";
                return d.data.label;
            });
    }
}
