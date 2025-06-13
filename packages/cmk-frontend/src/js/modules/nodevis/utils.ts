/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import type {BaseType, Selection} from "d3";
import {select} from "d3";

import type {AbstractNodeVisConstructor} from "./layer_utils";
import type {StyleMatcherConditions} from "./layout_utils";
import {get} from "./texts";
import type {
    BoundingRect,
    Coords,
    d3Selection,
    d3SelectionDiv,
    InputRangeOptions,
    NodeConfig,
    NodevisNode,
    Quickinfo,
    Tooltip,
} from "./type_defs";
import type {Viewport} from "./viewport";

// TODO: remove or fix logging
export function log(level: number, ...args: any[]) {
    if (level < 4) console.log(...Array.from(args));
}

export class DefaultTransition {
    static duration() {
        return 500;
    }

    static add_transition<GType extends BaseType, Data>(
        selection: Selection<GType, Data, BaseType, unknown>,
    ) {
        return selection.transition().duration(DefaultTransition.duration());
    }
}

// Stores node visualization classes
export type TypeWithName = {
    class_name: () => string;
};

export class AbstractClassRegistry<Type extends TypeWithName> {
    _classes: {[name: string]: AbstractNodeVisConstructor<Type>} = {};

    register(class_template: AbstractNodeVisConstructor<Type>) {
        this._classes[class_template.prototype.class_name()] = class_template;
    }

    get_class(class_name: string): AbstractNodeVisConstructor<Type> {
        return this._classes[class_name];
    }

    get_classes(): {[name: string]: AbstractNodeVisConstructor<Type>} {
        return this._classes;
    }
}

export class NodeMatcher {
    _node_config: NodeConfig;

    constructor(node_config: NodeConfig) {
        this._node_config = node_config;
    }

    find_node(matcher: StyleMatcherConditions): NodevisNode | null {
        const nodes_to_check: NodevisNode[] =
            this._node_config.hierarchy.descendants();

        if (this._is_bi_rule_matcher(matcher)) {
            for (const idx in nodes_to_check) {
                const node = nodes_to_check[idx];
                if (node.data.node_type != "bi_aggregator") continue;
                if (this._match_by_bi_rule(matcher, node)) return node;
            }
        }

        for (const idx in nodes_to_check) {
            const node = nodes_to_check[idx];
            if (node.data.node_type == "bi_aggregator") continue;
            if (this._match_by_generic_attr(matcher, node)) return node;
        }
        return null;
    }

    _is_bi_rule_matcher(matcher: StyleMatcherConditions): boolean {
        if (matcher.rule_name) return true;
        if (matcher.rule_id) return true;
        return false;
    }

    _match_by_bi_rule(
        matcher: StyleMatcherConditions,
        node: NodevisNode,
    ): boolean {
        // List matches
        const list_elements = ["aggr_path_name", "aggr_path_id"] as const;
        for (const idx in list_elements) {
            const match_type = list_elements[idx];
            if (!matcher[match_type]) continue;
            if (matcher[match_type]!.disabled) continue;
            if (
                JSON.stringify(matcher[match_type]!.value) !=
                JSON.stringify(node.data[match_type])
            )
                return false;
        }

        // Complex matches for bi aggregators
        if (
            matcher.rule_id &&
            !matcher.rule_id.disabled &&
            node.data.rule_id.rule != matcher.rule_id.value
        )
            return false;

        return !(
            matcher.rule_name &&
            !matcher.rule_name.disabled &&
            node.data.name != matcher.rule_name.value
        );
    }

    _match_by_generic_attr(
        matcher: StyleMatcherConditions,
        node: NodevisNode,
    ): boolean {
        const match_type = "id";
        if (matcher[match_type] && !matcher[match_type]!.disabled) {
            if (node.data[match_type] != matcher[match_type]!.value)
                return false;
        }

        const match_types = ["hostname", "service"] as const;
        for (const idx in match_types) {
            const match_type = match_types[idx];
            if (matcher[match_type] && !matcher[match_type]!.disabled) {
                const type_specific = node.data.type_specific;
                if (!type_specific) return false;
                const core_info = node.data.type_specific.core;
                if (
                    !core_info ||
                    core_info[match_type] != matcher[match_type]!.value
                )
                    return false;
            }
        }
        return true;
    }
}

export function get_bounding_rect(list_of_coords: Coords[]): BoundingRect {
    const rect = {
        x_min: 10000,
        x_max: -10000,
        y_min: 10000,
        y_max: -10000,
        width: 10000,
        height: 10000,
    };

    list_of_coords.forEach(coord => {
        rect.x_min = Math.min(coord.x, rect.x_min);
        rect.y_min = Math.min(coord.y, rect.y_min);
        rect.x_max = Math.max(coord.x, rect.x_max);
        rect.y_max = Math.max(coord.y, rect.y_max);
    });
    rect.width = rect.x_max - rect.x_min;
    rect.height = rect.y_max - rect.y_min;
    return rect;
}

export function get_bounding_rect_of_rotated_vertices(
    vertices: Coords[],
    rotation_in_rad: number,
): BoundingRect {
    // TODO: check this
    // Vertices with less than 3 elements will fail
    if (vertices.length < 3)
        return {
            x_min: vertices[0].x,
            x_max: vertices[0].x + 10,
            y_min: vertices[0].y,
            y_max: vertices[0].y + 10,
            width: 10,
            height: 10,
        };

    const cos_x = Math.cos(rotation_in_rad);
    const sin_x = Math.sin(rotation_in_rad);
    const rotated_vertices: {x: number; y: number}[] = [];
    vertices.forEach(coords => {
        rotated_vertices.push({
            x: cos_x * coords.x + sin_x * coords.y,
            y: cos_x * coords.y + sin_x * coords.x,
        });
    });
    return get_bounding_rect(rotated_vertices);
}

export function update_browser_url(updated_params: {[name: string]: string}) {
    // @ts-ignore
    const current_url = new URL(window.location);
    for (const [key, value] of Object.entries(updated_params)) {
        current_url.searchParams.set(key, value);
    }
    window.history.replaceState({}, "", current_url.toString());
}

export class SearchFilters {
    _root_node: d3SelectionDiv;
    constructor(root_node_selector: string | null = null) {
        if (root_node_selector == null) root_node_selector = "#form_filter";
        this._root_node = select(root_node_selector);
    }

    add_hosts_to_host_regex(add_hosts: Set<string>) {
        this._get_current_host_regex_hosts().forEach(hostname => {
            add_hosts.add(hostname);
        });
        this.set_host_regex_filter(this._build_regex_from_set(add_hosts));
    }

    remove_hosts_from_host_regex(remove_hosts: Set<string>) {
        const current_hosts = this._get_current_host_regex_hosts();
        remove_hosts.forEach(hostname => {
            current_hosts.delete(hostname);
        });
        this.set_host_regex_filter(this._build_regex_from_set(current_hosts));
    }

    _build_regex_from_set(entries: Set<string>): string {
        const list_entries: string[] = [];
        entries.forEach(hostname => {
            list_entries.push(hostname + "$");
        });

        if (list_entries.length > 1) return "(" + list_entries.join("|") + ")";
        else if (list_entries.length == 1) return list_entries[0];
        else return "";
    }

    _get_current_host_regex_hosts(): Set<string> {
        const params = this.get_filter_params();
        const current_hosts: Set<string> = new Set();
        const filter_host_regex = params["host_regex"];
        filter_host_regex
            .replace(/^\(+/, "")
            .replace(/\)+$/, "")
            .split("|")
            .forEach((hostname?: string) => {
                if (hostname) current_hosts.add(hostname.replace(/\$+$/g, ""));
            });
        return current_hosts;
    }

    set_host_regex_filter(host_regex: string) {
        const host_regex_filter =
            this._root_node.select<HTMLSelectElement>("#host_regex");
        host_regex_filter
            .insert("option", "option")
            .attr("value", host_regex)
            .text(host_regex);
        const node = host_regex_filter.node();
        if (node == null) return;
        node.selectedIndex = 0;
        this._root_node
            .select("span#select2-host_regex-container")
            .text(host_regex);
        update_browser_url({host_regex: host_regex});
    }
    get_filter_params() {
        const inputs = this._root_node.selectAll<HTMLInputElement, null>(
            "input,select",
        );
        const params: Record<string, string> = {};
        inputs.each((_d, idx, nodes) => {
            const input = nodes[idx];
            if (input.type == "checkbox")
                params[input.name] = input.checked ? "1" : "";
            else params[input.name] = input.value;
        });
        params["filled_in"] = "filter";
        return params;
    }
}

export class LiveSearch {
    _root_node: d3SelectionDiv;
    _search_button: Selection<HTMLInputElement, null, any, unknown>;
    _update_handler: () => void;
    _last_body = "";
    _sent_last_body = "";
    _check_interval = 300; // Check every 300ms
    _stabilize_duration = 300; // Trigger update if there are no additional changes for duration
    _start_update_at = 0;
    _update_active = false;
    _enabled = false;
    _interval_id = 0;
    _original_submit_handler: string;
    constructor(root_node_selector: string, update_handler: () => void) {
        // root_node_selector should point to a <form> tag
        this._root_node = select(root_node_selector);
        this._search_button =
            this._root_node.select<HTMLInputElement>("input#_apply");
        this._update_handler = update_handler;
        this._original_submit_handler = this._root_node.attr("onsubmit");
    }

    enable(): void {
        this._enabled = true;
        clearInterval(this._interval_id);
        this._root_node
            .select<HTMLInputElement>("input#_reset")
            .style("display", "none");
        this._search_button.property("value", get("live_search"));
        this._search_button.attr("title", get("live_search_help"));
        this._search_button.style("pointer-events", "hover");
        this._initialize_last_body();
        // @ts-ignore
        this._interval_id = setInterval(
            () => this._check_update(),
            this._check_interval,
        );
        this._root_node.attr("onsubmit", "return false");
    }

    disable(): void {
        this._enabled = false;
        clearInterval(this._interval_id);
        this._root_node
            .select<HTMLInputElement>("input#_reset")
            .style("display", null);
        this._search_button.property("value", "Apply");
        this._search_button.attr("title", null);
        this._search_button.style("pointer-events", "all");
        this._root_node.attr("onsubmit", this._original_submit_handler);
    }

    _update_pending(_eta: number): void {
        // May show an indicator for an upcoming update
        return;
        //this._search_button.property(
        //    "value",
        //    "Live search starts in" + eta.toPrecision(2) + "s"
        //);
    }

    _update_started(): void {
        this._update_active = true;
        this._search_button.property("value", "LS running..");
    }

    update_finished(): void {
        this._update_active = false;
        this._search_button.property("value", "Live search");
    }

    _initialize_last_body(): void {
        this._last_body = this._dict_to_url(this.get_filter_params());
        this._sent_last_body = this._last_body;
    }

    _check_update(): void {
        if (!this._enabled) return;
        this._trigger_update_if_required(this.get_filter_params());
    }

    _trigger_update_if_required(params: Record<string, string>): void {
        const body = this._dict_to_url(params);
        if (body == this._sent_last_body) return;

        if (body != this._last_body) {
            this._start_update_at = Date.now() + this._stabilize_duration;
            this._last_body = body;
        }

        if (Date.now() < this._start_update_at) {
            this._update_pending((this._start_update_at - Date.now()) / 1000);
            return;
        }

        if (this._update_active) return;
        this._sent_last_body = body;
        this._update_started();
        this._update_handler();
    }

    get_filter_params(): Record<string, string> {
        const inputs = this._root_node
            .select("div.simplebar-content")
            .selectAll<HTMLInputElement, null>("input,select");
        const params: Record<string, string> = {live_search: "1"};
        inputs.each((_d, idx, nodes) => {
            const input = nodes[idx];
            if (input.classList.contains("ignored_in_livesearch")) return;
            if (input.type == "checkbox")
                params[input.name] = input.checked ? "1" : "";
            else params[input.name] = input.value;
        });
        return params;
    }

    _dict_to_url(dict: Record<any, any>): string {
        const str: string[] = [];
        for (const p in dict) {
            str.push(encodeURIComponent(p) + "=" + encodeURIComponent(dict[p]));
        }
        return str.join("&");
    }
}

export function render_input_range(
    parent: d3Selection,
    range_options: InputRangeOptions,
    value: number,
    option_changed_callback: (
        option_id: string,
        new_value: number,
    ) => void = () => {},
) {
    parent
        .selectAll("td.text." + range_options.id)
        .data([null])
        .enter()
        .append("td")
        .classed("range_input text " + range_options.id, true)
        .append("nobr")
        .text(range_options.title);

    function clamp_value(new_value: any): number {
        new_value = isNaN(parseFloat(new_value))
            ? range_options.default_value
            : parseFloat(new_value);
        new_value = Math.min(
            Math.max(new_value, range_options.min),
            range_options.max,
        );
        return new_value;
    }

    parent
        .selectAll("td input.range_input.slider." + range_options.id)
        .data([null])
        .join(enter =>
            enter
                .append("td")
                .classed("range_input slider " + range_options.id, true)
                .append("input")
                .attr("id", range_options.id)
                .classed("range_input slider " + range_options.id, true)
                .attr("name", range_options.id)
                .attr("type", "range")
                .attr("step", range_options.step)
                .attr("min", range_options.min)
                .attr("max", range_options.max)
                .on("input", event => {
                    option_changed_callback(
                        range_options.id,
                        parseFloat(event.target.value),
                    );
                    render_input_range(
                        parent,
                        range_options,
                        event.target.value,
                        option_changed_callback,
                    );
                })
                .on("wheel", event => {
                    let new_value = parseFloat(event.target.value);
                    if (event.wheelDelta > 0) new_value += range_options.step;
                    else new_value -= range_options.step;
                    new_value = clamp_value(new_value);

                    option_changed_callback(range_options.id, new_value);
                    render_input_range(
                        parent,
                        range_options,
                        new_value,
                        option_changed_callback,
                    );
                }),
        )
        .property("value", value);

    parent
        .selectAll("td input.manual_input." + range_options.id)
        .data([null])
        .join(enter =>
            enter
                .append("td")
                .append("input")
                .classed(
                    "range_input manual_input ignored_in_livesearch " +
                        range_options.id,
                    true,
                )
                .on("change", event => {
                    event.stopPropagation();
                    event.preventDefault();
                    const new_value = clamp_value(event.target.value);
                    option_changed_callback(range_options.id, new_value);
                    render_input_range(
                        parent,
                        range_options,
                        new_value,
                        option_changed_callback,
                    );
                }),
        )
        .property("value", value);
}

export class RadioGroupOption {
    ident = "";
    name = "";
    constructor(ident: string, name: string) {
        this.ident = ident;
        this.name = name;
    }
}

export function render_radio_group(
    selection: d3SelectionDiv,
    group_title: string,
    group_ident: string,
    options: RadioGroupOption[],
    active_option: string,
    option_changed_callback: (new_option: string) => void,
): void {
    const div = selection
        .selectAll("div.radio_group")
        .data([null])
        .join("div")
        .classed("radio_group", true);

    div.selectAll("label.title")
        .data([group_title])
        .enter()
        .append("label")
        .classed("title", true)
        .text(d => d);

    const row = div
        .selectAll<HTMLTableElement, string>("table.radio_group tr")
        .data([group_ident], d => d)
        .join(enter =>
            enter.append("table").classed("radio_group", true).append("tr"),
        );

    const option_cells = row
        .selectAll<HTMLTableCellElement, RadioGroupOption>("td.option")
        .data(options)
        .join("td")
        .classed("option", true);

    option_cells
        .selectAll<HTMLInputElement, RadioGroupOption>("input")
        .data(d => [d])
        .join("input")
        .attr("name", group_ident)
        .attr("id", option => option.ident)
        .attr("type", "radio")
        .attr("value", option => option.ident)
        .attr("checked", option => {
            return option.ident == active_option ? true : null;
        })
        .on("change", (_event, option) =>
            option_changed_callback(option.ident),
        );

    option_cells
        .selectAll("label")
        .data(d => [d])
        .join("label")
        .classed("noselect", true)
        .text(option => option.name)
        .attr("for", option => option.ident);
}

export function render_save_delete(
    selection: d3SelectionDiv,
    buttons: [string, string, string, () => void][],
) {
    const div_save_delete = selection
        .selectAll<HTMLDivElement, null>("div#save_delete")
        .data([null])
        .join(enter => enter.append("div").attr("id", "save_delete"));
    div_save_delete
        .selectAll<HTMLInputElement, [string, string, () => void]>(
            "input.save_delete",
        )
        .data(buttons)
        .enter()
        .append("input")
        .attr("type", "button")
        .attr("title", d => (d[2] ? d[2] : null))
        .attr("class", d => d[1])
        .attr("value", d => d[0])
        .on("click", (_event, d) => {
            d[3]();
        });
}

export function bound_monitoring_host(node: NodevisNode): string | null {
    const type_specific = node.data.type_specific;
    if (!type_specific) return null;
    const core_info = type_specific.core;
    if (!core_info) return null;
    if (core_info.hostname && !core_info.service) return core_info.hostname;
    return null;
}

export function add_basic_quickinfo(
    into_selection: d3SelectionDiv,
    quickinfo: Quickinfo,
): void {
    const table = into_selection
        .selectAll<HTMLTableSectionElement, string>("body table tbody")
        .data([null])
        .join(enter =>
            enter
                .append("body")
                .append("table")
                .classed("data", true)
                .classed("single", true)
                .append("tbody"),
        );

    let even = "even";
    const rows = table.selectAll("tr").data(quickinfo).enter().append("tr");
    rows.each(function () {
        this.setAttribute("class", even.concat("0 data"));
        even = even == "even" ? "odd" : "even";
    });
    rows.append("td")
        .classed("left", true)
        .text(d => d.name);
    rows.append("td")
        .text(d => d.value)
        .each((d, idx, tds) => {
            const td = select(tds[idx]);
            if (d.css_styles)
                for (const [key, value] of Object.entries(d.css_styles)) {
                    td.style(key, value);
                }
        });
}

export function show_tooltip(
    event: {layerX: number; layerY: number},
    tooltip: Tooltip,
    viewport: Viewport,
) {
    const viewport_size = viewport.get_size();

    let info = "";
    if (tooltip.html) info = tooltip.html;
    if (tooltip.quickinfo) {
        const div = select<HTMLDivElement, null>(document.createElement("div"));
        add_basic_quickinfo(div, tooltip.quickinfo);
        info += div.html();
    }

    viewport
        .get_nodes_layer()
        .get_div_selection()
        .selectAll("label.link_info")
        .data(info ? [info] : [])
        .join(enter =>
            enter
                .append("label")
                .classed("link_info", true)
                .html(d => d)
                .style("position", "absolute"),
        )
        .style("left", event.layerX + 10 + "px")
        .style("bottom", viewport_size.height - event.layerY + 30 + "px");
}
