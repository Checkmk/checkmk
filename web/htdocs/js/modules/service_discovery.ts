/**
 * Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import * as ajax from "ajax";
import * as async_progress from "async_progress";
import * as utils from "utils";

//#   +--------------------------------------------------------------------+
//#   | Handling of the asynchronous service discovery dialog              |
//#   '--------------------------------------------------------------------'

interface Check {
    site: string;
    folder_path: string;
    hostname: string;
    checktype: string;
    item: any;
    divid: string;
}

// Stores the latest discovery_result object which was used by the python
// code to render the current page. It will be sent back to the python
// code for further actions. It contains the check_table which actions of
// the user are based on.
let g_service_discovery_result: string | null = null;
let g_show_updating_timer: number | null = null;

type DiscoveryAction =
    | ""
    | "stop"
    | "fix_all"
    | "refresh"
    | "tabula_rasa"
    | "single_update"
    | "bulk_update"
    | "update_host_labels"
    | "update_services";

interface DiscoveryOptions {
    action: DiscoveryAction;
    show_checkboxes: boolean;
    show_parameters: boolean;
    show_discovered_labels: boolean;
    show_plugin_names: boolean;
    ignore_errors: boolean;
}
interface AjaxServiceDiscovery {
    is_finished: boolean;
    job_state: any;
    message: string | null;
    body: string;
    datasources: string;
    fixall: string;
    page_menu: string;
    pending_changes_info: string | null;
    pending_changes_tooltip: string;
    discovery_options: DiscoveryOptions;
    discovery_result: string;
}

interface ServiceDiscoveryHandlerData {
    update_url: string;
    error_function: (response: AjaxServiceDiscovery) => void;
    update_function: (
        update_data: ServiceDiscoveryHandlerData,
        response: AjaxServiceDiscovery
    ) => void;
    is_finished_function: (response: AjaxServiceDiscovery) => void;
    finish_function: (response: AjaxServiceDiscovery) => void;
    post_data: string;
    start_time?: number;
    host_name: string;
    folder_path: string;
    transid: string;
}

export function start(
    host_name: string,
    folder_path: string,
    discovery_options: DiscoveryOptions,
    transid: string,
    request_vars: Record<string, any> | null
) {
    // When we receive no response for 2 seconds, then show the updating message
    g_show_updating_timer = window.setTimeout(function () {
        async_progress.show_info("Updating...");
    }, 2000);

    lock_controls(
        true,
        get_state_independent_controls().concat(get_page_menu_controls())
    );
    async_progress.monitor({
        update_url: "ajax_service_discovery.py",
        host_name: host_name,
        folder_path: folder_path,
        transid: transid,
        start_time: utils.time(),
        is_finished_function: (response: AjaxServiceDiscovery) =>
            response.is_finished,
        update_function: update,
        finish_function: finish,
        error_function: error,
        post_data: get_post_data(
            host_name,
            folder_path,
            discovery_options,
            transid,
            request_vars
        ),
    });
}

function get_post_data(
    host_name: string,
    folder_path: string,
    discovery_options: DiscoveryOptions,
    transid: string,
    request_vars: Record<string, any> | null
) {
    let request: Record<string, any> = {
        host_name: host_name,
        folder_path: folder_path,
        discovery_options: discovery_options,
        discovery_result: g_service_discovery_result,
    };

    if (request_vars !== undefined && request_vars !== null) {
        request = Object.assign(request, request_vars);
    }

    if (["bulk_update", "update_services"].includes(discovery_options.action)) {
        const checked_checkboxes: string[] = [];
        const checkboxes = document.getElementsByClassName(
            "service_checkbox"
        ) as HTMLCollectionOf<HTMLInputElement>;
        for (let i = 0; i < checkboxes.length; i++) {
            if (checkboxes[i].checked) {
                checked_checkboxes.push(checkboxes[i].name);
            }
        }
        request["update_services"] = checked_checkboxes;
    }

    let post_data = "request=" + encodeURIComponent(JSON.stringify(request));

    // Can currently not be put into "request" because the generic transaction
    // manager relies on the HTTP var _transid.
    if (transid !== undefined)
        post_data += "&_transid=" + encodeURIComponent(transid);

    return post_data;
}

function finish(response: AjaxServiceDiscovery) {
    if (response.job_state == "exception" || response.job_state == "stopped") {
        async_progress.show_error(response.message!);
    } else {
        //async_progress.hide_msg();
    }

    // Only unlock the "per service" actions here. The page menu entries are unlocked by individual
    // calls to enable_page_menu_entry depending on the state of the page.
    lock_controls(false, get_state_independent_controls());
}

function error(response: string) {
    if (g_show_updating_timer) {
        clearTimeout(g_show_updating_timer);
    }
    async_progress.show_error(response);
}

function update(
    handler_data: ServiceDiscoveryHandlerData,
    response: AjaxServiceDiscovery
) {
    if (g_show_updating_timer) {
        clearTimeout(g_show_updating_timer);
    }

    if (response.message) {
        async_progress.show_info(response.message);
    } else {
        async_progress.hide_msg();
    }

    g_service_discovery_result = response.discovery_result;
    handler_data.post_data = get_post_data(
        handler_data.host_name,
        handler_data.folder_path,
        response.discovery_options,
        handler_data.transid,
        null
    );

    // Save values not meant for update
    const menu_display = document.getElementById("general_display_options")!;

    // Update the page menu
    const page_menu_bar = document.getElementById("page_menu_bar")!;
    page_menu_bar.outerHTML = response.page_menu;
    utils.execute_javascript_by_object(page_menu_bar);

    // Set saved values to old value
    document
        .getElementById("general_display_options")!
        .replaceWith(menu_display);

    // Update datasources
    const ds_container = document.getElementById("datasources_container")!;
    ds_container.innerHTML = response.datasources;

    // Update fix all button
    const fixall_container = document.getElementById("fixall_container")!;
    fixall_container.style.display = response.fixall ? "block" : "none";
    fixall_container.innerHTML = response.fixall;
    utils.execute_javascript_by_object(fixall_container);

    // Update the content table
    const container = document.getElementById("service_container")!;
    container.style.display = "block";
    container.innerHTML = response.body;
    utils.execute_javascript_by_object(container);

    if (response.pending_changes_info) {
        utils.update_pending_changes(
            response.pending_changes_info,
            response.pending_changes_tooltip
        );
    }

    // Also execute delayed active checks once to trigger delayed checks that are initially visible.
    trigger_delayed_active_checks();
}

function get_state_independent_controls() {
    let elements: HTMLElement[] = [];
    elements = elements.concat(
        Array.prototype.slice.call(
            document.getElementsByClassName("service_checkbox"),
            0
        )
    );
    elements = elements.concat(
        Array.prototype.slice.call(
            document.getElementsByClassName("service_button"),
            0
        )
    );
    elements = elements.concat(
        Array.prototype.slice.call<
            HTMLCollectionOf<Element>,
            [number],
            HTMLElement[]
        >(document.getElementsByClassName("toggle"), 0)
    );
    return elements;
}

function get_page_menu_controls() {
    return Array.prototype.slice.call<
        HTMLCollectionOf<Element>,
        [number],
        HTMLElement[]
    >(document.getElementsByClassName("action"), 0);
}

function lock_controls(lock: boolean, elements: HTMLElement[]) {
    let element;
    for (let i = 0; i < elements.length; i++) {
        element = elements[i];
        if (!element) continue;

        if (lock) utils.add_class(element, "disabled");
        else utils.remove_class(element, "disabled");

        //@ts-ignore
        element.disabled = lock;
    }
}

const g_delayed_active_checks: Check[] = [];

export function register_delayed_active_check(
    site: string,
    folder_path: string,
    hostname: string,
    checktype: string,
    item: string | null,
    divid: string
) {
    // Register event listeners on first call
    if (g_delayed_active_checks.length == 0) {
        //@ts-ignore
        utils
            //@ts-ignore
            .content_scrollbar()!
            .getScrollElement()
            .addEventListener("scroll", trigger_delayed_active_checks);
        utils.add_event_handler("resize", trigger_delayed_active_checks);
    }

    g_delayed_active_checks.push({
        site: site,
        folder_path: folder_path,
        hostname: hostname,
        checktype: checktype,
        item: item,
        divid: divid,
    });
}

// Is executed on scroll / resize events in case at least one graph is
// using the delayed graph rendering mechanism
function trigger_delayed_active_checks() {
    const num_delayed = g_delayed_active_checks.length;
    if (num_delayed == 0) return; // no delayed graphs: Nothing to do

    let i = num_delayed;
    while (i--) {
        const entry = g_delayed_active_checks[i];
        if (utils.is_in_viewport(document.getElementById(entry.divid)!)) {
            execute_active_check(entry);
            g_delayed_active_checks.splice(i, 1);
        }
    }
    return true;
}

export function execute_active_check(entry: Check) {
    const div = document.getElementById(entry.divid)!;
    ajax.call_ajax("wato_ajax_execute_check.py", {
        post_data:
            "site=" +
            encodeURIComponent(entry.site) +
            "&folder=" +
            encodeURIComponent(entry.folder_path) +
            "&host=" +
            encodeURIComponent(entry.hostname) +
            "&checktype=" +
            encodeURIComponent(entry.checktype) +
            "&item=" +
            encodeURIComponent(entry.item),
        method: "POST",
        response_handler: handle_execute_active_check,
        handler_data: div,
    });
}

function handle_execute_active_check(oDiv: HTMLElement, response_json: string) {
    const response = JSON.parse(response_json);

    let state, statename, output;
    if (response.result_code == 1) {
        state = 3;
        statename = "UNKN";
        output = response.result;
    } else {
        state = response.result.state;
        if (state == -1) state = "p"; // Pending
        statename = response.result.state_name;
        output = response.result.output;
    }

    oDiv.innerHTML = output;

    // Change name and class of status columns
    const oTr = oDiv.parentNode!.parentNode as HTMLElement;
    if (utils.has_class(oTr, "even0")) utils.add_class(oTr, "even" + state);
    else utils.add_class(oTr, "odd" + state);

    const oTdState = oTr.getElementsByClassName("state")[0] as HTMLElement;
    utils.remove_class(oTdState, "statep");
    utils.add_class(oTdState, "state" + state);

    const span = document.createElement("span");
    utils.add_class(span, "state_rounded_fill");
    span.innerHTML = statename;
    oTdState.replaceChild(span, oTdState.firstChild!);
}
