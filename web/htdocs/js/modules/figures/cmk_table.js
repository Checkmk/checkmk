/* eslint-disable indent */

import * as d3 from "d3";
import * as dc from "dc";
import * as cmk_figures from "cmk_figures";

export class TableFigure extends cmk_figures.FigureBase {
    static ident() {
        return "table";
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

    update_data(data) { // eslint-disable-line no-unused-vars
    }

    update_gui(data) {
        // TODO: clear table when no rows exist
        if (!data.rows)
            return;
        if (data.classes)
            this._table.classed(data.classes.join(" "), true);

        let rows = this._table.selectAll("tr").data(data.rows);

        rows.exit()
            .transition()
            .duration(1000)
            .style("opacity", 0)
            .remove();

        rows = rows.enter().append("tr").merge(rows);
        rows.each((d, idx, nodes)=>{
            if (!d.classes)
                return;
            d3.select(nodes[idx]).classed(d.classes.join(" "), true);
        });

        let cells = rows.selectAll(".cell").data(d=>d.cells);
        let new_cells = cells.enter().each((d,idx, nodes)=>{
            let parent_node = d3.select(nodes[idx]);
            let cell = parent_node.append(d.cell_type ? d.cell_type : "td");
            cell.classed("cell", true);

            if (d.colspan)
                cell.attr("colspan", d.colspan);
            if (d.rowspan)
                cell.attr("rowspan", d.rowspan);
             });
        new_cells = rows.selectAll(".cell");

        new_cells.style("opacity", 0).transition().style("opacity", 1);

        new_cells.merge(cells)
            .each(function(d) { // Update classes
                let cell = d3.select(this);
                if (d.classes)
                    cell.classed(d.classes.join(" "), true);
                if (d.id)
                    cell.attr("id", d.id);
                if (d.text != null)
                    cell.text(d.text);
                if (d.html != null)
                    cell.html(d.html);
            });

        _update_dc_graphs_in_selection(this._div_selection);
    }
}

cmk_figures.figure_registry.register(TableFigure);


function _update_dc_graphs_in_selection(selection, graph_group) {
    selection.selectAll(".figure_cell").each((d, idx, nodes) => {
        // TODO: implement better intialization solution, works for now
        let node = d3.select(nodes[idx]);
        let svg = node.select("svg");
        if (svg.empty()) {
            let new_crossfilter = new crossfilter(d.figure_config.data);
            let label_dimension = new_crossfilter.dimension(d=>d.label);
            let label_group = label_dimension.group().reduceSum(d=>d.value);
            let pie_chart = dc.pieChart(d.figure_config.selector, graph_group);
            pie_chart
                .width(450)
                .height(200)
                .dimension(label_dimension)
                .radius(150)
                .innerRadius(30)
//                .drawPaths(true)
                .minAngleForLabel(0)
                .externalLabels(15)
                .externalRadiusPadding(40)
                .title(d=>d.value)
                .group(label_group)
                .emptyTitle("No data available")
                .on("postRender", (chart)=>{_pie_chart_custom_renderlet(chart, d);});

            pie_chart.filter = function() {};
            pie_chart.render();
            nodes[idx].__crossfilter__ = new_crossfilter;
        } else {
            // Update
            nodes[idx].__crossfilter__.remove(()=>true);
            nodes[idx].__crossfilter__.add(d.figure_config.data);
        }
    });
}

function _pie_chart_custom_renderlet(chart, d) {
    if (d.figure_config.title) {
        chart.select("svg g").selectAll("label.pie_chart_title").data([d.figure_config.title])
            .enter()
            .append("text")
            .attr("text-anchor", "middle")
            .classed("pie_chart_title", true)
            .text(d=>d);
    }

    if (chart.svg().select(".empty-chart").empty())
        return;

    // TODO: WIP
    let labels_data = [];
    chart.selectAll("text.pie-label").each((d, idx, nodes)=>{
        labels_data.push(d3.select(nodes[idx]));
    });


    let labels_key = chart.select("g.pie-label-group").selectAll("text.pie-label-key").data(labels_data, d=>d.datum().data.key);
    labels_key.exit().remove();

    labels_key = labels_key.enter().append("text")
        .classed("pie-label-key", true);

    labels_key.exit().remove();
    labels_key.attr("transform", d=>{
            let coords = _get_translation(d.attr("transform"));
            return "translate(" + coords[0] + "," + (coords[1] + 10) + ")";
        }).text(d=>{
            let data = d.datum();
            return Math.round((data.endAngle - data.startAngle) / Math.PI * 50) + "%";}
        );
}

// TODO: put into library
function _get_translation(transform) {
  // Create a dummy g for calculation purposes only. This will never
  // be appended to the DOM and will be discarded once this function
  // returns.
  var g = document.createElementNS("http://www.w3.org/2000/svg", "g");

  // Set the transform attribute to the provided string value.
  g.setAttributeNS(null, "transform", transform);

  // consolidate the SVGTransformList containing all transformations
  // to a single SVGTransform of type SVG_TRANSFORM_MATRIX and get
  // its SVGMatrix.
  var matrix = g.transform.baseVal.consolidate().matrix;

  // As per definition values e and f are the ones for the translation.
  return [matrix.e, matrix.f];
}
