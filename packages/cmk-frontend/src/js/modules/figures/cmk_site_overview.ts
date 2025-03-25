/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import type {
    BaseType,
    D3ZoomEvent,
    Quadtree,
    Selection,
    ZoomTransform,
} from "d3";
import {
    group,
    json,
    pointer,
    quadtree,
    scaleLinear,
    select,
    zoom,
    zoomIdentity,
} from "d3";
import {hexbin as d3Hexbin_hexbin} from "d3-hexbin";

import {FigureTooltip} from "@/modules/figures/cmk_figure_tooltip";
import {FigureBase} from "@/modules/figures/cmk_figures";
import type {
    ABCElement,
    ElementSize,
    FigureData,
    HostElement,
    IconElement,
    SiteElement,
} from "@/modules/figures/figure_types";
import {makeuri, makeuri_contextless} from "@/modules/utils";

export interface HostGeometry {
    radius: number;
    box_height: number;
    hexagon_height: number;
    box_width: number;
    num_columns: number;
    box_area: BoxArea;
}

export interface SiteGeometry {
    hexagon_center_top: number;
    hexagon_center_left: number;
    num_columns: number;
    box_height: number;
    box_area: BoxArea;
    box_width: number;
    show_label: boolean;
    hexagon_radius: number;
    label_height: number;
}

type ABCSubElement = SiteElement | HostElement | IconElement;

interface BoxArea {
    top: number;
    left: number;
    width: number;
    height: number;
}

enum SiteOverviewRenderMode {
    Hosts = "hosts",
    Alerts = "alert_overview",
    Sites = "sites",
}

interface SiteData extends FigureData<ABCElement> {
    data: ABCElement[];
    title: string;
    title_url: string;
    render_mode: SiteOverviewRenderMode;
    upper_bound: number;
    box_scale: "default" | "large";
}

type HexagonContent<
    Geometry = HostGeometry | SiteGeometry,
    Element = HostElement | SiteElement,
> = {geometry: Geometry; elements: Element[]};

export class SiteOverview extends FigureBase<SiteData> {
    _max_box_width: Record<"default" | "large", number>;
    _test_filter: boolean;
    canvas!: Selection<HTMLCanvasElement, null, HTMLDivElement, any>;
    _quadtree!: Quadtree<HostElement>;
    _zoomable_modes!: string[];
    _last_zoom!: ZoomTransform;
    _tooltip!: Selection<HTMLDivElement, unknown, BaseType, unknown>;
    tooltip_generator!: FigureTooltip;
    _fetching_host_tooltip!: boolean;
    _last_hovered_host!: null | HostElement;
    _tooltip_timestamp!: number;
    _loading_img_html!: string;
    _hexagon_content!: null | HexagonContent;

    getEmptyData(): SiteData {
        return {
            data: [],
            plot_definitions: [],
            render_mode: SiteOverviewRenderMode.Sites,
            upper_bound: 0,
            title: "",
            title_url: "",
            box_scale: "default",
        };
    }

    override ident() {
        return "site_overview";
    }

    constructor(div_selector: string, fixed_size: null | ElementSize = null) {
        super(div_selector, fixed_size);
        this.margin = {top: 0, right: 0, bottom: 0, left: 0};

        this._max_box_width = {default: 96, large: 400};
        // Debugging/demo stuff
        this._test_filter = false;
    }

    override initialize(debug?: boolean) {
        FigureBase.prototype.initialize.call(this, debug);

        if (this._test_filter) this.add_filter();

        // Canvas, used as background for plot area
        // Does not process any pointer events
        this.canvas = this._div_selection
            .selectAll<HTMLCanvasElement, unknown>("canvas")
            .data([null])
            .join("canvas")
            .style("pointer-events", "none")
            .style("position", "absolute")
            .style("top", this.margin.top + "px")
            .style("left", this.margin.left + "px")
            .style("bottom", this.margin.bottom + "px")
            .style("right", this.margin.right + "px");

        // Quadtree is used in canvas mode to find elements within given position
        this._quadtree = quadtree<HostElement>()
            .x(d => d.x)
            .y(d => d.y);

        this.svg = this._div_selection
            .append("svg")
            .style("position", "absolute")
            .style("top", "0px")
            .style("left", "0px")
            .on("mousemove", event => this._update_quadtree_svg(event));

        const left = this.margin.left;
        const top = this.margin.top;
        this.plot = this.svg
            .append("g")
            .attr("transform", `translate(${left}, ${top})`)
            .append("svg")
            .classed("viewbox", true)
            .append("g")
            .classed("plot", true);

        this._zoomable_modes = [];
        this._last_zoom = zoomIdentity;

        this._tooltip = this._div_selection
            .append("div")
            .classed("tooltip", true);
        this.tooltip_generator = new FigureTooltip(this._tooltip);

        this._fetching_host_tooltip = false;
        this._last_hovered_host = null;
        this._tooltip_timestamp = 0;

        const loading_img = this._tooltip
            .append("div")
            .classed("loading_img", true);
        this._loading_img_html = loading_img.node()!.outerHTML;
        loading_img.remove();
    }

    add_filter() {
        // Simple text filter using the title dimension
        const hostname_filter = this._crossfilter.dimension(d => d.title);
        this._div_selection
            .append("input")
            .attr("type", "text")
            .classed("msg_filter", true)
            .on("input", event => {
                const target = select(event.target);
                const filter = target.property("value");
                hostname_filter.filter(d => {
                    //@ts-ignore
                    return d.toLowerCase().includes(filter.toLowerCase());
                });
                this._hexagon_content = this._compute_hosts();
                this._render_hexagon_content(this._hexagon_content);
            });
    }

    override update_data(data: SiteData) {
        FigureBase.prototype.update_data.call(this, data);
        this._crossfilter.remove(() => true);

        //if (this._data.render_mode == SiteOverviewRenderMode.Hosts) {
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

    override resize() {
        FigureBase.prototype.resize.call(this);
        this.svg!.attr("width", this.figure_size.width).attr(
            "height",
            this.figure_size.height,
        );
        this.plot
            .attr("width", this.plot_size.width)
            .attr("height", this.plot_size.height);

        this.tooltip_generator.update_sizes(this.figure_size, this.plot_size);
        this.svg!.select("svg.viewbox")
            .attr("width", this.plot_size.width)
            .attr("height", this.plot_size.height);

        this.svg!.call(
            zoom<SVGSVGElement, unknown>()
                .extent([
                    [0, 0],
                    [this.plot_size.width, this.plot_size.height],
                ])
                .scaleExtent([1, 14])
                .translateExtent([
                    [0, 0],
                    [this.plot_size.width, this.plot_size.height],
                ])
                .on("zoom", (event: D3ZoomEvent<SVGSVGElement, unknown>) => {
                    const zoom_enabled =
                        this._zoomable_modes.indexOf(this._data.render_mode) !=
                        -1;

                    if (!zoom_enabled) return;

                    this._last_zoom = zoom_enabled
                        ? event.transform
                        : zoomIdentity;
                    // @ts-ignore
                    this.plot.attr("transform", this._last_zoom);
                    this._render_hexagon_content(this._hexagon_content!);
                    //@ts-ignore
                    this.tooltip_generator.update_position(event);
                }),
        );
    }

    override update_gui() {
        this.resize();

        // Compute data: Geometry and element positions -> _hexagon_content
        this._hexagon_content = null;
        if (
            this._data.render_mode == SiteOverviewRenderMode.Hosts ||
            this._data.render_mode == SiteOverviewRenderMode.Alerts
        ) {
            this._hexagon_content = this._compute_hosts();
        } else if (this._data.render_mode == SiteOverviewRenderMode.Sites) {
            this._hexagon_content = this._compute_sites();
        }

        // Render data
        if (this._hexagon_content === null) this.plot.selectAll("*").remove();
        else this._render_hexagon_content(this._hexagon_content);

        this.render_title(this._data.title, this._data.title_url!);
    }

    _compute_host_geometry(
        num_elements: number,
        box_area: BoxArea,
    ): HostGeometry {
        let box_width = this._max_box_width[this._data.box_scale];
        let num_columns = Math.max(Math.floor(box_area.width / box_width), 1);

        for (;;) {
            if (num_elements >= num_columns * 2) {
                box_width = box_area.width / (num_columns + 0.5);
            } else {
                box_width = box_area.width / num_columns;
            }
            const num_rows = Math.ceil(num_elements / num_columns);
            const box_height = (box_width * Math.sqrt(3)) / 2;
            const necessary_total_height = box_height * (num_rows + 1 / 3);
            if (necessary_total_height <= box_area.height) {
                return {
                    radius: ((box_height * 2) / 3) * 0.87,
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

    _box_width(box_height: number) {
        return (Math.sqrt(3) * box_height) / 2.0;
    }

    _compute_box_area(plot_size: ElementSize): BoxArea {
        // TODO: The dashlet can be configured to NOT show a title. In this case the render()
        // method must not apply the header top margin (24px, see FigureBase.render_title)

        // TODO:
        // Die Hexagons werden jetzt innerhalb des Plots gerendert, dieser ist mit translate schon verschoben
        // Die header_height sollte hier also ueberhaupt nicht verwendet werden
        const header_height = 24;

        // Spacing between dashlet border and box area
        const canvas_v_padding = 10;
        const canvas_h_padding = 4;

        // The area where boxes are rendered to
        const top = header_height + canvas_v_padding;
        return {
            top: top,
            left: canvas_h_padding,
            width: plot_size.width - 2 * canvas_h_padding,
            height: plot_size.height - top - canvas_v_padding,
        };
    }

    _compute_hosts() {
        const data = this._crossfilter.allFiltered();
        const geometry = this._compute_host_geometry(
            data.length,
            this._compute_box_area(this.plot_size),
        );

        return {
            geometry: geometry,
            elements: this._compute_host_elements(geometry, data),
        };
    }

    _render_hexagon_content(hexagon_content: HexagonContent) {
        if (this._data.render_mode == SiteOverviewRenderMode.Hosts) {
            this._render_host_hexagons_as_canvas(
                hexagon_content as HexagonContent<HostGeometry, HostElement>,
            );
        } else if (this._data.render_mode == SiteOverviewRenderMode.Alerts) {
            this._render_host_hexagons_as_svg(hexagon_content);
        } else {
            this._render_sites(
                hexagon_content as HexagonContent<SiteGeometry, SiteElement>,
            );
        }
    }

    _compute_host_elements(geometry: HostGeometry, elements: HostElement[]) {
        const hexbin = d3Hexbin_hexbin();
        elements.forEach((d, idx) => {
            // Compute coordinates
            let x = ((idx % geometry.num_columns) + 0.5) * geometry.box_width;

            // shift to right (Every second line to the right)
            if (Math.floor(idx / geometry.num_columns) % 2 == 1) {
                x += geometry.box_width / 2;
            }
            let y =
                Math.trunc(idx / geometry.num_columns) * geometry.box_height;
            y += geometry.hexagon_height / 2;
            d.x = x + geometry.box_area.left;
            d.y = y + geometry.box_area.top;

            if (this._data.render_mode == SiteOverviewRenderMode.Hosts) {
                // Compute required hexagons
                const outer_css_class = d.has_host_problem
                    ? d.host_css_class
                    : d.service_css_class;
                d.hexagon_config = [
                    {
                        id: "outer_hexagon",
                        path: hexbin.hexagon(geometry.radius),
                        css_class: outer_css_class,
                        tooltip: "",
                    },
                ];

                if (!d.has_host_problem) {
                    // Center is reserved for displaying the host state
                    const mid_radius = 0.7;
                    let badness = d.num_problems / d.num_services;

                    // Hexagon border width: Ensure a minimum and apply discrete value steps
                    const thresholds = [
                        [0, 0.05, 0.05],
                        [0.05, 0.2, 0.3],
                        [0.2, 0.5, 0.6],
                        [0.5, 1, 1],
                    ];
                    for (const [min, max, map_val] of thresholds) {
                        if (min <= badness && badness <= max) {
                            badness = map_val;
                            break;
                        }
                    }

                    const goodness = 1.0 - badness;
                    const radius_factor = Math.pow(
                        (1.0 - mid_radius) * goodness + mid_radius,
                        2,
                    );
                    d.hexagon_config.push({
                        id: "inner_hexagon",
                        path: hexbin.hexagon(geometry.radius * radius_factor),
                        css_class: "up",
                        tooltip: "",
                    });
                }
            } else if (
                this._data.render_mode == SiteOverviewRenderMode.Alerts
            ) {
                const colors = scaleLinear()
                    .domain([0, this._data.upper_bound])
                    // @ts-ignore
                    .range(["#b1d2e880", "#08377580"]);
                d.hexagon_config = [
                    {
                        id: "outer_hexagon",
                        path: hexbin.hexagon(geometry.radius * 1.06),
                        color: colors(d.num_problems),
                        css_class: "alert_element",
                        tooltip: d.tooltip,
                    },
                ];
            } else {
                console.log("Unhandled render mode: " + this._data.render_mode);
            }
        });
        return elements;
    }

    _render_host_hexagons_as_svg(
        hexagon_content: HexagonContent,
        transition_duration = 250,
    ) {
        const elements = hexagon_content.elements;
        // Prepare Box
        let hexagon_boxes = this.plot
            .selectAll<SVGGElement, any>("g.element_box")
            .data(elements, d => d.title);

        hexagon_boxes = hexagon_boxes.join(enter =>
            enter
                .append("g")
                .classed("element_box", true)
                .classed("host_element", true)
                .style("cursor", "pointer")
                .on("click", (_event, d) => {
                    // @ts-ignore
                    location.href = d.link;
                })
                .each((_d, idx, nodes) => {
                    this.tooltip_generator.add_support(nodes[idx]);
                }),
        );

        // render all hexagons
        hexagon_boxes
            .selectAll("path.hexagon")
            .data(
                // @ts-ignore
                d => d.hexagon_config,
                // @ts-ignore
                d => d.id,
            )
            .join(enter => enter.append("path"))
            // @ts-ignore
            .attr("d", d => d.path)
            // @ts-ignore
            .attr("fill", d => d.color)
            // @ts-ignore
            .attr("class", d => "hexagon " + d.css_class);

        // move boxes
        if (!transition_duration) {
            // IE11 compatibility: otherwise 2 transition steps are used even if
            // transition_duration is "0".
            hexagon_boxes.attr("transform", d => {
                // @ts-ignore
                return `translate(${d.x}, ${d.y})`;
            });
        } else {
            hexagon_boxes
                .transition()
                .duration(transition_duration)
                .attr("transform", d => {
                    // @ts-ignore
                    return `translate(${d.x}, ${d.y})`;
                });
        }
    }

    _render_host_hexagons_as_canvas(
        hexagon_content: HexagonContent<HostGeometry, HostElement>,
    ) {
        const elements = hexagon_content.elements;
        const host_classes_iterable = group(
            elements,
            (d: HostElement) => d.host_css_class,
        ).keys();
        const service_classes_iterable = group(
            elements,
            (d: HostElement) => d.service_css_class,
        ).keys();

        // Obtain all needed fill colors (per state) by creating a respectively classed DOM element
        const fill_map: Record<string, string> = {};
        for (const iterable of [
            host_classes_iterable,
            service_classes_iterable,
        ]) {
            for (const css_class of iterable) {
                const tmp_elem = this.svg!.append("path").attr(
                    "class",
                    "hexagon host_element " + css_class,
                );
                fill_map[css_class] = tmp_elem.style("fill");
                tmp_elem.remove();
            }
        }

        this.canvas
            .attr("width", this.plot_size.width)
            .attr("height", this.plot_size.height);

        const ctx = this.canvas.node()!.getContext("2d")!;
        ctx.scale(this._last_zoom.k, this._last_zoom.k);

        // Quadtree: Used for coordinate lookup
        this._quadtree = quadtree<HostElement>()
            .x(d => d.x)
            .y(d => d.y);

        this._quadtree.addAll(elements);

        elements.forEach(element => {
            ctx.save();
            const trans_x = element.x + this._last_zoom.x / this._last_zoom.k;
            const trans_y = element.y + this._last_zoom.y / this._last_zoom.k;
            if (trans_x < -40 || trans_x > this.plot_size.width + 40) return;
            if (trans_y < -40 || trans_y > this.plot_size.height + 40) return;

            ctx.translate(trans_x, trans_y);
            element.hexagon_config.forEach(hexagon => {
                ctx.fillStyle = fill_map[hexagon.css_class];
                const p = new Path2D(hexagon.path);
                ctx.fill(p);
            });
            ctx.restore();
        });
    }

    _update_quadtree_svg(event: Event) {
        if (this._quadtree.size() == 0) return;
        const [x, y] = pointer(
            event,
            (event.target as HTMLElement).closest("svg"),
        );
        const host = this._quadtree.find(
            (x - this._last_zoom.x) / this._last_zoom.k,
            (y - this._last_zoom.y) / this._last_zoom.k,
            (this._hexagon_content!.geometry as HostGeometry).radius,
        );

        // Only fetch host tooltip if a new host is hovered or if the given tooltip is older than 5s
        if (
            host &&
            (host != this._last_hovered_host ||
                Date.now() - this._tooltip_timestamp >= 5000)
        ) {
            // Display a loading image when a new host is hovered
            if (host != this._last_hovered_host) {
                this._last_hovered_host = host;
                host.hexagon_config.forEach(
                    d =>
                        (d.tooltip =
                            "<h3>" +
                            host.title +
                            "</h3>" +
                            this._loading_img_html),
                );
            }

            // Only fetch host tooltip, if no fetch is currently underway
            if (!this._fetching_host_tooltip) {
                this._fetching_host_tooltip = true;
                this._fetch_host_tooltip(host);
            }

            this._tooltip_timestamp = Date.now();
        }
        const reduced_content = {
            geometry: this._hexagon_content!.geometry,
            elements: host ? [host] : [],
        };
        this._render_host_hexagons_as_svg(reduced_content, 0);
    }

    _compute_sites(): {geometry: SiteGeometry; elements: SiteElement[]} {
        const geometry = this._compute_site_geometry();
        return {
            geometry: geometry,
            elements: [], // Elements coordinates are currently computed within the render function
        };
    }

    _render_sites(hexagon_content: HexagonContent<SiteGeometry, SiteElement>) {
        const geometry = hexagon_content.geometry;

        const element_boxes = this.plot
            .selectAll("g.element_box")
            .data(this._crossfilter.all())
            .join(enter => enter.append("g").classed("element_box", true));

        this._render_site_hexagons(element_boxes, geometry);

        element_boxes.transition().attr("transform", (_d, idx) => {
            const x = (idx % geometry.num_columns) * geometry.box_width;
            // Place element_boxes
            const y =
                Math.trunc(idx / geometry.num_columns) * geometry.box_height;
            return (
                "translate(" +
                (x + geometry.box_area.left) +
                "," +
                (y + geometry.box_area.top) +
                ")"
            );
        });
    }

    _render_site_hexagons(
        element_boxes: Selection<
            BaseType | SVGGElement,
            any,
            SVGGElement,
            unknown
        >,
        geometry: SiteGeometry,
    ) {
        const handle_click = function (_event: Event, element: ABCSubElement) {
            if (element.type == "host_element") {
                location.href = element.link;
            } else if (element.type != "icon_element") {
                location.href = makeuri(element.url_add_vars);
            }
        };

        const hexagon_boxes = element_boxes
            .selectAll<SVGGElement, unknown>("g")
            .data(d => [d])
            .join("g")
            .attr(
                "transform",
                "translate(" +
                    geometry.hexagon_center_left +
                    "," +
                    geometry.hexagon_center_top +
                    ")",
            )
            .style("cursor", "pointer")
            .on("click", handle_click);

        let largest_element_count = 0;
        for (const element of this._crossfilter.all()) {
            if (
                element.type != "icon_element" &&
                element.total.count > largest_element_count
            )
                largest_element_count = element.total.count;
        }

        // Now render all hexagons
        const hexbin = d3Hexbin_hexbin();
        hexagon_boxes.each((element, idx, nodes) => {
            const hexagon_box = select(nodes[idx]);

            if (element.type == "icon_element") {
                // Special handling for IconElement (displaying down / disabled sites)
                hexagon_box
                    .selectAll("path.hexagon_0")
                    .data([element])
                    .join(enter =>
                        enter.append("path").classed("hexagon_0", true),
                    )
                    .attr("d", hexbin.hexagon(geometry.hexagon_radius * 0.5))
                    .attr("title", element.title)
                    .classed("icon_element", true)
                    .classed(element.css_class, true);

                hexagon_box
                    .selectAll("path.hexagon_icon")
                    .data([element])
                    .join(enter =>
                        enter.append("image").classed("hexagon_icon", true),
                    )
                    .attr(
                        "xlink:href",
                        "themes/modern-dark/images/icon_" +
                            element.css_class +
                            ".svg",
                    )
                    .attr("width", 24)
                    .attr("height", 24)
                    .attr("x", -12)
                    .attr("y", -12);
            } else {
                // The scale is controlled by the total count of an element compared to the largest
                // element
                const scale = Math.max(
                    0.5,
                    Math.pow(element.total.count / largest_element_count, 0.3),
                );

                // Now render the parts of an element (cubical sizing)
                let sum = element.total.count;
                for (let i = 0; i < element.parts.length; i++) {
                    const part = element.parts[element.parts.length - 1 - i];
                    const radius =
                        part.count == 0
                            ? 0
                            : (Math.pow(sum, 0.33) /
                                  Math.pow(element.total.count, 0.33)) *
                              geometry.hexagon_radius;
                    sum -= part.count;

                    hexagon_box
                        .selectAll<SVGPathElement, unknown>("path.hexagon_" + i)
                        .data([element])
                        .join(enter =>
                            enter.append("path").classed("hexagon_" + i, true),
                        )
                        .attr("d", hexbin.hexagon(radius * scale))
                        .attr("title", part.title)
                        .classed("hexagon", true)
                        .classed(part.css_class, true);
                }
            }
            this.tooltip_generator.add_support(hexagon_box.node()!);
        });

        // Text centered below the hexagon
        hexagon_boxes
            .selectAll<SVGTextElement, unknown>("text")
            .data(element => (geometry.show_label ? [element.title] : []))
            .join("text")
            .attr("text-anchor", "middle")
            .text((title: string) => title)
            .attr("y", geometry.hexagon_radius + geometry.label_height + 4)
            .classed("label", true)
            .style("font-size", geometry.label_height + "px")
            .each(function (title: string) {
                // Limit label lengths to not be wider than the hexagons
                const label = select(this);
                let text_len = label.node()!.getComputedTextLength();
                while (text_len > geometry.box_width && title.length > 0) {
                    title = title.slice(0, -1);
                    label.text(title + "…");
                    text_len = label.node()!.getComputedTextLength();
                }

                // TODO: warum reposition? der text hat doch einen text-anchor middle
                //       habs erstmal auskommentiert
                // reposition after truncating
                //                label.attr("x", geometry.label_center_left - label.node().getBBox().width / 2);
            });
    }

    _compute_site_geometry(): SiteGeometry {
        const max_box_width = this._max_box_width[this._data.box_scale];
        // Effective height of the label (based on styling)
        const min_label_height = 12;
        const label_v_padding = 8;
        // In case this minimum width is reached, hide the label
        const min_label_width = 60;

        // The area where boxes are rendered to
        const box_area = this._compute_box_area(this.plot_size);

        // Must not be larger than the "host/service statistics" hexagons
        const box_v_rel_padding = 0.05;
        const box_h_rel_padding = 0.2;
        // Calculating the distance from center to top of hexagon
        const hexagon_max_radius = max_box_width / 2;

        const num_elements = this._crossfilter.allFiltered().length;

        if (box_area.width < 20 || box_area.height < 20) {
            // @ts-ignore
            return; // Does not make sense to continue
        }

        // Calculate number of columns and rows we need to render all elements
        let num_columns = Math.max(
            Math.floor(box_area.width / max_box_width),
            1,
        );

        // Rough idea of this algorithm: Increase the number of columns, then calculate the number
        // of rows needed to fit all elements into the box_area. Then calculate the box size based
        // on the number of columns and available space. Then check whether or not it fits into the
        // box_are.  In case it does not fit, increase the number of columns (which then may also
        // decrease the size of the box sizes).
        function compute_geometry(num_columns: number): null | SiteGeometry {
            const num_rows = Math.ceil(num_elements / num_columns);
            // Calculating the distance from center to top of hexagon
            let box_width = box_area.width / num_columns;

            let hexagon_radius = Math.min(box_width / 2, hexagon_max_radius);
            hexagon_radius -= hexagon_radius * box_h_rel_padding;
            const label_height = Math.floor(
                Math.max(hexagon_radius / 5, min_label_height),
            );

            let necessary_box_height =
                hexagon_radius * 2 * (1 + box_v_rel_padding);

            const show_label = box_width >= min_label_width;
            if (show_label)
                necessary_box_height += label_v_padding * 2 + label_height;

            if (num_columns == 100) {
                return null;
            }

            if (necessary_box_height * num_rows > box_area.height) {
                // With the current number of columns we are not able to render all boxes on the
                // box_area. Next, try with one more column.
                return null;
            }

            const box_height = box_area.height / num_rows;
            const hexagon_center_top =
                hexagon_radius * (1 + box_v_rel_padding) +
                (box_height - necessary_box_height) / 2;

            // Reduce number of columns, trying to balance the rows
            num_columns = Math.ceil(num_elements / num_rows);
            box_width = box_area.width / num_columns;

            const hexagon_center_left = box_width / 2;

            return {
                num_columns: num_columns,
                hexagon_center_top: hexagon_center_top,
                hexagon_center_left: hexagon_center_left,
                hexagon_radius: hexagon_radius,
                box_area: box_area,
                box_width: box_width,
                box_height: box_height,
                show_label: show_label,
                label_height: label_height,
            };
        }

        let geometry: null | SiteGeometry = null;
        while (geometry === null) {
            geometry = compute_geometry(num_columns++);
        }
        return geometry;
    }

    _fetch_host_tooltip(host: HostElement) {
        // Destructuring the object host to post the needed data only
        const post_data = (({
            title,
            host_css_class,
            service_css_class,
            num_services,
            num_problems,
        }) => ({
            title,
            host_css_class,
            service_css_class,
            num_services,
            num_problems,
        }))(host);

        json(makeuri_contextless(post_data, "ajax_host_overview_tooltip.py"), {
            credentials: "include",
            method: "POST",
            headers: {
                "Content-type": "application/x-www-form-urlencoded",
            },
        })
            .then(json_data => {
                if (host == this._last_hovered_host) {
                    // @ts-ignore
                    const host_tooltip: string = json_data.result.host_tooltip;
                    host.hexagon_config.forEach(
                        (d: {tooltip: string}) => (d.tooltip = host_tooltip),
                    );
                    this._tooltip.html(host_tooltip);
                    this._fetching_host_tooltip = false;
                } else {
                    // Start a new fetch if the hovered host has already changed
                    this._fetch_host_tooltip(this._last_hovered_host!);
                }
            })
            .catch(e => {
                console.error(e);
                this._show_error_info("Error fetching tooltip data", "");
                this._fetching_host_tooltip = false;
            });
    }
}
