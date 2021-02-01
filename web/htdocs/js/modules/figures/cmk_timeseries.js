import * as d3 from "d3";
import * as cmk_figures from "cmk_figures";
import * as crossfilter from "crossfilter2";

// Used for rapid protoyping, bypassing webpack
//var cmk_figures = cmk.figures; /*eslint-disable-line no-undef*/
//var dc = dc; /*eslint-disable-line no-undef*/
//var d3 = d3; /*eslint-disable-line no-undef*/
//var crossfilter = crossfilter; /*eslint-disable-line no-undef*/

// The TimeseriesFigure provides a renderer mechanic. It does not actually render the bars/dot/lines/areas.
// Instead, it manages a list of subplots. Each subplot receives a drawing area and render its data when when
// being told by the TimeseriesFigure
class TimeseriesFigure extends cmk_figures.FigureBase {
    static ident() {
        return "timeseries";
    }

    constructor(div_selector, fixed_size = null) {
        super(div_selector, fixed_size);
        this._subplots = [];
        this._subplots_by_id = {};
        this.margin = {top: 28, right: 10, bottom: 30, left: 65};
        this._legend_dimension = this._crossfilter.dimension(d => d.tag);
    }

    get_id() {
        return this._div_selection.attr("id");
    }

    initialize() {
        // TODO: check double diff, currently used for absolute/auto styling
        this._div_selection.classed("timeseries", true).style("overflow", "visible");
        let main_div = this._div_selection
            .append("div")
            .classed("figure_content", true)
            .style("position", "absolute")
            .style("display", "inline-block")
            .style("overflow", "visible")
            .on("click", () => this._mouse_click())
            .on("mousedown", () => this._mouse_down())
            .on("mousemove", () => this._mouse_move())
            .on("mouseleave", () => this._mouse_out());

        // The main svg, covers the whole figure
        this.svg = main_div
            .append("svg")
            .datum(this)
            .classed("renderer", true)
            .style("overflow", "visible");

        // The g for the subplots, checks margins
        this.g = this.svg.append("g");

        this._tooltip = main_div.append("div");
        this.tooltip_generator = new cmk_figures.FigureTooltip(this._tooltip);
        // TODO: uncomment to utilize the tooltip collapser
        //let collapser = this._tooltip.append("div").classed("collapser", true);
        //collapser.append("img").attr("src", "themes/facelift/images/tree_closed.png")
        //    .on("click", ()=>{
        //        collapser.classed("active", !collapser.classed("active"));
        //    });

        // All subplots share the same scale
        this.scale_x = d3.scaleTime();
        this.orig_scale_x = d3.scaleTime();
        this.scale_y = d3.scaleLinear();
        this.orig_scale_y = d3.scaleLinear();

        this._setup_legend();
        this.resize();
        this._setup_zoom();

        this.lock_zoom_x = false;
        this.lock_zoom_y = false;
        this.lock_zoom_x_scale = false;
    }

    _setup_legend() {
        this._legend = this._div_selection
            .select("div.figure_content")
            .append("div")
            .style("display", "none")
            .style("top", this.margin.top + "px");
        this.legend_generator = new cmk_figures.FigureLegend(this._legend);
    }

    _mouse_down() {}

    _mouse_click() {}

    _mouse_out() {}

    _mouse_move() {}

    crossfilter() {
        if (!arguments.length) {
            return this._crossfilter;
        }
        this._crossfilter = crossfilter;
        return this;
    }

    get_plot_id(plot_id) {
        return this._subplots_by_id[plot_id];
    }

    resize() {
        let new_size = this._fixed_size;
        if (new_size === null)
            new_size = {
                width: this._div_selection.node().parentNode.offsetWidth,
                height: this._div_selection.node().parentNode.offsetHeight,
            };
        this.figure_size = new_size;
        if (this._title) {
            this.margin.top = 10 + 24; // 24 from UX project
        }
        this.plot_size = {
            width: new_size.width - this.margin.left - this.margin.right,
            height:
                new_size.height - this.margin.top - this.margin.bottom - this._get_legend_height(),
        };
        this.tooltip_generator.update_sizes(this.figure_size, this.plot_size);
        this._div_selection.style("height", this.figure_size.height + "px");
        this.svg.attr("width", this.figure_size.width);
        this.svg.attr("height", this.figure_size.height);
        this.g.attr("transform", "translate(" + this.margin.left + "," + this.margin.top + ")");

        this.orig_scale_x.range([0, this.plot_size.width]);
        this.orig_scale_y.range([this.plot_size.height, 0]);
    }

    _get_legend_height() {
        return 0;
    }

    _setup_zoom() {
        this._current_zoom = d3.zoomIdentity;
        this._zoom_active = false;
        this._zoom = d3
            .zoom()
            .scaleExtent([0.01, 100])
            .on("zoom", () => {
                let last_y = this._current_zoom.y;
                if (this.lock_zoom_x) {
                    d3.event.transform.x = 0;
                    d3.event.transform.k = 1;
                }
                if (this.lock_zoom_x_scale) d3.event.transform.k = 1;

                this._current_zoom = d3.event.transform;
                if (d3.event.sourceEvent.type === "wheel") this._current_zoom.y = last_y;
                this._zoomed();
            });
        this.svg.call(this._zoom);
    }

    _zoomed() {
        this._zoom_active = true;
        this.render();
        this._zoom_active = false;
    }

    add_plot(plot) {
        plot.renderer(this);
        this._subplots.push(plot);
        this._subplots_by_id[plot.definition.id] = plot;

        if (plot.main_g) {
            let removed = plot.main_g.remove();
            this._div_selection.select("g").select(function () {
                this.appendChild(removed.node());
            });
        }
    }

    remove_plot(plot) {
        let idx = this._subplots.indexOf(plot);
        if (idx > -1) {
            this._subplots.splice(idx, 1);
            delete this._subplots_by_id[plot.definition.id];
        }
        plot.remove();
    }

    update_data(data) {
        data.data.forEach(d => {
            d.date = new Date(d.timestamp * 1000);
        });
        cmk_figures.FigureBase.prototype.update_data.call(this, data);
        this._title = data.title;
        this._update_zoom_settings();
        this._update_crossfilter(data.data);
        this._update_subplots(data.plot_definitions);
        this._compute_stack_values();
    }

    _update_zoom_settings() {
        let settings = this._data.zoom_settings;
        if (settings === undefined) return;

        ["lock_zoom_x", "lock_zoom_y", "lock_zoom_x_scale"].forEach(option => {
            if (settings[option] == undefined) return;
            this[option] = settings[option];
        });
    }

    update_gui() {
        this.update_domains();
        this.resize();
        this.render();
    }

    update_domains() {
        let all_domains = [];
        this._subplots.forEach(subplot => {
            let domains = subplot.get_domains();
            if (domains) all_domains.push(domains);
        });
        this._x_domain = [d3.min(all_domains, d => d.x[0]), d3.max(all_domains, d => d.x[1])];
        this._y_domain = [d3.min(all_domains, d => d.y[0]), d3.max(all_domains, d => d.y[1] * 1.1)];
        this.orig_scale_x.domain(this._x_domain);
        this.orig_scale_y.domain(this._y_domain);
    }

    _update_crossfilter(data) {
        this._crossfilter.remove(() => true);
        this._crossfilter.add(data);
    }

    _update_subplots(plot_definitions) {
        // Mark all existing plots for removal
        this._subplots.forEach(subplot => {
            subplot.marked_for_removal = true;
        });

        plot_definitions.forEach(definition => {
            if (this._plot_exists(definition.id)) {
                delete this._subplots_by_id[definition.id]["marked_for_removal"];
                // Update definition of existing plot
                this._subplots_by_id[definition.id].definition = definition;
                return;
            }
            // Add new plot
            this.add_plot(this.create_plot_from_definition(definition));
        });

        // Remove vanished plots
        this._subplots.forEach(subplot => {
            if (subplot.marked_for_removal) this.remove_plot(subplot);
        });

        this._subplots.forEach(subplot => subplot.update_transformed_data());
    }

    create_plot_from_definition(definition) {
        let new_plot = new (subplot_factory.get_plot(definition.plot_type))(definition);
        let dimension = this._crossfilter.dimension(d => d.date);
        new_plot.renderer(this);
        new_plot.dimension(dimension);
        return new_plot;
    }

    _plot_exists(plot_id) {
        for (let idx in this._subplots) {
            if (this._subplots[idx].definition.id == plot_id) return true;
        }
        return false;
    }

    render() {
        this.render_title(this._title);

        // Prepare scales, the subplots need them to render the data
        this._prepare_scales();

        // Prepare render area for subplots
        // TODO: move to plot creation
        this._subplots.forEach(subplot => {
            subplot.prepare_render();
        });

        // Render subplots
        this._subplots.forEach(subplot => {
            subplot.render();
        });

        this.render_axis();
        this.render_grid();
        this.render_legend();
    }

    render_legend() {
        this._legend.style("display", this._subplots.length > 0 ? null : "none");

        if (this._subplots.length <= 1) return;

        let items = this._legend
            .selectAll(".legend_item")
            .data(this._subplots, d => d.definition.id);
        items.exit().remove();
        let new_items = items
            .enter()
            .append("div")
            .classed("legend_item", true)
            .classed("noselect", true);

        new_items.append("div").classed("color_code", true);
        new_items.style("pointer-events", "all");
        new_items.append("label").text(d => d.definition.label);

        new_items.on("click", (legend_d, idx, nodes) => {
            let item = d3.select(nodes[idx]);
            item.classed("disabled", !item.classed("disabled"));
            item.style("background", (item.classed("disabled") && "grey") || null);
            let all_disabled = [];
            this._div_selection.selectAll(".legend_item.disabled").each(d => {
                all_disabled.push(d.definition.use_tags[0]);
            });
            this._legend_dimension.filter(d => {
                return all_disabled.indexOf(d) == -1;
            });
            this._compute_stack_values();
            this._subplots.forEach(subplot => subplot.update_transformed_data());
            this.update_gui();
        });

        // Easter egg
        //new_items.call(
        //    d3.drag()
        //        .on("start", () => this.legend_generator._dragstart())
        //        .on("drag", () => this.legend_generator._drag())
        //        .on("end", () => this.legend_generator._dragend())
        //);

        new_items
            .merge(items)
            .selectAll("div")
            .style("background", d => d.get_color());
    }

    _prepare_scales() {
        this.scale_x = this._current_zoom.rescaleX(this.orig_scale_x);
        this.scale_y.range(this.orig_scale_y.range());
        this.scale_y.domain(this.orig_scale_y.domain());

        if (this.lock_zoom_y) this.scale_y.domain(this.orig_scale_y.domain());
        else {
            let y_max = this.orig_scale_y.domain()[1];
            let y_stretch = Math.max(0.05 * y_max, y_max + (this._current_zoom.y / 100) * y_max);
            this.scale_y.domain([0, y_stretch]);
        }
    }

    _find_metric_to_stack(definition, all_disabled) {
        if (!this._subplots_by_id[definition.stack_on]) return null;
        if (all_disabled.indexOf(definition.stack_on) == -1) return definition.stack_on;
        if (this._subplots_by_id[definition.stack_on].definition.stack_on)
            return this._find_metric_to_stack(
                this._subplots_by_id[definition.stack_on].definition,
                all_disabled
            );
        return null;
    }

    _compute_stack_values() {
        // Disabled metrics
        let all_disabled = [];
        this._div_selection.selectAll(".legend_item.disabled").each(d => {
            all_disabled.push(d.definition.id);
        });

        // Identify stacks
        let required_stacks = {};
        this._subplots.forEach(subplot => {
            subplot.stack_values = null;
            if (subplot.definition.stack_on) {
                let stack_on = this._find_metric_to_stack(subplot.definition, all_disabled);
                if (stack_on != null) required_stacks[subplot.definition.id] = stack_on;
            }
        });

        // Order stacks
        // TBD:

        // Update stacks
        let base_values = {};
        for (let target in required_stacks) {
            let source = this._subplots_by_id[required_stacks[target]];
            source.update_transformed_data();
            let references = {};
            source.transformed_data.forEach(point => {
                references[point.timestamp] = point.value;
            });
            base_values[source.definition.id] = references;
            this._subplots_by_id[target].stack_values = references;
            this._subplots_by_id[target].update_transformed_data();
        }
    }

    render_axis() {
        let x = this.g
            .selectAll("g.x_axis")
            .data([null])
            .join("g")
            .classed("x_axis", true)
            .classed("axis", true);

        this.transition(x).call(
            d3
                .axisBottom(this.scale_x)
                .tickFormat(d => {
                    if (d.getMonth() === 0 && d.getDate() === 1) return d3.timeFormat("%Y")(d);
                    else if (d.getHours() === 0 && d.getMinutes() === 0)
                        return d3.timeFormat("%m-%d")(d);
                    return d3.timeFormat("%H:%M")(d);
                })
                .ticks(6)
        );
        x.attr("transform", "translate(0," + this.plot_size.height + ")");

        let render_function = this.get_scale_render_function();
        let y = this.g
            .selectAll("g.y_axis")
            .data([null])
            .join("g")
            .classed("y_axis", true)
            .classed("axis", true);
        this.transition(y).call(
            d3
                .axisLeft(this.scale_y)
                .tickFormat(d => render_function(d))
                .ticks(Math.min(Math.floor(this.plot_size.height / 16), 6))
        );
    }

    render_grid() {
        // Grid
        let height = this.plot_size.height;
        this.g
            .selectAll("g.grid.vertical")
            .data([null])
            .join("g")
            .classed("grid vertical", true)
            .attr("transform", "translate(0," + height + ")")
            .call(d3.axisBottom(this.scale_x).ticks(5).tickSize(-height).tickFormat(""));

        let width = this.plot_size.width;
        this.g
            .selectAll("g.grid.horizontal")
            .data([null])
            .join("g")
            .classed("grid horizontal", true)
            .call(d3.axisLeft(this.scale_y).ticks(5).tickSize(-width).tickFormat(""));
    }

    transition(selection) {
        if (this._zoom_active) {
            selection.interrupt();
            return selection;
        } else return selection.transition().duration(500);
    }
}

cmk_figures.figure_registry.register(TimeseriesFigure);

// A generic average scatterplot chart with median/mean lines and scatterpoints for each instance
// Requirements:
//     Subplots with id
//       - id_scatter
//       - id_mean
//       - id_median
//     Data tagged with
//       - line_mean
//       - line_median
//       - scatter
class AverageScatterplotFigure extends TimeseriesFigure {
    static ident() {
        return "average_scatterplot";
    }

    _mouse_down() {
        // d3.event.button == 1 equals a pressed mouse wheel
        if (d3.event.button == 1 && this._selected_scatterpoint) {
            window.open(this._selected_scatterpoint.url);
        }
    }

    _mouse_click() {
        if (this._selected_scatterpoint) window.location = this._selected_scatterpoint.url;
    }

    _mouse_out() {
        this.g.select("path.pin").remove();
        this._tooltip.selectAll("table").remove();
        this._tooltip.style("opacity", 0);
    }

    _mouse_move() {
        let ev = d3.event;
        // TODO KO: clean up these mouse events for better performance
        if (
            !["svg", "path"].includes(ev.target.tagName) ||
            ev.layerX < this.margin.left ||
            ev.layerY < this.margin.top ||
            ev.layerX > this.margin.left + this.plot_size.width ||
            ev.layerY > this.margin.top + this.plot_size.height
        ) {
            this._mouse_out();
            return;
        }
        if (!this._crossfilter || !this._subplots_by_id["id_scatter"]) return;

        // TODO AB: change this dimensions to members
        //          filter_dimension -> tag_dimension
        //          result_dimension -> date_dimension
        let filter_dimension = this._crossfilter.dimension(d => d);
        let result_dimension = this._crossfilter.dimension(d => d.timestamp);

        // Find focused scatter point and highlight it
        let scatter_plot = this._subplots_by_id["id_scatter"];
        let scatterpoint = scatter_plot.quadtree.find(
            ev.layerX - this.margin.left,
            ev.layerY - this.margin.top,
            10
        );
        this._selected_scatterpoint = scatterpoint;

        let use_date = null;
        scatter_plot.redraw_canvas();
        if (scatterpoint !== undefined) {
            use_date = scatterpoint.date;
            // Highlight all incidents, based on this scatterpoint's label
            let ctx = scatter_plot.canvas.node().getContext("2d");
            let points = scatter_plot.transformed_data.filter(d => d.label == scatterpoint.label);
            let line = d3
                .line()
                .x(d => d.scaled_x)
                .y(d => d.scaled_y)
                .context(ctx);
            ctx.beginPath();
            line(points);
            let hilited_host_color = this._get_css("stroke", "path", ["host", "hilite"]);
            ctx.strokeStyle = hilited_host_color;
            ctx.stroke();

            // Highlight selected point
            ctx.beginPath();
            ctx.arc(scatterpoint.scaled_x, scatterpoint.scaled_y, 3, 0, Math.PI * 2, false);
            let hilited_node_color = this._get_css("fill", "circle", ["scatterdot", "hilite"]);
            ctx.fillStyle = hilited_node_color;
            ctx.fill();
            ctx.stroke();
        } else {
            use_date = this.scale_x.invert(ev.layerX - this.margin.left);
        }

        // Find nearest mean point
        filter_dimension.filter(d => d.tag == "line_mean");
        let results = result_dimension.bottom(Infinity);
        let nearest_bisect = d3.bisector(d => d.timestamp).left;
        let idx = nearest_bisect(results, use_date.getTime() / 1000);

        let mean_point = results[idx];
        if (mean_point == undefined) {
            filter_dimension.dispose();
            result_dimension.dispose();
            return;
        }

        // Get corresponding median point
        filter_dimension.filter(d => d.tag == "line_median");
        let median_point = result_dimension.bottom(Infinity)[idx];

        // Get scatter points for this date
        filter_dimension.filter(d => d.timestamp == mean_point.timestamp && d.tag == "scatter");
        let scatter_matches = result_dimension.top(Infinity);
        scatter_matches.sort((first, second) => first.value > second.value);
        let top_matches = scatter_matches.slice(-5, -1).reverse();
        let bottom_matches = scatter_matches.slice(0, 4).reverse();

        this._selected_meanpoint = mean_point;
        this._update_pin();

        this._render_tooltip(top_matches, bottom_matches, mean_point, median_point, scatterpoint);

        filter_dimension.dispose();
        result_dimension.dispose();
    }

    _zoomed() {
        super._zoomed();
        this._update_pin();
    }

    _update_pin() {
        if (this._selected_meanpoint) {
            this.g.select("path.pin").remove();
            let x = this.scale_x(this._selected_meanpoint.date);
            this.g
                .append("path")
                .classed("pin", true)
                .attr(
                    "d",
                    d3.line()([
                        [x, 0],
                        [x, this.plot_size.height],
                    ])
                )
                .attr("pointer-events", "none");
        }
    }

    _render_tooltip(top_matches, bottom_matches, mean_point, median_point, scatterpoint) {
        this._tooltip.selectAll("table").remove();

        let table = this._tooltip.append("table");

        let date_row = table.append("tr").classed("date", true);
        date_row.append("td").text(mean_point.date).attr("colspan", 2);

        let mean_row = table.append("tr").classed("mean", true);
        mean_row.append("td").text(mean_point.label);
        mean_row.append("td").text(mean_point.value.toFixed(2));
        let median_row = table.append("tr").classed("median", true);
        median_row.append("td").text(median_point.label);
        median_row.append("td").text(median_point.value.toFixed(2));

        if (scatterpoint) {
            let scatter_row = table.append("tr").classed("scatterpoint", true);
            let hilited_host_color = this._get_css("stroke", "path", ["host", "hilite"]);
            scatter_row
                .append("td")
                .text(scatterpoint.tooltip.split(" ")[0] + " (selected)")
                .style("color", hilited_host_color);
            scatter_row.append("td").text(scatterpoint.value.toFixed(2));
        }

        let top_rows = table
            .selectAll("tr.top_matches")
            .data(top_matches)
            .enter()
            .append("tr")
            .classed("top_matches", true);
        top_rows.append("td").text(d => d.tooltip.split(" ")[0]);
        top_rows.append("td").text(d => d.value.toFixed(3));

        let bottom_rows = table
            .selectAll("tr.bottom_matches")
            .data(bottom_matches)
            .enter()
            .append("tr")
            .classed("bottom_matches", true);
        bottom_rows.append("td").text(d => d.tooltip.split(" ")[0]);
        bottom_rows.append("td").text(d => d.value.toFixed(3));

        this.tooltip_generator.update_position();
    }

    _get_css(prop, tag, classes) {
        let obj = this.svg.append(tag);
        classes.forEach(cls => obj.classed(cls, true));
        let css = obj.style(prop);
        obj.remove();
        return css;
    }
}

cmk_figures.figure_registry.register(AverageScatterplotFigure);

// A single metric figure with optional graph rendering in the background
class SingleMetricFigure extends TimeseriesFigure {
    static ident() {
        return "single_metric";
    }

    constructor(div_selector, fixed_size = null) {
        super(div_selector, fixed_size);
        this.margin = {top: 10, right: 10, bottom: 10, left: 10};
    }

    initialize() {
        super.initialize();
        this.lock_zoom_x = true;
        this.lock_zoom_y = true;
        this.lock_zoom_x_scale = true;
    }

    _setup_zoom() {
        this._current_zoom = d3.zoomIdentity;
    }

    render_legend() {}
    render_grid() {
        if (this._data.plot_definitions.filter(d => d.plot_type == "area").length == 1)
            super.render_grid();
    }

    render_axis() {}
}

cmk_figures.figure_registry.register(SingleMetricFigure);

// Base class for all SubPlots
// It renders its data into a <g> provided by the renderer instance
class SubPlot {
    constructor(definition) {
        this.definition = definition;

        this._renderer = null; // Graph which renders this plot
        this._dimension = null; // The crossfilter dimension (x_axis)
        this.transformed_data = []; // data shifted/scaled by subplot definition

        this.stack_values = null; // timestamp/value pairs provided by the target plot

        this.main_g = null; // toplevel g, contains svg/canvas elements
        this.svg = null; // svg content
        return this;
    }

    _get_css(prop, tag, classes) {
        let obj = this.svg.append(tag);
        classes.forEach(cls => obj.classed(cls, true));
        let css = obj.style(prop);
        obj.remove();
        return css;
    }

    renderer(renderer) {
        if (!arguments.length) {
            return this._renderer;
        }
        this._renderer = renderer;
        this.prepare_render();
        return this;
    }

    remove() {
        this.main_g.transition().duration(1000).style("opacity", 0).remove();
    }

    get_color() {
        if (this.definition.color) return d3.color(this.definition.color);
        return;
    }

    get_opacity() {
        if (this.definition.opacity) return this.definition.opacity;
        return 1;
    }

    dimension(dimension) {
        if (!arguments.length) {
            return this._dimension;
        }
        this._dimension = dimension;
        return this;
    }

    get_domains() {
        // Return the x/y domain boundaries
        if (this.definition.is_scalar) return;

        return {
            x: [
                d3.min(this.transformed_data, d => d.date),
                d3.max(this.transformed_data, d => d.date),
            ],
            y: [0, d3.max(this.transformed_data, d => d.value)],
        };
    }

    get_legend_data(start, end) {
        // Returns the currently shown x/y domain boundaries
        if (this.definition.is_scalar) return {data: this.transformed_data};

        let data = this.transformed_data.filter(d => {
            return d.timestamp >= start && d.timestamp <= end;
        });

        let value_accessor =
            this.definition.stack_on && this.definition.stack_values ? "unstacked_value" : "value";
        return {
            x: [d3.min(data, d => d.date), d3.max(data, d => d.date)],
            y: [0, d3.max(data, d => d[value_accessor])],
            data: data,
        };
    }

    prepare_render() {
        let plot_size = this._renderer.plot_size;

        // The subplot main_g contains all graphical components for this subplot
        this.main_g = this._renderer.g
            .selectAll("g.subplot_main_g." + this.definition.id)
            .data([null])
            .join("g")
            .classed("subplot_main_g", true)
            .classed(this.definition.id, true);

        if (this.definition.css_classes)
            this.main_g.classed(this.definition.css_classes.join(" "), true);

        // Default drawing area
        this.svg = this.main_g
            .selectAll("svg.subplot")
            .data([null])
            .join("svg")
            .attr("width", plot_size.width)
            .attr("height", plot_size.height)
            .classed("subplot", true);
    }

    // Currently unused. Handles the main_g of SubPlots between different TimeseriesFigure instances
    migrate_to(other_renderer) {
        let delta = null;
        if (this._renderer) {
            this._renderer.remove_plot(this);
            let old_box = this._renderer._div_selection.node().getBoundingClientRect();
            let new_box = other_renderer._div_selection.node().getBoundingClientRect();
            delta = {x: old_box.x - new_box.x, y: old_box.top - new_box.top};
        }
        other_renderer.add_plot(this);
        if (delta) {
            other_renderer.g
                .select(".subplot_main_g." + this.definition.id)
                .attr("transform", "translate(" + delta.x + "," + delta.y + ")")
                .transition()
                .duration(2500)
                .attr("transform", "translate(0,0) scale(1)");
        }

        // TODO: Refactor, introduces dashlet dependency
        let dashlet = d3.select(other_renderer._div_selection.node().closest(".dashlet"));
        if (!dashlet.empty())
            dashlet.style("z-index", 1000).transition().duration(2000).style("z-index", 0);

        other_renderer.remove_loading_image();
        other_renderer.update_gui();
    }

    get_coord_shifts() {
        let shift_seconds = this.definition.shift_seconds || 0;
        let shift_y = this.definition.shift_y || 0;
        let scale_y = this.definition.scale_y || 1;
        return [shift_seconds, shift_y, scale_y];
    }

    update_transformed_data() {
        let shifts = this.get_coord_shifts();
        let shift_second = shifts[0];
        let shift_y = shifts[1];
        let scale_y = shifts[2];

        let data = this._dimension.top(Infinity);
        data = data.filter(d => d.tag == this.definition.use_tags[0]);
        //let data = this._dimension.filter(d=>d.tag == this.definition.use_tags[0]).top(Infinity);
        //this._dimension.filterAll();

        // Create a deepcopy
        this.transformed_data = JSON.parse(JSON.stringify(data));
        this.transformed_data.forEach(point => {
            point.timestamp += shift_second;
            point.date = new Date(point.timestamp * 1000);
        });

        if (shift_y != 0)
            this.transformed_data.forEach(point => {
                point.value += shift_y;
            });

        if (scale_y != 1)
            this.transformed_data.forEach(point => {
                point.value *= scale_y;
            });

        if (this.stack_values != null)
            this.transformed_data.forEach(point => {
                point.unstacked_value = point.value;
                point.value += this.stack_values[point.timestamp] || 0;
            });
    }
}

// Renders a single uninterrupted line
class LinePlot extends SubPlot {
    static ident() {
        return "line";
    }

    render() {
        let line = d3
            .line()
            .curve(d3.curveLinear)
            .x(d => this._renderer.scale_x(d.date))
            .y(d => this._renderer.scale_y(d.value));

        let path = this.svg
            .selectAll("g.graph_data path")
            .data([this.transformed_data])
            .join(enter =>
                enter.append("g").classed("graph_data", true).append("path").classed("line", true)
            )
            .classed((this.definition.css_classes || []).join(" "), true);

        let stroke_width = this.definition.stroke_width || 2;
        let color = this.get_color();
        let opacity = this.get_opacity() || 1;

        this._renderer
            .transition(path)
            .attr("d", d => line(d))
            .attr("fill", "none")
            .style("stroke-width", stroke_width)
            .style("opacity", opacity)
            .style("stroke", color);
    }

    get_color() {
        let color = SubPlot.prototype.get_color.call(this);
        let classes = (this.definition.css_classes || []).concat("line");
        return color != undefined ? color : d3.color(this._get_css("stroke", "path", classes));
    }
}

// Renders an uninterrupted area
class AreaPlot extends SubPlot {
    static ident() {
        return "area";
    }

    render() {
        let shift_y = this.get_coord_shifts()[1];
        let base = this._renderer.scale_y(shift_y);
        let area = d3
            .area()
            .curve(d3.curveLinear)
            //.curve(d3.curveCardinal)
            .x(d => this._renderer.scale_x(d.date))
            .y1(d => this._renderer.scale_y(d.value))
            .y0(d => {
                if (this.stack_values != null)
                    return this._renderer.scale_y(this.stack_values[d.timestamp] || 0);
                else return base;
            });

        let color = this.get_color();
        let opacity = this.get_opacity();
        let stroke_width = this.get_stroke_width();

        let path = this.svg
            .selectAll("g.graph_data path")
            .data([this.transformed_data])
            .join(enter =>
                enter.append("g").classed("graph_data", true).append("path").classed("area", true)
            )
            .classed((this.definition.css_classes || []).join(" "), true);

        this._renderer
            .transition(path)
            .attr("d", d => area(d))
            .style("fill", color)
            .style("stroke", color)
            .style("stroke-width", stroke_width)
            .style("fill-opacity", opacity);
    }

    get_color() {
        let color = SubPlot.prototype.get_color.call(this);
        let classes = (this.definition.css_classes || []).concat("area");
        return color != undefined ? color : d3.color(this._get_css("fill", "path", classes));
    }

    get_opacity() {
        let opacity = this.definition.opacity;
        let classes = (this.definition.css_classes || []).concat("area");
        return opacity != undefined ? opacity : this._get_css("opacity", "path", classes);
    }

    get_stroke_width() {
        return this.definition.stroke_width || 2;
    }
}

// Renders scatterplot points on a canvas
// Provides quadtree to find points on canvas
class ScatterPlot extends SubPlot {
    static ident() {
        return "scatterplot";
    }

    constructor(definition) {
        super(definition);
        this.quadtree = null;
        this.canvas = null;
        return this;
    }

    prepare_render() {
        SubPlot.prototype.prepare_render.call(this);
        let plot_size = this._renderer.plot_size;
        let fo = this.main_g
            .selectAll("foreignObject.canvas_object")
            .data([plot_size])
            .join("foreignObject")
            .style("pointer-events", "none")
            .classed("canvas_object", true)
            .attr("width", d => d.width)
            .attr("height", d => d.height);

        let body = fo.selectAll("xhtml").data([null]).join("xhtml").style("margin", "0px");

        this.canvas = body
            .selectAll("canvas")
            .data([plot_size])
            .join("canvas")
            .classed("subplot", true)
            .attr("x", 0)
            .attr("y", 0)
            .attr("width", d => d.width)
            .attr("height", d => d.height);
    }

    render() {
        let scale_x = this._renderer.scale_x;
        let scale_y = this._renderer.scale_y;
        this.transformed_data.forEach(point => {
            point.scaled_x = scale_x(point.date);
            point.scaled_y = scale_y(point.value);
        });

        this.quadtree = d3
            .quadtree()
            .x(d => d.scaled_x)
            .y(d => d.scaled_y)
            .addAll(this.transformed_data);
        this.redraw_canvas();
    }

    redraw_canvas() {
        let plot_size = this._renderer.plot_size;
        let ctx = this.canvas.node().getContext("2d");
        if (!this._last_canvas_size) this._last_canvas_size = plot_size;

        ctx.clearRect(-1, -1, this._last_canvas_size.width + 2, this._last_canvas_size.height + 2);
        let canvas_data = ctx.getImageData(0, 0, plot_size.width, plot_size.height);

        let color = this.get_color();
        let r = color.r;
        let b = color.b;
        let g = color.g;
        this.transformed_data.forEach(point => {
            if (point.scaled_x > plot_size.width || point.scaled_x < 0) return;
            let index = (parseInt(point.scaled_x) + parseInt(point.scaled_y) * plot_size.width) * 4;
            canvas_data.data[index + 0] = r;
            canvas_data.data[index + 1] = g;
            canvas_data.data[index + 2] = b;
            canvas_data.data[index + 3] = 255;
        });
        ctx.putImageData(canvas_data, 0, 0);
        this._last_canvas_size = plot_size;
    }

    get_color() {
        let color = SubPlot.prototype.get_color.call(this);
        return color != undefined
            ? color
            : d3.color(this._get_css("fill", "circle", ["scatterdot"]));
    }
}

// Renders multiple bars, each based on date->end_date
class BarPlot extends SubPlot {
    static ident() {
        return "bar";
    }

    render() {
        let plot_size = this._renderer.plot_size;
        let bars = this.svg.selectAll("rect.bar").data(this.transformed_data);
        bars.exit().remove();

        const classes = this.definition.css_classes || [];
        const bar_spacing = classes.includes("barbar_chart") ? 2 : 4;
        const css_classes = classes.concat("bar").join(" ");

        this._bars = bars
            .enter()
            .append("a")
            .attr("xlink:href", d => d.url)
            .append("rect")
            // Add new bars
            .each((d, idx, nodes) => this._renderer.tooltip_generator.add_support(nodes[idx]))
            .classed("bar", true)
            .attr("y", plot_size.height)
            .merge(bars)
            // Update new and existing bars
            .attr("x", d => this._renderer.scale_x(d.date))
            .attr(
                "width",
                d =>
                    this._renderer.scale_x(new Date(d.ending_timestamp * 1000)) -
                    this._renderer.scale_x(d.date) -
                    bar_spacing
            )
            .attr("class", css_classes);

        this._renderer
            .transition(this._bars)
            .style("opacity", this.get_opacity())
            .attr("fill", this.get_color())
            .attr("rx", 2)
            .attr("y", d => this._renderer.scale_y(d.value))
            .attr("height", d => {
                let y_base = 0;
                if (this.stack_values != null) y_base = this.stack_values[d.timestamp] || 0;
                return plot_size.height - this._renderer.scale_y(d.value - y_base);
            });
    }

    get_color() {
        let color = SubPlot.prototype.get_color.call(this);
        let classes = (this.definition.css_classes || []).concat("bar");
        return color != undefined ? color : d3.color(this._get_css("fill", "rect", classes));
    }
}
// Renders a single value
// Per default, the latest timestamp of the given timeline is used
class SingleValuePlot extends SubPlot {
    static ident() {
        return "single_value";
    }

    render() {
        const plot = this._renderer._data.plot_definitions.filter(
            d => d.plot_type == "single_value"
        )[0];
        const domain = cmk_figures.adjust_domain(
            cmk_figures.calculate_domain(this.transformed_data),
            plot.metrics
        );
        const levels = cmk_figures.make_levels(domain, plot.metrics);

        const formatter = cmk_figures.plot_render_function(plot);
        const last_value = this.transformed_data.find(element => element.last_value);
        const plot_size = this._renderer.plot_size;
        const color = levels.length
            ? levels.find(element => last_value.value < element.to).color
            : "#FFFFFF";
        const font_size = Math.min(plot_size.width / 5, (plot_size.height * 2) / 3);

        const value = cmk_figures.split_unit({
            formatted_value: formatter(last_value.value),
            url: last_value.url,
        });
        cmk_figures.metric_value_component(
            this.svg,
            value,
            {x: plot_size.width / 2, y: plot_size.height / 2 + font_size / 3},
            {font_size, color}
        );

        if (this.definition.svc_state)
            cmk_figures.state_component(this._renderer, this.definition.svc_state);
    }

    get_color() {
        return d3.color("white");
    }
}

class SubPlotFactory {
    constructor() {
        this._plot_types = {};
    }

    get_plot(plot_type) {
        return this._plot_types[plot_type];
    }

    register(subplot) {
        this._plot_types[subplot.ident()] = subplot;
    }
}

let subplot_factory = new SubPlotFactory();
subplot_factory.register(LinePlot);
subplot_factory.register(AreaPlot);
subplot_factory.register(ScatterPlot);
subplot_factory.register(BarPlot);
subplot_factory.register(SingleValuePlot);

class CmkGraphTimeseriesFigure extends TimeseriesFigure {
    static ident() {
        return "cmk_graph_timeseries";
    }

    constructor(div_selector, fixed_size = null) {
        super(div_selector, fixed_size);
        this.subscribe_data_pre_processor_hook(data => this._convert_graph_to_figures(data));
        this._div_selection.classed("graph", true).style("width", "100%");
    }

    _setup_legend() {
        this._small_legend = false;
        this._legend = this._div_selection
            .select("div.figure_content")
            .append("div")
            .classed("figure_legend graph_with_timeranges graph", true)
            .style("position", "absolute");
    }

    _get_legend_height() {
        if (!this._legend || this._small_legend) return 0;
        return this._legend.node().getBoundingClientRect().height + 20;
    }

    _convert_graph_to_figures(graph_data) {
        let plot_definitions = [];
        let data = [];

        // Metrics
        let step = graph_data.graph.step;
        let start_time = graph_data.graph.start_time;
        graph_data.graph.curves.forEach((curve, idx) => {
            let curve_tag = "metric_" + idx;
            let stack_tag = "stack_" + curve_tag;
            let use_stack = curve.type == "area" && d3.max(curve.points, d => d[0]) > 0;
            curve.points.forEach((point, idx) => {
                let timestamp = start_time + idx * step;
                let value = 0;
                let base_value = 0;
                if (curve.type == "line") value = point;
                else {
                    base_value = point[0];
                    value = point[1];
                }

                data.push({
                    timestamp: timestamp,
                    value: value - (base_value || 0),
                    tag: curve_tag,
                });

                if (use_stack)
                    data.push({
                        timestamp: timestamp,
                        value: base_value,
                        tag: stack_tag,
                    });
            });

            let plot_definition = {
                label: curve.title,
                plot_type: curve.type,
                color: curve.color,
                id: curve_tag,
                use_tags: [curve_tag],
            };

            if (use_stack) {
                plot_definitions.push({
                    hidden: true,
                    label: "stack_base " + curve.title,
                    plot_type: "line",
                    color: curve.color,
                    id: stack_tag,
                    use_tags: [stack_tag],
                });
                plot_definition["stack_on"] = stack_tag;
            }
            plot_definitions.push(plot_definition);
        });

        // Levels
        let start = d3.min(data, d => d.timestamp);
        let end = d3.max(data, d => d.timestamp);
        graph_data.graph.horizontal_rules.forEach((rule, idx) => {
            let rule_tag = "level_" + idx;
            plot_definitions.push({
                label: rule[3],
                plot_type: "line",
                color: rule[2],
                id: rule_tag,
                is_scalar: true,
                use_tags: [rule_tag],
            });
            data.push({
                timestamp: start,
                value: rule[0],
                tag: rule_tag,
            });
            data.push({
                timestamp: end,
                value: rule[0],
                tag: rule_tag,
            });
        });

        return {
            plot_definitions: plot_definitions,
            data: data,
        };
    }

    _process_api_response(graph_data) {
        this.process_data(graph_data);
        this._fetch_data_latency = +(new Date() - this._fetch_start) / 1000;
    }

    render_legend() {
        let domains = this.scale_x.domain();
        let start = parseInt(domains[0].getTime() / 1000);
        let end = parseInt(domains[1].getTime() / 1000);
        let subplot_data = [];
        this._subplots.forEach(subplot => {
            subplot_data.push({
                definition: subplot.definition,
                data: subplot.get_legend_data(start, end),
            });
        });

        this._div_selection
            .selectAll("div.toggle")
            .data([null])
            .enter()
            .append("div")
            .classed("toggle noselect", true)
            .style("position", "absolute")
            .style("bottom", "0px")
            .text("Toggle legend")
            .on("click", () => {
                this._small_legend = !this._small_legend;
                this.render_legend();
                this.resize();
                this.render();
            });

        this._render_legend(subplot_data, this._small_legend);
    }

    _render_legend(subplot_data, small) {
        let new_table = this._legend.selectAll("tbody").empty();
        let table = this._legend
            .selectAll("tbody")
            .data([null])
            .join(enter =>
                enter.append("table").classed("legend", true).style("width", "100%").append("tbody")
            );

        table
            .selectAll("tr.headers")
            .data([["", "MINIMUM", "MAXIMUM", "AVERAGE", "LAST"]])
            .join("tr")
            .classed("headers", true)
            .selectAll("th")
            .data(d => d)
            .join("th")
            .text(d => d);

        // Metrics
        let rows = table
            .selectAll("tr.metric")
            .data(subplot_data.filter(d => d.definition.id.startsWith("metric_")))
            .join("tr")
            .classed("metric", true);
        rows.selectAll("td.name")
            .data(d => [d])
            .enter()
            .append("td")
            .classed("name small", true)
            .each((d, idx, nodes) => {
                let td = d3.select(nodes[idx]);
                td.classed("name", true);
                td.append("div").classed("color", true).style("background", d.definition.color);
                td.append("label").text(d.definition.label);
            });
        rows.selectAll("td.min")
            .data(d => [d])
            .join("td")
            .classed("scalar min", true)
            .text(d => (d.data.data.length == 0 ? "NaN" : d.data.y[0].toFixed(2)));
        rows.selectAll("td.max")
            .data(d => [d])
            .join("td")
            .classed("scalar max", true)
            .text(d => (d.data.data.length == 0 ? "NaN" : d.data.y[1].toFixed(2)));
        rows.selectAll("td.average")
            .data(d => [d])
            .join("td")
            .classed("scalar average", true)
            .text(d =>
                d.data.data.length == 0 ? "NaN" : d3.mean(d.data.data, d => d.value).toFixed(2)
            );
        rows.selectAll("td.last")
            .data(d => [d])
            .join("td")
            .classed("scalar last", true)
            .text(d => {
                if (d.data.data.length == 0) return "NaN";

                if (d.data.data[0].value == null) return "NaN";

                if (d.data.data[0].unstacked_value)
                    return d.data.data[0].unstacked_value.toFixed(2);
                else return d.data.data[0].value.toFixed(2);
            });

        // Levels
        rows = table
            .selectAll("tr.level")
            .data(subplot_data.filter(d => d.definition.id.startsWith("level_")))
            .join(enter =>
                enter
                    .append("tr")
                    .classed("level scalar", true)
                    .each((d, idx, nodes) => {
                        if (idx == 0) d3.select(nodes[idx]).classed("first", true);
                    })
            );
        rows.selectAll("td.name")
            .data(d => [d])
            .enter()
            .append("td")
            .classed("name", true)
            .each((d, idx, nodes) => {
                let td = d3.select(nodes[idx]);
                td.classed("name", true);
                td.append("div").classed("color", true).style("background", d.definition.color);
                td.append("label").text(d.definition.label);
            });
        rows.selectAll("td.min")
            .data(d => [d])
            .join("td")
            .classed("scalar min", true)
            .text("");
        rows.selectAll("td.max")
            .data(d => [d])
            .join("td")
            .classed("scalar max", true)
            .text("");
        rows.selectAll("td.average")
            .data(d => [d])
            .join("td")
            .classed("scalar average", true)
            .text("");
        rows.selectAll("td.last")
            .data(d => [d])
            .join("td")
            .classed("scalar last", true)
            .text(d => (d.data.data.length == 0 ? "NaN" : d.data.data[0].value.toFixed(2)));

        if (small) {
            this._legend.selectAll("th").style("display", "none");
            this._legend.selectAll("td").style("display", "none");
            this._legend.selectAll("td.small").style("display", null);
            this.transition(this._legend)
                .style("top", this.margin.top + "px")
                .style("width", null)
                .style("right", "20px")
                .style("left", null);
        } else {
            this._legend.selectAll("th").style("display", null);
            this._legend.selectAll("td").style("display", null);
            if (new_table)
                this._legend
                    .style("width", "100%")
                    .style("top", this.figure_size.height - this._get_legend_height() + "px")
                    .style("left", "40px");
            else
                this.transition(this._legend)
                    .style("width", "100%")
                    .style("top", this.figure_size.height - this._get_legend_height() + "px")
                    .style("left", "40px");
        }
    }
}
cmk_figures.figure_registry.register(CmkGraphTimeseriesFigure);

class CmkGraphShifter extends CmkGraphTimeseriesFigure {
    static ident() {
        return "cmk_graph_shifter";
    }

    constructor(div_selector, fixed_size = null) {
        super(div_selector, fixed_size);
        this.subscribe_data_pre_processor_hook(data => {
            this._apply_shift_config(data);
            return data;
        });
        this._cutter_div = null;
        this._shifts = [];
    }

    _apply_shift_config(data) {
        let new_definitions = data.plot_definitions.filter(d => d.is_shift !== true);
        this._shifts.forEach(config => {
            if (config.seconds === 0) return;
            let shift = JSON.parse(
                JSON.stringify(this._subplots_by_id[config.shifted_id].definition)
            );
            let seconds = config.seconds;
            shift.id += "_shifted";
            shift.color = config.color;
            shift.shift_seconds = seconds;
            shift.label += config.label_suffix;
            shift.opacity = 0.5;
            shift.is_shift = true;
            new_definitions.push(shift);
        });
        data.plot_definitions = new_definitions;
    }

    initialize() {
        CmkGraphTimeseriesFigure.prototype.initialize.call(this);
        this._setup_cutter_options_panel();
    }

    update_gui() {
        CmkGraphTimeseriesFigure.prototype.update_gui.call(this);
        this._update_cutter_options_panel();
    }

    _setup_cutter_options_panel() {
        this._cutter_div = this._div_selection
            .select("div.figure_content")
            .selectAll("div.cutter_options")
            .data([null])
            .join(enter =>
                enter
                    .append("div")
                    .style("position", "absolute")
                    .style("top", "0px")
                    .style("left", 40 + this.figure_size.width + "px")
                    .classed("cutter_options noselect", true)
            );

        this._cutter_div
            .append("label")
            .style("margin-left", "-60px")
            .style("border", "grey")
            .style("border-style", "solid")
            .text("Shift data")
            .on("click", (d, idx, nodes) => {
                let node = d3.select(nodes[idx]);
                let active = !node.classed("active");
                node.classed("active", active);
                this._cutter_div
                    .select("div.options")
                    .transition()
                    .style("width", active ? null : "0px");
                node.style("background", active ? "green" : null);
            });
        let options = [
            {id: "Hours", min: 0, max: 24},
            {id: "Days", min: 0, max: 31},
        ];
        let div_options = this._cutter_div
            .append("div")
            .style("overflow", "hidden")
            .style("width", "0px")
            .classed("options", true);
        let new_table = div_options.selectAll("table").data([null]).enter().append("table");

        let new_rows = new_table
            .selectAll("tr.shift_option")
            .data(options)
            .enter()
            .append("tr")
            .classed("shift_option", true);
        new_rows.append("td").text(d => d.id);
        new_rows
            .append("td")
            .text("0")
            .classed("value", true)
            .attr("id", d => d.id);
        new_rows
            .append("td")
            .append("input")
            .attr("type", "range")
            .attr("min", d => d.min)
            .attr("max", d => d.max)
            .attr("value", 0)
            .on("change", d => {
                this._cutter_div.selectAll("td.value#" + d.id).text(d3.event.target.value);
                this._update_shifts();
            });
    }

    _update_cutter_options_panel() {
        let table = this._cutter_div
            .select("div.options")
            .selectAll("table.metrics")
            .data([null])
            .join("table")
            .classed("metrics", true);
        let rows = table
            .selectAll("tr.metric")
            .data(
                this._subplots.filter(
                    d => !(d.definition.is_scalar || d.definition.is_shift || d.definition.hidden)
                ),
                d => d.definition.id
            )
            .join("tr")
            .classed("metric", true);
        rows.selectAll("input")
            .data(d => [d])
            .join("input")
            .attr("type", "checkbox")
            .style("display", "inline-block")
            .on("change", () => this._update_shifts());
        let metric_td = rows
            .selectAll("td.color")
            .data(d => [d])
            .enter()
            .append("td")
            .classed("color", true);
        metric_td
            .append("div")
            .classed("color", true)
            .style("background", d => d.definition.color);
        metric_td.append("label").text(d => d.definition.label);
    }

    _update_shifts() {
        let hours = parseInt(this._cutter_div.selectAll("td.value#Hours").text());
        let days = parseInt(this._cutter_div.selectAll("td.value#Days").text());

        let checked_metrics = this._cutter_div.selectAll("input[type=checkbox]:checked");
        this._shifts = [];
        checked_metrics.each(d => {
            this._shifts.push({
                shifted_id: d.definition.id,
                seconds: hours * 3600 + days * 86400,
                color: "white",
                label_suffix: "- shifted " + days + " days, " + hours + " hours",
            });
        });

        this._apply_shift_config(this._data);
        this._legend.selectAll("table").remove();
        this.update_gui();
    }
}

cmk_figures.figure_registry.register(CmkGraphShifter);
