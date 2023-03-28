// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

import * as utils from "utils";
import * as ajax from "ajax";
import * as d3 from "d3";
import * as valuespecs from "valuespecs";

export function toggle_subtree(oImg, lazy) {
    if (oImg.tagName == "SPAN") {
        // clicked on title,
        oImg = oImg.previousElementSibling;
    }
    const oSubtree = oImg.parentNode.getElementsByTagName("ul")[0];
    let url = "bi_save_treestate.py?path=" + encodeURIComponent(oSubtree.id);
    let do_open;

    if (utils.has_class(oImg, "closed")) {
        utils.change_class(oSubtree, "closed", "open");
        utils.toggle_folding(oImg, true);

        url += "&state=open";
        do_open = true;
    } else {
        utils.change_class(oSubtree, "open", "closed");
        utils.toggle_folding(oImg, false);

        url += "&state=closed";
        do_open = false;
    }

    if (lazy && do_open)
        ajax.call_ajax(url, {
            response_handler: bi_update_tree,
            handler_data: oImg,
        });
    else ajax.call_ajax(url);
}

function bi_update_tree(container) {
    // Deactivate clicking - the update can last a couple
    // of seconds. In that time we must inhibit further clicking.
    container.onclick = null;

    // First find enclosding <div class=bi_tree_container>
    let bi_container = container;
    while (
        bi_container &&
        !utils.has_class(bi_container, "bi_tree_container")
    ) {
        bi_container = bi_container.parentNode;
    }
    ajax.call_ajax("bi_render_tree.py", {
        method: "POST",
        post_data: bi_container.id,
        response_handler: bi_update_tree_response,
        handler_data: bi_container,
    });
}

function bi_update_tree_response(bi_container, code) {
    bi_container.innerHTML = code;
    utils.execute_javascript_by_object(bi_container);
}

export function toggle_box(container, lazy) {
    let url = "bi_save_treestate.py?path=" + encodeURIComponent(container.id);
    let do_open;

    if (utils.has_class(container, "open")) {
        if (lazy) return; // do not close in lazy mode
        utils.change_class(container, "open", "closed");
        url += "&state=closed";
        do_open = false;
    } else {
        utils.change_class(container, "closed", "open");
        url += "&state=open";
        do_open = true;
    }

    // TODO: Make asynchronous
    if (lazy && do_open)
        ajax.call_ajax(url, {
            response_handler: bi_update_tree,
            handler_data: container,
        });
    else {
        ajax.call_ajax(url);
        // find child nodes that belong to this node and
        // control visibility of those. Note: the BI child nodes
        // are *no* child nodes in HTML but siblings!
        let found = 0;
        for (const i in container.parentNode.children) {
            const onode = container.parentNode.children[i];

            if (onode == container) found = 1;
            else if (found) {
                if (do_open) onode.style.display = "inline-block";
                else onode.style.display = "none";
                return;
            }
        }
    }
}

export function toggle_assumption(link, site, host, service) {
    const img = link.getElementsByTagName("img")[0];

    // get current state
    const path_parts = img.src.split("/");
    const file_part = path_parts.pop();
    let current = file_part.replace(/icon_assume_/, "").replace(/.png/, "");

    if (current == "none")
        // Assume WARN when nothing assumed yet
        current = "1";
    else if (current == "3" || (service == "" && current == "2"))
        // Assume OK when unknown assumed (or when critical assumed for host)
        current = "0";
    else if (current == "0")
        // Disable assumption when ok assumed
        current = "none";
    // In all other cases increase the assumption
    else current = parseInt(current) + 1;

    let url =
        "bi_set_assumption.py?site=" +
        encodeURIComponent(site) +
        "&host=" +
        encodeURIComponent(host);
    if (service) {
        url += "&service=" + encodeURIComponent(service);
    }
    url += "&state=" + current;
    img.src = path_parts.join("/") + "/icon_assume_" + current + ".png";
    ajax.call_ajax(url);
}

export function update_argument_hints() {
    d3.selectAll<HTMLSelectElement, unknown>(
        "select[onchange='cmk.bi.update_argument_hints();']"
    ).each((d, idx, nodes) => {
        const node = d3.select(nodes[idx]);
        const rule_arguments =
            window["bi_rule_argument_lookup"][node.property("value")];
        const rule_body = node.select(function () {
            // @ts-ignore
            return this.closest("tbody");
        });
        const required_inputs = rule_arguments.length;

        // Create nodes
        let newNodes = rule_body
            .selectAll<HTMLDivElement, unknown>("div.listofstrings")
            .selectAll<HTMLInputElement, unknown>("input.text")
            .nodes();
        while (required_inputs >= newNodes.length) {
            valuespecs.list_of_strings_extend(
                nodes[nodes.length - 1],
                false,
                ""
            );
            newNodes = rule_body
                .selectAll<HTMLDivElement, unknown>("div.listofstrings")
                .selectAll<HTMLInputElement, unknown>("input.text")
                .nodes();
        }

        // Update placeholder
        const input_nodes = rule_body
            .selectAll("div.listofstrings")
            .selectAll("input.text");
        input_nodes.attr("placeholder", "");
        input_nodes.each((d, idx, nodes) => {
            if (idx >= rule_arguments.length) return;
            const argument_input = d3.select(nodes[idx]);
            argument_input.attr("placeholder", rule_arguments[idx]);
        });
    });
}

export class BIPreview {
    _root_node;
    _preview_active: boolean;
    _varprefix: string;
    _last_body: string;
    _update_interval: number;
    _update_active: boolean;
    constructor(root_node, varprefix) {
        this._root_node = d3.select(root_node);
        this._preview_active = false;
        this._varprefix = varprefix;
        this._last_body = "";
        this._update_interval = 500;
        this._update_active = false;
        this._create_search_preview();
        setInterval(() => this._check_update(), this._update_interval);
    }

    // eslint-disable-next-line @typescript-eslint/no-empty-function
    _create_search_preview() {}

    // eslint-disable-next-line @typescript-eslint/no-empty-function
    _check_update() {}

    _get_update_url() {
        return encodeURI("ajax_bi_node_preview.py");
    }

    _update_previews(_json_data?) {
        this._update_active = false;
        this._check_update();
    }

    _trigger_update_if_required(params) {
        const body = this._dict_to_url(params);
        if (this._last_body == body) {
            return;
        }

        if (this._update_active) return;

        d3.json(this._get_update_url(), {
            credentials: "include",
            method: "POST",
            body: body,
            headers: {
                "Content-type": "application/x-www-form-urlencoded",
            },
        }).then(json_data => this._update_previews(json_data));
        this._update_active = true;
        this._last_body = body;
    }

    _create_node_preview_div(selection) {
        selection.append("div").classed("node_preview", true);
    }

    _update_preview_of_node(data_rows, title, node_preview_div) {
        const headers = Object.keys(data_rows[0]);
        node_preview_div.selectAll("*").remove();
        node_preview_div.append("h3").text(title);
        const node_preview_table = node_preview_div.append("table");

        // Header row
        node_preview_table
            .append("thead")
            .selectAll("tr")
            .data([headers])
            .join("tr")
            .selectAll("th")
            .data(d => d)
            .join("th")
            .style("text-align", "left")
            .text(d => d);

        // Content row(s)
        node_preview_table
            .append("tbody")
            .selectAll("tr")
            .data(data_rows)
            .join("tr")
            .selectAll("td")
            .data(d => {
                const cells: string[] = [];
                headers.forEach(header => {
                    cells.push(d[header]);
                });
                return cells;
            })
            .join(enter =>
                enter
                    .append("td")
                    .style("padding", "5px")
                    .style("text-align", "left")
            )
            .text(d => d);
    }

    _determine_params() {
        const inputs = this._root_node.selectAll("input,select");
        const params = {varprefix: this._varprefix};
        inputs.each((d, idx, nodes) => {
            const input = nodes[idx];
            params[input.name] = input.value;
        });
        return params;
    }

    _dict_to_url(dict) {
        const url_tokens: string[] = [];
        for (const p in dict) {
            url_tokens.push(
                encodeURIComponent(p) + "=" + encodeURIComponent(dict[p])
            );
        }
        return url_tokens.join("&");
    }
}

export class BIRulePreview extends BIPreview {
    _check_update() {
        BIPreview.prototype._check_update.call(this);
        const display = this._preview_active ? null : "none";
        // @ts-ignore
        d3.selectAll("span.title").style("display", display);
        // @ts-ignore
        d3.selectAll("span.arguments").style("display", display);

        if (!this._preview_active) {
            setTimeout(() => this._check_update(), this._update_interval);
            return;
        }

        const params = this._determine_params();
        params["example_arguments"] = JSON.stringify(
            this._get_example_arguments()
        );
        this._trigger_update_if_required(params);
    }

    _get_update_url() {
        return encodeURI("ajax_bi_rule_preview.py");
    }

    _get_example_arguments() {
        const example_arguments: string[] = [];
        this._root_node
            .select("span.arguments")
            .selectAll("input")
            .each((d, idx, nodes) => {
                example_arguments.push(nodes[idx].value);
            });
        return example_arguments;
    }

    _update_previews(json_data) {
        this._update_simulated_parameters(json_data.result.params);
        const nodes = d3
            .selectAll("#rule_p_nodes_container > tr")
            .data(json_data.result.data);

        const node_previews = nodes
            .select(".vlof_content")
            .selectAll("div.node_preview")
            .data(d => [d])
            // @ts-ignore
            .join(enter => {
                this._create_node_preview_div(enter);
            });

        node_previews.each((d, idx, nodes) => {
            this._update_preview_of_node(
                d,
                json_data.result.title,
                d3.select(nodes[idx])
            );
        });
        BIPreview.prototype._update_previews.call(this, json_data);
    }

    _update_simulated_parameters(params) {
        const preview_toggle = this._root_node.select("div.preview_toggle");
        preview_toggle
            .select("span.title")
            .selectAll("label")
            .data([null])
            .join("label")
            .text("Example arguments for this rule");
        preview_toggle
            .select("span.arguments")
            .selectAll("input")
            .data(params)
            .join("input")
            .attr("placeholder", d => d);
    }

    _create_search_preview() {
        const preview_toggle = this._root_node
            .select("#rule_d_nodes")
            .insert("div", "div");
        preview_toggle.classed("preview_toggle", true);
        preview_toggle.style("text-align", "right");
        preview_toggle.append("span").classed("title", true);
        preview_toggle.append("span").classed("arguments", true);
        preview_toggle
            .append("span")
            .append("input")
            .attr("type", "button")
            .attr("value", "Toggle Search Preview")
            .classed("button", true)
            .on("click", () => {
                this._preview_active = !this._preview_active;
                d3.selectAll("div.node_preview").style(
                    "display",
                    this._preview_active ? "block" : "none"
                );
                this._check_update();
            });
    }
}

export class BIAggregationPreview extends BIPreview {
    _check_update() {
        BIPreview.prototype._check_update.call(this);
        if (!this._preview_active) {
            return;
        }

        const params = this._determine_params();
        this._trigger_update_if_required(params);
    }

    _get_update_url() {
        return encodeURI("ajax_bi_aggregation_preview.py");
    }

    _get_preview_div(selection) {
        let node_preview_div = selection.select("div.node_preview");
        if (node_preview_div.empty()) {
            node_preview_div = selection
                .append("div")
                .classed("node_preview", true);
        }
        return node_preview_div;
    }

    _update_previews(json_data) {
        const node_preview_div = this._get_preview_div(
            d3.select("div#aggr_d_node")
        );
        this._update_preview_of_node(
            json_data.result.data[0],
            json_data.result.title,
            node_preview_div
        );
        BIPreview.prototype._update_previews.call(this, json_data);
    }

    _create_search_preview() {
        this._root_node
            .select("#aggr_d_node")
            .insert("div", "select")
            .style("text-align", "right")
            .append("input")
            .attr("type", "button")
            .classed("button", true)
            .attr("value", "Toggle Search Preview")
            .on("click", () => {
                this._preview_active = !this._preview_active;
                d3.selectAll("div.node_preview").style(
                    "display",
                    this._preview_active ? "block" : "none"
                );
                this._check_update();
            });
    }
}
