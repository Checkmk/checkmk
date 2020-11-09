import * as d3 from "d3";
import * as cmk_figures from "cmk_figures";

// Used for rapid protoyping, bypassing webpack
// var cmk_figures = cmk.figures; /* eslint-disable-line no-undef */
// var dc = dc; /* eslint-disable-line no-undef */
// var d3 = d3; /* eslint-disable-line no-undef */
// var crossfilter = crossfilter; /* eslint-disable-line no-undef */

class GaugeFigure extends cmk_figures.FigureBase {
    static ident() {
        return "gauge";
    }

    constructor(div_selector, fixed_size = null) {
        super(div_selector, fixed_size);
        this._tag_dimension = this._crossfilter.dimension(d => d.tag);
        this.margin = {top: 10, right: 10, bottom: 10, left: 10};
        this._levels = [];
    }

    initialize(debug) {
        if (debug) this._add_scheduler_debugging();
        this.svg = this._div_selection.append("svg");
        this.plot = this.svg.append("g");
    }

    resize() {
        if (this._data.title) {
            this.margin.top = 10 + 24; // 24 from UX project
        } else {
            this.margin.top = 10;
        }

        cmk_figures.FigureBase.prototype.resize.call(this);
        this.svg.attr("width", this.figure_size.width).attr("height", this.figure_size.height);
        this.plot.attr(
            "transform",
            "translate(" +
                (this.plot_size.width / 2 + this.margin.left) +
                "," +
                (this.figure_size.height - this.margin.bottom) +
                ")"
        );
        this._radius = Math.min(this.plot_size.width / 2, this.plot_size.height) / 1.35;
    }

    update_data(data) {
        cmk_figures.FigureBase.prototype.update_data.call(this, data);
        this._levels = [];
        let plot = this._data.plot_definitions.filter(d => d.plot_type == "single_value")[0];
        if (!plot) return;

        let metrics = plot.metrics;
        if (!metrics) return;

        this._levels = [
            {from: metrics.min || 0, to: metrics.warn, color: "green"},
            {from: metrics.warn, to: metrics.crit, color: "yellow"},
            {from: metrics.crit, to: Infinity, color: "red"},
        ];
    }

    update_gui() {
        this._crossfilter.remove(() => true);
        this._crossfilter.add(this._data.data);

        let filter_tag = null;
        if (this._data.plot_definitions && this._data.plot_definitions.length > 0)
            filter_tag = this._data.plot_definitions[this._data.plot_definitions.length - 1]
                .use_tags[0];
        this._tag_dimension.filter(d => d == filter_tag);

        this.resize();
        this.render();
    }

    render() {
        this._update_domain();
        this._render_fixed_elements();
        this._render_levels();
        this._render_histogram();
        this._render_pointer();
        this._render_text();
        this.render_title(this._data.title);

        let plot = this._data.plot_definitions.filter(d => d.plot_type == "single_value")[0];
        if (!plot) return;
        cmk_figures.state_component(this, plot.svc_state);
    }

    _update_domain() {
        this._domain = d3.extent(this._crossfilter.allFiltered(), d => d.value);
        let domain_max = this._domain[1];
        // TODO: discuss visible domain of gauge
        //this._levels.forEach(level=>{
        //    if (level.to != Infinity)
        //        domain_max = Math.max(level.to, domain_max);
        //});
        // The visible domain is currently the max value plus 20%
        this._domain[0] = 0;
        this._domain[1] = domain_max * 1.2;
    }

    _render_fixed_elements() {
        this.plot
            .selectAll("path.background")
            .data([null])
            .join(enter => enter.append("path").classed("background", true))
            .attr("fill", "grey")
            .attr("opacity", 0.1)
            .attr(
                "d",
                d3
                    .arc()
                    .innerRadius(this._radius * 0.9)
                    .outerRadius(this._radius * 1.35)
                    .startAngle(-Math.PI / 2)
                    .endAngle(Math.PI / 2)
            );
    }

    _render_levels() {
        const scale_x = d3
            .scaleLinear()
            .domain(this._domain)
            .range([-Math.PI / 2, Math.PI / 2]);
        this.plot
            .selectAll("path.level")
            .data(this._levels)
            .join(enter => enter.append("path").classed("level", true))
            .attr("fill", d => d.color)
            .attr("opacity", 0.9)
            .attr(
                "d",
                d3
                    .arc()
                    .innerRadius(this._radius)
                    .outerRadius(this._radius * 1.08)
                    .startAngle(d => Math.min(Math.PI / 2, scale_x(d.from)))
                    .endAngle(d => {
                        if (d.to == Infinity) return Math.PI / 2;
                        else return Math.min(Math.PI / 2, scale_x(d.to));
                    })
            )
            .selectAll("title")
            .data(d => [d])
            .join("title")
            .text(d => d.from + " -> " + d.to);
    }

    _render_histogram() {
        let data = this._crossfilter.allFiltered();
        let num_bins = 20;
        const x = d3.scaleLinear().domain([0, num_bins]).range(this._domain);
        const bins = d3
            .histogram()
            .value(d => d.value)
            .thresholds(d3.range(num_bins).map(x))
            .domain(x.range())(data);

        let record_count = data.length;
        const bin_scale = d3
            .scaleLinear()
            .domain([0, d3.max(bins, d => d.length)])
            .range([0, this._radius * 0.2]);
        const angle_between_bins = Math.PI / bins.length;
        this.plot
            .selectAll("path.bin")
            .data(bins)
            .join(enter => enter.append("path").classed("bin", true))
            .attr("fill", "steelblue")
            .attr("stroke", d => (d.length > 0 ? "black" : null))
            .attr(
                "d",
                d3
                    .arc()
                    .innerRadius(this._radius * 1.1)
                    .outerRadius(
                        d => this._radius * 1.1 + bin_scale(d.length) + (d.length > 0 ? 2 : 0)
                    )
                    .startAngle((d, idx) => -Math.PI / 2 + idx * angle_between_bins)
                    .endAngle((d, idx) => -Math.PI / 2 + (idx + 1) * angle_between_bins)
            )
            .selectAll("title")
            .data(d => [d])
            .join("title")
            .text(d => {
                let title = "";
                if (d.length == 0) return title;
                title += ((100.0 * d.length) / record_count).toPrecision(3);
                title += "%: " + d.x0.toPrecision(3);
                title += " -> " + d.x1.toPrecision(3);
                return title;
            });
    }

    _render_pointer() {
        let data = this._crossfilter.allFiltered();
        let pointer_perc = 0;

        if (data.length > 0) {
            pointer_perc = data[data.length - 1].value / this._domain[1];
        }
        const rotation = -90 + pointer_perc * 180;
        const pointer_scale = this._radius / 1.2 / 14; // The svg path below has a height of 14px
        this.plot
            .selectAll("path.pointer")
            .data([pointer_perc])
            .join(enter => enter.append("path").classed("pointer", true))
            .transition()
            .attr("fill", "#bb6a6a")
            .attr("transform", "scale(" + pointer_scale + ") rotate(" + rotation + ")")
            .attr("d", "m 0 -4 l 1 -3 l -1 -6 l -1 6");
    }

    _render_text() {
        let data = this._crossfilter.allFiltered();
        if (data.length) {
            let value = cmk_figures.split_unit(data[data.length - 1]);
            cmk_figures.metric_value_component(
                this.plot,
                value,
                this._radius / 5,
                0,
                -this.plot_size.height / 3
            );
        }
    }
}

cmk_figures.figure_registry.register(GaugeFigure);
