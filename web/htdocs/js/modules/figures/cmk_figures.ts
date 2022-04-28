import * as d3 from "d3";
import * as crossfilter from "crossfilter2";
import * as utils from "../utils";

interface ElementSize {
    width: number | null;
    height: number | null;
}

// The FigureRegistry holds all figure class templates
class FigureRegistry {
    private _figures: Record<string, typeof FigureBase>;

    constructor() {
        this._figures = {};
    }

    register(figure_class: typeof FigureBase): void {
        let instance = new figure_class(null, null);
        this._figures[instance.ident()] = figure_class;
    }

    get_figure(ident: string): typeof FigureBase {
        return this._figures[ident];
    }
}

export let figure_registry = new FigureRegistry();

// Data update scheduler
// Receives one function pointer which is regularly called
// Supports scheduling modes
// - enable
// - disable
// - force_update
// - suspend_for (seconds)
// - update_if_older_than (seconds)
class Scheduler {
    _scheduled_function: Function;
    _update_interval: number;
    _enabled: boolean;
    _last_update: number;
    _suspend_updates_until: number;

    constructor(scheduled_function, update_interval) {
        this._scheduled_function = scheduled_function;
        this._update_interval = update_interval;
        this._enabled = false;
        this._last_update = 0;
        this._suspend_updates_until = 0;
        setInterval(() => this._schedule(), 1000);
    }

    get_update_interval() {
        return this._update_interval;
    }

    set_update_interval(seconds) {
        this._update_interval = seconds;
    }

    enable() {
        this._enabled = true;
    }

    disable() {
        this._enabled = false;
    }

    suspend_for(seconds) {
        this._suspend_updates_until =
            Math.floor(new Date().getTime() / 1000) + seconds;
    }

    update_if_older_than(seconds) {
        let now = Math.floor(new Date().getTime() / 1000);
        if (now > this._last_update + seconds) {
            this._scheduled_function();
            let now = Math.floor(new Date().getTime() / 1000);
            this._last_update = now;
        }
    }

    force_update() {
        this._scheduled_function();
        let now = Math.floor(new Date().getTime() / 1000);
        this._last_update = now;
    }

    _schedule() {
        if (!this._enabled) return;
        if (!utils.is_window_active()) return;
        let now = Math.floor(new Date().getTime() / 1000);
        if (now < this._suspend_updates_until) return;
        // This function is called every second. Add 0.5 seconds grace time
        // for function which expect an update every second
        if (now + 0.5 > this._last_update + this._update_interval) {
            this._last_update = now;
            this._scheduled_function();
        }
    }
}

interface BodyContent {
    interval: number | Function[];
}

interface URLBody {
    body: BodyContent;
}

interface URL {
    url: URLBody;
}

// Allows scheduling of multiple url calls
// Registered hooks will be call on receiving data
export class MultiDataFetcher {
    scheduler: Scheduler;
    _fetch_operations: URL;
    _fetch_hooks: URL;

    constructor() {
        this.reset();
        this.scheduler = new Scheduler(() => this._schedule_operations(), 1);
        this._fetch_operations = {} as URL;
        this._fetch_hooks = {} as URL;
    }

    reset() {
        // Urls to call
        // {"url": {"body": {"interval": 10}}
        this._fetch_operations = {} as URL;

        // Hooks to call when receiving data
        // {"url": {"body": [funcA, funcB]}}
        this._fetch_hooks = {} as URL;
    }

    subscribe_hook(post_url, post_body, subscriber_func) {
        // New url and body
        if (this._fetch_hooks[post_url] == undefined) {
            this._fetch_hooks[post_url] = {};
            this._fetch_hooks[post_url][post_body] = [subscriber_func];
            return;
        }
        // New body to existing url
        if (this._fetch_hooks[post_url][post_body] == undefined) {
            this._fetch_hooks[post_url][post_body] = [subscriber_func];
            return;
        }
        // Existing url and body
        this._fetch_hooks[post_url][post_body].push(subscriber_func);
    }

    add_fetch_operation(post_url, post_body, interval) {
        if (this._fetch_operations[post_url] == undefined)
            this._fetch_operations[post_url] = {};

        this._fetch_operations[post_url][post_body] =
            this._default_operation_options(interval);
    }

    _default_operation_options(interval) {
        return {
            active: true, // May be used to temporarily disable the operation
            last_update: 0, // Last time the fetch operation was sent (not received)
            fetch_in_progress: false,
            interval: interval,
        };
    }

    _schedule_operations() {
        if (!utils.is_window_active()) return;
        for (let url_id in this._fetch_operations) {
            for (let body_id in this._fetch_operations[url_id]) {
                this._process_operation(url_id, body_id);
            }
        }
    }

    _process_operation(post_url, post_body) {
        let now = Math.floor(new Date().getTime() / 1000);
        let operation = this._fetch_operations[post_url][post_body];
        if (!operation.active || operation.fetch_in_progress) return;

        if (operation.last_update + operation.interval > now) return;

        operation.last_update = now;
        operation.fetch_in_progress = true;
        this._fetch(post_url, post_body);
    }

    _fetch(post_url, post_body) {
        // TODO: improve error handling, d3js supports promises
        d3.json(encodeURI(post_url), {
            credentials: "include",
            method: "POST",
            body: post_body,
            headers: {
                "Content-type": "application/x-www-form-urlencoded",
            },
        }).then(response =>
            this._fetch_callback(post_url, post_body, response)
        );
    }

    _fetch_callback(post_url, post_body, api_response) {
        let response = api_response.result;
        let data = response.figure_response;

        let now = Math.floor(new Date().getTime() / 1000);

        if (
            this._fetch_operations[post_url] == undefined ||
            this._fetch_operations[post_url][post_body] == undefined
        )
            return;
        this._fetch_operations[post_url][post_body].last_update = now;
        this._fetch_operations[post_url][post_body].fetch_in_progress = false;

        // Inform subscribers
        this._fetch_hooks[post_url][post_body].forEach(subscriber_func => {
            subscriber_func(data);
        });
    }
}

// Base class for all cmk_figure based figures
// Introduces
//  - Figure sizing
//  - Post url and body
//  - Automatic update of data via scheduler
//  - Various hooks for each phase
//  - Loading icon

interface ELementMargin {
    top: number;
    right: number;
    bottom: number;
    left: number;
}

export class FigureBase {
    _div_selector;
    _div_selection;
    svg;
    plot;
    _fixed_size: ElementSize | null;
    margin: ELementMargin;
    _fetch_start: number;
    _fetch_data_latency: number;
    _data_pre_processor_hooks;
    _pre_render_hooks: Function[];
    _post_render_hooks: Function[];
    _post_url: string;
    _post_body: string;
    _data;
    // @ts-ignore
    _crossfilter: crossfilter;
    scheduler: Scheduler;
    figure_size;
    plot_size;

    ident() {
        return "figure_base_class";
    }

    constructor(div_selector, fixed_size = null) {
        this._div_selector = div_selector; // The main container
        this._div_selection = d3.select(this._div_selector); // The d3-seletion of the main container

        this.svg = null; // The svg representing the figure
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
        // -> _pre_render_hooks         # call registered hook when receiving data
        // -> _update_data/update_gui   # the actual rendering graph rendering
        // -> _post_render_hooks        # call registered hooks when the rendering is finsihed

        // The preprocessor can convert arbitary api data, into a figure convenient format
        this._data_pre_processor_hooks = [];
        this._pre_render_hooks = [];
        this._post_render_hooks = [];

        // Post url and body for fetching the graph data
        this._post_url = "";
        this._post_body = "";

        // Current data of this figure
        this._data = {data: [], plot_definitions: []};
        // @ts-ignore
        this._crossfilter = new crossfilter.default();
        this.scheduler = new Scheduler(
            () => this._fetch_data(),
            this.get_update_interval()
        );
    }

    initialize(with_debugging) {
        if (with_debugging) this._add_scheduler_debugging();
        this.show_loading_image();
    }

    add_plot_definition(plot_definition) {
        this._data.plot_definitions.push(plot_definition);
    }

    add_data(data) {
        this._data.data = this._data.data.concat(data);
    }

    remove_plot_definition(plot_definition) {
        let plot_id = plot_definition.id;
        for (let idx in this._data.plot_definitions) {
            let plot_def = this._data.plot_definitions[idx];
            if (plot_def.id == plot_id) {
                this._data.plot_definitions.splice(+idx, 1);
                return;
            }
        }
    }

    resize() {
        let new_size = this._fixed_size;
        if (new_size === null) {
            new_size = {
                width: this._div_selection.node().parentNode.offsetWidth,
                height: this._div_selection.node().parentNode.offsetHeight,
            };
        }
        this.figure_size = new_size;
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

    subscribe_data_pre_processor_hook(func) {
        this._data_pre_processor_hooks.push(func);
    }

    unsubscribe_data_pre_processor_hook(func) {
        let idx = this._data_pre_processor_hooks.indexOf(func);
        this._data_pre_processor_hooks.splice(idx, 1);
    }

    subscribe_pre_render_hook(func) {
        this._pre_render_hooks.push(func);
    }

    unsubscribe_pre_render_hook(func) {
        let idx = this._pre_render_hooks.indexOf(func);
        this._pre_render_hooks.splice(idx, 1);
    }

    subscribe_post_render_hook(func) {
        this._post_render_hooks.push(func);
    }

    unsubscribe_post_render_hook(func) {
        let idx = this._post_render_hooks.indexOf(func);
        this._post_render_hooks.splice(idx, 1);
    }

    get_update_interval() {
        return 10;
    }

    set_post_url_and_body(url, body = "") {
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
        let post_settings = this.get_post_settings();

        if (!post_settings.url) return;

        this._fetch_start = Math.floor(new Date().getTime() / 1000);
        d3.json(encodeURI(post_settings.url), {
            credentials: "include",
            method: "POST",
            body: post_settings.body,
            headers: {
                "Content-type": "application/x-www-form-urlencoded",
            },
        })
            .then(json_data => this._process_api_response(json_data))
            .catch(e => {
                this._show_error_info("Error fetching data", "error");
                this.remove_loading_image();
            });
    }

    _process_api_response(api_response) {
        // Current api data format
        // {"result_code": 0, "result": {
        //      "figure_response": {
        //         "plot_definitions": [] // definitions for the plots to render
        //         "data": []             // the actual data
        //      },
        // }}
        if (api_response.result_code != 0) {
            this._show_error_info(api_response.result, api_response.severity);
            return;
        }
        this._clear_error_info();
        this.process_data(api_response.result.figure_response);
        this._fetch_data_latency =
            +(new Date().getDate() - this._fetch_start) / 1000;
    }

    process_data(data) {
        this._data_pre_processor_hooks.forEach(pre_processor_func => {
            data = pre_processor_func(data);
        });
        this._call_pre_render_hooks(data);
        this.update_data(data);
        this.remove_loading_image();
        this.update_gui();
        this._call_post_render_hooks(data);
    }

    _show_error_info(error_info, div_class) {
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

    _call_pre_render_hooks(data) {
        this._pre_render_hooks.forEach(hook => hook(data));
    }

    _call_post_render_hooks(data) {
        this._post_render_hooks.forEach(hook => hook(data));
    }

    // Triggers data update mechanics in a figure, e.g. store some data from response
    update_data(data) {
        this._data = data;
    }

    // Triggers gui update mechanics in a figure, e.g. rendering
    update_gui() {}

    // Simple re-rendering of existing data
    // TODO: merge with update_gui?
    render() {}

    // Adds some basic debug features for the scheduler
    _add_scheduler_debugging() {
        let debugging = this._div_selection.append("div");
        // Stop button
        debugging
            .append("input")
            .attr("type", "button")
            .attr("value", "Stop")
            .on("click", () => this.scheduler.disable());
        // Start button
        debugging
            .append("input")
            .attr("type", "button")
            .attr("value", "Start")
            .on("click", () => this.scheduler.enable());
        // Suspend 5 seconds
        debugging
            .append("input")
            .attr("type", "button")
            .attr("value", "Suspend 5 seconds")
            .on("click", () => this.scheduler.suspend_for(5));
        // Force update
        debugging
            .append("input")
            .attr("type", "button")
            .attr("value", "Force")
            .on("click", () => this.scheduler.force_update());
    }

    render_title(title, title_url) {
        if (!this.svg) return;
        title = title ? [{title: title, url: title_url}] : [];

        let title_component = this.svg
            .selectAll(".title")
            .data(title)
            .join("g")
            .classed("title", true);

        let config = new URLSearchParams(this._post_body);
        let settings = config.get("settings");
        let highlight_container = false;
        if (settings != undefined)
            highlight_container = JSON.parse(settings).show_title == true;

        title_component
            .selectAll("rect")
            .data(d => [d])
            .join("rect")
            .attr("x", 0)
            .attr("y", 0.5)
            .attr("width", this.figure_size.width)
            .attr("height", 22)
            .classed(highlight_container ? "highlighted" : "", true);

        if (title_url) {
            title_component = title_component
                .selectAll("a")
                .data(d => [d])
                .join("a")
                .attr("xlink:href", d => d.url || "#");
        }

        let text_element = title_component
            .selectAll("text")
            .data(d => [d])
            .join("text")
            .text(d => d.title)
            .classed("title", true)
            .attr("y", 16)
            .attr("x", this.figure_size.width / 2)
            .attr("text-anchor", "middle");

        let title_padding_left = 0;
        const title_padding_left_raw = utils.get_computed_style(
            d3.select("div.dashlet div.title").node(),
            "padding-left"
        );
        if (title_padding_left_raw) {
            title_padding_left = parseInt(
                title_padding_left_raw.replace("px", "")
            );
        }

        text_element.each((d, idx, nodes) => {
            this._svg_text_overflow_ellipsis(
                nodes[idx],
                this.figure_size.width,
                title_padding_left
            );
        });
    }

    /**
     * Component to realize the css property text-overflow: ellipsis for svg text elements
     * @param {DOMElement} text or tspan DOM element
     * @param {number} width - Max width for the text/tspan element
     * @param {number} padding - Padding for the text/tspan element
     */
    _svg_text_overflow_ellipsis(node, width, padding) {
        let length = node.getComputedTextLength();
        if (length <= width - padding) return;

        const node_sel = d3.select(node);
        let text = node_sel.text();
        d3.select(node.parentNode)
            .selectAll("title")
            .data(d => [text])
            .join("title")
            .text(d => d)
            .classed("svg_text_tooltip", true);

        while (length > width - padding && text.length > 0) {
            text = text.slice(0, -1);
            node_sel.text(text + "...");
            length = node.getComputedTextLength();
        }
        node_sel.attr("x", padding).attr("text-anchor", "left");
    }

    get_scale_render_function() {
        // Create uniform behaviour with Graph dashlets: Display no unit at y-axis if value is 0
        const f = render_function => v =>
            Math.abs(v) < 10e-16 ? "0" : render_function(v);
        if (this._data.plot_definitions.length > 0)
            return f(plot_render_function(this._data.plot_definitions[0]));
        return f(plot_render_function({}));
    }
}

export class TextFigure extends FigureBase {
    constructor(div_selector, fixed_size = null) {
        super(div_selector, fixed_size);
        this.margin = {top: 0, right: 0, bottom: 0, left: 0};
    }

    initialize(debug) {
        FigureBase.prototype.initialize.call(this, debug);
        this.svg = this._div_selection.append("svg");
        this.plot = this.svg.append("g");
    }

    resize() {
        if (this._data.title) {
            this.margin.top = 22; // magic number: title height
        }
        FigureBase.prototype.resize.call(this);
        this.svg
            .attr("width", this.figure_size.width)
            .attr("height", this.figure_size.height);
        this.plot.attr(
            "transform",
            "translate(" + this.margin.left + "," + this.margin.top + ")"
        );
    }

    update_gui() {
        this.resize();
        this.render();
    }
}

export function calculate_domain(data) {
    const [lower, upper] = d3.extent(data, d => d.value);
    return [lower + upper * (1 - 1 / 0.95), upper / 0.95];
}

export function adjust_domain(domain, metrics) {
    let [dmin, dmax] = domain;

    if (metrics.max != null && metrics.max <= dmax) dmax = metrics.max;
    if (metrics.min != null && dmin <= metrics.min) dmin = metrics.min;
    return [dmin, dmax];
}

export function clamp(value, domain) {
    return Math.min(Math.max(value, domain[0]), domain[1]);
}

export function make_levels(domain, bounds) {
    let [dmin, dmax] = domain;
    if (bounds.warn == null || bounds.crit == null) return [];

    if (bounds.warn >= dmax) bounds.warn = dmax;
    if (bounds.crit >= dmax) bounds.crit = dmax;
    if (bounds.warn <= dmin) dmin = bounds.warn;

    return [
        {from: bounds.crit, to: dmax, style: "metricstate state2"},
        {
            from: bounds.warn,
            to: bounds.crit,
            style: "metricstate state1",
        },
        {from: dmin, to: bounds.warn, style: "metricstate state0"},
    ];
}

// Base class for dc.js based figures (using crossfilter)
export class DCFigureBase extends FigureBase {
    _graph_group;
    _dc_chart;

    constructor(div_selector, crossfilter, graph_group) {
        super(div_selector);
        this._crossfilter = crossfilter; // Shared dataset
        this._graph_group = graph_group; // Shared group among graphs
        this._dc_chart = null;
    }

    get_dc_chart() {
        return this._dc_chart;
    }
}

// Class which handles the display of a tooltip
// It generates basic tooltips and handles its correct positioning
export class FigureTooltip {
    _tooltip;
    figure_size: ElementSize;
    plot_size: ElementSize;

    constructor(tooltip_selection) {
        this._tooltip = tooltip_selection;
        this._tooltip
            .style("opacity", 0)
            .style("position", "absolute")
            .classed("tooltip", true);
        this.figure_size = {width: null, height: null};
        this.plot_size = {width: null, height: null};
    }

    update_sizes(figure_size, plot_size) {
        this.figure_size = figure_size;
        this.plot_size = plot_size;
    }

    update_position(event) {
        if (!this.active()) return;

        let tooltip_size = {
            width: this._tooltip.node().offsetWidth,
            height: this._tooltip.node().offsetHeight,
        };

        const [x, y] = d3.pointer(event, event.target.closest("svg"));

        const is_at_right_border =
            event.pageX >= document.body.clientWidth - tooltip_size.width;
        const is_at_bottom_border =
            event.pageY >= document.body.clientHeight - tooltip_size.height;

        const left = is_at_right_border
            ? x - tooltip_size.width + "px"
            : x + "px";
        const top = is_at_bottom_border
            ? y - tooltip_size.height + "px"
            : y + "px";
        this._tooltip
            .style("left", left)
            .style("right", "auto")
            .style("bottom", "auto")
            .style("top", top)
            .style("pointer-events", "none")
            .style("opacity", 1);
    }

    add_support(node) {
        let element = d3.select(node);
        element
            .on("mouseover", event => this._mouseover(event))
            .on("mouseleave", event => this._mouseleave(event))
            .on("mousemove", event => this._mousemove(event));
    }

    activate() {
        d3.select(this._tooltip.node().closest("div.dashlet")).style(
            "z-index",
            "99"
        );
        this._tooltip.style("display", null);
    }

    deactivate() {
        d3.select(this._tooltip.node().closest("div.dashlet")).style(
            "z-index",
            ""
        );
        this._tooltip.style("display", "none");
    }

    active() {
        return this._tooltip.style("display") != "none";
    }

    _mouseover(event) {
        let node_data = d3.select(event.target).datum();
        if (node_data == undefined || node_data.tooltip == undefined) return;
        this.activate();
    }

    _mousemove(event) {
        let node_data = d3.select(event.target).datum();
        if (node_data == undefined || node_data.tooltip == undefined) return;
        this._tooltip.html(node_data.tooltip);
        this.update_position(event);
    }

    _mouseleave(event) {
        this.deactivate();
    }
}

/**
 * Component to draw a label at the bottom of the dashlet
 * @param {FigureBase} figurebase - Draw label on this dashlet
 * @param {Object} options - Configuration of the label
 * @param {string} options.label - Text to draw in the label
 * @param {string} options.css_class - Css classes to append to the label
 * @param {boolean} options.visible - Whether to draw the label at all
 * @param {string} options.font_size - Optional font size
 */
// Figure which inherited from FigureBase. Needs access to svg and size
export function state_component(figurebase, options) {
    // TODO: use figurebase.svg as first parameter and move size to options
    if (!options.visible) {
        figurebase.svg.selectAll(".state_component").remove();
        return;
    }
    //hard fix for the moment
    let font_size = options.font_size ? options.font_size : 14;
    let state_component = figurebase.svg
        .selectAll(".state_component")
        .data([options])
        .join("g")
        .classed("state_component", true)
        .attr(
            "transform",
            "translate(" +
                (figurebase.figure_size.width - font_size * 8) / 2 +
                ", " +
                (figurebase.figure_size.height - font_size * 2) +
                ")"
        );
    let label_box = state_component
        .selectAll("rect.status_label")
        .data(d => [d])
        .join("rect")
        .attr("class", d => `status_label ${d.css_class}`)
        // status_label css class is also defined for WATO and not encapsulated
        // it predifines other sizes, we use thus style instead of attr for size
        // to override that
        .style("width", font_size * 8)
        .style("height", font_size * 1.5)
        .attr("rx", 2);

    let the_text = state_component
        .selectAll("text")
        .data(d => [d])
        .join("text")
        .attr("text-anchor", "middle")
        .attr("dx", font_size * 4)
        .attr("dy", font_size * 1.1)
        .style("font-size", font_size + "px")
        .style("fill", "black")
        .style("font-weight", "bold")
        .text(d => d.label);
}

export function renderable_value(value, domain, plot) {
    const formatter = plot_render_function(plot);
    return {
        ...split_unit(formatter(value.value)),
        url: value.url || "",
    };
}

// Adhoc hack to extract the unit from a formatted string, which has units
// Once we migrate metric system to the frontend drop this
export function split_unit(formatted_value) {
    if (!formatted_value) return {};
    // Separated by space, most rendered quantities
    let splitted_text = formatted_value.split(" ");
    if (splitted_text.length == 2)
        return {value: splitted_text[0], unit: splitted_text[1]};

    // Percentages have no space
    if (formatted_value.endsWith("%"))
        return {value: formatted_value.slice(0, -1), unit: "%"};

    // It's a counter, unitless
    return {value: formatted_value, unit: ""};
}

export function getIn(object, ...args) {
    return args.reduce((obj, level) => obj && obj[level], object);
}

export function get_function(render_string) {
    return new Function(`"use strict"; return ${render_string}`)();
}

export function plot_render_function(plot) {
    let js_render = getIn(plot, "metric", "unit", "js_render");
    if (js_render) return get_function(js_render);
    return get_function(
        "function(v) { return cmk.number_format.fmt_number_with_precision(v, 1000, 2, true); }"
    );
}

export function svc_status_css(paint, params) {
    let status_cls =
        getIn(params, "paint") === paint ? getIn(params, "css") || "" : "";
    if (status_cls.endsWith("0") && getIn(params, "status") === "not_ok")
        return "";
    return status_cls;
}

/**
 * Draw an individual shape
 *
 * @callback pathCallback
 * @param {d3.path} path - d3 path object to draw a shape with, it is filled with color to reflect the status.
 */

/**
 * Component to draw a background color on a dashlet
 * @param {d3.selection} selection - d3 object to draw on
 * @param {Object} options - Configuration of the background
 * @param {Object} options.size - When path_callback is not given draw a rect
 * @param {number} options.size.height - Height of the background rect
 * @param {number} options.size.width - Width of the background rect
 * @param {pathCallback} options.path_callback - Draw individual shape instead of rect
 * @param {string} options.css_class - Css classes to append to the background
 * @param {boolean} options.visible - Whether to draw the background at all
 */
export function background_status_component(selection, options) {
    const data = options.visible ? [null] : [];

    let path_callback =
        options.path_callback ||
        function (path) {
            path.rect(0, 0, options.size.width, options.size.height);
        };

    let background_path = d3.path();
    path_callback(background_path);

    selection
        .selectAll("path.status_background")
        .data(data)
        .join(enter => enter.insert("path", ":first-child"))
        .attr("class", `status_background ${options.css_class}`)
        .attr("d", background_path.toString());
}

/**
 * Component to draw a big centered value on a dashlet
 * @param {d3.selection} selection - d3 object to draw on
 * @param {Object} options - Configuration of the value
 * @param {Object} options.value - Configuration of the text to draw
 * @param {string} options.value.url - When given, add a link to the text
 * @param {string} options.value.unit - Append a unit to the value. e.g. '%'
 * @param {string} options.value.value - Text to display
 * @param {Object} options.position - Where to draw the Text
 * @param {number} options.position.x - X position relative to the center of the text
 * @param {number} options.position.y - Y position relative to the baseline of the text
 * @param {number} options.font_size - Size of the font, clamped to [12, 50]
 * @param {boolean} options.visible - Whether to draw the value at all
 */
export function metric_value_component(selection, options) {
    const font_size = clamp(options.font_size, [12, 50]);
    const data = options.visible ? [options.value] : [];

    let link = selection
        .selectAll("a.single_value")
        .data(data)
        .join("a")
        .classed("single_value", true)
        .attr("xlink:href", d => d.url || null);
    let text = link
        .selectAll("text")
        .data(d => [d])
        .join("text")
        .text(d => d.value)
        .attr("x", options.position.x)
        .attr("y", options.position.y)
        .attr("text-anchor", "middle")
        .attr("dominant-baseline", "central")
        .style("font-weight", "bold")
        .style("font-size", font_size + "px");

    let unit = text
        .selectAll("tspan")
        .data(d => [d])
        .join("tspan")
        .style("font-size", font_size / 2 + "px")
        .style("font-weight", "lighter")
        .text(d => d.unit);
    if (options.value.unit !== "%") {
        unit.attr("dx", font_size / 6 + "px").attr("dy", font_size / 8 + "px");
    }
}

/**
 * Function to provide default options for metric_value_component
 * @param {Object} size - Size of container to draw to
 * @param {number} size.width - Width of container
 * @param {number} size.height - Height of container
 * @param {Object} options - Configuration the values
 * @param {number} options.font_size - Overwrite auto font_size (calculated by size)
 * @param {boolean} options.visible - Overwrite auto visible (true)
 * @param {Object} options.position - Overwrite a position value
 * @param {number} options.position.y - Overwrite y position
 *
 * The function provides the following options in the result:
 * * position
 * * font_size
 * * visible
 */
export function metric_value_component_options_big_centered_text(
    size,
    options
) {
    if (options == undefined) {
        options = {};
    }

    let font_size = Math.min(size.width / 5, (size.height * 2) / 3);
    if (options.font_size !== undefined) {
        font_size = options.font_size;
    }

    let visible = true;
    if (options.visible !== undefined) {
        visible = options.visible;
    }

    const position_x = size.width / 2;

    let position_y = size.height / 2;
    if (options.position !== undefined && options.position.y !== undefined) {
        position_y = options.position.y;
    }

    return {
        position: {
            x: position_x,
            y: position_y,
        },
        font_size: font_size,
        visible: visible,
    };
}
