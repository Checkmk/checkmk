import * as d3 from "d3";
import * as cmk_figures from "cmk_figures";
import * as crossfilter from "crossfilter2";


// Used for rapid protoyping, bypassing webpack
//var cmk_figures = cmk.figures; /*eslint-disable-line no-undef*/
//var dc = dc; /*eslint-disable-line no-undef*/
//var d3 = d3; /*eslint-disable-line no-undef*/
//var crossfilter = crossfilter; /*eslint-disable-line no-undef*/


// The TimeseriesFigures provides a renderer mechanic. It does not actually render the bars/dot/lines/areas.
// Instead, it manages a list of subplots. Each subplot receives a drawing area and render its data when when
// being told by the TimeseriesFigure
class TimeseriesFigure extends cmk_figures.FigureBase {
    static ident() {
        return "timeseries";
    }

    constructor(div_selector, fixed_size=null) {
        super(div_selector, fixed_size);
        this._subplots = [];
        this._subplots_by_id = {};
        this._crossfilter = null;

        this.margin = {top: 28, right: 10, bottom: 30, left: 50};

        this._div_selection.classed("timeseries", true)
            .style("overflow", "visible");
        let main_div = this._div_selection.append("div")
            .style("position", "absolute")
            .style("display", "inline-block")
            .style("overflow", "visible")
            .on("click", ()=>this._mouse_click())
            .on("mousedown", ()=>this._mouse_down())
            .on("mousemove", ()=>this._mouse_move())
            .on("mouseleave", ()=>this._mouse_out());

        // The main svg, covers the whole figure
        this.svg = main_div.append("svg")
            .datum(this)
            .classed("renderer", true)
            .style("overflow", "visible");

        // The g for the subplots, checks margins
        this.g = this.svg.append("g");

        this._tooltip = main_div.append("div");
        this.tooltip_generator = new cmk_figures.FigureTooltip(this._tooltip);
        // TODO: uncomment to utilize the tooltip collapser
        // let collapser = this._tooltip.append("div").classed("collapser", true);
        // collapser.append("img").attr("src", "themes/facelift/images/tree_closed.png")
        //     .on("click", ()=>{
        //         collapser.classed("active", !collapser.classed("active"));
        //     });

        this._setup_legend(main_div);

        // All subplots share the same scale
        this.scale_x = d3.scaleTime();
        this.scale_y = d3.scaleLinear();

        this._setup_zoom();
        this.resize();
    }

    _mouse_down() {}

    _mouse_click() {}

    _mouse_out() {}

    _mouse_move() {}

    _setup_zoom() {
        // TODO KO: update zoom scaling on resize, general cleanup
        this._current_zoom = d3.zoomIdentity;
        this._zoom_active = false;

        // const extent = [[0, 0], [this.plot_size.width, this.plot_size.height]];
        // X/Y scale zooming based on translation and zoom factor
        this._zoom = d3.zoom()
            .scaleExtent([.5, 20])
            //.translateExtent([[0, 0], [this.plot_size.width, this.plot_size.height + 10000]])
            //.extent(extent)
            .on("zoom", ()=>{
                this._current_zoom = d3.event.transform;

                // The flag is used to prevent transitions during zoom
                this._zoom_active = true;
                this.render();
                this._zoom_active = false;
            });

        // Stretch X scale zooming based on mouse wheel
        this.svg.call(this._zoom)
            .on("wheel.zoom", ()=>{
                this.wheel_scaling -= d3.event.deltaY * 3;
                this.wheel_scaling = Math.min(Math.max(this.wheel_scaling, 100), 199);

                // The flag is used to prevent transitions during zoom
                this._zoom_active = true;
                this.render();
                this._zoom_active = false;
            });

        this.wheel_scaling = 100;
    }

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
        this.plot_size = {
            width: new_size.width - this.margin.left - this.margin.right,
            height: new_size.height - this.margin.top - this.margin.bottom,
        };
        this._div_selection.style("height", this.figure_size.height + "px");
        this.svg.attr("width", this.figure_size.width);
        this.svg.attr("height", this.figure_size.height);
        this.g.attr("transform", "translate(" + this.margin.left + "," + this.margin.top + ")");
        this.render();
    }

    add_plot(plot) {
        plot.renderer(this);
        this._subplots.push(plot);
        this._subplots_by_id[plot.definition.id] = plot;


        if (plot.migration) {
            let removed = plot.migration.remove();
            this._div_selection.select("g").select(function() {
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
    }

    update_gui(data) {
        this.remove_loading_image();

        data.data.forEach(d=>{
            d.date = new Date(d.timestamp * 1000);
        });

        this._title = data.title;
        this._update_crossfilter(data.data);
        this._update_subplots(data.plot_definitions);
        this.render();
    }

    _update_crossfilter(data) {
        if (this._crossfilter == null)
            this._crossfilter = new crossfilter.default();

        this._crossfilter.remove(()=>true);
        this._crossfilter.add(data);
    }

    _update_subplots(plot_definitions) {
        // Create/Remove plots
        plot_definitions.forEach(definition=>{
            if (this._plot_exists(definition.id))
                return;

            // New plot
            let new_plot = new (subplot_factory.get_plot(definition.plot_type))(definition);

            let dimension = this._crossfilter.dimension(d=>d.date);
            new_plot.renderer(this);
            new_plot.dimension(dimension);
            this.add_plot(new_plot);
        });
    }

    _plot_exists(plot_id) {
        for (let idx in this._subplots) {
            if (this._subplots[idx].definition.id == plot_id)
                return true;
        }
        return false;
    }

    render() {
        this.render_title();

        // Prepare render area for subplots
        this._subplots.forEach(subplot=>{
            subplot.prepare_render();
        });

        // Prepare scales, the subplots need them to render the data
        this._prepare_scales();

        // Render subplots
        this._subplots.forEach(subplot=>{
            subplot.render_data();
        });

        this.render_axis();
        this.render_legend();
    }

    render_title() {
        this.g.selectAll(".title").data([this._title])
            .join("text")
            .text(d=>d)
            .attr("y", -10)
            .attr("x", this.plot_size.width/2)
            .attr("text-anchor", "middle")
            .classed("title", true);
    }

    _setup_legend(main_div) {
        this._legend = main_div.append("div")
            .classed("legend", true);
    }

    render_legend() {
        this._legend
            .style("display", this._subplots.length > 0 ? null : "none")
            .style("top", this.margin.top + "px");
        let items = this._legend.selectAll(".legend_item").data(this._subplots);
        let new_items = items.enter().append("div")
            .classed("legend_item", true)
            .classed("noselect", true);

        new_items.append("div").classed("color_code", true).style("background", d=>d.get_color());
        new_items.style("pointer-events", "all");
        new_items.append("label").text(d=>d.definition.label);
        new_items.call(d3.drag()
            .on("start", ()=>this._legend_dragstart())
            .on("drag", ()=>this._legend_drag())
            .on("end", ()=>this._legend_dragend()));
    }

    // TODO KO: move legend dragging into cmk_figures.js:FigureTooltip
    //          this is a base functionality for all figures
    _legend_dragstart() {
        this._dragged_object = d3.select(d3.event.sourceEvent.currentTarget);
    }

    _legend_drag() {
        this._dragged_object.style("position", "absolute")
            .style("top", d3.event.y + "px")
            .style("right", -d3.event.x + "px");
    }

    _legend_dragend() {
        this._dragged_object.remove();

        let point_in_rect = (r,p)=>((p.x > r.x1 && p.x < r.x2) && (p.y > r.y1 && p.y < r.y2));
        let renderer_instances = d3.selectAll("svg.renderer");
        let target_renderer = null;
        renderer_instances.each((d, idx, nodes)=>{
            let rect = nodes[idx].getBoundingClientRect();
            let x1 = rect.left;
            let x2 = x1 + rect.width;
            let y1 = rect.top;
            let y2 = y1 + rect.height;
            if (point_in_rect({x1: x1, y1: y1, x2: x2, y2: y2}, {x: d3.event.sourceEvent.clientX, y: d3.event.sourceEvent.clientY}))
                target_renderer = d;
        });


        if (target_renderer != null && target_renderer != d3.event.subject.renderer)
            d3.event.subject.migrate_to(target_renderer);

    }

    _prepare_scales() {
        let all_domains = [];
        this._subplots.forEach(subplot=>all_domains.push(subplot.get_domains()));

        let x_domain = [d3.min(all_domains, d=>d.x[0]), d3.max(all_domains, d=>d.x[1])];

        // Scale x-domain by mouse wheel factor
        let x_duration = x_domain[1] - x_domain[0];
        let wheel_scaled_duration = x_duration / 100 * this.wheel_scaling;
        let duration_delta = x_duration - wheel_scaled_duration;
        // TODO: wheel_scaling >= 200; fix inverse x_domain
        x_domain[0] = x_domain[0] - new Date(duration_delta / 2);
        x_domain[1] = x_domain[1] - new Date(-duration_delta / 2);
        this.scale_x.domain(x_domain);
        this.scale_x.range([0, this.plot_size.width]);

        let y_domain = [d3.min(all_domains, d=>d.y[0]), d3.max(all_domains, d=>d.y[1])];

        // Scale y-domain by d3.event.transform.y
        let new_domain_scale = null;
        if (this._current_zoom.y >= 0)
            new_domain_scale = (100 + this._current_zoom.y) / 100;
        else
            new_domain_scale = 1 / ((Math.log(Math.abs(this._current_zoom.y/10) + 1) / Math.log(2)) + 1);

        y_domain[1] =  y_domain[1] * new_domain_scale;

        this.scale_y.domain(y_domain);
        this.scale_y.range([this.plot_size.height, 0]);

        this.scale_x = this._current_zoom.rescaleX(this.scale_x);
    }

    render_axis() {
        let x = this.g.selectAll("g.x_axis").data([null]).join("g")
            .classed("x_axis", true)
            .classed("axis", true);
        x.call(d3.axisBottom(this.scale_x)
            .tickFormat(d=>{
                if (d.getMonth() === 0 && d.getDate() === 1)
                    return d3.timeFormat("%Y")(d);
                else if (d.getHours() === 0 && d.getMinutes() === 0)
                    return d3.timeFormat("%m-%d")(d);
                return d3.timeFormat("%H:%M")(d);
            })
            .ticks(6));
        x.attr("transform", "translate(0," + this.plot_size.height + ")");

        let y = this.g.selectAll("g.y_axis").data([null]).join("g")
            .classed("y_axis", true)
            .classed("axis", true);
        y.call(d3.axisLeft(this.scale_y)
            .tickFormat(d=>{
                if (d > 999)
                    return d3.format(".2s")(d);
                return d3.format(",")(d);
            }));
    }

    transition(selection) {
        if (this._zoom_active)
            return selection;
        else
            return selection.transition().duration(2000);
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

    _mouse_down() {}

    _mouse_click() {
        if (this._selected_scatterpoint)
            window.location = this._selected_scatterpoint.url;
    }

    _mouse_out() {
        this.g.select("path.pin").remove();
        this._tooltip.selectAll("table").remove();
        this._tooltip.style("opacity", 0);
    }

    _mouse_move() {
        let ev = d3.event;
        // TODO KO: clean up these mouse events for better performance
        if (ev.target != this.svg.node() ||
            ev.layerX < this.margin.left ||
            ev.layerY < this.margin.top ||
            ev.layerX > this.margin.left + this.plot_size.width ||
            ev.layerY > this.margin.top + this.plot_size.height) {
            this._mouse_out();
            return;
        }
        if (!this._crossfilter || !this._subplots_by_id["id_scatter"])
            return;

        // TODO AB: change this dimensions to members
        //          filter_dimension -> tag_dimension
        //          result_dimension -> date_dimension
        let filter_dimension = this._crossfilter.dimension(d=>d);
        let result_dimension = this._crossfilter.dimension(d=>d.timestamp);

        // Find focused scatter point and highlight it
        let scatter_plot = this._subplots_by_id["id_scatter"];
        let scatterpoint = scatter_plot.quadtree.find(ev.layerX - this.margin.left, ev.layerY - this.margin.top, 10);
        this._selected_scatterpoint = scatterpoint;

        let use_date = null;
        scatter_plot.redraw_canvas();
        if (scatterpoint !== undefined) {
            use_date = scatterpoint.date;

            // Highlight all incidents, based on this scatterpoint's label
            let ctx = scatter_plot.canvas.node().getContext("2d");
            filter_dimension.filter(d=>d.label == scatterpoint.label);
            let points = result_dimension.top(Infinity);
            let line = d3.line().x(d=>d.scaled_x).y(d=>d.scaled_y).context(ctx);
            ctx.beginPath();
            line(points);
            let hilited_host_color = this._get_css("stroke", "path", ["host", "hilite"]);
            ctx.strokeStyle = hilited_host_color;
            ctx.stroke();

            // Highlight selected point
            ctx.beginPath();
            ctx.arc(scatterpoint.scaled_x,
                scatterpoint.scaled_y, 3, 0, Math.PI*2, false);
            let hilited_node_color = this._get_css("fill", "circle", ["scatterdot", "hilite"]);
            ctx.fillStyle = hilited_node_color;
            ctx.fill();
            ctx.stroke();
        }
        else {
            use_date = this.scale_x.invert(ev.layerX - this.margin.left);
        }

        // Find nearest mean point
        filter_dimension.filter(d=>d.tag == "line_mean");
        let results = result_dimension.bottom(Infinity);
        let nearest_bisect = d3.bisector(d=>d.timestamp).left;
        let idx = nearest_bisect(results, use_date.getTime()/1000);

        let mean_point = results[idx];
        if (mean_point == undefined) {
            filter_dimension.dispose();
            result_dimension.dispose();
            return;
        }

        // Get corresponding median point
        filter_dimension.filter(d=>d.tag == "line_median");
        let median_point = result_dimension.bottom(Infinity)[idx];

        // Get scatter points for this date
        filter_dimension.filter(d=>d.timestamp == mean_point.timestamp && d.tag == "scatter");
        let scatter_matches = result_dimension.top(Infinity);
        scatter_matches.sort((first, second)=>first.value>second.value);
        let top_matches = scatter_matches.slice(-5, -1).reverse();
        let bottom_matches = scatter_matches.slice(0, 4).reverse();


        // TODO KO: the pin should also move on zooming
        this.g.select("path.pin").remove();
        let x = this.scale_x(mean_point.date);
        this.g.append("path").classed("pin", true)
            .attr("d", d3.line()([[x, 0],[x, this.plot_size.height]]))
            .attr("pointer-events", "none");

        this._render_tooltip(top_matches, bottom_matches, mean_point, median_point, scatterpoint);

        filter_dimension.dispose();
        result_dimension.dispose();
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
            scatter_row.append("td").text(scatterpoint.tooltip.split(" ")[0] + " (selected)")
                .style("color", hilited_host_color);
            scatter_row.append("td").text(scatterpoint.value.toFixed(2));
        }

        let top_rows = table.selectAll("tr.top_matches").data(top_matches)
            .enter().append("tr")
            .classed("top_matches",true);
        top_rows.append("td").text(d=>d.tooltip.split(" ")[0]);
        top_rows.append("td").text(d=>d.value.toFixed(3));

        let bottom_rows = table.selectAll("tr.bottom_matches").data(bottom_matches)
            .enter().append("tr")
            .classed("bottom_matches",true);
        bottom_rows.append("td").text(d=>d.tooltip.split(" ")[0]);
        bottom_rows.append("td").text(d=>d.value.toFixed(3));

        let tooltip_size = { width: this._tooltip.node().offsetWidth, height: this._tooltip.node().offsetHeight };
        let render_to_the_left = this.figure_size.width - d3.event.layerX < tooltip_size.width + 20;
        let render_upwards = this.figure_size.height - d3.event.layerY < tooltip_size.height - 20;
        // TODO KO: Create generic tooltip alignment in cmk_figures.js:FigureTooltip
        this._tooltip
            .style("left", ()=>{
                if (!render_to_the_left)
                    return d3.event.layerX + 20 + "px";
                return "auto";
            })
            .style("right", ()=>{
                if (render_to_the_left)
                    return this.plot_size.width - d3.event.layerX + 75 + "px";
                return "auto";
            })
            .style("bottom", ()=>{
                if (render_upwards)
                    return "6px";
                return "auto";
            })
            .style("top", ()=>{
                if (!render_upwards)
                    return d3.event.layerY - 20 + "px";
                return "auto";
            })
            //.style("top", -40 + d3.event.layerY + "px")
            .style("pointer-events", "none")
            .style("opacity", 1);
    }

    _get_css(prop, tag, classes) {
        let obj = this.svg.append(tag);
        classes.forEach(cls=>obj.classed(cls, true));
        let css = obj.style(prop);
        obj.remove();
        return css;
    }
}

cmk_figures.figure_registry.register(AverageScatterplotFigure);

// Base class for all SubPlots
// It renders its data into a <g> provided by the renderer instance
class SubPlot {
    constructor(definition) {
        this.definition = definition;

        this._renderer = null;    // Graph which renders this plot
        this._dimension = null;   // The crossfilter dimension (x_axis)
        this._use_canvas = false;

        this.svg = null; // svg content
        this.canvas = null; // canvas content
        return this;
    }

    renderer(renderer) {
        if (!arguments.length) {
            return this._renderer;
        }
        this._renderer = renderer;
        return this;
    }

    get_color() {
        return this.definition.color ? this.definition : "black";
    }

    dimension(dimension) {
        if (!arguments.length) {
            return this._dimension;
        }
        this._dimension = dimension;
        return this;
    }

    get_domains() {
        let data = this.data().filter(d=>d.tag == this.definition.use_tags[0]);
        return {
            x: [d3.min(data, d=>d.date), d3.max(data, d=>d.date)],
            y: [0, d3.max(data, d=>d.value)]
        };
    }

    prepare_render() {
        // TODO AB: cleanup prepare render
        if (this.svg)
            return;

        // The subplot migration g is used to visualize the transfer of subplots between plots
        let plot_size = this._renderer.plot_size;

        this.migration = this._renderer.g.selectAll("g.subplot_migration." + this.definition.id).data([null])
            .join("g")
            .classed("subplot_migration", true)
            .classed(this.definition.id, true);

        if (this.definition.css_classes)
            this.definition.css_classes.forEach(classname=>{
                this.migration.classed(classname, true);
            });

        // svg
        this.svg = this.migration.selectAll("svg.subplot").data([null])
            .join("svg")
            .attr("width", plot_size.width)
            .attr("height", plot_size.height)
            .classed("subplot", true);

        if (!this._use_canvas || this.canvas)
            return;

        let fo = this.migration.append("foreignObject")
            .style("pointer-events", "none")
            .attr("width", plot_size.width)
            .attr("height", plot_size.height);
        let body = fo.append("xhtml:body")
            .style("margin", "0px")
            .style("width", plot_size.width + "px")
            .style("height", plot_size.height + "px");

        this.canvas = body.append("canvas")
            .attr("x", 0)
            .attr("y", 0)
            .attr("width", plot_size.width)
            .attr("height", plot_size.height)
            .classed("subplot", true);
    }

    data() {
        return this._dimension.top(Infinity);
    }

    // Currently unused. Handles the migration of SubPlots between different TimeseriesFigure instances
    migrate_to(other_renderer) {
        let delta = null;
        if (this._renderer) {
            this._renderer.remove_plot(this);
            let old_box =  this._renderer._div_selection.node().getBoundingClientRect();
            let new_box =  other_renderer._div_selection.node().getBoundingClientRect();
            delta = {x: old_box.x - new_box.x, y: old_box.top - new_box.top};
        }
        other_renderer.add_plot(this);
        if (delta)
            other_renderer.g.select(".subplot_migration." + this.definition.id)
                .attr("transform", "translate(" + delta.x + "," + delta.y + ")")
                .transition()
                .duration(2500)
                .attr("transform", "translate(0,0)");
        other_renderer.remove_loading_image();
        other_renderer.render();
    }
}

// Renders a single uninterrupted line
class LinePlot extends SubPlot {
    static ident() {
        return "line";
    }

    render_data() {
        // note: d3.line can render in svg and canvas
        let line = d3.line()
            .x(d=>{
                return this._renderer.scale_x(d.date);
            }
            )
            .y(d=>{
                return this._renderer.scale_y(d.value);
            });

        let data = this._dimension.top(Infinity);
        data = data.filter(d=>d.tag == this.definition.use_tags[0]);

        let graph_data = this.svg.selectAll("g.graph_data").data([null]);
        graph_data = graph_data.enter().append("g").classed("graph_data", true).merge(graph_data);

        let path = graph_data.selectAll("path").data([data]);
        path = path.enter().append("path").classed("line", true).merge(path);

        this.definition.css_classes.forEach(classname=>path.classed(classname, true));

        this._renderer.transition(path)
            .attr("d", d=>line(d))
            .attr("fill", "none");
    }

    get_color() {
        // Get color from css
        return this.svg.select("path.line").style("stroke");
    }
}

// Renders an uninterrupted area
class AreaPlot extends SubPlot {
    static ident() {
        return "area";
    }

    render_data() {
        //To be done
        //let area = d3.area()
        //    .x(d=>this._renderer.scale_x(d.x))
        //    .y1(d=>this._renderer.scale_y(d.y+10 + Math.random() * 3))
        //    .y0(d=>this._renderer.scale_y(d.y+5 + Math.random() * 3));


        //let graph_data = this.svg.selectAll("g.graph_data").data([null]);
        //graph_data = graph_data.enter().append("g").classed("graph_data", true).merge(graph_data);

        //let path = graph_data.selectAll("path").data([data]);
        //path = path.enter().append("path").merge(path);

        //this._renderer.transition(path)
        //    .attr("d", d=>area(d))
        //    .attr("stroke", "black")
        //    .attr("fill", "#13d389");
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
        this._use_canvas = true;
        return this;
    }

    render_data() {
        this._data = this._dimension.top(Infinity).filter(d=>d.tag == this.definition.use_tags[0]);
        this._data.forEach(point=>{
            point.scaled_x = this._renderer.scale_x(point.date);
            point.scaled_y = this._renderer.scale_y(point.value);
        });
        this.quadtree = d3.quadtree()
            .x(d=>d.scaled_x)
            .y(d=>d.scaled_y)
            .addAll(this._data);
        this.redraw_canvas();
    }

    get_color() {
        // Get color from css
        let circle = this.svg.append("circle").classed("scatterdot", true);
        let color = circle.style("fill");
        this.svg.select("circle.scatterdot").remove();
        return color;
    }

    redraw_canvas() {
        let plot_size = this._renderer.plot_size;
        let ctx = this.canvas.node().getContext("2d");
        if (!this._last_canvas_size)
            this._last_canvas_size = plot_size;

        ctx.clearRect(-1, -1,this._last_canvas_size.width * this._renderer.wheel_scaling + 2, this._last_canvas_size.height + 2);
        let color = this.get_color();
        this._data.forEach(point=>{
            ctx.beginPath();
            ctx.arc(point.scaled_x,point.scaled_y, 1, 0, Math.PI*2, false);

            ctx.fillStyle = color;
            ctx.fill();
        });

        this._last_canvas_size = plot_size;
    }
}

// Renders multiple bars, each based on date->end_date
class BarPlot extends SubPlot {
    static ident() {
        return "bar";
    }

    get_color() {
        return this.svg.select("rect").style("fill");
    }

    render_data() {
        let plot_size = this._renderer.plot_size;
        let bars = this.svg.selectAll("rect").data(
            this._dimension.top(Infinity).filter(d=>d.tag == this.definition.use_tags[0])
        );
        bars.exit().remove();

        this._bars = bars.enter().append("a")
            .attr("xlink:href", d=>d.url)
            .append("rect")
            // Add new bars
            .each((d, idx, nodes)=>this._renderer.tooltip_generator.add_support(nodes[idx]))
            .classed("bar", true)
            .attr("y", plot_size.height)
            .merge(bars)
            // Update new and existing bars
            .attr("x", d=>this._renderer.scale_x(d.date))
            .attr("width", d=>this._renderer.scale_x(new Date(d.end_time * 1000)) - this._renderer.scale_x(d.date))
            .each((d, idx, nodes)=>{
                // Update classes
                let rect = d3.select(nodes[idx]);
                let classes = ["bar"];
                classes = classes.concat(this.definition.css_classes || []);
                rect.classed(classes.join(" "), true);
            })
            .attr("y", d=>this._renderer.scale_y(d.value))
            .attr("height", d=>{return plot_size.height - this._renderer.scale_y(d.value);});
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
