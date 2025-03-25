/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import type {Crossfilter, Dimension} from "crossfilter2";
import type {BaseType, Selection} from "d3";
import {descending} from "d3";
import type {DataTableWidget} from "dc";
import {dataTable} from "dc";

import {DCFigureBase, FigureBase} from "@/modules/figures/cmk_figures";
import type {FigureData} from "@/modules/figures/figure_types";

// Basic dc table with pagination
export class DCTableFigure<
    DCTableFigureData extends FigureData = FigureData,
> extends DCFigureBase<DCTableFigureData> {
    _offset: number;
    _pages: number;
    _dimension: Dimension<any, any> | null;
    _columns: null | any[];
    _paging: Selection<HTMLDivElement, unknown, BaseType, unknown> | null;
    _div_options: Selection<HTMLDivElement, unknown, BaseType, unknown>;
    _chart!: DataTableWidget;
    _sort_by!: (d: any) => any;
    _use_dynamic_paging: boolean;
    _paging_maximum: number;
    constructor(div_selector: string, group: string | null) {
        super(div_selector, null, null);
        this._graph_group = group;
        this._offset = 0;
        this._pages = 20;
        this._dimension = null;
        this._columns = null;
        this._paging = null;
        this._use_dynamic_paging = false;
        this._paging_maximum = 0;
        this._div_options = this._div_selection
            .insert("div", this._div_selector)
            .classed("options", true);
    }

    override ident() {
        return "dc_table";
    }

    override initialize(with_debugging?: boolean) {
        FigureBase.prototype.initialize.call(this, with_debugging);
        this._setup_paging();
        this._setup_chart();
    }

    override update_data(data: any) {
        if (this._use_dynamic_paging && data?.length !== undefined) {
            this.set_paging_maximum(data.length);
        }
        data = data?.data !== undefined ? data.data : data;
        DCFigureBase.prototype.update_data.call(this, data);
        this._crossfilter.remove(() => true);
        this._crossfilter.add(data);
    }

    reset() {
        this._crossfilter.remove(() => true);
        this.update_gui();
        this.show_loading_image();
    }

    //@ts-ignore
    getEmptyData() {
        return {data: [], plot_definitions: []};
    }

    override update_gui() {
        // TODO: find better place
        this._chart.redraw();
    }

    activate_dynamic_paging() {
        this._use_dynamic_paging = true;
    }

    set_paging_maximum(size: number) {
        this._paging_maximum = size;
    }

    _setup_paging() {
        this._paging = this._div_options.append("div").attr("class", "paging");

        // display text
        this._paging.append("label").attr("id", "display_text");

        // navigation
        const div = this._paging.append("div").attr("class", "buttons");
        div.append("input")
            .attr("type", "button")
            .attr("class", "prev")
            .property("value", "<<")
            .on("click", () => this.first());
        div.append("input")
            .attr("type", "button")
            .attr("class", "prev")
            .property("value", "<")
            .on("click", () => this.prev());
        div.append("input")
            .attr("type", "button")
            .attr("class", "next")
            .property("value", ">")
            .on("click", () => this.next());
        div.append("input")
            .attr("type", "button")
            .attr("class", "next")
            .property("value", ">>")
            .on("click", () => this.last());
    }

    _setup_chart() {
        if (this._dimension == null)
            this._dimension = this._crossfilter.dimension(d => d);

        const table_selection = this._div_selection
            .append("table")
            .attr("id", "dc_table_figure")
            .classed("table", true);
        // @ts-ignore
        this._chart = dataTable(table_selection, this._graph_group);
        this._chart
            .dimension(this._dimension)
            .size(Infinity)
            .showSections(false)
            // @ts-ignore
            .columns(this.columns())
            // @ts-ignore
            .sortBy(this.sort_by())
            .order(descending)
            .on("preRender", () => this._update_offset())
            .on("preRedraw", () => this._update_offset())
            .on("pretransition", () => this._display());
        this._chart.render();
    }

    override get_dc_chart() {
        return this._chart;
    }

    crossfilter(crossfilter: Crossfilter<any>): void | Crossfilter<any> {
        if (!arguments.length) {
            return this._crossfilter;
        }
        this._crossfilter = crossfilter;
    }

    dimension(
        dimension: Dimension<any, any>,
    ): void | null | Dimension<any, any> {
        if (!arguments.length) {
            return this._dimension;
        }
        this._dimension = dimension;
    }

    columns(columns?: any[]): void | any[] {
        if (!arguments.length || columns === undefined) {
            return this._columns || [];
        }
        this._columns = columns;
    }

    sort_by(sort_by?: (d: any) => any): void | ((arg: any) => any) {
        if (!arguments.length || sort_by === undefined) {
            return this._sort_by ? this._sort_by : (d: any) => d.date;
        }
        this._sort_by = sort_by;
    }

    _update_offset() {
        const totFilteredRecs = this._use_dynamic_paging
            ? this._paging_maximum
            : this._crossfilter.groupAll<number>().value();
        this._offset =
            this._offset >= totFilteredRecs
                ? Math.floor((totFilteredRecs - 1) / this._pages) * this._pages
                : this._offset;
        this._offset = this._offset < 0 ? 0 : this._offset;

        if (!this._use_dynamic_paging) {
            this._chart.beginSlice(this._offset);
            this._chart.endSlice(this._offset + this._pages);
        } else {
            this._chart.beginSlice(0);
            this._chart.endSlice(this._pages);
            this._post_body = this._post_body.replace(
                /(offset=).*?(&)?$/,
                "$1" + this._offset + "$2",
            );
        }
    }

    _display() {
        if (!this._paging) {
            throw new Error("_paging is not defined!");
        }
        const totalRecs = this._use_dynamic_paging
            ? this._paging_maximum
            : this._crossfilter.size();
        if (totalRecs < this._pages) {
            this._paging.style("display", "none");
            return;
        }
        this._paging.style("display", null);
        const totFilteredRecs = this._use_dynamic_paging
            ? this._paging_maximum
            : this._crossfilter.groupAll<number>().value();
        const end =
            this._offset + this._pages > totFilteredRecs
                ? totFilteredRecs
                : this._offset + this._pages;
        const begin = end === 0 ? this._offset : this._offset + 1;
        let totalFiltered = "";
        if (
            totFilteredRecs != this._crossfilter.size() &&
            !this._use_dynamic_paging
        ) {
            totalFiltered =
                "(filtered Total: " + this._crossfilter.size() + ")";
        }
        // buttons
        this._paging
            .selectAll(".prev")
            .attr("disabled", this._offset - this._pages < 0 ? "true" : null);
        this._paging
            .selectAll(".next")
            .attr(
                "disabled",
                this._offset + this._pages >= totFilteredRecs ? "true" : null,
            );
        // display text
        const text =
            begin + " - " + end + " of " + totFilteredRecs + totalFiltered;
        this._paging.select("#display_text").text(text);
    }

    first() {
        this._offset = 0;
        this._update_offset();
        if (this._use_dynamic_paging) {
            this.show_loading_image();
            this.scheduler.force_update();
        }
        this._chart.redraw();
    }

    last() {
        this._offset = this._use_dynamic_paging
            ? this._paging_maximum
            : this._crossfilter.size();
        this._update_offset();
        if (this._use_dynamic_paging) {
            this.show_loading_image();
            this.scheduler.force_update();
        }
        this._chart.redraw();
    }

    next() {
        this._offset += this._pages;
        this._update_offset();
        if (this._use_dynamic_paging) {
            this.show_loading_image();
            this.scheduler.force_update();
        }
        this._chart.redraw();
    }

    prev() {
        this._offset -= this._pages;
        this._update_offset();
        if (this._use_dynamic_paging) {
            this.show_loading_image();
            this.scheduler.force_update();
        }
        this._chart.redraw();
    }
}
