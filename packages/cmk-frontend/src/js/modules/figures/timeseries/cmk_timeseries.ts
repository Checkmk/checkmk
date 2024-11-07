/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import type {Dimension} from "crossfilter2";
import type {
    BaseType,
    ScaleLinear,
    ScaleTime,
    Selection,
    ZoomBehavior,
    ZoomTransform,
} from "d3";
import {
    range,
    axisBottom,
    axisLeft,
    max,
    min,
    scaleLinear,
    scaleTime,
    select,
    timeFormat,
    zoom,
    zoomIdentity,
} from "d3";

import type {
    Domain,
    SubPlotPlotDefinition,
    TimeseriesFigureData,
} from "@/modules/figures/cmk_enterprise_figure_types";
import {FigureTooltip} from "@/modules/figures/cmk_figure_tooltip";
import {FigureBase} from "@/modules/figures/cmk_figures";
import {getIn} from "@/modules/figures/cmk_figures_utils";
import type {
    ElementSize,
    FigureBaseDashletSpec,
} from "@/modules/figures/figure_types";
import {domainIntervals, partitionableDomain} from "@/modules/number_format";

import type {
    AreaPlot,
    BarPlot,
    LinePlot,
    ScatterPlot,
    SubPlot,
} from "./sub_plot";
import {subplot_factory} from "./sub_plot";

// Used for rapid protoyping, bypassing webpack
//var cmk_figures = cmk.figures; /*eslint-disable-line no-undef*/
//var dc = dc; /*eslint-disable-line no-undef*/
//var d3 = d3; /*eslint-disable-line no-undef*/
//var crossfilter = crossfilter; /*eslint-disable-line no-undef*/

// The TimeseriesFigure provides a renderer mechanic. It does not actually render the bars/dot/lines/areas.
// Instead, it manages a list of subplots. Each subplot receives a drawing area and render its data when when
// being told by the TimeseriesFigure

export type SubplotSubs = LinePlot | ScatterPlot | AreaPlot | BarPlot;

export class TimeseriesFigure<
    _DashletSpec extends FigureBaseDashletSpec = FigureBaseDashletSpec,
> extends FigureBase<TimeseriesFigureData, _DashletSpec> {
    _subplots: SubPlot[];
    _subplots_by_id: Record<string, SubPlot>;
    g!: Selection<SVGGElement, unknown, BaseType, unknown>;
    _tooltip!: Selection<HTMLDivElement, unknown, BaseType, unknown>;
    _legend_dimension: Dimension<any, string>;
    tooltip_generator!: FigureTooltip;
    scale_x!: ScaleTime<number, number>;
    orig_scale_x!: ScaleTime<number, number>;
    scale_y!: ScaleLinear<number, number>;
    orig_scale_y!: ScaleLinear<number, number>;
    lock_zoom_x!: boolean;
    lock_zoom_y!: boolean;
    lock_zoom_x_scale!: boolean;
    _legend!: Selection<HTMLDivElement, SubPlot, BaseType, unknown>;
    _title!: string;
    _zoom_active!: boolean;
    _zoom!: ZoomBehavior<SVGSVGElement, unknown>;
    _current_zoom!: ZoomTransform;
    _title_url!: string;
    _x_domain!: number[];
    _y_domain!: number[];
    _y_domain_step!: number;
    override ident() {
        return "timeseries";
    }

    getEmptyData() {
        return {
            data: [],
            plot_definitions: [],
            title: "",
            title_url: "",
        };
    }

    constructor(div_selector: string, fixed_size: null | ElementSize = null) {
        super(div_selector, fixed_size);
        this._subplots = [];
        this._subplots_by_id = {};
        this.margin = {top: 20, right: 10, bottom: 30, left: 65};
        this._legend_dimension = this._crossfilter.dimension<string>(
            d => d.tag,
        );
    }

    get_id() {
        return this._div_selection.attr("id");
    }

    override initialize() {
        // TODO: check double diff, currently used for absolute/auto styling
        this._div_selection
            .classed("timeseries", true)
            .style("overflow", "visible");
        const main_div = this._div_selection
            .append("div")
            .classed("figure_content", true)
            .style("position", "absolute")
            .style("display", "inline-block")
            .style("overflow", "visible")
            .on("click", event => this._mouse_click(event))
            .on("mousedown", event => this._mouse_down(event))
            .on("mousemove", event => this._mouse_move(event))
            .on("mouseleave", event => this._mouse_out(event));

        // The main svg, covers the whole figure
        //@ts-ignore
        this.svg = main_div
            .append("svg")
            .datum(this)
            .classed("renderer", true)
            .style("overflow", "visible");

        // The g for the subplots, checks margins
        this.g = this.svg!.append("g");

        this._tooltip = main_div.append("div");
        this.tooltip_generator = new FigureTooltip(this._tooltip);
        // TODO: uncomment to utilize the tooltip collapser
        //let collapser = this._tooltip.append("div").classed("collapser", true);
        //collapser.append("img").attr("src", "themes/facelift/images/tree_closed.svg")
        //    .on("click", ()=>{
        //        collapser.classed("active", !collapser.classed("active"));
        //    });

        // All subplots share the same scale
        this.scale_x = scaleTime();
        this.orig_scale_x = scaleTime();
        this.scale_y = scaleLinear();
        this.orig_scale_y = scaleLinear();
        this._setup_legend();
        this.resize();
        this._setup_zoom();

        this.lock_zoom_x = false;
        this.lock_zoom_y = false;
        this.lock_zoom_x_scale = false;
    }

    _setup_legend() {
        //@ts-ignore
        this._legend = this._div_selection
            .select("div.figure_content")
            .append("div")
            .classed("legend", true)
            .style("display", "none")
            .style("top", this.margin.top + "px");
    }

    // eslint-disable-next-line @typescript-eslint/no-empty-function
    _mouse_down(_event: MouseEvent) {}

    // eslint-disable-next-line @typescript-eslint/no-empty-function
    _mouse_click(_event: MouseEvent) {}

    // eslint-disable-next-line @typescript-eslint/no-empty-function
    _mouse_out(_event: MouseEvent) {}

    // eslint-disable-next-line @typescript-eslint/no-empty-function
    _mouse_move(_event: MouseEvent) {}

    crossfilter() {
        if (!arguments.length) {
            return this._crossfilter;
        }
        // @ts-ignore
        this._crossfilter = crossfilter;
        return this;
    }

    get_plot_id(plot_id: string) {
        return this._subplots_by_id[plot_id];
    }

    override resize() {
        let new_size = this._fixed_size as ElementSize | null;
        if (new_size === null)
            new_size = {
                // @ts-ignore
                width: this._div_selection.node().parentNode.offsetWidth,
                // @ts-ignore
                height: this._div_selection.node().parentNode.offsetHeight,
            };
        this.figure_size = new_size;
        if (this._title) {
            this.margin.top = 8 + 24; // 8 timeseries y-label margin, 24 from UX project title
            this._adjust_margin();
        }
        this.plot_size = {
            width: new_size.width! - this.margin.left - this.margin.right,
            height:
                new_size.height! -
                this.margin.top -
                this.margin.bottom -
                this._get_legend_height(),
        };
        this.tooltip_generator?.update_sizes(this.figure_size, this.plot_size);
        this._div_selection.style("height", this.figure_size.height + "px");
        this.svg!.attr("width", this.figure_size.width);
        this.svg!.attr("height", this.figure_size.height);
        this.g.attr(
            "transform",
            "translate(" + this.margin.left + "," + this.margin.top + ")",
        );

        this.orig_scale_x.range([0, this.plot_size.width]);
        this.orig_scale_y.range([this.plot_size.height, 0]);
    }

    // eslint-disable-next-line @typescript-eslint/no-empty-function
    _adjust_margin() {}
    _get_legend_height() {
        return 0;
    }
    _setup_zoom() {
        this._current_zoom = zoomIdentity;
        this._zoom_active = false;
        this._zoom = zoom<SVGSVGElement, unknown>()
            .scaleExtent([0.01, 100])
            .on("zoom", event => {
                const last_y = this._current_zoom.y;
                if (this.lock_zoom_x) {
                    event.transform.x = 0;
                    event.transform.k = 1;
                }
                if (this.lock_zoom_x_scale) event.transform.k = 1;

                this._current_zoom = event.transform;
                if (event.sourceEvent.type === "wheel") {
                    //@ts-ignore
                    this._current_zoom.y = last_y;
                }
                this._zoomed();
            });
        this.svg!.call(this._zoom);
    }

    _zoomed() {
        this._zoom_active = true;
        this.render();
        this._zoom_active = false;
    }

    add_plot(plot: SubPlot) {
        plot.renderer(this);
        this._subplots.push(plot);
        this._subplots_by_id[plot.definition!.id] = plot;

        if (plot.main_g) {
            const removed = plot.main_g.remove();
            // @ts-ignore
            this._div_selection.select("g").select(function () {
                // @ts-ignore
                this.appendChild(removed.node());
            });
        }
    }

    remove_plot(plot: SubPlot) {
        const idx = this._subplots.indexOf(plot);
        if (idx > -1) {
            this._subplots.splice(idx, 1);
            delete this._subplots_by_id[plot.definition!.id];
        }
        plot.remove();
    }

    override update_data(data: TimeseriesFigureData) {
        data.data.forEach(d => {
            d.date = new Date(d.timestamp * 1000);
        });
        FigureBase.prototype.update_data.call(this, data);
        this._title = data.title;
        this._title_url = data.title_url;
        this._update_zoom_settings();
        this._update_crossfilter(data.data);
        this._update_subplots(data.plot_definitions);
        this._compute_stack_values();
    }

    _update_zoom_settings() {
        const settings: Record<string, boolean> | undefined =
            this._data.zoom_settings;
        if (settings === undefined) return;

        ["lock_zoom_x", "lock_zoom_y", "lock_zoom_x_scale"].forEach(option => {
            if (settings[option] == undefined) return;
            //@ts-ignore
            this[option] = settings[option];
        });
    }

    override update_gui() {
        this.update_domains();
        this.resize();
        this.render();
    }

    update_domains() {
        const all_domains: Domain[] = [];
        this._subplots.forEach(subplot => {
            const domains = subplot.get_domains();
            if (domains) all_domains.push(domains);
        });
        const now = new Date();
        let time_range = getIn(this, "_data", "time_range");
        if (time_range) {
            time_range = time_range.map((d: number) => new Date(d * 1000));
        } else {
            time_range = [now, now];
        }

        const domain_min = min(all_domains, d => d.x[0]);
        const domain_max = max(all_domains, d => d.x[1]);
        this._x_domain = [
            // @ts-ignore
            domain_min < time_range[0] ? domain_min : time_range[0],
            // @ts-ignore
            domain_max > time_range[1] ? domain_max : time_range[1],
        ];

        const y_tick_count = Math.max(2, Math.ceil(this.plot_size.height / 50));
        const [min_val, max_val, step] = partitionableDomain(
            [min(all_domains, d => d.y[0])!, max(all_domains, d => d.y[1])!],
            y_tick_count,
            domainIntervals(
                getIn(
                    this,
                    "_data",
                    "plot_definitions",
                    0,
                    "metric",
                    "unit",
                    "stepping",
                ),
            ),
        );
        this._y_domain = [min_val, max_val];
        this._y_domain_step = step;
        this.orig_scale_x.domain(this._x_domain);
        this.orig_scale_y.domain(this._y_domain);
    }

    _update_crossfilter(data: any) {
        this._crossfilter.remove(() => true);
        this._crossfilter.add(data);
    }

    _update_subplots(plot_definitions: SubPlotPlotDefinition[]) {
        // Mark all existing plots for removal
        this._subplots.forEach(subplot => {
            subplot.marked_for_removal = true;
        });

        plot_definitions.forEach(definition => {
            if (this._plot_exists(definition.id)) {
                delete this._subplots_by_id[definition.id][
                    "marked_for_removal"
                ];
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

    create_plot_from_definition(definition: SubPlotPlotDefinition) {
        const new_plot = new (subplot_factory.get_plot(definition.plot_type))(
            definition,
        );
        const dimension = this._crossfilter.dimension(d => d.date);
        new_plot.renderer(this);
        new_plot.dimension(dimension);
        return new_plot;
    }

    _plot_exists(plot_id: string) {
        for (const idx in this._subplots) {
            if (this._subplots[idx].definition!.id == plot_id) return true;
        }
        return false;
    }

    override render() {
        this.render_title(this._title, this._title_url!);

        // Prepare scales, the subplots need them to render the data
        this._prepare_scales();

        // Prepare render area for subplots
        // TODO: move to plot creation
        this._subplots.forEach(subplot => {
            subplot.prepare_render();
        });

        // Render subplots
        this._subplots.forEach(subplot => {
            (subplot as SubplotSubs).render();
        });

        this.render_axis();
        this.render_grid();
        this.render_legend();
    }

    render_legend() {
        this._legend.style(
            "display",
            //@ts-ignore
            this._subplots.length > 1 ? null : "none",
        );

        if (this._subplots.length <= 1) return;

        const items = this._legend
            .selectAll<HTMLDivElement, SubplotSubs>(".legend_item")
            .data(this._subplots, d => d.definition!.id);
        items.exit().remove();
        const new_items = items
            .enter()
            .append("div")
            .classed("legend_item", true)
            .classed("noselect", true);

        new_items.append("div").classed("color_code", true);
        new_items.style("pointer-events", "all");
        new_items.append("label").text(d => d.definition!.label);
        new_items.on("click", event => {
            const item = select(event.currentTarget);
            item.classed("disabled", !item.classed("disabled"));
            // @ts-ignore
            item.style(
                "background",
                // @ts-ignore
                (item.classed("disabled") && "grey") || null,
            );
            const all_disabled: string[] = [];
            this._div_selection.selectAll(".legend_item.disabled").each(d => {
                // @ts-ignore
                all_disabled.push(d.definition.use_tags[0]);
            });
            this._legend_dimension.filter(d => {
                return all_disabled.indexOf(<string>d) == -1;
            });
            this._compute_stack_values();
            this._subplots.forEach(subplot =>
                subplot.update_transformed_data(),
            );
            this.update_gui();
        });

        new_items
            .merge(items)
            .selectAll<HTMLDivElement, SubplotSubs>("div")
            // 2769: No overload matches this call
            // @ts-ignore
            .style("background", d => d.get_color());
    }

    _prepare_scales() {
        this.scale_x = this._current_zoom.rescaleX(this.orig_scale_x);
        this.scale_y.range(this.orig_scale_y.range());
        this.scale_y.domain(this.orig_scale_y.domain());

        if (this.lock_zoom_y) this.scale_y.domain(this.orig_scale_y.domain());
        else {
            const y_max = this.orig_scale_y.domain()[1];
            const y_stretch = Math.max(
                0.05 * y_max,
                y_max + (this._current_zoom.y / 100) * y_max,
            );
            this.scale_y.domain([0, y_stretch]);
        }
    }

    _find_metric_to_stack(
        definition: SubPlotPlotDefinition,
        all_disabled: string[],
    ): string | undefined | null {
        if (!definition.stack_on || !this._subplots_by_id[definition.stack_on])
            return null;
        if (all_disabled.indexOf(definition.stack_on) == -1)
            return definition.stack_on;
        if (this._subplots_by_id[definition.stack_on].definition!.stack_on)
            return this._find_metric_to_stack(
                this._subplots_by_id[definition.stack_on].definition!,
                all_disabled,
            );
        return null;
    }

    _compute_stack_values() {
        // Disabled metrics
        const all_disabled: string[] = [];
        this._div_selection
            .selectAll<HTMLElement, SubplotSubs>(".legend_item.disabled")
            .each(d => {
                all_disabled.push(d.definition!.id);
            });

        // Identify stacks
        const required_stacks: Record<string, any> = {};
        this._subplots.forEach(subplot => {
            subplot.stack_values = null;
            if (subplot.definition!.stack_on) {
                const stack_on = this._find_metric_to_stack(
                    subplot.definition!,
                    all_disabled,
                );
                if (stack_on != null)
                    required_stacks[subplot.definition!.id] = stack_on;
            }
        });

        // Order stacks
        // TBD:

        // Update stacks
        const base_values: Record<string, any> = {};
        for (const target in required_stacks) {
            const source = this._subplots_by_id[required_stacks[target]];
            source.update_transformed_data();
            const references: number[] = [];
            source.transformed_data.forEach(point => {
                references[point.timestamp] = point.value;
            });
            base_values[source.definition!.id] = references;
            this._subplots_by_id[target].stack_values = references;
            this._subplots_by_id[target].update_transformed_data();
        }
    }

    render_axis() {
        const x = this.g
            .selectAll("g.x_axis")
            .data([null])
            .join("g")
            .classed("x_axis", true)
            .classed("axis", true);

        const x_tick_count = Math.min(Math.ceil(this.plot_size.width / 65), 6);
        this.transition(x).call(
            axisBottom(this.scale_x)
                .tickFormat(d => {
                    // @ts-ignore
                    if (d.getMonth() === 0 && d.getDate() === 1)
                        // @ts-ignore
                        return timeFormat("%Y")(d);
                    // @ts-ignore
                    else if (d.getHours() === 0 && d.getMinutes() === 0)
                        // @ts-ignore
                        return timeFormat("%m-%d")(d);
                    // @ts-ignore
                    return timeFormat("%H:%M")(d);
                })
                .ticks(x_tick_count),
        );
        x.attr("transform", "translate(0," + this.plot_size.height + ")");

        const y = this.g
            .selectAll("g.y_axis")
            .data([null])
            .join("g")
            .classed("y_axis", true)
            .classed("axis", true);

        const render_function = this.get_scale_render_function();
        this.transition(y).call(
            axisLeft(this.scale_y)
                .tickFormat(d => render_function(d).replace(/\.0+\b/, ""))
                .ticks(this._y_ticks()),
        );
    }

    _y_ticks(): number {
        const max = range(
            this._y_domain[0],
            this._y_domain[1] + 1,
            this._y_domain_step,
        ).length;
        const min = Math.ceil(this.plot_size.height / 65);
        return Math.min(min, max);
    }

    render_grid() {
        // Grid
        const height = this.plot_size.height;
        axisBottom(this.scale_x)
            .ticks(5)
            .tickSize(-height)
            // @ts-ignore
            .tickFormat("")(
            this.g
                .selectAll<SVGGElement, unknown>("g.grid.vertical")
                .data([null])
                .join("g")
                .classed("grid vertical", true)
                .attr("transform", "translate(0," + height + ")"),
        );

        const width = this.plot_size.width;

        axisLeft(this.scale_y)
            .tickSize(-width)
            .ticks(this._y_ticks() * 2)
            // @ts-ignore
            .tickFormat("")(
            this.g
                .selectAll<SVGGElement, unknown>("g.grid.horizontal")
                .data([null])
                .join("g")
                .classed("grid horizontal", true),
        );
    }

    //typing this argument as selection causes a
    // lot of typing errors which I couldn't solve until now
    transition(selection: any) {
        if (this._zoom_active) {
            selection.interrupt();
            return selection;
        } else return selection.transition().duration(500);
    }
}
