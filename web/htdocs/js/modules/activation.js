// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

import * as ajax from "ajax";
import * as async_progress from "async_progress";
import * as utils from "utils";
import * as page_menu from "page_menu";

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

export function activate_changes(mode, site_id) {
    var sites = [];

    if (mode == "selected") {
        var checkboxes = document.getElementsByClassName("site_checkbox");
        for (var i = 0; i < checkboxes.length; i++) {
            if (checkboxes[i].checked) {
                // strip leading "site_" to get the site id
                sites.push(checkboxes[i].name.substr(5));
            }
        }

        if (sites.length == 0) {
            async_progress.show_error("You have to select a site.");
            return;
        }
    } else if (mode == "site") {
        sites.push(site_id);
    }

    var activate_until = document.getElementById("activate_until");
    if (!activate_until) return;

    var comment = "";
    var comment_field = document.getElementsByName("activate_p_comment")[0];
    if (comment_field && comment_field.value != "") comment = comment_field.value;

    var activate_foreign = 0;
    var foreign_checkbox = document.getElementsByName("activate_p_foreign")[0];
    if (foreign_checkbox && foreign_checkbox.checked) activate_foreign = 1;

    start_activation(sites, activate_until.value, comment, activate_foreign);
}

function start_activation(sites, activate_until, comment, activate_foreign) {
    async_progress.show_info("Initializing activation...");

    var post_data =
        "activate_until=" +
        encodeURIComponent(activate_until) +
        "&sites=" +
        encodeURIComponent(sites.join(",")) +
        "&comment=" +
        encodeURIComponent(comment) +
        "&activate_foreign=" +
        encodeURIComponent(activate_foreign);

    ajax.call_ajax("ajax_start_activation.py", {
        response_handler: handle_start_activation,
        error_handler: handle_start_activation_error,
        method: "POST",
        post_data: post_data,
        add_ajax_id: false,
    });

    lock_activation_controls(true);
}

function handle_start_activation(_unused, response_json) {
    var response = JSON.parse(response_json);

    if (response.result_code == 1) {
        async_progress.show_error(response.result);
        lock_activation_controls(false);
    } else {
        async_progress.show_info("Activating...");
        async_progress.monitor({
            update_url:
                "ajax_activation_state.py?activation_id=" +
                encodeURIComponent(response.result.activation_id),
            start_time: utils.time(),
            update_function: update_activation_state,
            is_finished_function: is_activation_progress_finished,
            finish_function: finish_activation,
            error_function: function (response) {
                async_progress.show_error(response);
            },
            post_data: "",
        });
    }
}

function handle_start_activation_error(_unused, status_code, error_msg) {
    async_progress.show_error("Failed to start activation [" + status_code + "]: " + error_msg);
}

function lock_activation_controls(lock) {
    var elements = [];

    elements = elements.concat(
        Array.prototype.slice.call(document.getElementsByName("activate_p_comment"), 0)
    );
    elements = elements.concat(
        Array.prototype.slice.call(document.getElementsByClassName("site_checkbox"), 0)
    );
    elements = elements.concat(
        Array.prototype.slice.call(document.getElementsByClassName("activate_site"), 0)
    );

    for (var i = 0; i < elements.length; i++) {
        if (!elements[i]) continue;

        if (lock) utils.add_class(elements[i], "disabled");
        else utils.remove_class(elements[i], "disabled");

        elements[i].disabled = lock ? "disabled" : false;
    }

    page_menu.enable_menu_entry("activate_selected", !lock);
    page_menu.enable_menu_entry("discard_changes", !lock);
}

function is_activation_progress_finished(response) {
    for (var site_id in response["sites"]) {
        // skip loop if the property is from prototype
        if (!response["sites"].hasOwnProperty(site_id)) continue;

        var site_state = response["sites"][site_id];
        if (site_state["_phase"] != "done") return false;
    }

    return true;
}

function update_activation_state(_unused_handler_data, response) {
    for (var site_id in response["sites"]) {
        // skip loop if the property is from prototype
        if (!response["sites"].hasOwnProperty(site_id)) continue;

        var site_state = response["sites"][site_id];

        // Catch empty site states
        var is_empty = true;
        for (var prop in site_state) {
            if (site_state.hasOwnProperty(prop)) {
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

export function update_site_activation_state(site_state) {
    // Show status text (overlay text on the progress bar)
    const msg = document.getElementById("site_" + site_state["_site_id"] + "_status");
    msg.innerHTML = site_state["_status_text"];

    if (site_state["_phase"] == "done") {
        utils.remove_class(msg, "in_progress");
        utils.add_class(msg, "state_" + site_state["_state"]);
    } else {
        utils.add_class(msg, "in_progress");
    }

    // Show status details
    if (site_state["_status_details"]) {
        const details = document.getElementById("site_" + site_state["_site_id"] + "_details");

        let detail_content = site_state["_status_details"];
        if (site_state["_state"] == "warning" || site_state["_state"] == "error") {
            detail_content =
                "<div class='" + site_state["_state"] + "'>" + detail_content + "</div>";
        }

        details.innerHTML = detail_content;
    }

    update_site_progress(site_state);
}

function update_site_progress(site_state) {
    var max_width = 160;

    var progress = document.getElementById("site_" + site_state["_site_id"] + "_progress");

    if (site_state["_phase"] == "done") {
        progress.style.width = max_width + "px";

        utils.remove_class(progress, "in_progress");
        utils.add_class(progress, "state_" + site_state["_state"]);
        return;
    } else {
        utils.add_class(progress, "in_progress");
    }

    // TODO: Visualize overdue

    if (site_state["_time_started"] === null) {
        return; // Do not update width in case it was not started yet
    }

    var duration = parseFloat(utils.time() - site_state["_time_started"]);

    var expected_duration = site_state["_expected_duration"];
    var duration_percent = (duration * 100.0) / expected_duration;
    var width = parseInt((parseFloat(max_width) * duration_percent) / 100);

    if (width > max_width) width = max_width;

    progress.style.width = width + "px";
}

function finish_activation(result) {
    utils.schedule_reload(utils.makeuri({_finished: "1"}), 1000);

    // Handle special state "Locked" with a timeout to show the message to the
    // user. We can only determine this state via warning state for now
    var site_result = result.sites;
    var is_warning = false;
    for (let [site_id, site_keys] of Object.entries(site_result)) {
        if (site_keys._state == "warning") {
            is_warning = true;
            break;
        }
    }

    // Trigger a reload of the sidebar (to update changes in WATO snapin)
    if (is_warning == true) {
        setTimeout(function () {
            utils.reload_whole_page();
        }, 1000);
    } else {
        utils.reload_whole_page();
    }
}
