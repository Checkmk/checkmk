import * as d3 from "d3";
import * as utils from "utils";
import * as cmk_figures from "cmk_figures";

class SiteOverview extends cmk_figures.FigureBase {
    static ident() {
        return "site_overview";
    }

    constructor(div_selector, fixed_size = null) {
        super(div_selector, fixed_size);
        this.margin = {top: 0, right: 0, bottom: 0, left: 0};
    }

    initialize(debug) {
        cmk_figures.FigureBase.prototype.initialize.call(this, debug);
        this.svg = this._div_selection.append("svg");

        this._tooltip = this._div_selection.append("div").classed("tooltip", true);
        this.tooltip_generator = new cmk_figures.FigureTooltip(this._tooltip);
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
        //    }
        //   ]
        // }
        cmk_figures.FigureBase.prototype.update_data.call(this, data);
        this._crossfilter.remove(() => true);
        for (let i = 0; i < 4; i++) {
            this._crossfilter.add(this._data.data);
        }
    }

    resize() {
        cmk_figures.FigureBase.prototype.resize.call(this);
        this.svg.attr("width", this.figure_size.width);
        this.svg.attr("height", this.figure_size.height);
        this.tooltip_generator.update_sizes(this.figure_size, this.plot_size);
    }

    update_gui() {
        this.resize();

        let element_boxes = this.svg
            .selectAll("g.element_box")
            .data(this._crossfilter.all())
            .join(enter => enter.append("g").classed("element_box", true));

        if (this._data.render_mode == "hosts") {
            this.render_hosts(element_boxes);
        } else if (this._data.render_mode == "sites") {
            this.render_sites(element_boxes);
        }

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
            let num_rows = Math.ceil(num_elements / num_columns);
            let box_height = (box_width * Math.sqrt(3)) / 2;
            let necessary_total_height = box_height * (num_rows + 1 / 3);

            if (necessary_total_height <= box_area.height) {
                return {
                    radius: ((box_height * 2) / 3) * 0.95,
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

    render_hosts(element_boxes) {
        let elements = this._crossfilter.all();
        let geometry = this._compute_host_geometry(
            elements.length,
            this._compute_box_area(this.plot_size)
        );
        console.log(geometry);

        this._render_host_hexagons(element_boxes, geometry);

        // Place element_boxes
        element_boxes.transition().attr("transform", (d, idx) => {
            let x = ((idx % geometry.num_columns) + 0.5) * geometry.box_width;

            // shift to right (Every second line to the right)
            if (Math.floor(idx / geometry.num_columns) % 2 == 1) {
                x += geometry.box_width / 2;
            }

            let y = Math.trunc(idx / geometry.num_columns) * geometry.box_height;
            y += geometry.hexagon_height / 2;

            return (
                "translate(" +
                (x + geometry.box_area.left) +
                "," +
                (y + geometry.box_area.top) +
                ")"
            );
        });
    }

    _render_host_hexagons(element_boxes, geometry) {
        let tooltip_generator = this.tooltip_generator;

        let handle_click = function (element) {
            location.href = element.link;
        };

        let hexagon_boxes = element_boxes
            .selectAll("g")
            .data(elements => [elements])
            .join("g")
            .style("cursor", "pointer")
            .on("click", handle_click);

        hexagon_boxes.each(function (element) {
            let hexagon_box = d3.select(this);

            let hexagon = hexagon_box
                .selectAll("path.hexagon_0")
                .data([element])
                .join(enter => enter.append("path").classed("hexagon_0", true))
                .attr("d", d3.hexbin().hexagon(geometry.radius));

            let color;
            let paint_core = !element.has_host_problem;
            if (element.has_host_problem) {
                color = element.host_color;
            } else {
                color = element.service_color;
            }

            hexagon.attr("fill", color);

            if (paint_core) {
                // Center is reserved for displaying the host state
                let mid_radius = 0.7;
                let badness = element.num_problems / element.num_services;
                let goodness = 1.0 - badness;
                let radius_factor = Math.pow((1.0 - mid_radius) * goodness + mid_radius, 2);
                let core_radius = geometry.radius * radius_factor;

                let hexagon = hexagon_box
                    .selectAll("path.hexagon_core")
                    .data([element])
                    .join(enter => enter.append("path").classed("hexagon_core", true))
                    .attr("d", d3.hexbin().hexagon(core_radius))
                    .attr("fill", "#1f3334");

                if (core_radius == geometry.radius) hexagon.attr("stroke", "#13d389");
            }

            tooltip_generator.add_support(hexagon_box.node());
        });
    }

    render_sites(element_boxes) {
        let geometry = this._compute_site_geometry();
        this._render_site_hexagons(element_boxes, geometry);

        // Place element_boxes
        element_boxes.transition().attr("transform", (d, idx) => {
            let x = (idx % geometry.num_columns) * geometry.box_width;
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
        let tooltip_generator = this.tooltip_generator;

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
        hexagon_boxes.each(function (element) {
            let hexagon_box = d3.select(this);

            if (element.type == "icon_element") {
                // Special handling for IconElement (displaying down / disabled sites)
                hexagon_box
                    .selectAll("path.hexagon_0")
                    .data([element])
                    .join(enter => enter.append("path").classed("hexagon_0", true))
                    .attr("d", d3.hexbin().hexagon(geometry.hexagon_radius * 0.5))
                    .attr("title", element.title)
                    .classed(element.css_class, true)
                    .attr("fill", "#ffffff30");

                // TODO: Enable once we have our icons
                //hexagon_box
                //    .selectAll("path.hexagon_icon")
                //    .data([element])
                //    .join(enter => enter.append("image").classed("hexagon_icon", true))
                //    .attr(
                //        "xlink:href",
                //        "themes/modern-dark/images/icon_" + element.css_class + ".svg"
                //    )
                //    .attr("width", 24)
                //    .attr("height", 24)
                //    .attr("x", -12)
                //    .attr("y", -12);
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

                    let hexagon = hexagon_box
                        .selectAll("path.hexagon_" + i)
                        .data([element])
                        .join(enter => enter.append("path").classed("hexagon_" + i, true))
                        .attr("d", d3.hexbin().hexagon(radius * scale))
                        .attr("title", part.title)
                        .attr("fill", part.color);

                    if (i == 0) hexagon.attr("stroke", "#13d389");
                }
            }
            tooltip_generator.add_support(hexagon_box.node());
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

                // reposition after truncating
                label.attr("x", geometry.label_center_left - label.node().getBBox().width / 2);
            });
    }

    _render_inner_hexagons(selection, outer_radius) {
        // Nur als Beispiel, kann wieder raus

        let data = this._crossfilter.all();
        // Daten vorbereiten
        data.forEach(entry => {
            // Hier werden jeweils 4 innen Hexagons angelegt
            let inner_config = [];
            inner_config.push({
                name: "crit",
                radius: outer_radius * 0.7,
                color: "red",
            });
            inner_config.push({
                name: "warn",
                radius: outer_radius * 0.4,
                color: "yellow",
            });
            inner_config.push({
                name: "downtime",
                radius: outer_radius * 0.2,
                color: "blue",
            });
            inner_config.push({
                name: "ok",
                radius: outer_radius * 0.1,
                color: "green",
            });
            entry.inner_config = inner_config;
        });

        // Daten rendern
        selection
            .selectAll("path.inner")
            .data(
                d => d.inner_config,
                d => d.name
            )
            .join("path")
            .classed("inner", true)
            .attr("d", d => d3.hexbin().hexagon(d.radius))
            .attr("fill", d => d.color);
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
        let max_box_width = 114;
        let box_v_rel_padding = 0.05;
        let box_h_rel_padding = 0;
        // Calculating the distance from center to top of hexagon
        let hexagon_max_radius = max_box_width / 2;

        let num_elements = this._data.data.length;

        if (box_area.width < 20 || box_area.height < 20) {
            return; // Does not make sense to continue
        }

        // Calculate number of columns and rows we need to render all elements
        let num_columns = Math.max(Math.floor(box_area.width / max_box_width), 1);

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
