// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

import * as d3 from "d3";
import {StyleMatcherConditions} from "nodevis/layout_utils";
import {
    BoundingRect,
    Coords,
    d3SelectionDiv,
    NodeChunk,
    NodevisNode,
} from "nodevis/type_defs";

// TODO: remove or fix logging
export function log(level, ...args) {
    if (level < 4) console.log(...Array.from(args));
}

export class DefaultTransition {
    static duration() {
        return 500;
    }

    static add_transition(selection) {
        return selection.transition().duration(DefaultTransition.duration());
    }
}

// Stores node visualization classes
export type TypeWithName = {
    class_name: string;
};

export class AbstractClassRegistry<Type> {
    _classes: {[name: string]: Type} = {};

    register(class_template: TypeWithName) {
        // @ts-ignore
        this._classes[class_template.class_name] = class_template as Type;
    }

    get_class(class_name: string): Type {
        return this._classes[class_name] as unknown as Type;
    }

    get_classes(): {[name: string]: Type} {
        return this._classes;
    }
}

export class NodeMatcher {
    _chunk_list: NodeChunk[];

    constructor(chunk_list: NodeChunk[]) {
        this._chunk_list = chunk_list;
    }

    find_node(matcher: StyleMatcherConditions): NodevisNode | null {
        const nodes_to_check: NodevisNode[] = this._get_all_nodes();

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

    _is_bi_rule_matcher(matcher): boolean {
        if (matcher.rule_name) return true;
        if (matcher.rule_id) return true;
        return false;
    }

    // Duplicate to viewport.ts:get_all_nodes
    _get_all_nodes(): NodevisNode[] {
        let all_nodes: NodevisNode[] = [];
        this._chunk_list.forEach(chunk => {
            all_nodes = all_nodes.concat(chunk.nodes);
        });
        return all_nodes;
    }

    _match_by_bi_rule(matcher, node: NodevisNode): boolean {
        // List matches
        const list_elements = ["aggr_path_name", "aggr_path_id"];
        for (const idx in list_elements) {
            const match_type = list_elements[idx];
            if (!matcher[match_type]) continue;
            if (matcher[match_type].disabled) continue;
            if (
                JSON.stringify(matcher[match_type].value) !=
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

        if (
            matcher.rule_name &&
            !matcher.rule_name.disabled &&
            node.data.name != matcher.rule_name.value
        )
            return false;

        return true;
    }

    _match_by_generic_attr(matcher, node: NodevisNode): boolean {
        const match_types = ["hostname", "service", "id"];
        for (const idx in match_types) {
            const match_type = match_types[idx];
            if (matcher[match_type] && !matcher[match_type].disabled) {
                if (node.data[match_type] != matcher[match_type].value)
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
    vertices,
    rotation_in_rad
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
        this._root_node = d3.select(root_node_selector);
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
            list_entries.push(hostname);
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
            .forEach(hostname => {
                if (hostname) current_hosts.add(hostname);
            });
        return current_hosts;
    }

    set_host_regex_filter(host_regex) {
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
            "input,select"
        );
        const params = {};
        inputs.each((d, idx, nodes) => {
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
    _search_button: d3.Selection<HTMLInputElement, unknown, any, unknown>;
    _update_handler: () => {return};
    _last_body = "";
    _sent_last_body = "";
    _check_interval = 300; // Check every 300ms
    _stabilize_duration = 300; // Trigger update if there are no additional changes for duration
    _start_update_at = 0;
    _update_active = false;
    _enabled = false;
    _interval_id = 0;
    constructor(root_node, update_handler) {
        this._root_node = d3.select(root_node);
        this._search_button =
            this._root_node.select<HTMLInputElement>("input#_apply");
        this._update_handler = update_handler;
    }

    enable(): void {
        this._enabled = true;
        clearInterval(this._interval_id);
        this._search_button.property("value", "Live search");
        this._search_button.style("pointer-events", "none");
        this._initialize_last_body();
        // @ts-ignore
        this._interval_id = setInterval(
            () => this._check_update(),
            this._check_interval
        );
    }

    disable(): void {
        this._enabled = false;
        clearInterval(this._interval_id);
        this._search_button.property("value", "Apply");
        this._search_button.style("pointer-events", "all");
    }

    _update_pending(_eta): void {
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
        if (this._enabled == false) return;
        this._trigger_update_if_required(this.get_filter_params());
    }

    _trigger_update_if_required(params): void {
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

    get_filter_params(): {[name: string]: string} {
        const inputs = this._root_node
            .select("div.simplebar-content")
            .selectAll<HTMLInputElement, null>("input,select");
        const params = {live_search: "1"};
        inputs.each((d, idx, nodes) => {
            const input = nodes[idx];
            if (input.type == "checkbox")
                params[input.name] = input.checked ? "1" : "";
            else params[input.name] = input.value;
        });
        return params;
    }

    _dict_to_url(dict): string {
        const str: string[] = [];
        for (const p in dict) {
            str.push(encodeURIComponent(p) + "=" + encodeURIComponent(dict[p]));
        }
        return str.join("&");
    }
}
