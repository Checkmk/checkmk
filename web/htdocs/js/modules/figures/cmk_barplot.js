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
        this.margin = {top: 28, right: 10, bottom: 150, left: 70};

        this._time_dimension = this._crossfilter.dimension(d => d.timestamp);
        this._tag_dimension = this._crossfilter.dimension(d => d.tag);

        this._plot_definitions = [];
    }

    initialize() {
        this.svg = this._div_selection.append("svg");
        this.plot = this.svg
            .append("g")
            .attr("transform", "translate(" + this.margin.left + "," + this.margin.top + ")");

        // X axis
        this.scale_x = d3.scaleBand().padding(0.2);
        this.plot.append("g").classed("x_axis", true).call(d3.axisBottom(this.scale_x));

        // Y axis
        this.scale_y = d3.scaleLinear();
        this.plot.append("g").classed("y_axis", true).call(d3.axisLeft(this.scale_y));
    }

    render() {
        if (this._data) this.update_gui(this._data);
    }

    resize() {
        cmk_figures.FigureBase.prototype.resize.call(this);
        this.svg.attr("width", this.figure_size.width).attr("height", this.figure_size.height);
        this.scale_x.range([0, this.plot_size.width]);
        this.scale_y.range([this.plot_size.height, 0]);
        this.plot
            .select("g.x_axis")
            .attr("transform", "translate(0," + this.plot_size.height + ")");
    }

    _update_plot_definitions(plot_definitions) {
        this._plot_definitions = [];

        // We are only interested in the single_value plot types, they may include metrics info
        plot_definitions.forEach(plot_definition => {
            if (plot_definition.plot_type != "single_value") return;
            this._plot_definitions.push(plot_definition);
        });
    }

    update_gui(data) {
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
        this.scale_x.domain(this._plot_definitions.map(d => d.label));
        this.plot
            .selectAll("g.x_axis")
            .call(d3.axisBottom(this.scale_x))
            .selectAll("text")
            .attr("transform", "translate(-8, 0) rotate(-45)")
            .style("text-anchor", "end");

        let used_tags = this._plot_definitions.map(d => d.use_tags[0]);
        let points = this._tag_dimension.filter(d => used_tags.includes(d)).top(Infinity);
        this.scale_y.domain([0, d3.max(points, d => d.value) * 1.2]);
        this._tag_dimension.filterAll();
        this.plot.selectAll("g.y_axis").call(
            d3.axisLeft(this.scale_y).tickFormat(d => {
                if (d > 999) return d3.format(".2s")(d);
                return d3.format(",")(d);
            })
        );

        this._render_bar_containers();
        this._render_values();
        this._render_levels();
        this._render_bar_tilers();
        this._render_bar_gradients();
    }

    _render_bar_containers() {
        this.plot
            .selectAll("g.bar")
            .data(this._plot_definitions, d => d.id)
            .join(enter => enter.append("g").classed("bar", true))
            .attr("transform", d => {
                return "translate(" + this.scale_x(d.label) + ",0)";
            });
    }

    _render_values() {
        this.plot
            .selectAll("g.bar")
            .selectAll("rect.value")
            .data(d => {
                let point = this._tag_dimension.filter(tag => tag == d.use_tags[0]).top(1)[0];
                return [point != undefined ? point : {value: 0}];
            })
            .join(enter =>
                enter
                    .append("rect")
                    .classed("value", true)
                    .attr("y", d => this.scale_y(d.value))
                    .attr("width", this.scale_x.bandwidth())
                    .attr("height", d => this.plot_size.height - this.scale_y(d.value))
            )
            .transition()
            .attr("y", d => this.scale_y(d.value))
            .attr("width", this.scale_x.bandwidth())
            .attr("height", d => this.plot_size.height - this.scale_y(d.value))
            .attr("fill", (d, idx) => "url(#color-gradient-bar-" + idx + ")");

        this._tag_dimension.filterAll();
    }

    _render_levels() {
        let levels = this.plot
            .selectAll("g.bar")
            .selectAll("rect.level")
            .data(
                d => {
                    let levels = [];
                    let metrics = d.metrics;
                    // TODO: remove dummy metrics
                    // metrics = {};
                    // metrics.crit = 0.9 * d.value;
                    // metrics.warn = 0.8 * d.value;
                    if (metrics == undefined) return levels;
                    [
                        {what: "warn", color: "#fffe44"},
                        {what: "crit", color: "#ff3232"},
                    ].forEach(level => {
                        if (metrics[level.what] == undefined) return;
                        levels.push({level: level, value: metrics[level.what]});
                    });
                    return levels;
                },
                d => d.what
            );

        levels
            .join(enter => enter.append("rect").classed("level", true))
            .attr("y", d => this.scale_y(d["value"]))
            .attr("opacity", 0.5)
            .attr("fill", d => d.level.color)
            .attr("width", this.scale_x.bandwidth())
            .attr("height", 2);
    }

    _render_bar_tilers() {
        let tiles = [];
        let max_tiles = 20;
        let tile_height = this.plot_size.height / max_tiles;

        for (let i = 1; i <= max_tiles; i++) tiles.push(i);

        this.plot
            .selectAll("g.bar")
            .selectAll("rect.tiler")
            .data(tiles)
            .join(enter =>
                enter
                    .append("rect")
                    .classed("tiler", true)
                    .attr("stroke", "#dddddd1f")
                    .attr("opacity", 0.5)
                    .attr("stroke-width", 1.5)
                    .attr("fill", "none")
            )
            .attr("y", d => this.plot_size.height - d * tile_height)
            .attr("height", () => tile_height - 2)
            .attr("width", () => this.scale_x.bandwidth());
    }

    _render_bar_gradients() {
        // Add the color gradient for each bar
        this.plot
            .selectAll("g.bar")
            .selectAll("linearGradient")
            .data((d, idx) => [[d, idx]])
            .join("linearGradient")
            .attr("id", d => "color-gradient-bar-" + d[1])
            .attr("gradientUnits", "userSpaceOnUse")
            .attr("x1", 0)
            .attr("y1", 0)
            .attr("x2", this.scale_x.bandwidth())
            .attr("y2", 0)
            .selectAll("stop")
            .data(() => {
                return [
                    {offset: "0%", color: "#343434", opacity: 0.0},
                    {offset: "30%", color: "#13d389", opacity: 0.35},
                    {offset: "50%", color: "#13d389", opacity: 1},
                    {offset: "70%", color: "#13d389", opacity: 0.35},
                    {offset: "100%", color: "#343434", opacity: 0.0},
                ];
            })
            .enter()
            .append("stop")
            .attr("offset", d => d.offset)
            .attr("stop-color", d => d.color)
            .attr("stop-opacity", d => d.opacity);
    }
}

cmk_figures.figure_registry.register(BarplotFigure);
