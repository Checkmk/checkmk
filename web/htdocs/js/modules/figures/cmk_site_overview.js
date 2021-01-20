import * as d3 from "d3";
import * as cmk_figures from "cmk_figures";
import * as utils from "utils";

// Used for rapid protoyping, bypassing webpack
// var cmk_figures = cmk.figures; /* eslint-disable-line no-undef */
// var dc = dc; /* eslint-disable-line no-undef */
// var d3 = d3; /* eslint-disable-line no-undef */
// var crossfilter = crossfilter; /* eslint-disable-line no-undef */

class SiteOverview extends cmk_figures.FigureBase {
    static ident() {
        return "site_overview";
    }

    constructor(div_selector, fixed_size = null) {
        super(div_selector, fixed_size);
        this.margin = {top: 10, right: 10, bottom: 10, left: 10};
    }

    initialize(debug) {
        cmk_figures.FigureBase.prototype.initialize.call(this, debug);
        this.svg = this._div_selection.append("svg");
        this.plot = this.svg.append("g");
    }

    update_data(data) {
        // Data format (based on cmk_figures general data format)
        // {"data" :
        //   [
        //    {
        //      "name": "munich",
        //      "values"
        //      "count_warning": 22,
        //      "count_critical": 22,
        //      "count_in_downtime": 22,
        //    }
        //   ],
        //  "plot_definitions" : [
        //    {
        //       "display_optionA": blabla
        //    }
        //   ]
        // }
        cmk_figures.FigureBase.prototype.update_data.call(this, data);
        this._crossfilter.remove(() => true);
        this._crossfilter.add(this._data.data);
    }

    resize() {
        cmk_figures.FigureBase.prototype.resize.call(this);
        this.svg.attr("width", this.figure_size.width);
        this.svg.attr("height", this.figure_size.height);
    }

    update_gui() {
        this.resize();
        this.render();
    }

    render() {
        this.render_title(this._data.title);
        let width = this.plot_size.width;
        let margin = 5;

        // Plan for dynamic sizing:
        // TODO: ...
        // TODO: In case hexagon_size < X we set entry_height = hexagon_size and skip rendering the label

        // TODO: Formel auskobeln
        let hexagon_size = 80;
        let entry_height = 100;
        let entry_width = hexagon_size;
        let max_columns = Math.trunc(width / (entry_width + margin));

        let site_boxes = this.svg
            .selectAll("g.main_box")
            .data(this._data.data.sites)
            .join(enter => enter.append("g").classed("main_box", true));

        let centered_translation = "translate(" + entry_width / 2 + "," + entry_height / 2 + ")";

        let site_boxes_centered_g = site_boxes
            .selectAll("g")
            .data(d => [d])
            .join("g")
            .attr("transform", centered_translation)
            .style("cursor", "pointer")
            .on("click", d => {
                location.href = utils.makeuri({site: d.site_id});
            });

        site_boxes_centered_g
            .selectAll("path.outer_line")
            .data(d => [d])
            .join(enter => enter.append("path").classed("outer_line", true))
            .attr("d", d3.hexbin().hexagon(hexagon_size / 2))
            .attr("stroke", "#13d389");

        site_boxes_centered_g
            .selectAll("path.inner_line")
            .data(d => [d])
            .join(enter => enter.append("path").classed("inner_line", true))
            .attr("d", d3.hexbin().hexagon(hexagon_size / 4))
            .attr("fill", "yellow");

        site_boxes
            .selectAll("text")
            .data(d => [d.title])
            .join("text")
            .text(d => d)
            .attr("x", function (d) {
                return entry_width / 2 - this.getBBox().width / 2;
            })
            .attr("y", function (d) {
                return entry_height + 4;
            })
            .style("cursor", "pointer")
            .on("click", d => {
                location.href = utils.makeuri({site: d.site_id});
            });

        site_boxes.transition().attr("transform", (d, idx) => {
            let x = idx === 0 ? 0 : (idx % max_columns) * (entry_width + margin);
            let y = Math.trunc(idx / max_columns) * (entry_height + margin);
            return "translate(" + x + "," + y + ")";
        });
    }
}

cmk_figures.figure_registry.register(SiteOverview);
