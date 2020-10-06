// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

import * as utils from "utils";
import * as ajax from "ajax";

var g_num_replsites = 0;
var profile_replication_progress = {};

export function prepare(num) {
    g_num_replsites = num;
}

export function start(siteid, est, progress_text) {
    ajax.call_ajax("wato_ajax_profile_repl.py", {
        response_handler: function (handler_data, response_json) {
            var response = JSON.parse(response_json);
            var success = response.result_code === 0;
            var msg = response.result;

            set_result(handler_data["site_id"], success, msg);
        },
        error_handler: function (handler_data, status_code, error_msg) {
            set_result(
                handler_data["site_id"],
                false,
                "Failed to perform profile replication [" + status_code + "]: " + error_msg
            );
        },
        method: "POST",
        post_data:
            "request=" +
            encodeURIComponent(
                JSON.stringify({
                    site: siteid,
                })
            ),
        handler_data: {
            site_id: siteid,
        },
        add_ajax_id: false,
    });

    profile_replication_progress[siteid] = 20; // 10 of 10 10ths
    setTimeout(
        "cmk.profile_replication.step('" + siteid + "', " + est + ", '" + progress_text + "');",
        est / 20
    );
}

function set_status(siteid, image, text) {
    var icon = document.getElementById("site-" + siteid).getElementsByClassName("repl_status")[0];
    icon.title = text;
    icon.className = "icon repl_status " + image;
}

export function step(siteid, est, progress_text) {
    if (profile_replication_progress[siteid] > 0) {
        profile_replication_progress[siteid]--;
        var perc = ((20.0 - profile_replication_progress[siteid]) * 100) / 20;
        var img;
        if (perc >= 75) img = "repl_75";
        else if (perc >= 50) img = "repl_50";
        else if (perc >= 25) img = "repl_25";
        else img = "repl_pending";
        set_status(siteid, img, progress_text);
        setTimeout(
            "cmk.profile_replication.step('" + siteid + "'," + est + ", '" + progress_text + "');",
            est / 20
        );
    }
}

function set_result(site_id, success, msg) {
    profile_replication_progress[site_id] = 0;

    var icon_name = success ? "repl_success" : "repl_failed";

    set_status(site_id, icon_name, msg);

    g_num_replsites--;
    if (g_num_replsites == 0) {
        setTimeout(finish, 1000);
    }
}

function finish() {
    // check if we have a sidebar-main frame setup
    if (this.parent && parent && parent.frames[0] == this) utils.reload_sidebar();
}
