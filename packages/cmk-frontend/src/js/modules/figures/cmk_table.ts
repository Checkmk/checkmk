/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

/* eslint-disable indent */
import type {BaseType, Selection} from "d3";
import {select} from "d3";

import {figure_registry, FigureBase} from "./cmk_figures";
import type {FigureData} from "./figure_types";

export interface Cell<Config = PieChartData | NtopTalkerData> {
    id?: string;
    text: string;
    html: string;
    cell_type: string;
    classes: string[];
    rowspan: number;
    colspan: number;
    figure_config: Config;
}

export interface NtopTalkerDataPlotDefinition {
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

export interface NtopTalkerData {
    id: string;
    figure_type: string;
    zoom_settings: {lock_zoom_x: boolean; lock_zoom_x_scale: boolean};
    size: {width: number; height: number};
    plot_definitions: NtopTalkerDataPlotDefinition[];
    data: NtopTalkerDataData[];
    selector: string;
}

interface NtopTalkerDataData {
    timestamp: number;
    ending_timestamp: number;
    value: any;
    tag: string;
}

interface PieChartData {
    id: string;
    type: string;
    title: string;
    data: PieChartDataData[];
    selector: string;
}

interface PieChartDataData {
    label: string;
    value: string | number;
}

export interface Row<Config = PieChartData | NtopTalkerData> {
    classes: string[];
    cells: Cell<Config>[];
}

export interface TableFigureData<Config = PieChartData | NtopTalkerData>
    extends FigureData {
    title?: string;
    rows: Row<Config>[];
    classes?: string[];
}

export class TableFigure extends FigureBase<TableFigureData> {
    _table!: Selection<HTMLTableElement, unknown, BaseType, unknown>;

    override ident() {
        return "table";
    }

    getEmptyData(): TableFigureData {
        return {data: [], plot_definitions: [], rows: []};
    }

    override initialize(debug?: boolean) {
        FigureBase.prototype.initialize.call(this, debug);
        this._table = this._div_selection.append("table");
    }

    // Data format
    // data = {
    //   title: "My title",              // Optional
    //   headers: []
    //   rows: [
    //      [ {                 // Dict, representing a row
    //          "cells": [ {    // Dict, representing a cell
    //            content: "Text to display",
    //            classes: ["styles", "to", "apply"],
    //            colspan: 3,
    //          } ]
    //      ], ...
    //   ]
    // }

    override update_gui() {
        // TODO: clear table when no rows exist
        const data = this._data;
        if (!data.rows) return;
        if (data.classes) this._table.classed(data.classes.join(" "), true);

        const rows = this._table
            .selectAll<HTMLTableRowElement, TableFigureData>("tr")
            .data(data.rows)
            .join("tr")
            .attr("class", d => (d.classes && d.classes.join(" ")) || null);

        rows.selectAll<HTMLElement, Row>(".cell")
            .data<Cell>(d => d.cells)
            .join(enter =>
                enter.append(d => {
                    return document.createElement(d.cell_type || "td");
                }),
            )
            .attr("class", d => ["cell"].concat(d.classes || []).join(" "))
            .attr("id", d => d.id || null)
            .attr("colspan", d => d.colspan || null)
            .attr("rowspan", d => d.rowspan || null)
            .each(function (d) {
                const cell = select(this);
                if (d.text != null) cell.text(d.text);
                if (d.html != null) cell.html(d.html);
            });

        // New td inline figures
        _update_figures_in_selection(this._div_selection);
    }
}

class HTMLTableCellElement extends HTMLElement {
    __figure_instance__?: FigureBase<FigureData>;
    __crossfilter__: any;
}

function _update_figures_in_selection(
    selection: Selection<HTMLDivElement, unknown, BaseType, unknown>,
) {
    selection
        .selectAll<HTMLTableCellElement, Cell>(".figure_cell")
        .each((d, idx, nodes) => {
            const figure_config = d["figure_config"];
            if (nodes[idx].__figure_instance__ == undefined) {
                const figure_class = figure_registry.get_figure(
                    //@ts-ignore
                    figure_config["figure_type"],
                );
                if (figure_class == undefined)
                    // unknown figure type
                    return;

                const new_figure = new figure_class(
                    figure_config["selector"],
                    (<NtopTalkerData>figure_config)["size"],
                );
                new_figure.initialize(false);
                nodes[idx].__figure_instance__ = new_figure;
            }

            // @ts-ignore
            nodes[idx].__figure_instance__!.update_data(figure_config);
            nodes[idx].__figure_instance__!.update_gui();
        });
}

// TODO: put into library
function _get_translation(transform: string) {
    // Create a dummy g for calculation purposes only. This will never
    // be appended to the DOM and will be discarded once this function
    // returns.
    const g = document.createElementNS("http://www.w3.org/2000/svg", "g");

    // Set the transform attribute to the provided string value.
    g.setAttributeNS(null, "transform", transform);

    // consolidate the SVGTransformList containing all transformations
    // to a single SVGTransform of type SVG_TRANSFORM_MATRIX and get
    // its SVGMatrix.
    const matrix = g.transform.baseVal.consolidate()!.matrix;

    // As per definition values e and f are the ones for the translation.
    return [matrix.e, matrix.f];
}
