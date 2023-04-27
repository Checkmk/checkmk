/* eslint-disable indent */

import * as d3 from "d3";
import * as dc from "dc";
import * as cmk_figures from "cmk_figures";
import crossfilter from "crossfilter2";

export interface Rows {
    classes: string[];
    cells: {
        text: string;
        html: string;
        cell_type: string;
        classes: string[];
        rowspan: number;
        colspan: number;
        figure_config;
    };
}
interface TableFigureData extends cmk_figures.FigureData {
    rows?: Rows[];
    classes?: string[];
}

export class TableFigure extends cmk_figures.FigureBase<TableFigureData> {
    _table;

    ident() {
        return "table";
    }

    getEmptyData(): TableFigureData {
        return cmk_figures.getEmptyBasicFigureData();
    }

    initialize(debug) {
        cmk_figures.FigureBase.prototype.initialize.call(this, debug);
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

    update_gui() {
        // TODO: clear table when no rows exist
        const data = this._data;
        if (!data.rows) return;
        if (data.classes) this._table.classed(data.classes.join(" "), true);

        const rows = this._table
            .selectAll("tr")
            .data(data.rows)
            .join("tr")
            .attr("class", d => (d.classes && d.classes.join(" ")) || null);

        rows.selectAll(".cell")
            .data(d => d.cells)
            .join(enter =>
                enter.append(d => {
                    return document.createElement(d.cell_type || "td");
                })
            )
            .attr("class", d => ["cell"].concat(d.classes || []).join(" "))
            .attr("id", d => d.id || null)
            .attr("colspan", d => d.colspan || null)
            .attr("rowspan", d => d.rowspan || null)
            .each(function (d) {
                const cell = d3.select(this);
                if (d.text != null) cell.text(d.text);
                if (d.html != null) cell.html(d.html);
            });

        // New td inline figures
        _update_figures_in_selection(this._div_selection);
        // Legacy inline figures
        _update_dc_graphs_in_selection(this._div_selection, null);
    }
}

function _update_figures_in_selection(selection) {
    selection.selectAll(".figure_cell").each((d, idx, nodes) => {
        const figure_config = d["figure_config"];
        if (nodes[idx].__figure_instance__ == undefined) {
            const figure_class = cmk_figures.figure_registry.get_figure(
                figure_config["figure_type"]
            );
            if (figure_class == undefined)
                // unknown figure type
                return;

            const new_figure = new figure_class(
                figure_config["selector"],
                figure_config["size"]
            );
            new_figure.initialize(false);
            nodes[idx].__figure_instance__ = new_figure;
        }

        nodes[idx].__figure_instance__.update_data(figure_config);
        nodes[idx].__figure_instance__.update_gui();
    });
}

cmk_figures.figure_registry.register(TableFigure);

function _update_dc_graphs_in_selection(selection, graph_group) {
    selection.selectAll(".figure_cell").each((d, idx, nodes) => {
        // TODO: implement better intialization solution, works for now
        if (!d.figure_config || !d.figure_config.type)
            // new format, not to be handled by this legacy block
            return;

        const node = d3.select(nodes[idx]);
        const svg = node.select("svg");
        if (svg.empty()) {
            const new_crossfilter = crossfilter<any>(d.figure_config.data);
            const label_dimension = new_crossfilter.dimension(d => d.label);
            const label_group = label_dimension.group().reduceSum(d => d.value);
            const pie_chart = dc.pieChart(
                d.figure_config.selector,
                graph_group
            );
            pie_chart
                .width(450)
                .height(200)
                .dimension(label_dimension)
                .radius(150)
                .innerRadius(30)
                .externalRadiusPadding(40)
                .minAngleForLabel(0.5)
                .externalLabels(25)
                .group(label_group)
                .emptyTitle("No data available")
                .on("postRender", chart => {
                    _pie_chart_custom_renderlet(chart, d);
                });
            // eslint-disable-next-line @typescript-eslint/no-empty-function
            pie_chart.filter = function () {};
            pie_chart.render();
            nodes[idx].__crossfilter__ = new_crossfilter;
        } else {
            // Update
            nodes[idx].__crossfilter__.remove(() => true);
            nodes[idx].__crossfilter__.add(d.figure_config.data);
        }
    });
}

function _pie_chart_custom_renderlet(chart, d) {
    if (d.figure_config.title) {
        chart
            .select("svg g")
            .selectAll("label.pie_chart_title")
            .data([d.figure_config.title])
            .enter()
            .append("text")
            .attr("text-anchor", "middle")
            .classed("pie_chart_title", true)
            .text(d => d);
    }

    if (chart.svg().select(".empty-chart").empty()) return;

    // TODO: WIP
    const labels_data: Selection[] = [];
    chart.selectAll("text.pie-label").each((d, idx, nodes) => {
        // @ts-ignore
        labels_data.push(d3.select(nodes[idx]));
    });

    let labels_key = chart
        .select("g.pie-label-group")
        .selectAll("text.pie-label-key")
        .data(labels_data, d => d.datum().data.key);
    labels_key.exit().remove();

    labels_key = labels_key
        .enter()
        .append("text")
        .classed("pie-label-key", true);

    labels_key.exit().remove();
    labels_key
        .attr("transform", d => {
            const coords = _get_translation(d.attr("transform"));
            return "translate(" + coords[0] + "," + (coords[1] + 10) + ")";
        })
        .text(d => {
            const data = d.datum();
            return (
                Math.round(((data.endAngle - data.startAngle) / Math.PI) * 50) +
                "%"
            );
        });
}

// TODO: put into library
function _get_translation(transform) {
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
