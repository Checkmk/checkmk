// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

import * as utils from "utils";
import * as ajax from "ajax";
import * as d3 from "d3";
import * as valuespecs from "valuespecs";

export function toggle_subtree(oImg, lazy)
{
    if (oImg.tagName == "SPAN") { // clicked on title,
        oImg = oImg.previousElementSibling;
    }
    var oSubtree = oImg.parentNode.getElementsByTagName("ul")[0];
    var url = "bi_save_treestate.py?path=" + encodeURIComponent(oSubtree.id);
    var do_open;

    if (utils.has_class(oImg, "closed")) {
        utils.change_class(oSubtree, "closed", "open");
        utils.toggle_folding(oImg, true);

        url += "&state=open";
        do_open = true;
    }
    else {
        utils.change_class(oSubtree, "open", "closed");
        utils.toggle_folding(oImg, false);

        url += "&state=closed";
        do_open = false;
    }

    if (lazy && do_open)
        ajax.get_url(url, bi_update_tree, oImg);
    else
        ajax.get_url(url);
}

function bi_update_tree(container)
{
    // Deactivate clicking - the update can last a couple
    // of seconds. In that time we must inhibit further clicking.
    container.onclick = null;

    // First find enclosding <div class=bi_tree_container>
    var bi_container = container;
    while (bi_container && !utils.has_class(bi_container, "bi_tree_container")) {
        bi_container = bi_container.parentNode;
    }

    ajax.post_url("bi_render_tree.py", bi_container.id, bi_update_tree_response, bi_container);
}

function bi_update_tree_response(bi_container, code) {
    bi_container.innerHTML = code;
    utils.execute_javascript_by_object(bi_container);
}

export function toggle_box(container, lazy)
{
    var url = "bi_save_treestate.py?path=" + encodeURIComponent(container.id);
    var do_open;

    if (utils.has_class(container, "open")) {
        if (lazy)
            return; // do not close in lazy mode
        utils.change_class(container, "open", "closed");
        url += "&state=closed";
        do_open = false;
    }
    else {
        utils.change_class(container, "closed", "open");
        url += "&state=open";
        do_open = true;
    }

    // TODO: Make asynchronous
    if (lazy && do_open)
        ajax.get_url(url, bi_update_tree, container);
    else {
        ajax.get_url(url);
        // find child nodes that belong to this node and
        // control visibility of those. Note: the BI child nodes
        // are *no* child nodes in HTML but siblings!
        var found = 0;
        for (var i in container.parentNode.children) {
            var onode = container.parentNode.children[i];

            if (onode == container)
                found = 1;

            else if (found) {
                if (do_open)
                    onode.style.display = "inline-block";
                else
                    onode.style.display = "none";
                return;
            }
        }
    }
}

export function toggle_assumption(link, site, host, service)
{
    var img = link.getElementsByTagName("img")[0];

    // get current state
    var path_parts = img.src.split("/");
    var file_part = path_parts.pop();
    var current = file_part.replace(/icon_assume_/, "").replace(/.png/, "");

    if (current == "none")
        // Assume WARN when nothing assumed yet
        current = "1";
    else if (current == "3" || (service == "" && current == "2"))
        // Assume OK when unknown assumed (or when critical assumed for host)
        current = "0";
    else if (current == "0")
        // Disable assumption when ok assumed
        current = "none";
    else
        // In all other cases increase the assumption
        current = parseInt(current) + 1;

    var url = "bi_set_assumption.py?site=" + encodeURIComponent(site)
            + "&host=" + encodeURIComponent(host);
    if (service) {
        url += "&service=" + encodeURIComponent(service);
    }
    url += "&state=" + current;
    img.src = path_parts.join("/") + "/icon_assume_" + current + ".png";
    ajax.get_url(url);
}

export function update_argument_hints() {
    d3.selectAll("select[onchange='cmk.bi.update_argument_hints();']").each((d, idx, nodes)=>{
        let node = d3.select(nodes[idx]);
        let rule_arguments = window.bi_rule_argument_lookup[node.property("value")];
        let rule_body = node.select(function() {return this.closest("tbody");});
        let required_inputs = rule_arguments.length;

        // Create nodes
        nodes = rule_body.selectAll("div.listofstrings").selectAll("input.text").nodes();
        while (required_inputs >= nodes.length) {
            valuespecs.list_of_strings_add_new_field(nodes[nodes.length-1]);
            nodes = rule_body.selectAll("div.listofstrings").selectAll("input.text").nodes();
        }

        // Update placeholder
        let input_nodes = rule_body.selectAll("div.listofstrings").selectAll("input.text");
        input_nodes.attr("placeholder", "");
        input_nodes.each((d, idx, nodes)=>{
            if (idx >= rule_arguments.length)
                return;
            let argument_input = d3.select(nodes[idx]);
            argument_input.attr("placeholder", rule_arguments[idx]);
        });
    });
}


export class BIPreview {
    constructor(root_node, varprefix) {
        this._root_node = d3.select(root_node);
        this._preview_active = false;
        this._varprefix = varprefix;
        this._last_body = "";
        this._update_interval = 500;
        this._update_active = false;
        this._create_search_preview([]);
        setInterval(()=>this._check_update(), this._update_interval);
    }

    _check_update() {}

    _get_update_url() {
        return encodeURI("ajax_bi_node_preview.py");
    }

    _update_previews() {
        this._update_active = false;
        this._check_update();
    }

    _trigger_update_if_required(params) {
        let body = this._dict_to_url(params);
        if (this._last_body == body) {
            return;
        }

        if (this._update_active)
            return;

        d3.json(this._get_update_url(),
            {
                credentials: "include",
                method: "POST",
                body: body,
                headers: {
                    "Content-type": "application/x-www-form-urlencoded"
                }
            }
        ).then(json_data=>this._update_previews(json_data));
        this._update_active = true;
        this._last_body = body;
    }

    _update_preview(data_rows, title, selection) {
        let div_preview = selection.selectAll("div.preview").data([null]).join(
            enter=>enter.append("div").classed("preview", true));

        div_preview.selectAll("h3").data([null]).join(enter=>enter.append("h3")
            .classed("search_preview", true))
            .text(title);

        let table = div_preview.selectAll("table").data([null]).join(
            enter=>enter.append("table")
                .style("overflow", "auto")
                .style("display", "block")
                .style("max-height", "400px")
        );
        let thead = table.selectAll("thead").data([null]).join("thead");
        let tbody = table.selectAll("tbody").data([null]).join("tbody");

        let headers = Object.keys(data_rows[0]);
        let header_row = thead.selectAll("tr").data([headers]).join("tr");
        header_row.selectAll("th").data(d=>d).join(
            enter=>enter.append("th")
                .classed("search_preview", true)
                .style("text-align", "left"))
            .text(d=>d);

        let body_rows = tbody.selectAll("tr").data(data_rows).join("tr");
        body_rows.selectAll("td").data(d=>{
            let cells = [];
            headers.forEach(header=>{
                cells.push(d[header]);
            });
            return cells;
        })
            .join(enter=>enter.append("td")
                .style("padding", "5px")
                .style("text-align", "left"))
            .text(d=>d);
    }

    _determine_params() {
        let inputs = this._root_node.selectAll("input,select");
        let params = {"varprefix": this._varprefix};
        inputs.each((d, idx, nodes)=>{
            let input = nodes[idx];
            params[input.name] = input.value;
        });
        return params;
    }

    _dict_to_url(dict) {
        let str = [];
        for(var p in dict){
            str.push(encodeURIComponent(p) + "=" + encodeURIComponent(dict[p]));
        }
        return str.join("&");
    }
}

export class BIRulePreview extends BIPreview {
    _check_update() {
        BIPreview.prototype._check_update.call(this);
        let display = this._preview_active ? null : "none";
        d3.selectAll("span.title").style("display", display);
        d3.selectAll("span.arguments").style("display", display);

        if (!this._preview_active) {
            setTimeout(()=>this._check_update(), this._update_interval);
            return;
        }

        let params = this._determine_params();
        params.example_arguments = JSON.stringify(this._get_example_arguments());
        this._trigger_update_if_required(params);
    }

    _get_update_url() {
        return encodeURI("ajax_bi_rule_preview.py");
    }

    _get_example_arguments() {
        let example_arguments = [];
        this._root_node.select("span.arguments").selectAll("input").each((d, idx, nodes)=>{
            example_arguments.push(nodes[idx].value);
        });
        return example_arguments;
    }

    _update_previews(json_data) {
        this._update_simulated_parameters(json_data.result.params);
        let nodes = d3.selectAll("#rule_p_nodes_container > tr").data(json_data.result.data);
        nodes.selectAll("td.search_preview").data(d=>[d])
            .join(enter=>enter.append("td")
                .classed("search_preview", true)
                .style("width", "700px")
                .style("vertical-align", "top"))

            .each((rows, idx, nodes)=>{
                this._update_preview(rows, json_data.result.title, d3.select(nodes[idx]));
            });
        BIPreview.prototype._update_previews.call(this, json_data);
    }

    _update_simulated_parameters(params) {
        let example_arguments = this._root_node.select("form > table:nth-child(2n) tbody tr td");
        example_arguments.style("text-align", "right");
        example_arguments.select("span.title").selectAll("label").data([null]).join("label").text("Example arguments for this rule");
        example_arguments.select("span.arguments").selectAll("input").data(params)
            .join("input")
            .attr("placeholder", d=>d);
    }

    _create_search_preview() {
        let example_arguments = this._root_node.select("form > table:nth-child(2n) tbody tr td");
        example_arguments.style("text-align", "right");
        example_arguments.selectAll("span").data(["title", "arguments", "button"]).join("span").attr("class", d=>d);
        example_arguments.select("span.button").selectAll("input.toggle_search_preview").data([null]).join(
            enter=>enter.append("input")
                .classed("toggle_search_preview", true)
                .attr("type", "button")
                .attr("value", "Toggle Search Preview")
                .on("click", (d, idx, nodes)=>{
                    this._preview_active = !this._preview_active;
                    d3.select(nodes[idx]).classed("active", this._preview_active);
                    d3.selectAll("div.preview").style("display", this._preview_active ? "block" : "none");
                    this._check_update();
                })
        );
    }
}

export class BIAggregationPreview extends BIPreview {
    _check_update() {
        BIPreview.prototype._check_update.call(this);
        if (!this._preview_active) {
            return;
        }

        let params = this._determine_params();
        this._trigger_update_if_required(params);
    }

    _get_update_url() {
        return encodeURI("ajax_bi_aggregation_preview.py");
    }

    _update_previews(json_data) {
        this._update_preview(json_data.result.data[0], json_data.result.title, this._preview_box);
        BIPreview.prototype._update_previews.call(this, json_data);
    }

    _create_search_preview() {
        let node_search_td = this._root_node.select("#aggr_p_node_d_search");
        this._preview_box = d3.select(node_search_td.node().parentNode.parentNode).selectAll("td.search_preview").data([null]).join("td");
        this._preview_box.style("text-align", "right").style("vertical-align", "top");
        this._preview_box.selectAll("span").data(["button"]).join("span").attr("class", d=>d);
        this._preview_box.select("span.button").selectAll("input.toggle_search_preview").data([null]).join(
            enter=>enter.append("input")
                .classed("toggle_search_preview", true)
                .attr("type", "button")
                .attr("value", "Toggle Search Preview")
                .on("click", (d, idx, nodes)=>{
                    this._preview_active = !this._preview_active;
                    d3.select(nodes[idx]).classed("active", this._preview_active);
                    d3.selectAll("div.preview").style("display", this._preview_active ? "block" : "none");
                    this._check_update();
                })
        );
    }
}
