import * as d3 from "d3";

// The FigureRegistry holds all figure class templates
class FigureRegistry{
    constructor() {
        this._figures = {};
    }

    register(figure_class) {
        this._figures[figure_class.ident()] = figure_class;
    }

    get_figure(ident) {
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
    constructor(scheduled_function, update_interval) {
        this._scheduled_function = scheduled_function;
        this._update_interval = update_interval;
        this._enabled = false;
        this._last_update = 0;
        this._suspend_updates_until = 0;
        setInterval(()=>this._schedule(), 1000);
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
        this._suspend_updates_until  = Math.floor(new Date().getTime()/1000) + seconds;
    }

    update_if_older_than(seconds) {
        let now = Math.floor(new Date().getTime()/1000);
        if (now > this._last_update + seconds) {
            this._scheduled_function();
            let now = Math.floor(new Date().getTime()/1000);
            this._last_update = now;
        }
    }

    force_update() {
        this._scheduled_function();
        let now = Math.floor(new Date().getTime()/1000);
        this._last_update = now;
    }

    _schedule() {
        if (!this._enabled)
            return;
        let now = Math.floor(new Date().getTime()/1000);
        if (now < this._suspend_updates_until)
            return;
        // This function is called every second. Add 0.5 seconds grace time
        // for function which expect an update every second
        if (now + 0.5 > (this._last_update + this._update_interval)) {
            this._last_update = now;
            this._scheduled_function();
        }
    }
}


// Allows scheduling of multiple url calls
// Registered hooks will be call on receiving data
export class MultiDataFetcher {
    constructor() {
        this.reset();
        this.scheduler = new Scheduler(()=>this._schedule_operations(), 1);
    }

    reset() {
        // Urls to call
        // {"url": {"body": {"interval": 10}}
        this._fetch_operations = {};

        // Hooks to call when receiving data
        // {"url": {"body": [funcA, funcB]}}
        this._fetch_hooks = {};
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

        this._fetch_operations[post_url][post_body] = this._default_operation_options(interval);
    }

    _default_operation_options(interval) {
        return {
            active: true,      // May be used to temporarily disable the operation
            last_update: 0,    // Last time the fetch operation was sent (not received)
            fetch_in_progress: false,
            interval: interval
        };
    }

    _schedule_operations() {
        for (let url_id in this._fetch_operations) {
            for (let body_id in this._fetch_operations[url_id]) {
                this._process_operation(url_id, body_id);
            }
        }
    }

    _process_operation(post_url, post_body) {
        let now = Math.floor(new Date().getTime()/1000);
        let operation = this._fetch_operations[post_url][post_body];
        if (!operation.active || operation.fetch_in_progress)
            return;

        if (operation.last_update + operation.interval > now)
            return;

        operation.last_update = now;
        operation.fetch_in_progress = true;
        this._fetch(post_url, post_body);
    }


    _fetch(post_url, post_body) {
        // TODO: improve error handling, d3js supports promises
        d3.json(encodeURI(post_url),
            {
                credentials: "include",
                method: "POST",
                body: post_body,
                headers: {
                    "Content-type": "application/x-www-form-urlencoded"
                }
            }
        ).then(response=>this._fetch_callback(post_url, post_body, response));
    }

    _fetch_callback(post_url, post_body, api_response) {
        let response = api_response.result;
        let data = response.data;

        let now = Math.floor(new Date().getTime()/1000);

        if (this._fetch_operations[post_url] == undefined ||
            this._fetch_operations[post_url][post_body] == undefined)
            return;
        this._fetch_operations[post_url][post_body].last_update  = now;
        this._fetch_operations[post_url][post_body].fetch_in_progress = false;

        // Inform subscribers
        this._fetch_hooks[post_url][post_body].forEach(subscriber_func=>{
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
export class FigureBase {
    static ident() {
        return "figure_base_class";
    }

    constructor(div_selector, fixed_size=null) {
        this._div_selector = div_selector;                          // The main container
        this._div_selection = d3.select(this._div_selector);  // The d3-seletion of the main container

        if (fixed_size !== null)
            this._fixed_size = fixed_size;
        else
            this._fixed_size = null;

        this._div_selection
            .classed(this.constructor.ident(), true)
            .classed("cmk_figure", true);

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
        this._post_render_hooks= [];

        this.scheduler = new Scheduler(()=>this._fetch_data(), this.get_update_interval());

        // Post url and body for fetching the graph data
        this._post_url = "";
        this._post_body = "";
    }

    initialize(with_debugging) {
        if (with_debugging)
            this._add_scheduler_debugging();
        this.show_loading_image();
    }

    resize() {}

    show_loading_image() {
        this._div_selection.selectAll("div.loading_img").data([null]).enter()
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

    set_post_url_and_body(url, body="") {
        this._post_url = url;
        this._post_body = body;
    }

    get_post_settings() {
        return {
            url: this._post_url,
            body: this._post_body
        };
    }

    _fetch_data() {
        // API Spec is WIP
        // {
        //
        // }
        let post_settings = this.get_post_settings();

        if (!post_settings.url)
            return;

        this._fetch_start = Math.floor(new Date().getTime()/1000);
        d3.json(encodeURI(post_settings.url),
            {
                credentials: "include",
                method: "POST",
                body: post_settings.body,
                headers: {
                    "Content-type": "application/x-www-form-urlencoded"
                }
            }
        ).then(json_data=>this._process_api_response(json_data)).catch(
            ()=> {
                this._show_error_info("Error fetching data");
                this.remove_loading_image();
            });
    }

    _process_api_response(api_response) {
        // Current api data format
        // {"result_code": 0, "result": {
        //      "data": {},    // data relevant for rendering
        // }}
        if (api_response.result_code != 0) {
            this._show_error_info(api_response.result);
            return;
        }
        this._clear_error_info();

        let data = api_response.result.data;
        this.process_data(data);
        this._fetch_data_latency = +(new Date() - this._fetch_start) / 1000;
    }

    process_data(data) {
        this._data_pre_processor_hooks.forEach(pre_processor_func=>{
            data = pre_processor_func(data);
        });
        this._call_pre_render_hooks(data);
        this.update_data(data);
        this.remove_loading_image();
        this.update_gui(data);
        this._call_post_render_hooks(data);
    }

    _show_error_info(error_info) {
        let error = this._div_selection.selectAll("label#figure_error").data([null]);
        error = error.enter().append("label")
            .attr("id", "figure_error")
            .merge(error);
        error.text(error_info);
    }

    _clear_error_info() {
        this._div_selection.select("#figure_error").remove();
    }

    _call_pre_render_hooks(data) {
        this._pre_render_hooks.forEach(hook=>hook(data));
    }

    _call_post_render_hooks(data) {
        this._post_render_hooks.forEach(hook=>hook(data));
    }

    // Triggers data update mechanics in a figure, e.g. store some data from response
    update_data() {}

    // Triggers gui update mechanics in a figure, e.g. rendering
    update_gui() {}

    // Adds some basic debug features for the scheduler
    _add_scheduler_debugging() {
        let debugging = this._div_selection.append("div");
        // Stop button
        debugging.append("input")
            .attr("type", "button")
            .attr("value", "Stop")
            .on("click", ()=>this.scheduler.disable());
        // Start button
        debugging.append("input")
            .attr("type", "button")
            .attr("value", "Start")
            .on("click", ()=>this.scheduler.enable());
        // Suspend 5 seconds
        debugging.append("input")
            .attr("type", "button")
            .attr("value", "Suspend 5 seconds")
            .on("click", ()=>this.scheduler.suspend_for(5));
        // Force update
        debugging.append("input")
            .attr("type", "button")
            .attr("value", "Force")
            .on("click", ()=>this.scheduler.force_update());
    }
}

// Base class for dc.js based figures (using crossfilter)
export class DCFigureBase extends FigureBase {
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
    constructor(tooltip_selection) {
        this._tooltip = tooltip_selection;
        this._tooltip.style("opacity", 0)
            .style("position", "absolute")
            .classed("tooltip", true);
    }

    add_support(node) {
        let element = d3.select(node);
        element.on("mouseover", ()=>this._mouseover())
            .on("mouseleave", ()=>this._mouseleave())
            .on("mousemove", ()=>this._mousemove());
    }

    _mouseover(){
        let node_data = d3.select(d3.event.target).datum();
        if (node_data == undefined || node_data.tooltip == undefined)
            return;

        this._tooltip.style("opacity", 1);
    }

    _mousemove(){
        let node_data = d3.select(d3.event.target).datum();
        if (node_data == undefined || node_data.tooltip == undefined)
            return;
        let parentWidth = this._tooltip.node().parentNode.clientWidth;
        this._tooltip.html(node_data.tooltip)
            .style("left", ()=>{
                if (parentWidth - d3.event.layerX > Math.max(.2 * parentWidth, 165)) {
                    return (d3.event.layerX + 20) + "px";
                }
                return "auto";
            })
            .style("right", ()=>{
                if (parentWidth - d3.event.layerX <= Math.max(.2 * parentWidth, 165)) {
                    return (parentWidth - d3.event.layerX + 20) + "px";
                }
                return "auto";
            })
            .style("top", d3.event.layerY - 50 + "px");
    }

    _mouseleave(){
        this._tooltip.style("opacity", 0);
    }
}
