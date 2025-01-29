/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import type {BaseType, Selection} from "d3";
import {select} from "d3";

import type {Shift} from "@/modules/figures/cmk_enterprise_figure_types";
import {figure_registry} from "@/modules/figures/cmk_figures";
import type {ElementSize, FigureData} from "@/modules/figures/figure_types";

import {CmkGraphTimeseriesFigure} from "./cmk_graph_timeseries_figure";
import type {SubPlot} from "./sub_plot";

//TODO: delete this class if there is no need for it
export class CmkGraphShifter extends CmkGraphTimeseriesFigure {
    _cutter_div: null | Selection<HTMLDivElement, null, BaseType, unknown>;
    _shifts: Shift[];

    override ident() {
        return "cmk_graph_shifter";
    }

    constructor(div_selector: string, fixed_size: ElementSize | null = null) {
        super(div_selector, fixed_size);
        this.subscribe_data_pre_processor_hook(data => {
            this._apply_shift_config(data);
            return data;
        });
        this._cutter_div = null;
        this._shifts = [];
    }

    _apply_shift_config(data: FigureData) {
        //I still have no idea how this data are being get since this class has
        //no equivalent in python.
        const new_definitions = data.plot_definitions.filter(
            d => d.is_shift !== true,
        );
        this._shifts.forEach(config => {
            if (config.seconds === 0) return;
            const shift = JSON.parse(
                JSON.stringify(
                    this._subplots_by_id[config.shifted_id].definition,
                ),
            );
            const seconds = config.seconds;
            shift.id += "_shifted";
            shift.color = config.color;
            shift.shift_seconds = seconds;
            shift.label += config.label_suffix;
            shift.opacity = 0.5;
            shift.is_shift = true;
            new_definitions.push(shift);
        });
        data.plot_definitions = new_definitions;
    }

    override initialize() {
        CmkGraphTimeseriesFigure.prototype.initialize.call(this);
        this._setup_cutter_options_panel();
    }

    override update_gui() {
        CmkGraphTimeseriesFigure.prototype.update_gui.call(this);
        this._update_cutter_options_panel();
    }

    _setup_cutter_options_panel() {
        this._cutter_div = this._div_selection
            .select("div.figure_content")
            .selectAll<HTMLDivElement, unknown>("div.cutter_options")
            .data([null])
            .join(enter =>
                enter
                    .append("div")
                    .style("position", "absolute")
                    .style("top", "0px")
                    .style("left", 40 + this.figure_size.width + "px")
                    .classed("cutter_options noselect", true),
            );

        this._cutter_div!.append("label")
            .style("margin-left", "-60px")
            .style("border", "grey")
            .style("border-style", "solid")
            .text("Shift data")
            // @ts-ignore
            .on("click", (_event, _d, idx: number, nodes) => {
                const node = select(nodes[idx]);
                const active = !node.classed("active");
                node.classed("active", active);
                this._cutter_div!.select("div.options")
                    .transition()
                    // @ts-ignore
                    .style("width", active ? null : "0px");
                // @ts-ignore
                node.style("background", active ? "green" : null);
            });

        const options = [
            {id: "Hours", min: 0, max: 24},
            {id: "Days", min: 0, max: 31},
        ];
        const div_options = this._cutter_div!.append("div")
            .style("overflow", "hidden")
            .style("width", "0px")
            .classed("options", true);
        const new_table = div_options
            .selectAll("table")
            .data([null])
            .enter()
            .append("table");

        const new_rows = new_table
            .selectAll("tr.shift_option")
            .data(options)
            .enter()
            .append("tr")
            .classed("shift_option", true);
        new_rows.append("td").text(d => d.id);
        new_rows
            .append("td")
            .text("0")
            .classed("value", true)
            .attr("id", d => d.id);
        new_rows
            .append("td")
            .append("input")
            .attr("type", "range")
            .attr("min", d => d.min)
            .attr("max", d => d.max)
            .attr("value", 0)
            .on("change", (event, d) => {
                this._cutter_div!.selectAll("td.value#" + d.id).text(
                    event.target.value,
                );
                this._update_shifts();
            });
    }

    _update_cutter_options_panel() {
        const table = this._cutter_div!.select("div.options")
            .selectAll("table.metrics")
            .data([null])
            .join("table")
            .classed("metrics", true);
        const rows = table
            .selectAll<HTMLTableCellElement, SubPlot>("tr.metric")
            .data(
                this._subplots.filter(
                    d =>
                        !(
                            d.definition!.is_scalar ||
                            d.definition!.is_shift ||
                            d.definition!.hidden
                        ),
                ),
                d => d.definition!.id,
            )
            .join("tr")
            .classed("metric", true);
        rows.selectAll("input")
            .data(d => [d])
            .join("input")
            .attr("type", "checkbox")
            .style("display", "inline-block")
            .on("change", () => this._update_shifts());
        const metric_td = rows
            .selectAll("td.color")
            .data(d => [d])
            .enter()
            .append("td")
            .classed("color", true);
        metric_td
            .append("div")
            .classed("color", true)
            .style("background", d => d.definition!.color || "");
        metric_td.append("label").text(d => d.definition!.label);
    }

    _update_shifts() {
        const hours = parseInt(
            this._cutter_div!.selectAll("td.value#Hours").text(),
        );
        const days = parseInt(
            this._cutter_div!.selectAll("td.value#Days").text(),
        );

        const checked_metrics = this._cutter_div!.selectAll<
            HTMLInputElement,
            any
        >("input[type=checkbox]:checked");
        this._shifts = [];
        checked_metrics.each(d => {
            this._shifts.push({
                shifted_id: d.definition.id,
                seconds: hours * 3600 + days * 86400,
                color: "white",
                label_suffix:
                    "- shifted " + days + " days, " + hours + " hours",
            });
        });

        this._apply_shift_config(this._data);
        this._legend.selectAll("table").remove();
        this.update_gui();
    }
}

figure_registry.register(CmkGraphShifter);
