/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import type {Crossfilter} from "crossfilter2";
import crossfilter from "crossfilter2";
import type {BaseType, Selection} from "d3";
import {json, select} from "d3";

import type {CMKAjaxReponse} from "@/modules/types";
import {get_computed_style} from "@/modules/utils";

import {
    add_scheduler_debugging,
    plot_render_function,
    svg_text_overflow_ellipsis,
} from "./cmk_figures_utils";
import type {
    ElementMargin,
    ElementSize,
    FigureBaseDashletSpec,
    FigureData,
} from "./figure_types";
import {Scheduler} from "./multi_data_fetcher";

// Base class for all cmk_figure based figures
// Introduces
//  - Figure sizing
//  - Post url and body
//  - Automatic update of data via scheduler
//  - Various hooks for each phase
//  - Loading icon

export abstract class FigureBase<
    T extends FigureData,
    DashletSpec extends FigureBaseDashletSpec = FigureBaseDashletSpec,
> {
    _div_selector: string;
    _div_selection: Selection<HTMLDivElement, unknown, BaseType, unknown>;
    svg: Selection<SVGSVGElement, unknown, BaseType, unknown> | null;
    plot: Selection<SVGGElement, unknown, any, any>;
    _fixed_size: ElementSize | null;
    margin: ElementMargin;
    _fetch_start: number;
    _fetch_data_latency: number;
    //TODO: specify type of data
    _data_pre_processor_hooks: ((data?: any) => any)[];
    _post_render_hooks: ((data?: any) => void)[];
    _post_url: string;
    _post_body: string;
    _dashlet_spec: DashletSpec;
    //TODO: figure out how the type of _data should look like:
    // here in figureBase its like {data, plot_definitions}
    // however, in some places it's overwritten to be only data from the above mentioned type data = this._data.data
    // and in other spots like ntop_flows it's totally different and it will be something like data.flows
    // this not only effects the _data type but also _crossfilter
    // and adding types to _data_pre_processor_hooks and _pre_render_hooks
    _data: T;
    _crossfilter: Crossfilter<any>;
    scheduler: Scheduler;
    figure_size!: ElementSize;
    plot_size!: ElementSize;

    ident() {
        return "figure_base_class";
    }

    constructor(div_selector: string, fixed_size: ElementSize | null = null) {
        this._div_selector = div_selector; // The main container
        this._div_selection = select(this._div_selector); // The d3-seletion of the main container

        this.svg = null; // The svg representing the figure
        // @ts-ignore
        this.plot = null; // The plot representing the drawing area, is shifted by margin

        if (fixed_size !== null) this._fixed_size = fixed_size;
        else this._fixed_size = null;
        this.margin = {top: 10, right: 10, bottom: 10, left: 10};

        this._div_selection
            .classed(this.ident(), true)
            .classed("cmk_figure", true)
            .datum(this);

        // Parameters used for profiling
        this._fetch_start = 0;
        this._fetch_data_latency = 0;

        // List of hooks which may modify data received from api call
        // Processing Pipeline:
        // -> _data_pre_processor_hooks # call registered hooks which may modifiy data from api call
        // -> _update_data/update_gui   # the actual rendering graph rendering
        // -> _post_render_hooks        # call registered hooks when the rendering is finsihed

        // The preprocessor can convert arbitary api data, into a figure convenient format
        this._data_pre_processor_hooks = [];
        this._post_render_hooks = [];

        // Post url and body for fetching the graph data
        this._post_url = "";
        this._post_body = "";
        this._dashlet_spec = {} as DashletSpec;

        // Current data of this figure
        this._data = this.getEmptyData();
        this._crossfilter = crossfilter();
        this.scheduler = new Scheduler(
            () => this._fetch_data(),
            this.get_update_interval(),
        );
    }

    abstract getEmptyData(): T;

    initialize(with_debugging?: boolean) {
        if (with_debugging)
            add_scheduler_debugging(this._div_selection, this.scheduler);
        this.show_loading_image();
    }

    resize() {
        let new_size = this._fixed_size;
        if (new_size === null) {
            new_size = {
                // @ts-ignore
                width: this._div_selection.node().parentNode.offsetWidth,
                // @ts-ignore
                height: this._div_selection.node().parentNode.offsetHeight,
            };
        }
        this.figure_size = new_size as ElementSize;
        this.plot_size = {
            width:
                this.figure_size.width - this.margin.left - this.margin.right,
            height:
                this.figure_size.height - this.margin.top - this.margin.bottom,
        };
    }

    show_loading_image() {
        this._div_selection
            .selectAll("div.loading_img")
            .data([null])
            .enter()
            .insert("div", ":first-child")
            .classed("loading_img", true);
    }

    remove_loading_image() {
        this._div_selection.selectAll("div.loading_img").remove();
    }

    subscribe_data_pre_processor_hook(func: (_data?: any) => any) {
        this._data_pre_processor_hooks.push(func);
    }

    subscribe_post_render_hook(func: (data?: any) => void) {
        this._post_render_hooks.push(func);
    }

    get_update_interval() {
        return 10;
    }

    set_dashlet_spec(dashlet_spec: DashletSpec) {
        this._dashlet_spec = dashlet_spec;
    }

    set_post_url_and_body(url: string, body = "") {
        this._post_url = url;
        this._post_body = body;
    }

    get_post_settings() {
        return {
            url: this._post_url,
            body: this._post_body,
        };
    }

    _fetch_data() {
        const post_settings = this.get_post_settings();

        if (!post_settings.url) return;

        this._fetch_start = Math.floor(new Date().getTime() / 1000);
        json(encodeURI(post_settings.url), {
            credentials: "include",
            method: "POST",
            body: post_settings.body,
            headers: {
                "Content-type": "application/x-www-form-urlencoded",
            },
        })
            .then(json_data =>
                this._process_api_response(
                    json_data as CMKAjaxReponse<{figure_response: T}>,
                ),
            )
            .catch(() => {
                this._show_error_info("Error fetching data", "error");
                this.remove_loading_image();
            });
    }

    _process_api_response(api_response: CMKAjaxReponse<{figure_response: T}>) {
        // Current api data format
        // {"result_code": 0, "result": {
        //      "figure_response": {
        //         "plot_definitions": [] // definitions for the plots to render
        //         "data": []             // the actual data
        //      },
        // }}
        if (api_response.result_code != 0) {
            this._show_error_info(
                String(api_response.result),
                api_response.severity,
            );
            return;
        }
        this._clear_error_info();
        this.process_data(api_response.result.figure_response);
        this._fetch_data_latency =
            +(new Date().getDate() - this._fetch_start) / 1000;
    }

    process_data(data: T) {
        //TODO: data os overwritten below each time a function of _data_pre_processor_hooks
        // so head it's not clear how it will look like at the end
        // it's better to seperate the typing here between data the parameter (T extends FigureData)
        // and the overwritten data from _data_pre_processor_hooks
        this._data_pre_processor_hooks.forEach(pre_processor_func => {
            data = pre_processor_func(data);
        });
        this.update_data(data);
        this.remove_loading_image();
        this.update_gui();
        this._call_post_render_hooks(data);
    }

    _show_error_info(error_info: string, div_class: string) {
        this._div_selection
            .selectAll("div#figure_error")
            .data([null])
            .join("div")
            .attr("id", "figure_error")
            .attr("class", div_class)
            .text(error_info);
        if (!this.svg) return;
        this.svg.style("display", "none");
    }

    _clear_error_info() {
        this._div_selection.select("#figure_error").remove();
        if (!this.svg) return;
        this.svg.style("display", null);
    }

    _call_post_render_hooks(data: T) {
        this._post_render_hooks.forEach(hook => hook(data));
    }

    // Triggers data update mechanics in a figure, e.g. store some data from response
    update_data(data: T) {
        this._data = data;
    }

    // Triggers gui update mechanics in a figure, e.g. rendering
    // TOSOLVE should this method become abstract?
    //in some cases it's not implemented in other classes
    // eslint-disable-next-line @typescript-eslint/no-empty-function
    update_gui() {}

    // Simple re-rendering of existing data
    // TODO: merge with update_gui?
    // eslint-disable-next-line @typescript-eslint/no-empty-function
    render() {}

    render_title(title: undefined | string, title_url: string) {
        if (!this.svg) return;
        const renderedTitle = title ? [{title: title, url: title_url}] : [];
        let title_component = this.svg
            .selectAll<SVGElement, unknown>(".title")
            .data(renderedTitle)
            .join("g")
            .classed("title", true);

        const highlight_container = this._dashlet_spec.show_title == true;

        title_component
            .selectAll<SVGRectElement, unknown>("rect")
            .data(d => [d])
            .join("rect")
            .attr("x", 0)
            .attr("y", 0.5)
            .attr("width", this.figure_size.width)
            .attr("height", 22)
            .classed(highlight_container ? "highlighted" : "", true);

        if (title_url) {
            //@ts-ignore
            title_component = title_component
                .selectAll<HTMLAnchorElement, unknown>("a")
                .data(d => [d])
                .join("a")
                .attr("xlink:href", d => d.url || "#");
        }

        const text_element = title_component
            .selectAll<SVGTextElement, unknown>("text")
            .data(d => [d])
            .join("text")
            .text(d => d.title)
            .classed("title", true)
            .attr("y", 16)
            .attr("x", this.figure_size.width / 2)
            .attr("text-anchor", "middle");

        let title_padding_left = 0;
        const title_padding_left_raw = get_computed_style(
            select("div.dashlet div.title").node() as HTMLElement,
            "padding-left",
        );
        if (title_padding_left_raw) {
            title_padding_left = parseInt(
                title_padding_left_raw.replace("px", ""),
            );
        }

        text_element.each((_d, idx, nodes) => {
            svg_text_overflow_ellipsis(
                nodes[idx],
                this.figure_size.width,
                title_padding_left,
            );
        });
    }

    get_scale_render_function() {
        // Create uniform behaviour with Graph dashlets: Display no unit at y-axis if value is 0
        //@ts-ignore
        const f = render_function => v =>
            Math.abs(v) < 10e-16 ? "0" : render_function(v);
        if (this._data.plot_definitions.length > 0)
            return f(plot_render_function(this._data.plot_definitions[0]));
        return f(plot_render_function({}));
    }
}

export interface TextFigureData<D = any, P = any> extends FigureData<D, P> {
    title: string;
    title_url: string;
}

export abstract class TextFigure<
    T extends TextFigureData = TextFigureData,
> extends FigureBase<T> {
    constructor(div_selector: string, fixed_size: ElementSize | null) {
        super(div_selector, fixed_size);
        this.margin = {top: 0, right: 0, bottom: 0, left: 0};
    }

    override initialize(debug: boolean) {
        FigureBase.prototype.initialize.call(this, debug);
        this.svg = this._div_selection.append("svg");
        this.plot = this.svg.append("g");
    }

    override resize() {
        if (this._data.title) {
            this.margin.top = 22; // magic number: title height
        }
        FigureBase.prototype.resize.call(this);
        this.svg!.attr("width", this.figure_size.width).attr(
            "height",
            this.figure_size.height,
        );
        this.plot.attr(
            "transform",
            "translate(" + this.margin.left + "," + this.margin.top + ")",
        );
    }

    override update_gui() {
        this.resize();
        this.render();
    }
}

// Base class for dc.js based figures (using crossfilter)
export abstract class DCFigureBase<
    DCFigureData extends FigureData,
> extends FigureBase<DCFigureData> {
    _graph_group: any;
    _dc_chart: any;

    constructor(div_selector: string, crossfilter: any, graph_group: any) {
        super(div_selector);
        this._crossfilter = crossfilter; // Shared dataset
        this._graph_group = graph_group; // Shared group among graphs
        this._dc_chart = null;
    }

    get_dc_chart() {
        return this._dc_chart;
    }
}

export class FigureRegistry<T extends FigureData> {
    private _figures: Record<
        string,
        new (div_selector: string, fixed_size?: any) => FigureBase<T>
    >;

    constructor() {
        this._figures = {};
    }

    register(
        figure_class: new (
            div_selector: string,
            fixed_size?: any,
        ) => FigureBase<T>,
    ): void {
        this._figures[figure_class.prototype.ident()] = figure_class;
    }

    get_figure(
        ident: string,
    ): new (div_selector: string, fixed_size?: any) => FigureBase<T> {
        return this._figures[ident];
    }
}

export const figure_registry = new FigureRegistry(); // The FigureRegistry holds all figure class templates
