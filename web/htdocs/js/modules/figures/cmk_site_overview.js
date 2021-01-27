import * as d3 from "d3";
import * as utils from "utils";
import * as cmk_figures from "cmk_figures";

export class SiteOverview extends cmk_figures.FigureBase {
    static ident() {
        return "site_overview";
    }

    constructor(div_selector, fixed_size = null) {
        super(div_selector, fixed_size);
        this.margin = {top: 0, right: 0, bottom: 0, left: 0};

        this._max_box_width = 114;

        // Debugging/demo stuff
        this._test_filter = false;
        this._use_canvas_for_hosts = false;
    }

    initialize(debug) {
        cmk_figures.FigureBase.prototype.initialize.call(this, debug);

        if (this._test_filter) this.add_filter();

        // Canvas, used as background for plot area
        // Does not process any pointer events
        this.canvas = this._div_selection
            .selectAll("canvas")
            .data([null])
            .join("canvas")
            .style("pointer-events", "none")
            .style("position", "absolute")
            .style("top", this.margin.top + "px")
            .style("left", this.margin.left + "px")
            .style("bottom", this.margin.bottom + "px")
            .style("right", this.margin.right + "px");

        // Quadtree is used in canvas mode to find elements within given position
        this._quadtree = d3
            .quadtree()
            .x(d => d.x)
            .y(d => d.y);

        this.svg = this._div_selection
            .append("svg")
            .style("position", "absolute")
            .style("top", "0px")
            .style("left", "0px")
            .on("mousemove", () => this._update_quadtree_svg());

        let left = this.margin.left;
        let top = this.margin.top;
        this.plot = this.svg
            .append("g")
            .attr("transform", `translate(${left}, ${top})`)
            .append("svg")
            .classed("viewbox", true)
            .append("g")
            .classed("plot", true);

        //this._zoomable_modes = ["hosts", "sites"];
        this._zoomable_modes = ["hosts"];
        this._last_zoom = d3.zoomIdentity;

        this._tooltip = this._div_selection.append("div").classed("tooltip", true);
        this.tooltip_generator = new cmk_figures.FigureTooltip(this._tooltip);
    }

    add_filter() {
        // Simple text filter using the title dimension
        let hostname_filter = this._crossfilter.dimension(d => d.title);
        this._div_selection
            .append("input")
            .attr("type", "text")
            .classed("msg_filter", true)
            .on("input", () => {
                let target = d3.select(d3.event.target);
                let filter = target.property("value");
                hostname_filter.filter(d => {
                    return d.toLowerCase().includes(filter.toLowerCase());
                });
                this._hexagon_content = this._compute_hosts();
                this._render_hexagon_content(this._hexagon_content);
            });
    }

    update_data(data) {
        cmk_figures.FigureBase.prototype.update_data.call(this, data);
        this._crossfilter.remove(() => true);

        //if (this._data.render_mode == "hosts") {
        //    for (let i = 0; i < 200; i++) {
        //        // Create new data instead of references
        //        let demo_host = JSON.parse(JSON.stringify(this._data.data[0]));
        //        demo_host.num_services = 10;
        //        demo_host.num_problems = 0;
        //        demo_host.has_host_problem = false;
        //        demo_host.host_color = "#262f38";
        //        demo_host.service_color = "#262f38";
        //        demo_host.tooltip = "Demo host" + i;
        //        demo_host.title += i;
        //        this._crossfilter.add([demo_host]);
        //    }
        //}
        this._crossfilter.add(this._data.data);
    }

    resize() {
        cmk_figures.FigureBase.prototype.resize.call(this);
        this.svg.attr("width", this.figure_size.width).attr("height", this.figure_size.height);
        this.plot.attr("width", this.plot_size.width).attr("height", this.plot_size.height);

        this.tooltip_generator.update_sizes(this.figure_size, this.plot_size);
        this.svg
            .select("svg.viewbox")
            .attr("width", this.plot_size.width)
            .attr("height", this.plot_size.height);

        this.svg.call(
            d3
                .zoom()
                .extent([
                    [0, 0],
                    [this.plot_size.width, this.plot_size.height],
                ])
                .scaleExtent([1, 14])
                .translateExtent([
                    [0, 0],
                    [this.plot_size.width, this.plot_size.height],
                ])
                .on("zoom", () => {
                    let zoom_enabled = this._zoomable_modes.indexOf(this._data.render_mode) != -1;
                    this._last_zoom = zoom_enabled ? d3.event.transform : d3.zoomIdentity;
                    this.plot.attr("transform", this._last_zoom);
                    if (this._use_canvas_for_hosts)
                        this._render_hexagon_content(this._hexagon_content);
                    this.tooltip_generator.update_position();
                })
        );
    }

    update_gui() {
        this.resize();

        // Compute data: Geometry and element positions -> _hexagon_content
        this._hexagon_content = null;
        if (this._data.render_mode == "hosts" || this._data.render_mode == "alert_statistics") {
            this._hexagon_content = this._compute_hosts();
        } else if (this._data.render_mode == "sites") {
            this._hexagon_content = this._compute_sites();
        }

        // Render data
        if (this._hexagon_content === null) this.plot.selectAll("*").remove();
        else this._render_hexagon_content(this._hexagon_content);

        this.render_title(this._data.title);
    }

    _compute_host_geometry(num_elements, box_area) {
        let num_columns = 1;
        while (true) {
            let box_width;
            if (num_elements >= num_columns * 2) {
                box_width = box_area.width / (num_columns + 0.5);
            } else {
                box_width = box_area.width / num_columns;
            }

            if (box_width > this._max_box_width) {
                box_width = this._max_box_width;
                num_columns = Math.max(Math.floor(box_area.width / this._max_box_width), 1);
            }

            let num_rows = Math.ceil(num_elements / num_columns);
            let box_height = (box_width * Math.sqrt(3)) / 2;
            let necessary_total_height = box_height * (num_rows + 1 / 3);

            if (necessary_total_height <= box_area.height) {
                return {
                    radius: ((box_height * 2) / 3) * 0.92,
                    box_height: box_height,
                    hexagon_height: (box_height * 4) / 3,
                    box_width: box_width,
                    num_columns: num_columns,
                    box_area: box_area,
                };
            }
            num_columns += 1;
        }
    }

    _box_width(box_height) {
        return (Math.sqrt(3) * box_height) / 2.0;
    }

    _compute_box_area(plot_size) {
        // TODO: The dashlet can be configured to NOT show a title. In this case the render()
        // method must not apply the header top margin (24px, see FigureBase.render_title)

        // TODO:
        // Die Hexagons werden jetzt innerhalb des Plots gerendert, dieser ist mit translate schon verschoben
        // Die header_height sollte hier also ueberhaupt nicht verwendet werden
        let header_height = 24;

        // Spacing between dashlet border and box area
        let canvas_v_padding = 10;
        let canvas_h_padding = 4;

        // The area where boxes are rendered to
        let top = header_height + canvas_v_padding;
        return {
            top: top,
            left: canvas_h_padding,
            width: plot_size.width - 2 * canvas_h_padding,
            height: plot_size.height - top - canvas_v_padding,
        };
    }

    _compute_hosts() {
        let data = this._crossfilter.allFiltered();
        let geometry = this._compute_host_geometry(
            data.length,
            this._compute_box_area(this.plot_size)
        );

        return {
            geometry: geometry,
            elements: this._compute_host_elements(geometry, data),
        };
    }

    _render_hexagon_content(hexagon_content) {
        if (this._data.render_mode == "hosts") {
            if (this._use_canvas_for_hosts) {
                this._render_host_hexagons_as_canvas(hexagon_content);
            } else {
                this._render_host_hexagons_as_svg(hexagon_content);
            }
        } else if (this._data.render_mode == "alert_statistics") {
            this._render_host_hexagons_as_svg(hexagon_content);
        } else {
            this._render_sites(hexagon_content);
        }
    }

    _compute_host_elements(geometry, elements) {
        const hexbin = d3.hexbin();
        let outer_hexagon_path = hexbin.hexagon(geometry.radius);
        elements.forEach((d, idx) => {
            // Compute coordinates
            let x = ((idx % geometry.num_columns) + 0.5) * geometry.box_width;

            // shift to right (Every second line to the right)
            if (Math.floor(idx / geometry.num_columns) % 2 == 1) {
                x += geometry.box_width / 2;
            }
            let y = Math.trunc(idx / geometry.num_columns) * geometry.box_height;
            y += geometry.hexagon_height / 2;
            d.x = x + geometry.box_area.left;
            d.y = y + geometry.box_area.top;

            if (this._data.render_mode == "hosts") {
                // Compute required hexagons
                let tooltip = d.tooltip;
                d.hexagon_config = [
                    {
                        id: "outer_hexagon",
                        path: outer_hexagon_path,
                        color: d.has_host_problem ? d.host_color : d.service_color,
                        css_class: !d.has_host_problem && d.num_problems == 0 ? "ok" : "",
                        tooltip: tooltip,
                    },
                ];

                if (!d.has_host_problem) {
                    // Center is reserved for displaying the host state
                    let mid_radius = 0.7;
                    let badness = d.num_problems / d.num_services;
                    badness = 0;
                    let goodness = 1.0 - badness;
                    let radius_factor = Math.pow((1.0 - mid_radius) * goodness + mid_radius, 2);
                    radius_factor *= Math.random();
                    d.hexagon_config.push({
                        id: "inner_hexagon",
                        path: hexbin.hexagon(geometry.radius * radius_factor),
                        color: "#262f38",
                        css_class: "",
                        tooltip: tooltip,
                    });
                }
            } else if (this._data.render_mode == "alert_statistics") {
                const colors = d3
                    .scaleLinear()
                    .domain([0, this._data.upper_bound])
                    .range(["#b1d2e8", "#083775"]);
                d.hexagon_config = [
                    {
                        id: "outer_hexagon",
                        path: outer_hexagon_path,
                        color: colors(d.num_problems),
                        css_class: "",
                        tooltip: d.tooltip,
                    },
                ];
            } else {
                console.log("Unhandled render mode: " + this._data.render_mode);
            }
        });
        return elements;
    }

    _render_host_hexagons_as_svg(hexagon_content, transition_duration = 250) {
        let elements = hexagon_content.elements;
        // Prepare Box
        let hexagon_boxes = this.plot.selectAll("g.element_box").data(elements, d => {
            return d.title;
        });

        hexagon_boxes = hexagon_boxes.join(enter =>
            enter
                .append("g")
                .classed("element_box", true)
                .classed("host_element", true)
                .style("cursor", "pointer")
                .on("click", d => {
                    location.href = d.link;
                })
                .each((d, idx, nodes) => {
                    this.tooltip_generator.add_support(nodes[idx]);
                })
        );

        // render all hexagons
        hexagon_boxes
            .selectAll("path.hexagon")
            .data(
                d => d.hexagon_config,
                d => d.id
            )
            .join(enter => enter.append("path").classed("hexagon", true))
            .attr("d", d => d.path)
            .attr("fill", d => d.color)
            .each((d, idx, nodes) => {
                let element = d3.select(nodes[idx]);
                if (d.css_class) element.node().classList.add(d.css_class);
            });

        // move boxes
        hexagon_boxes
            .transition()
            .duration(transition_duration)
            .attr("transform", d => {
                return `translate(${d.x}, ${d.y})`;
            });
    }

    _render_host_hexagons_as_canvas(hexagon_content) {
        let elements = hexagon_content.elements;

        this.canvas.attr("width", this.plot_size.width).attr("height", this.plot_size.height);

        let ctx = this.canvas.node().getContext("2d");
        ctx.scale(this._last_zoom.k, this._last_zoom.k);

        // Quadtree: Used for coordinate lookup
        this._quadtree = d3
            .quadtree()
            .x(d => d.x)
            .y(d => d.y);
        this._quadtree.addAll(elements);

        elements.forEach(element => {
            ctx.save();
            let trans_x = element.x + this._last_zoom.x / this._last_zoom.k;
            let trans_y = element.y + this._last_zoom.y / this._last_zoom.k;
            if (trans_x < -40 || trans_x > this.plot_size.width + 40) return;
            if (trans_y < -40 || trans_y > this.plot_size.height + 40) return;

            ctx.translate(trans_x, trans_y);
            element.hexagon_config.forEach(hexagon => {
                ctx.fillStyle = hexagon.color;
                let p = new Path2D(hexagon.path);
                ctx.fill(p);
            });
            ctx.restore();
        });
    }

    _update_quadtree_svg() {
        if (this._quadtree.size() == 0) return;
        let x = d3.event.layerX - this.margin.left;
        let y = d3.event.layerY - this.margin.top;
        let host = this._quadtree.find(
            (x - this._last_zoom.x) / this._last_zoom.k,
            (y - this._last_zoom.y) / this._last_zoom.k,
            this._hexagon_content.geometry.radius
        );

        let reduced_content = {geometry: this._hexagon_content.geometry};
        reduced_content.elements = host ? [host] : [];
        this._render_host_hexagons_as_svg(reduced_content, 0);
        this.plot.selectAll("path.hexagon").attr("fill", "rgba(0, 0, 0, 0.2)");
    }

    _compute_sites() {
        let geometry = this._compute_site_geometry();
        return {
            geometry: geometry,
            elements: [], // Elements coordinates are currently computed within the render function
        };
    }

    _render_sites(hexagon_content) {
        let geometry = hexagon_content.geometry;

        let element_boxes = this.plot
            .selectAll("g.element_box")
            .data(this._crossfilter.all())
            .join(enter => enter.append("g").classed("element_box", true));

        this._render_site_hexagons(element_boxes, geometry);

        element_boxes.transition().attr("transform", (d, idx) => {
            let x = (idx % geometry.num_columns) * geometry.box_width;
            // Place element_boxes
            let y = Math.trunc(idx / geometry.num_columns) * geometry.box_height;
            return (
                "translate(" +
                (x + geometry.box_area.left) +
                "," +
                (y + geometry.box_area.top) +
                ")"
            );
        });
    }

    _render_site_hexagons(element_boxes, geometry) {
        let handle_click = function (element) {
            if (element.type == "host_element") {
                location.href = element.link;
            } else if (element.type != "icon_element") {
                location.href = utils.makeuri(element.url_add_vars);
            }
        };

        let hexagon_boxes = element_boxes
            .selectAll("g")
            .data(d => [d])
            .join("g")
            .attr(
                "transform",
                "translate(" +
                    geometry.hexagon_center_left +
                    "," +
                    geometry.hexagon_center_top +
                    ")"
            )
            .style("cursor", "pointer")
            .on("click", handle_click);

        let largest_element_count = 0;
        for (const element of this._crossfilter.all()) {
            if (element.type != "icon_element" && element.total.count > largest_element_count)
                largest_element_count = element.total.count;
        }

        // Now render all hexagons
        hexagon_boxes.each((element, idx, nodes) => {
            let hexagon_box = d3.select(nodes[idx]);

            if (element.type == "icon_element") {
                // Special handling for IconElement (displaying down / disabled sites)
                hexagon_box
                    .selectAll("path.hexagon_0")
                    .data([element])
                    .join(enter => enter.append("path").classed("hexagon_0", true))
                    .attr("d", d3.hexbin().hexagon(geometry.hexagon_radius * 0.5))
                    .attr("title", element.title)
                    .classed("icon_element", true)
                    .classed(element.css_class, true);

                hexagon_box
                    .selectAll("path.hexagon_icon")
                    .data([element])
                    .join(enter => enter.append("image").classed("hexagon_icon", true))
                    .attr(
                        "xlink:href",
                        "themes/modern-dark/images/icon_" + element.css_class + ".svg"
                    )
                    .attr("width", 24)
                    .attr("height", 24)
                    .attr("x", -12)
                    .attr("y", -12);
            } else {
                // The scale is controlled by the total count of an element compared to the largest
                // element
                let scale = Math.max(
                    0.5,
                    Math.pow(element.total.count / largest_element_count, 0.3)
                );

                // Now render the parts of an element (cubical sizing)
                let sum = element.total.count;
                for (let i = 0; i < element.parts.length; i++) {
                    let part = element.parts[element.parts.length - 1 - i];

                    let radius =
                        (Math.pow(sum, 0.33) / Math.pow(element.total.count, 0.33)) *
                        geometry.hexagon_radius;
                    sum -= part.count;

                    hexagon_box
                        .selectAll("path.hexagon_" + i)
                        .data([element])
                        .join(enter => enter.append("path").classed("hexagon_" + i, true))
                        .attr("d", d3.hexbin().hexagon(radius * scale))
                        .attr("title", part.title)
                        .classed("site_element", true)
                        .classed(part.css_class, true);
                }
            }
            this.tooltip_generator.add_support(hexagon_box.node());
        });

        // Text centered below the hexagon
        hexagon_boxes
            .selectAll("text")
            .data(element => (geometry.show_label ? [element.title] : []))
            .join("text")
            .attr("text-anchor", "middle")
            .text(title => title)
            .attr("y", geometry.hexagon_radius + 15)
            .classed("label", true)
            .each(function (title) {
                // Limit label lengths to not be wider than the hexagons
                let label = d3.select(this);
                let text_len = label.node().getComputedTextLength();
                while (text_len > geometry.box_width && title.length > 0) {
                    title = title.slice(0, -1);
                    label.text(title + "…");
                    text_len = label.node().getComputedTextLength();
                }

                // TODO: warum reposition? der text hat doch einen text-anchor middle
                //       habs erstmal auskommentiert
                // reposition after truncating
                //                label.attr("x", geometry.label_center_left - label.node().getBBox().width / 2);
            });
    }

    _compute_site_geometry() {
        // Effective height of the label (based on styling)
        let label_height = 11;
        let label_v_padding = 8;
        // In case this minimum width is reached, hide the label
        let min_label_width = 60;

        // The area where boxes are rendered to
        let box_area = this._compute_box_area(this.plot_size);

        // Must not be larger than the "host/service statistics" hexagons
        let box_v_rel_padding = 0.05;
        let box_h_rel_padding = 0;
        // Calculating the distance from center to top of hexagon
        let hexagon_max_radius = this._max_box_width / 2;

        let num_elements = this._crossfilter.allFiltered().length;

        if (box_area.width < 20 || box_area.height < 20) {
            return; // Does not make sense to continue
        }

        // Calculate number of columns and rows we need to render all elements
        let num_columns = Math.max(Math.floor(box_area.width / this._max_box_width), 1);

        // Rough idea of this algorithm: Increase the number of columns, then calculate the number
        // of rows needed to fit all elements into the box_area. Then calculate the box size based
        // on the number of columns and available space. Then check whether or not it fits into the
        // box_are.  In case it does not fit, increase the number of columns (which then may also
        // decrease the size of the box sizes).
        let compute_geometry = function (num_columns) {
            let num_rows = Math.ceil(num_elements / num_columns);
            // Calculating the distance from center to top of hexagon
            let box_width = box_area.width / num_columns;

            let hexagon_radius = Math.min(box_width / 2, hexagon_max_radius);
            hexagon_radius -= hexagon_radius * box_h_rel_padding;

            let necessary_box_height = hexagon_radius * 2 * (1 + box_v_rel_padding);

            let show_label = box_width >= min_label_width;
            if (show_label) necessary_box_height += label_v_padding * 2 + label_height;

            if (num_columns == 100) {
                return null;
            }

            if (necessary_box_height * num_rows > box_area.height) {
                // With the current number of columns we are not able to render all boxes on the
                // box_area. Next, try with one more column.
                return null;
            }

            let box_height = box_area.height / num_rows;
            let hexagon_center_top =
                hexagon_radius * (1 + box_v_rel_padding) + (box_height - necessary_box_height) / 2;

            // Reduce number of columns, trying to balance the rows
            num_columns = Math.ceil(num_elements / num_rows);
            box_width = box_area.width / num_columns;

            let hexagon_center_left = box_width / 2;

            return {
                num_columns: num_columns,
                hexagon_center_top: hexagon_center_top,
                hexagon_center_left: hexagon_center_left,
                hexagon_radius: hexagon_radius,
                box_area: box_area,
                box_width: box_width,
                box_height: box_height,
                show_label: show_label,
            };
        };

        let geometry = null;
        while (geometry === null) {
            geometry = compute_geometry(num_columns++);
        }
        return geometry;
    }
}

cmk_figures.figure_registry.register(SiteOverview);
