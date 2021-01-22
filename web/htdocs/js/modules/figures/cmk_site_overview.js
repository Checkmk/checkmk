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
        this._crossfilter.add(this._data.data);
    }

    resize() {
        cmk_figures.FigureBase.prototype.resize.call(this);
        this.svg.attr("width", this.figure_size.width);
        this.svg.attr("height", this.figure_size.height);
        this.tooltip_generator.update_sizes(this.figure_size, this.plot_size);
    }

    update_gui() {
        this.resize();

        if (this._data.render_mode == "hosts") {
            this.render_hosts();
        } else if (this._data.render_mode == "sites") {
            this.render_sites();
        }

        this.render_title(this._data.title);
    }

    render_hosts() {}

    render_sites() {
        let element_boxes = this.svg
            .selectAll("g.element_box")
            .data(this._crossfilter.all())
            .join(enter => enter.append("g").classed("element_box", true));

        let geometry = this._compute_geometry();
        this._render_hexagons(element_boxes, geometry);

        // Place element_boxes
        element_boxes.transition().attr("transform", (d, idx) => {
            let x = (idx % geometry.num_columns) * geometry.box_width;
            let y = Math.trunc(idx / geometry.num_columns) * geometry.box_height;
            return (
                "translate(" +
                (x + geometry.box_area_left) +
                "," +
                (y + geometry.box_area_top) +
                ")"
            );
        });
    }

    _render_hexagons(element_boxes, geometry) {
        let tooltip_generator = this.tooltip_generator;

        let handle_click = function (element) {
            if (element.type != "icon_element") {
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
            .text(element => element)
            .attr("y", geometry.hexagon_radius + 15);
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

    _compute_geometry() {
        let width = this.plot_size.width;
        let height = this.plot_size.height;

        // TODO: The dashlet can be configured to NOT show a title. In this case the render()
        // method must not apply the header top margin (24px, see FigureBase.render_title)
        let header_height = 24;
        // Effective height of the label (based on styling)
        let label_height = 11;
        let label_v_padding = 8;
        let min_label_width = 60;

        // Spacing between dashlet border and box area
        let canvas_v_padding = 10;
        let canvas_h_padding = 4;
        // The area where boxes are rendered to
        let box_area_top = header_height + canvas_v_padding;
        let box_area_left = canvas_h_padding;
        let box_area_width = width - 2 * canvas_h_padding;
        let box_area_height = height - box_area_top - canvas_v_padding;

        // Must not be larger than the "host/service statistics" hexagons
        let max_box_width = 114;
        let box_v_rel_padding = 0.05;
        let box_h_rel_padding = 0;
        // Calculating the distance from center to top of hexagon
        let hexagon_max_radius = max_box_width / 2;

        let num_elements = this._data.data.length;

        if (box_area_width < 20 || box_area_height < 20) {
            return; // Does not make sense to continue
        }

        // Calculate number of columns and rows we need to render all elements
        let num_columns = Math.max(Math.floor(box_area_width / max_box_width), 1);

        // Rough idea of this algorithm: Increase the number of columns, then calculate the number
        // of rows needed to fit all elements into the box_area. Then calculate the box size based
        // on the number of columns and available space. Then check whether or not it fits into the
        // box_are.  In case it does not fit, increase the number of columns (which then may also
        // decrease the size of the box sizes).
        let compute_geometry = function (num_columns) {
            let num_rows = Math.ceil(num_elements / num_columns);
            // Calculating the distance from center to top of hexagon
            let box_width = box_area_width / num_columns;

            let hexagon_radius = Math.min(box_width / 2, hexagon_max_radius);
            hexagon_radius -= hexagon_radius * box_h_rel_padding;

            let necessary_box_height = hexagon_radius * 2 * (1 + box_v_rel_padding);

            let show_label = box_width >= min_label_width;
            if (show_label) necessary_box_height += label_v_padding * 2 + label_height;

            if (num_columns == 100) {
                return null;
            }

            if (necessary_box_height * num_rows > box_area_height) {
                // With the current number of columns we are not able to render all boxes on the
                // box_area. Next, try with one more column.
                return null;
            }

            let box_height = box_area_height / num_rows;
            let hexagon_center_top =
                hexagon_radius * (1 + box_v_rel_padding) + (box_height - necessary_box_height) / 2;

            // Reduce number of columns, trying to balance the rows
            num_columns = Math.ceil(num_elements / num_rows);
            box_width = box_area_width / num_columns;

            let hexagon_center_left = box_width / 2;

            return {
                num_columns: num_columns,
                hexagon_center_top: hexagon_center_top,
                hexagon_center_left: hexagon_center_left,
                hexagon_radius: hexagon_radius,
                box_area_left: box_area_left,
                box_area_top: box_area_top,
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
