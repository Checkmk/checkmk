import * as d3 from "d3";
import * as cmk_figures from "cmk_figures";

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

    render_grid() {
        // Grid
        let height = this.plot_size.height;
        this.plot
            .selectAll("g.grid.vertical")
            .data([null])
            .join("g")
            .classed("grid vertical", true)
            .call(d3.axisTop(this.scale_x).ticks(5).tickSize(-height).tickFormat(""));
    }

    update_gui() {
        let data = this._data;
        this.render_title(data.title);
        this._update_plot_definitions(data.plot_definitions || []);
        this._crossfilter.remove(() => true);
        this._time_dimension.filterAll();
        this._crossfilter.add(data.data);

        // We expect, that all of the latest values have the same timestamp
        // Set the time dimension filter to the latest value
        // If this needs to be changed someday, simply iterate over all plot_definitions
        this._time_dimension.filter(d => d == this._time_dimension.top(1)[0].timestamp);

        this.resize();
        this.scale_y.domain(this._plot_definitions.map(d => d.label));
        this.plot
            .selectAll("g.y_axis")
            .classed("axis", true)
            .call(d3.axisRight(this.scale_y))
            .selectAll("text");

        let used_tags = this._plot_definitions.map(d => d.use_tags[0]);
        let points = this._tag_dimension.filter(d => used_tags.includes(d)).top(Infinity);
        const domain = [0, d3.max(points, d => d.value) * 1.2];
        this.scale_x.domain(domain);
        this._tag_dimension.filterAll();
        this.plot
            .selectAll("g.x_axis")
            .classed("axis", true)
            .call(
                d3.axisTop(this.scale_x).tickFormat(d => {
                    if (d > 999) return d3.format(".2s")(d);
                    return d3.format(",")(d);
                })
            );

        this.render_grid();

        this._render_bar_containers();
        this._render_values(domain);
        let plot = this._data.plot_definitions.filter(d => d.plot_type == "single_value")[0];
        if (!plot) return;
        cmk_figures.state_component(this, plot.svc_state);
    }

    _render_bar_containers() {
        this.plot
            .selectAll("g.bar")
            .data(this._plot_definitions, d => d.id)
            .join(enter => enter.append("g").classed("bar", true))
            .attr("transform", d => "translate(0, " + (this.scale_y(d.label) + 24) + ")");
    }

    _render_values(domain) {
        this.plot
            .selectAll("g.bar")
            .selectAll("rect.value")
            .data(d => {
                let point = this._tag_dimension.filter(tag => tag == d.use_tags[0]).top(1)[0];
                if (point === undefined) point = {value: 0};

                const levels = cmk_figures.make_levels(domain, d.metrics);
                point.level_color = levels.length
                    ? levels.find(element => point.value < element.to).color
                    : "#3CC2FF";
                return [point];
            })
            .join(enter =>
                enter
                    .append("rect")
                    .classed("value", true)
                    .attr("height", 4)
                    .attr("width", d => this.scale_x(d.value))
            )
            .transition()
            .attr("width", d => this.scale_x(d.value))
            .attr("fill", d => d.level_color);

        this._tag_dimension.filterAll();
    }
}

cmk_figures.figure_registry.register(BarplotFigure);
