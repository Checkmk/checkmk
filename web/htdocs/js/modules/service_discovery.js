// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

import * as utils from "utils";
import * as ajax from "ajax";
import * as async_progress from "async_progress";
import * as page_menu from "page_menu";

//#   +--------------------------------------------------------------------+
//#   | Handling of the asynchronous service discovery dialog              |
//#   '--------------------------------------------------------------------'

// Stores the latest discovery_result object which was used by the python
// code to render the current page. It will be sent back to the python
// code for further actions. It contains the check_table which actions of
// the user are based on.
var g_service_discovery_result = null;
var g_show_updating_timer = null;

export function start(host_name, folder_path, discovery_options, transid, request_vars)
{
    // When we receive no response for 2 seconds, then show the updating message
    g_show_updating_timer = setTimeout(function() {
        async_progress.show_info("Updating...");
    }, 2000);

    lock_controls(true, get_state_independent_controls().concat(get_page_menu_controls()));
    async_progress.monitor({
        "update_url" : "ajax_service_discovery.py",
        "host_name": host_name,
        "folder_path": folder_path,
        "transid": transid,
        "start_time" : utils.time(),
        "is_finished_function": is_finished,
        "update_function": update,
        "finish_function": finish,
        "error_function": error,
        "post_data": get_post_data(host_name, folder_path, discovery_options, transid, request_vars)
    });
}

function get_post_data(host_name, folder_path, discovery_options, transid, request_vars)
{
    var request = {
        "host_name": host_name,
        "folder_path": folder_path,
        "discovery_options": discovery_options,
        "discovery_result": g_service_discovery_result
    };

    if (request_vars !== undefined && request_vars !== null) {
        request = Object.assign(request, request_vars);
    }

    if (discovery_options.action == "bulk_update") {
        var checked_checkboxes = [];
        var checkboxes = document.getElementsByClassName("service_checkbox");
        for (var i = 0; i < checkboxes.length; i++) {
            if (checkboxes[i].checked) {
                checked_checkboxes.push(checkboxes[i].name);
            }
        }
        request["update_services"] = checked_checkboxes;
    }

    var post_data = "request=" + encodeURIComponent(JSON.stringify(request));

    // Can currently not be put into "request" because the generic transaction
    // manager relies on the HTTP var _transid.
    if (transid !== undefined)
        post_data += "&_transid=" + encodeURIComponent(transid);

    return post_data;
}

function is_finished(response) {
    return response.is_finished;
}

function finish(response)
{
    if (response.job_state == "exception"
        || response.job_state == "stopped") {
        async_progress.show_error(response.message);
    } else {
        //async_progress.hide_msg();
    }

    // Only unlock the "per service" actions here. The page menu entries are unlocked by individual
    // calls to enable_page_menu_entry depending on the state of the page.
    lock_controls(false, get_state_independent_controls());
}

function error(response)
{
    if (g_show_updating_timer) {
        clearTimeout(g_show_updating_timer);
    }
    async_progress.show_error(response);
}


function update(handler_data, response) {
    if (g_show_updating_timer) {
        clearTimeout(g_show_updating_timer);
    }

    if (response.message) {
        async_progress.show_info(response.message);
    } else {
        async_progress.hide_msg();
    }

    g_service_discovery_result = response.discovery_result;
    handler_data.post_data = get_post_data(handler_data.host_name, handler_data.folder_path, response.discovery_options, handler_data.transid);

    // Update the page menu
    var page_menu_bar = document.getElementById("page_menu_bar");
    page_menu_bar.outerHTML = response.page_menu;
    utils.execute_javascript_by_object(page_menu_bar);

    // Update the content table
    var container = document.getElementById("service_container");
    container.style.display = "block";
    container.innerHTML = response.body;
    utils.execute_javascript_by_object(container);

    page_menu.update_page_state_top_line(response.pending_changes_info);
}

function get_state_independent_controls() {
    var elements = [];
    elements = elements.concat(Array.prototype.slice.call(document.getElementsByClassName("service_checkbox"), 0));
    elements = elements.concat(Array.prototype.slice.call(document.getElementsByClassName("service_button"), 0));
    elements = elements.concat(Array.prototype.slice.call(document.getElementsByClassName("toggle"), 0));
    return elements;
}

function get_page_menu_controls() {
    return Array.prototype.slice.call(document.getElementsByClassName("action"), 0);
}

function lock_controls(lock, elements)
{
    let element;
    for (var i = 0; i < elements.length; i++) {
        element = elements[i];
        if (!element)
            continue;

        if (lock)
            utils.add_class(element, "disabled");
        else
            utils.remove_class(element, "disabled");

        element.disabled = lock;
    }
}

export function execute_active_check(site, folder_path, hostname, checktype, item, divid)
{
    var oDiv = document.getElementById(divid);
    var url = "wato_ajax_execute_check.py?" +
           "site="       + encodeURIComponent(site) +
           "&folder="    + encodeURIComponent(folder_path) +
           "&host="      + encodeURIComponent(hostname)  +
           "&checktype=" + encodeURIComponent(checktype) +
           "&item="      + encodeURIComponent(item);
    ajax.get_url(url, handle_execute_active_check, oDiv);
}


function handle_execute_active_check(oDiv, response_json)
{
    var response = JSON.parse(response_json);

    var state, statename, output;
    if (response.result_code == 1) {
        state = 3;
        statename = "UNKN";
        output = response.result;
    } else {
        state = response.result.state;
        if (state == -1)
            state = "p"; // Pending
        statename = response.result.state_name;
        output    = response.result.output;
    }

    oDiv.innerHTML = output;

    // Change name and class of status columns
    var oTr = oDiv.parentNode.parentNode;
    if (utils.has_class(oTr, "even0"))
        utils.add_class(oTr, "even" + state);
    else
        utils.add_class(oTr, "odd" + state);

    var oTdState = oTr.getElementsByClassName("state")[0];
    utils.remove_class(oTdState, "statep");
    utils.add_class(oTdState, "state" + state);

    oTdState.innerHTML = statename;
}
