import * as d3 from "d3";
import * as dc from "dc";
import * as cmk_figures from "cmk_figures";

// Basic dc table with pagination
export class DCTableFigure extends cmk_figures.DCFigureBase {
    constructor(div_selector, group) {
        super(div_selector);
        this._graph_group = group;
        this._offset = 0;
        this._pages = 20;
        this._dimension = null;
        this._columns = null;
        this._paging = null;
        this._div_options = this._div_selection
            .insert("div", this._div_selector)
            .classed("options", true);
    }

    static ident() {
        return "dc_table";
    }

    initialize(with_debugging) {
        cmk_figures.FigureBase.prototype.initialize.call(this, with_debugging);
        this._setup_paging();
        this._setup_chart();
    }

    update_gui() {
        // TODO: find better place
        this._chart.redraw();
    }

    _setup_paging() {
        this._paging = this._div_options.append("div").attr("class", "paging");

        // display text
        this._paging.append("label").attr("id", "display_text");

        // navigation
        let div = this._paging.append("div").attr("class", "buttons");
        div.append("input").attr("type", "button").attr("class", "prev").property("value", "<<").on("click", () => this.first());
        div.append("input").attr("type", "button").attr("class", "prev").property("value", "<").on("click", ()=>this.prev());
        div.append("input").attr("type", "button").attr("class", "next").property("value", ">").on("click", ()=>this.next());
        div.append("input").attr("type", "button").attr("class", "next").property("value", ">>").on("click", ()=>this.last());
    }


    _setup_chart() {
        let table_selection = this._div_selection.append("table").attr("id", "dc_table_figure").classed("table", true);
        this._chart = new dc.dataTable(table_selection, this._graph_group);
        this._chart
            .dimension(this._dimension)
            .size(Infinity)
            .showSections(false)
            .columns(this._columns)
            .sortBy(this._sort_by)
            .order(d3.descending)
            .on("preRender", ()=>this._update_offset())
            .on("preRedraw", ()=>this._update_offset())
            .on("pretransition", ()=>this._display());
        this._chart.render();
    }

    get_dc_chart() {
        return this._chart;
    }

    crossfilter(crossfilter) {
        if (!arguments.length) {
            return this._crossfilter;
        }
        this._crossfilter = crossfilter;
    }

    dimension(dimension) {
        if (!arguments.length) {
            return this._dimension;
        }
        this._dimension = dimension;
    }

    columns(columns) {
        if (!arguments.length) {
            return this._columns;
        }
        this._columns = columns;
    }

    sort_by(sort_by) {
        if (!arguments.length) {
            return this._sort_by;
        }
        this._sort_by = sort_by;
    }


    _update_offset() {
        let totFilteredRecs = this._crossfilter.groupAll().value();
        this._offset = this._offset >= totFilteredRecs ? Math.floor((totFilteredRecs - 1) / this._pages) * this._pages: this._offset;
        this._offset = this._offset < 0 ? 0: this._offset;

        this._chart.beginSlice(this._offset);
        this._chart.endSlice(this._offset+this._pages);
    }

    _display() {
        let totFilteredRecs = this._crossfilter.groupAll().value();
        var end = this._offset + this._pages > totFilteredRecs ? totFilteredRecs: this._offset + this._pages;
        let begin = end === 0 ? this._offset: this._offset + 1;
        let totalFiltered = "";
        if(totFilteredRecs != this._crossfilter.size()) {
            totalFiltered = "(filtered Total: " + this._crossfilter.size() + ")";
        }
        // buttons
        this._paging.selectAll(".prev").attr("disabled", this._offset - this._pages < 0 ? "true" : null);
        this._paging.selectAll(".next").attr("disabled", this._offset + this._pages >= totFilteredRecs ? "true" : null);
        // display text
        let text = begin + " - " + end + " of " + totFilteredRecs + totalFiltered;
        this._paging.select("#display_text").text(text);
    }

    first() {
        this._offset = 0;
        this._update_offset();
        this._chart.redraw();
    }

    last() {
        this._offset = this._crossfilter.size();
        this._update_offset();
        this._chart.redraw();
    }

    next() {
        this._offset += this._pages;
        this._update_offset();
        this._chart.redraw();
    }

    prev() {
        this._offset -= this._pages;
        this._update_offset();
        this._chart.redraw();
    }

}

cmk_figures.figure_registry.register(DCTableFigure);
