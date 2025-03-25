/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import {call_ajax} from "./ajax";
import {monitor, show_error, show_info} from "./async_progress";
import {enable_menu_entry} from "./page_menu";
import type {CMKAjaxReponse} from "./types";
import {
    add_class,
    makeuri,
    reload_whole_page,
    remove_class,
    remove_classes_by_prefix,
    schedule_reload,
    time,
} from "./utils";

//#.
//#   .-Activation---------------------------------------------------------.
//#   |              _        _   _            _   _                       |
//#   |             / \   ___| |_(_)_   ____ _| |_(_) ___  _ __            |
//#   |            / _ \ / __| __| \ \ / / _` | __| |/ _ \| '_ \           |
//#   |           / ___ \ (__| |_| |\ V / (_| | |_| | (_) | | | |          |
//#   |          /_/   \_\___|\__|_| \_/ \__,_|\__|_|\___/|_| |_|          |
//#   |                                                                    |
//#   +--------------------------------------------------------------------+
//#   | The WATO activation works this way:                                |
//#   | a) The user chooses one activation mode (affected sites, selected  |
//#   |    sites or a single site)                                         |
//#   | b) The JS GUI starts a single "worker" which calls the python code |
//#   |    first to locking the sites and creating the sync snapshot(s)    |
//#   | c) Then the snapshot is synced to the sites and activated on the   |
//#   |    sites indidivually.                                             |
//#   | d) Once a site finishes, it's changes are commited and the site is |
//#   |    unlocked individually.                                          |
//#   '--------------------------------------------------------------------'

export function activate_changes(mode: "selected" | "site", site_id: string) {
    const sites: string[] = [];

    if (mode == "selected") {
        const checkboxes = document.getElementsByClassName(
            "site_checkbox",
        ) as HTMLCollectionOf<HTMLInputElement>;
        for (let i = 0; i < checkboxes.length; i++) {
            if (checkboxes[i].checked) {
                // strip leading "site_" to get the site id
                sites.push(checkboxes[i].name.substr(5));
            }
        }

        if (sites.length == 0) {
            show_error("You have to select a site.");
            return;
        }
    } else if (mode == "site") {
        sites.push(site_id);
    }

    const activate_until = document.getElementById(
        "activate_until",
    ) as HTMLInputElement | null;
    if (!activate_until) return;

    let comment = "";
    const comment_field = document.getElementsByName(
        "activate_p_comment",
    )[0] as HTMLInputElement | null;
    if (comment_field && comment_field.value != "")
        comment = comment_field.value;

    let activate_foreign: 0 | 1 = 0;
    const foreign_checkbox = document.getElementsByName(
        "activate_p_foreign",
    )[0] as HTMLInputElement | null;
    if (foreign_checkbox && foreign_checkbox.checked) activate_foreign = 1;

    start_activation(sites, activate_until.value, comment, activate_foreign);
    initialize_site_progresses(sites);
}

function start_activation(
    sites: string[],
    activate_until: string,
    comment: string,
    activate_foreign: 0 | 1,
) {
    show_info("Initializing activation...");

    const post_data =
        "activate_until=" +
        encodeURIComponent(activate_until) +
        "&sites=" +
        encodeURIComponent(sites.join(",")) +
        "&comment=" +
        encodeURIComponent(comment) +
        "&activate_foreign=" +
        encodeURIComponent(activate_foreign);

    call_ajax("ajax_start_activation.py", {
        response_handler: handle_start_activation,
        error_handler: handle_start_activation_error,
        method: "POST",
        post_data: post_data,
        add_ajax_id: false,
    });

    lock_activation_controls(true);
}
function handle_start_activation(_unused: unknown, response_json: string) {
    const response: CMKAjaxReponse<{activation_id: string}> =
        JSON.parse(response_json);

    if (response.result_code == 1) {
        show_error(String(response.result));
        lock_activation_controls(false);
    } else {
        show_info("Activating...");
        monitor({
            update_url:
                "ajax_activation_state.py?activation_id=" +
                encodeURIComponent(response.result.activation_id),
            start_time: time(),
            update_function: update_activation_state,
            is_finished_function: is_activation_progress_finished,
            finish_function: finish_activation,
            error_function: function (response) {
                show_error(response);
            },
            post_data: "",
        });
    }
}

function handle_start_activation_error(
    _unused: unknown,
    status_code: number,
    error_msg: string,
) {
    show_error(
        "Failed to start activation [" + status_code + "]: " + error_msg,
    );
}

function lock_activation_controls(lock: boolean) {
    let elements: HTMLElement[] = [];

    elements = elements.concat(
        Array.prototype.slice.call(
            document.getElementsByName("activate_p_comment"),
            0,
        ),
    );
    elements = elements.concat(
        Array.prototype.slice.call(
            document.getElementsByClassName("site_checkbox"),
            0,
        ),
    );
    elements = elements.concat(
        Array.prototype.slice.call(
            document.getElementsByClassName("activate_site"),
            0,
        ),
    );

    for (let i = 0; i < elements.length; i++) {
        if (!elements[i]) continue;

        if (lock) add_class(elements[i], "disabled");
        else remove_class(elements[i], "disabled");

        (elements[i] as HTMLButtonElement).disabled = Boolean(lock);
    }

    enable_menu_entry("activate_selected", !lock);
    enable_menu_entry("discard_changes", !lock);
}

function is_activation_progress_finished(response: {
    sites: Record<string, any>;
}) {
    for (const site_id in response["sites"]) {
        // skip loop if the property is from prototype
        if (!Object.prototype.hasOwnProperty.call(response["sites"], site_id))
            continue;

        const site_state = response["sites"][site_id];
        if (site_state["_phase"] != "done") return false;
    }

    return true;
}

function initialize_site_progresses(sites: string[]) {
    for (const site_id of sites) {
        const progress = document.getElementById(
            "site_" + site_id + "_progress",
        );
        // Temporarily disable the transition for the reset
        if (!progress) throw new Error("progress shouldn't be null!");
        progress.style.transition = "none";
        progress.style.width = "0px";
        progress.style.transition = "";
    }
}

function update_activation_state(
    _unused_handler_data: unknown,
    response: {sites: Record<string, any>},
) {
    for (const site_id in response["sites"]) {
        // skip loop if the property is from prototype
        if (!Object.prototype.hasOwnProperty.call(response["sites"], site_id))
            continue;

        const site_state = response["sites"][site_id];

        // Catch empty site states
        let is_empty = true;
        for (const prop in site_state) {
            if (Object.prototype.hasOwnProperty.call(site_state, prop)) {
                is_empty = false;
                break;
            }
        }

        // Due to the asynchroneous nature of the activate changes site scheduler
        // the site state file may not be present within the first seconds
        if (is_empty) continue;

        update_site_activation_state(site_state);
    }
}

export function update_site_activation_state(site_state: Record<string, any>) {
    // Show status text (overlay text on the progress bar)
    const msg = document.getElementById(
        "site_" + site_state["_site_id"] + "_status",
    );
    if (!msg) throw new Error("msg shouldn't be null!");
    /* eslint-disable-next-line no-unsanitized/property -- Highlight existing violations CMK-17846 */
    msg.innerHTML = site_state["_status_text"];

    if (site_state["_phase"] == "done") {
        remove_class(msg, "in_progress");
        add_class(msg, "state_" + site_state["_state"]);
    } else {
        remove_classes_by_prefix(msg, "state_");
        add_class(msg, "in_progress");
    }

    // Show status details
    if (site_state["_status_details"]) {
        const details = document.getElementById(
            "site_" + site_state["_site_id"] + "_details",
        );
        if (!details) throw new Error("details shouldn't be null!");
        let detail_content = site_state["_status_details"];
        if (
            site_state["_state"] == "warning" ||
            site_state["_state"] == "error"
        ) {
            detail_content =
                "<div class='" +
                site_state["_state"] +
                "'>" +
                detail_content +
                "</div>";
        }

        /* eslint-disable-next-line no-unsanitized/property -- Highlight existing violations CMK-17846 */
        details.innerHTML = detail_content;
    }

    update_site_progress(site_state);
}

function update_site_progress(site_state: Record<string, any>) {
    const max_width = 160;

    const progress = document.getElementById(
        "site_" + site_state["_site_id"] + "_progress",
    );
    if (!progress) throw new Error("progress shouldn't be null!");

    if (site_state["_phase"] == "done") {
        progress.style.width = max_width + "px";

        remove_class(progress, "in_progress");
        add_class(progress, "state_" + site_state["_state"]);
        return;
    } else {
        remove_classes_by_prefix(progress, "state_");
        add_class(progress, "in_progress");
    }

    // TODO: Visualize overdue

    if (site_state["_time_started"] === null) {
        return; // Do not update width in case it was not started yet
    }

    const duration = time() - site_state["_time_started"];

    const expected_duration = site_state["_expected_duration"];
    const duration_percent = (duration * 100.0) / expected_duration;
    let width = Math.trunc((max_width * duration_percent) / 100);

    if (width > max_width) width = max_width;

    progress.style.width = width + "px";
}

function finish_activation(result: {sites: Record<string, any>}) {
    schedule_reload(makeuri({_finished: "1"}), 1000);

    // Handle special state "Locked" with a timeout to show the message to the
    // user. We can only determine this state via warning state for now
    const site_result = result.sites;
    let is_warning = false;
    for (const value of Object.values(site_result)) {
        if ((value as any)._state == "warning") {
            is_warning = true;
            break;
        }
    }

    // Trigger a reload of the sidebar (to update changes in WATO snapin)
    if (is_warning) {
        setTimeout(function () {
            reload_whole_page();
        }, 1000);
    } else {
        reload_whole_page();
    }
}
