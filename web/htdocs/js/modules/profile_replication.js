// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
// +------------------------------------------------------------------+
//
// This file is part of Check_MK.
// The official homepage is at http://mathias-kettner.de/check_mk.
//
// check_mk is free software;  you can redistribute it and/or modify it
// under the  terms of the  GNU General Public License  as published by
// the Free Software Foundation in version 2.  check_mk is  distributed
// in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
// out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
// PARTICULAR PURPOSE. See the  GNU General Public License for more de-
// ails.  You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

import * as utils from "utils";
import * as ajax from "ajax";

var g_num_replsites = 0;
var profile_replication_progress = {};

export function prepare(num) {
    g_num_replsites = num;
}

export function start(siteid, est, progress_text) {
    ajax.call_ajax("wato_ajax_profile_repl.py", {
        response_handler : function (handler_data, response_json) {
            var response = JSON.parse(response_json);
            var success = response.result_code === 0;
            var msg = response.result;

            set_result(handler_data["site_id"], success, msg);
        },
        error_handler    : function (handler_data, status_code, error_msg) {
            set_result(handler_data["site_id"], false,
                "Failed to perform profile replication [" + status_code + "]: " + error_msg);
        },
        method           : "POST",
        post_data        : "request=" + encodeURIComponent(JSON.stringify({
            "site": siteid
        })),
        handler_data     : {
            "site_id": siteid
        },
        add_ajax_id      : false
    });

    profile_replication_progress[siteid] = 20; // 10 of 10 10ths
    setTimeout(function() { step(siteid, est, progress_text); }, est/20);
}

function set_status(siteid, image, text) {
    var icon = document.getElementById("site-" + siteid).getElementsByClassName("repl_status")[0];
    icon.title = text;
    icon.className = "icon repl_status " + image;
}

function step(siteid, est, progress_text) {
    if (profile_replication_progress[siteid] > 0) {
        profile_replication_progress[siteid]--;
        var perc = (20.0 - profile_replication_progress[siteid]) * 100 / 20;
        var img;
        if (perc >= 75)
            img = "repl_75";
        else if (perc >= 50)
            img = "repl_50";
        else if (perc >= 25)
            img = "repl_25";
        else
            img = "repl_pending";
        set_status(siteid, img, progress_text);
        setTimeout(function() { step(siteid, est, progress_text); }, est/20);
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
    if (this.parent && parent && parent.frames[1] == this)
        utils.reload_sidebar();
}
