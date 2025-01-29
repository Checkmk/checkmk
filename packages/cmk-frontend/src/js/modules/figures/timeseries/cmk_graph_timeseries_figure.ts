/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import {max, mean, min, select} from "d3";

import type {SubPlotPlotDefinition} from "@/modules/figures/cmk_enterprise_figure_types";
import {figure_registry} from "@/modules/figures/cmk_figures";
import type {
    ElementSize,
    SubplotDataData,
} from "@/modules/figures/figure_types";
import type {
    AjaxGraph,
    HorizontalRule,
    LayoutedCurve,
    TimeSeriesValue,
} from "@/modules/graphs";
import type {CMKAjaxReponse} from "@/modules/types";

import {TimeseriesFigure} from "./cmk_timeseries";
import type {SubPlot} from "./sub_plot";

//TODO: delete this class if there is no need for it
export class CmkGraphTimeseriesFigure extends TimeseriesFigure {
    _small_legend!: boolean;

    override ident() {
        return "cmk_graph_timeseries";
    }

    constructor(div_selector: string, fixed_size: null | ElementSize = null) {
        super(div_selector, fixed_size);
        this.subscribe_data_pre_processor_hook(data =>
            this._convert_graph_to_figures(data),
        );
        this._div_selection.classed("graph", true).style("width", "100%");
    }

    override _setup_legend() {
        this._small_legend = false;
        //@ts-ignore
        this._legend = this._div_selection
            .select("div.figure_content")
            .append("div")
            .classed("figure_legend graph_with_timeranges graph", true)
            .style("position", "absolute");
    }

    override _get_legend_height() {
        if (!this._legend || this._small_legend) return 0;
        return this._legend.node()!.getBoundingClientRect().height + 20;
    }

    _convert_graph_to_figures(graph_data: AjaxGraph) {
        const plot_definitions: SubPlotPlotDefinition[] = [];
        const data: {timestamp: number; value: number | null; tag: string}[] =
            [];

        // Metrics
        const step = graph_data.graph.step;
        const start_time = graph_data.graph.start_time;
        graph_data.graph.curves.forEach((curve: LayoutedCurve, idx: number) => {
            const curve_tag = "metric_" + idx;
            const stack_tag = "stack_" + curve_tag;
            const use_stack =
                // @ts-ignore
                curve.type == "area" && max(curve.points, d => d[0]) > 0;
            curve.points.forEach(
                (
                    point: [TimeSeriesValue, TimeSeriesValue] | TimeSeriesValue,
                    idx: number,
                ) => {
                    const timestamp = start_time + idx * step;
                    let value: TimeSeriesValue = 0;
                    let base_value: TimeSeriesValue = 0;
                    if (curve.type == "line")
                        value = (point as TimeSeriesValue)!;
                    else {
                        base_value = (
                            point as [TimeSeriesValue, TimeSeriesValue]
                        )[0];
                        value = (
                            point as [TimeSeriesValue, TimeSeriesValue]
                        )[1];
                    }

                    data.push({
                        timestamp: timestamp,
                        value: value! - (base_value || 0),
                        tag: curve_tag,
                    });

                    if (use_stack)
                        data.push({
                            timestamp: timestamp,
                            value: base_value,
                            tag: stack_tag,
                        });
                },
            );

            const plot_definition: SubPlotPlotDefinition = {
                hidden: false,
                label: curve.title || "",
                plot_type: curve.type,
                color: curve.color,
                id: curve_tag,
                is_scalar: false,
                use_tags: [curve_tag],
            };

            if (use_stack) {
                plot_definitions.push({
                    hidden: true,
                    label: "stack_base " + curve.title,
                    plot_type: "line",
                    color: curve.color,
                    id: stack_tag,
                    is_scalar: false,
                    use_tags: [stack_tag],
                });
                plot_definition["stack_on"] = stack_tag;
            }
            plot_definitions.push(plot_definition);
        });

        // Levels
        const start = min(data, d => d.timestamp);
        const end = max(data, d => d.timestamp);
        graph_data.graph.horizontal_rules.forEach(
            (rule: HorizontalRule, idx: number) => {
                const rule_tag = "level_" + idx;
                plot_definitions.push({
                    hidden: false,
                    label: rule.title,
                    plot_type: "line",
                    color: rule.color,
                    id: rule_tag,
                    is_scalar: true,
                    use_tags: [rule_tag],
                });
                data.push({
                    // @ts-ignore
                    timestamp: start,
                    value: rule.value,
                    tag: rule_tag,
                });
                data.push({
                    // @ts-ignore
                    timestamp: end,
                    value: rule.value,
                    tag: rule_tag,
                });
            },
        );

        return {
            plot_definitions: plot_definitions,
            data: data,
        };
    }

    override _process_api_response(
        graph_data: CMKAjaxReponse<{figure_response: any}>,
    ) {
        //@ts-ignore
        this.process_data(graph_data);
        this._fetch_data_latency =
            +(new Date().getTime() - this._fetch_start) / 1000;
    }

    override render_legend() {
        const domains = this.scale_x.domain();
        const start = Math.trunc(domains[0].getTime() / 1000);
        const end = Math.trunc(domains[1].getTime() / 1000);
        const subplot_data: {
            definition: SubPlotPlotDefinition;
            data: SubplotDataData;
        }[] = [];
        this._subplots.forEach(subplot => {
            subplot_data.push({
                definition: subplot.definition!,
                data: subplot.get_legend_data(start, end),
            });
        });

        this._div_selection
            .selectAll("div.toggle")
            .data([null])
            .enter()
            .append("div")
            .classed("toggle noselect", true)
            .style("position", "absolute")
            .style("bottom", "0px")
            .text("Toggle legend")
            .on("click", () => {
                this._small_legend = !this._small_legend;
                this.render_legend();
                this.resize();
                this.render();
            });

        this._render_legend(subplot_data, this._small_legend);
    }

    _render_legend(
        subplot_data: {
            definition: SubPlotPlotDefinition;
            data: SubplotDataData;
        }[],
        small: boolean,
    ) {
        const new_table = this._legend.selectAll("tbody").empty();
        const table = this._legend
            .selectAll<HTMLTableSectionElement, unknown>("tbody")
            .data([null])
            .join(enter =>
                enter
                    .append("table")
                    .classed("legend", true)
                    .style("width", "100%")
                    .append("tbody"),
            );

        table
            .selectAll("tr.headers")
            .data([["", "MINIMUM", "MAXIMUM", "AVERAGE", "LAST"]])
            .join("tr")
            .classed("headers", true)
            .selectAll("th")
            .data(d => d)
            .join("th")
            .text(d => d);

        // Metrics
        let rows = table
            .selectAll<HTMLTableRowElement, unknown>("tr.metric")
            .data(
                subplot_data.filter(d =>
                    d.definition!.id.startsWith("metric_"),
                ),
            )
            .join("tr")
            .classed("metric", true);
        rows.selectAll("td.name")
            .data<any>(d => [d])
            .enter()
            .append("td")
            .classed("name small", true)
            .each((d, idx, nodes) => {
                const td = select(nodes[idx]);
                td.classed("name", true);
                td.append("div")
                    .classed("color", true)
                    .style("background", d.definition.color);
                td.append("label").text(d.definition.label);
            });
        rows.selectAll<HTMLTableCellElement, unknown>("td.min")
            .data<any>(d => [d])
            .join("td")
            .classed("scalar min", true)
            .text(d =>
                d.data.data.length == 0 ? "NaN" : d.data.y[0].toFixed(2),
            );
        rows.selectAll<HTMLTableCellElement, unknown>("td.max")
            .data<any>(d => [d])
            .join("td")
            .classed("scalar max", true)
            .text(d =>
                d.data.data.length == 0 ? "NaN" : d.data.y[1].toFixed(2),
            );
        rows.selectAll<HTMLTableCellElement, unknown>("td.average")
            .data<any>(d => [d])
            .join("td")
            .classed("scalar average", true)
            .text(d =>
                d.data.data.length == 0
                    ? "NaN"
                    : // @ts-ignore
                      mean(d.data.data, d => d.value).toFixed(2),
            );
        rows.selectAll<HTMLTableCellElement, unknown>("td.last")
            .data<any>(d => [d])
            .join("td")
            .classed("scalar last", true)
            .text(d => {
                if (d.data.data.length == 0) return "NaN";

                if (d.data.data[0].value == null) return "NaN";

                if (d.data.data[0].unstacked_value)
                    return d.data.data[0].unstacked_value.toFixed(2);
                else return d.data.data[0].value.toFixed(2);
            });

        // Levels
        rows = table
            .selectAll<HTMLTableRowElement, unknown>("tr.level")
            .data(
                subplot_data.filter(d => d.definition!.id.startsWith("level_")),
            )
            .join(enter =>
                enter
                    .append("tr")
                    .classed("level scalar", true)
                    .each((_d, idx, nodes) => {
                        if (idx == 0) select(nodes[idx]).classed("first", true);
                    }),
            );
        rows.selectAll<HTMLTableCellElement, SubPlot>("td.name")
            //@ts-ignore
            .data<SubPlot>(d => [d])
            .enter()
            .append("td")
            .classed("name", true)
            .each((d, idx, nodes) => {
                const td = select(nodes[idx]);
                td.classed("name", true);
                td.append("div")
                    .classed("color", true)
                    .style("background", d.definition!.color || "");
                td.append("label").text(d.definition!.label);
            });
        rows.selectAll<HTMLTableCellElement, unknown>("td.min")
            .data(d => [d])
            .join("td")
            .classed("scalar min", true)
            .text("");
        rows.selectAll<HTMLTableCellElement, unknown>("td.max")
            .data(d => [d])
            .join("td")
            .classed("scalar max", true)
            .text("");
        rows.selectAll<HTMLTableCellElement, unknown>("td.average")
            .data(d => [d])
            .join("td")
            .classed("scalar average", true)
            .text("");
        rows.selectAll<HTMLTableCellElement, unknown>("td.last")
            .data<any>(d => [d])
            .join<HTMLTableCellElement, unknown>("td")
            .classed("scalar last", true)
            .text(d =>
                d.data.data.length == 0
                    ? "NaN"
                    : d.data.data[0].value.toFixed(2),
            );

        if (small) {
            this._legend
                .selectAll<HTMLTableCellElement, unknown>("th")
                .style("display", "none");
            this._legend
                .selectAll<HTMLTableCellElement, unknown>("td")
                .style("display", "none");
            this._legend
                .selectAll<HTMLTableCellElement, unknown>("td.small")
                .style("display", null);
            this.transition(this._legend)
                .style("top", this.margin.top + "px")
                .style("width", null)
                .style("right", "20px")
                .style("left", null);
        } else {
            this._legend
                .selectAll<HTMLTableCellElement, unknown>("th")
                .style("display", null);
            this._legend
                .selectAll<HTMLTableCellElement, unknown>("td")
                .style("display", null);
            if (new_table)
                this._legend
                    .style("width", "100%")
                    .style(
                        "top",
                        this.figure_size.height -
                            this._get_legend_height() +
                            "px",
                    )
                    .style("left", "40px");
            else
                this.transition(this._legend)
                    .style("width", "100%")
                    .style(
                        "top",
                        this.figure_size.height -
                            this._get_legend_height() +
                            "px",
                    )
                    .style("left", "40px");
        }
    }
}

figure_registry.register(CmkGraphTimeseriesFigure);
