/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import {bisector, line as d3_line} from "d3";

import {figure_registry} from "@/modules/figures/cmk_figures";
import {getIn, plot_render_function} from "@/modules/figures/cmk_figures_utils";
import type {
    AverageScatterplotDashletConfig,
    TransformedData,
} from "@/modules/figures/figure_types";

import {TimeseriesFigure} from "./cmk_timeseries";
import type {ScatterPlot} from "./sub_plot";

// A generic average scatterplot chart with median/mean lines and scatterpoints for each instance
// Requirements:
//     Subplots with id
//       - id_scatter
//       - id_mean
//       - id_median
//     Data tagged with
//       - line_mean
//       - line_median
//       - scatter
export class AverageScatterplotFigure extends TimeseriesFigure<AverageScatterplotDashletConfig> {
    _selected_scatterpoint: TransformedData | undefined;
    _selected_meanpoint: TransformedData | undefined;

    override ident() {
        return "average_scatterplot";
    }

    override _mouse_down(event: MouseEvent) {
        // event.button == 1 equals a pressed mouse wheel
        if (event.button == 1 && this._selected_scatterpoint) {
            window.open(this._selected_scatterpoint.url);
        }
    }

    override _mouse_click(_event: MouseEvent) {
        if (this._selected_scatterpoint)
            //@ts-ignore
            window.location = this._selected_scatterpoint.url;
    }

    override _mouse_out(_event: MouseEvent) {
        this.g.select("path.pin").remove();
        this._tooltip.selectAll("table").remove();
        this._tooltip.style("opacity", 0);
        this.tooltip_generator?.deactivate();
    }

    override _mouse_move(event: MouseEvent) {
        //TODO: layerX/layerY is non-standard and is not on a standards track. It will not work for every user.
        // see: https://developer.mozilla.org/en-US/docs/Web/API/MouseEvent/layerY
        // TODO KO: clean up these mouse events for better performance
        if (
            !["svg", "path"].includes((<HTMLElement>event.target).tagName) ||
            //@ts-ignore
            event.layerX < this.margin.left ||
            //@ts-ignore
            event.layerY < this.margin.top ||
            //@ts-ignore
            event.layerX > this.margin.left + this.plot_size.width ||
            //@ts-ignore
            event.layerY > this.margin.top + this.plot_size.height
        ) {
            this._mouse_out(event);
            return;
        }
        if (!this._crossfilter || !this._subplots_by_id["id_scatter"]) return;

        // TODO AB: change this dimensions to members
        //          filter_dimension -> tag_dimension
        //          result_dimension -> date_dimension
        const filter_dimension = this._crossfilter.dimension(d => d);
        const timestamp_dimension = this._crossfilter.dimension<number>(
            d => d.timestamp,
        );

        // Find focused scatter point and highlight it
        const scatter_plot = this._subplots_by_id["id_scatter"] as ScatterPlot;
        const scatter_point = scatter_plot.quadtree!.find(
            //@ts-ignore
            event.layerX - this.margin.left,
            //@ts-ignore
            event.layerY - this.margin.top,
            10,
        );
        this._selected_scatterpoint = scatter_point;

        let use_date: Date;
        scatter_plot.redraw_canvas();
        if (scatter_point !== undefined) {
            use_date = scatter_point.date;
            // Highlight all incidents, based on this scatterpoint's label
            const ctx = scatter_plot.canvas!.node()!.getContext("2d")!;
            const points = scatter_plot.transformed_data.filter(
                d => d.label == scatter_point.label,
            );
            const line = d3_line<TransformedData>()
                .x(d => d.scaled_x)
                .y(d => d.scaled_y)
                .context(ctx);
            ctx.beginPath();
            line(points);
            ctx.strokeStyle = this._get_css("stroke", "path", [
                "host",
                "hilite",
            ]);
            ctx.stroke();

            // Highlight selected point
            ctx.beginPath();
            ctx.arc(
                scatter_point.scaled_x,
                scatter_point.scaled_y,
                3,
                0,
                Math.PI * 2,
                false,
            );
            ctx.fillStyle = this._get_css("fill", "circle", [
                "scatterdot",
                "hilite",
            ]);
            ctx.fill();
            ctx.stroke();
        } else {
            //@ts-ignore
            use_date = this.scale_x.invert(event.layerX - this.margin.left);
        }

        // @ts-ignore
        const nearest_bisect = bisector(d => d.timestamp).left;

        // Find nearest mean point
        //@ts-ignore
        filter_dimension.filter(d => d.tag == "line_mean");
        const results = timestamp_dimension.bottom(Infinity);
        const idx = nearest_bisect(results, use_date.getTime() / 1000);
        const mean_point = results[idx];

        // Get corresponding median point
        //@ts-ignore
        filter_dimension.filter(d => d.tag == "line_median");
        const median_point = timestamp_dimension.bottom(Infinity)[idx];

        if (mean_point == undefined || median_point == undefined) {
            filter_dimension.dispose();
            timestamp_dimension.dispose();
            return;
        }

        // Get scatter points for this date
        filter_dimension.filter(
            //@ts-ignore
            d => d.timestamp == mean_point.timestamp && d.tag == "scatter",
        );
        const scatter_matches: TransformedData[] =
            timestamp_dimension.top(Infinity);
        scatter_matches.sort((first, second) =>
            Number(first.value > second.value),
        );
        const top_matches = scatter_matches.slice(-5, -1).reverse();
        const bottom_matches = scatter_matches.slice(0, 4).reverse();

        this._selected_meanpoint = mean_point;
        this._update_pin();

        this._render_tooltip(
            event,
            top_matches,
            bottom_matches,
            mean_point,
            median_point,
            scatter_point,
        );

        filter_dimension.dispose();
        timestamp_dimension.dispose();
    }

    override _zoomed() {
        super._zoomed();
        this._update_pin();
    }

    _update_pin() {
        if (this._selected_meanpoint) {
            this.g.select("path.pin").remove();
            const x = this.scale_x(this._selected_meanpoint.date);
            this.g
                .append("path")
                .classed("pin", true)
                .attr(
                    "d",
                    d3_line()([
                        [x, 0],
                        [x, this.plot_size.height],
                    ]),
                )
                .attr("pointer-events", "none");
        }
    }

    _render_tooltip(
        event: MouseEvent,
        top_matches: TransformedData[],
        bottom_matches: TransformedData[],
        mean_point: TransformedData,
        median_point: TransformedData,
        scatterpoint: TransformedData | undefined,
    ) {
        this._tooltip.selectAll("table").remove();

        const table = this._tooltip.append("table");

        const date_row = table.append("tr").classed("date", true);
        date_row.append("td").text(String(mean_point.date)).attr("colspan", 2);
        const formatter = plot_render_function(
            getIn(this, "_subplots", 0, "definition"),
        );

        const mean_row = table.append("tr").classed("mean", true);
        mean_row.append("td").text(mean_point.label);
        mean_row.append("td").text(formatter(mean_point.value));
        const median_row = table.append("tr").classed("median", true);
        median_row.append("td").text(median_point.label);
        median_row.append("td").text(formatter(median_point.value));

        if (scatterpoint) {
            const scatter_row = table
                .append("tr")
                .classed("scatterpoint", true);
            const hilited_host_color = this._get_css("stroke", "path", [
                "host",
                "hilite",
            ]);
            scatter_row
                .append("td")
                .text(scatterpoint.tooltip + " (selected)")
                .style("color", hilited_host_color);
            scatter_row.append("td").text(formatter(scatterpoint.value));
        }

        const top_rows = table
            .selectAll<HTMLTableCellElement, unknown>("tr.top_matches")
            .data<TransformedData>(top_matches)
            .enter()
            .append("tr")
            .classed("top_matches", true);
        top_rows.append("td").text(d => String(d.tooltip));
        top_rows.append("td").text(d => formatter(d.value));

        const bottom_rows = table
            .selectAll<HTMLTableCellElement, unknown>("tr.bottom_matches")
            .data<TransformedData>(bottom_matches)
            .enter()
            .append("tr")
            .classed("bottom_matches", true);
        bottom_rows.append("td").text(d => String(d.tooltip));
        bottom_rows.append("td").text(d => formatter(d.value));

        this.tooltip_generator?.activate();
        this.tooltip_generator?.update_position(event);
    }

    _get_css(prop: string, tag: string, classes: string[]) {
        const obj = this.svg!.append(tag);
        classes.forEach(cls => obj.classed(cls, true));
        const css = obj.style(prop);
        obj.remove();
        return css;
    }
}

figure_registry.register(AverageScatterplotFigure);
