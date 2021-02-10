import * as d3 from "d3";
import {range} from "lodash";
import * as cmk_figures from "cmk_figures";
import {partitionableDomain, domainIntervals} from "number_format";

// Used for rapid protoyping, bypassing webpack
//var cmk_figures = cmk.figures; /*eslint-disable-line no-undef*/
//var dc = dc; /*eslint-disable-line no-undef*/
//var d3 = d3; /*eslint-disable-line no-undef*/
//var crossfilter = crossfilter; /*eslint-disable-line no-undef*/

class BarplotFigure extends cmk_figures.FigureBase {
    static ident() {
        return "barplot";
    }

    constructor(div_selector, fixed_size = null) {
        super(div_selector, fixed_size);
        this.margin = {top: 20, right: 10, bottom: 10, left: 10};

        this._time_dimension = this._crossfilter.dimension(d => d.timestamp);
        this._tag_dimension = this._crossfilter.dimension(d => d.tag);

        this._plot_definitions = [];
    }

    initialize() {
        this.svg = this._div_selection.append("svg").classed("renderer", true);
        this.plot = this.svg.append("g");
        this.bars = this.plot.append("g").classed("bars", true);

        // X axis
        this.scale_x = d3.scaleLinear();
        this.plot.append("g").classed("x_axis", true).call(d3.axisTop(this.scale_x));

        // Y axis
        this.scale_y = d3.scaleBand().padding(0.2);
        this.plot.append("g").classed("y_axis", true).call(d3.axisRight(this.scale_y));
    }

    render() {
        if (this._data) this.update_gui();
    }

    resize() {
        if (this._data.title) {
            this.margin.top = 20 + 24; // 24 from UX project
        } else {
            this.margin.top = 20;
        }
        cmk_figures.FigureBase.prototype.resize.call(this);
        this.svg.attr("width", this.figure_size.width).attr("height", this.figure_size.height);
        this.scale_x.range([0, this.plot_size.width]);
        this.scale_y.range([this.plot_size.height, 0]);
        this.plot.attr("transform", "translate(" + this.margin.left + "," + this.margin.top + ")");
    }

    _update_plot_definitions(plot_definitions) {
        this._plot_definitions = [];

        // We are only interested in the single_value plot types, they may include metrics info
        plot_definitions.forEach(plot_definition => {
            if (plot_definition.plot_type != "single_value") return;
            this._plot_definitions.push(plot_definition);
        });
    }

    render_grid(ticks) {
        // Grid
        let height = this.plot_size.height;
        this.plot
            .selectAll("g.grid.vertical")
            .data([null])
            .join("g")
            .classed("grid vertical", true)
            .call(d3.axisTop(this.scale_x).tickValues(ticks).tickSize(-height).tickFormat(""));
    }

    update_gui() {
        let data = this._data;
        this._update_plot_definitions(data.plot_definitions || []);
        if (data.plot_definitions.length == 0) return;
        this._crossfilter.remove(() => true);
        this._time_dimension.filterAll();
        this._crossfilter.add(data.data);

        // We expect, that all of the latest values have the same timestamp
        // Set the time dimension filter to the latest value
        // If this needs to be changed someday, simply iterate over all plot_definitions
        this._time_dimension.filter(d => d == this._time_dimension.top(1)[0].timestamp);

        this.resize();
        this.render_title(data.title);
        this.scale_y.domain(this._plot_definitions.map(d => d.label));
        this.plot
            .selectAll("g.y_axis")
            .classed("axis", true)
            .call(d3.axisRight(this.scale_y))
            .selectAll("text")
            .attr("transform", `translate(0,${-this.scale_y.bandwidth() / 2})`);

        let used_tags = this._plot_definitions.map(d => d.use_tags[0]);
        let points = this._tag_dimension.filter(d => used_tags.includes(d)).top(Infinity);
        const tickcount = Math.max(2, Math.ceil(this.plot_size.width / 85));
        const [min_val, max_val, step] = partitionableDomain(
            [0, d3.max(points, d => d.value)],
            tickcount,
            domainIntervals(this._plot_definitions[0].stepping)
        );
        const domain = [min_val, max_val];
        const tick_vals = range(min_val, max_val, step);

        this.scale_x.domain(domain);
        this._tag_dimension.filterAll();

        const render_function = this.get_scale_render_function();

        this.plot
            .selectAll("g.x_axis")
            .classed("axis", true)
            .style("text-anchor", "start")
            .call(
                d3
                    .axisTop(this.scale_x)
                    .tickValues(tick_vals)
                    .tickFormat(d => render_function(d))
            );

        this.render_grid(range(min_val, max_val, step / 2));
        this._render_values(domain);
    }

    _render_values(domain) {
        const points = this._plot_definitions.map(d => {
            let point = this._tag_dimension.filter(tag => tag == d.use_tags[0]).top(1)[0];
            if (point === undefined) point = {value: 0};

            const levels = cmk_figures.make_levels(domain, d.metrics);
            point.level_color = levels.length
                ? levels.find(element => point.value < element.to).color
                : "#3CC2FF";
            return {...d, ...point};
        });
        this.bars
            .selectAll("a")
            .data(points, d => d.id)
            .join("a")
            .attr("xlink:href", d => d.url)
            .selectAll("rect.value")
            .data(d => [d])
            .join("rect")
            .classed("value", true)
            .attr("y", d => this.scale_y(d.label) + 6) // 6 is half the default font size. Thus bar stays bellow text
            .attr("height", Math.max(this.scale_y.bandwidth() - 12, 4))
            .attr("width", d => this.scale_x(d.value))
            .attr("fill", d => d.level_color);

        this._tag_dimension.filterAll();
    }
}

cmk_figures.figure_registry.register(BarplotFigure);
