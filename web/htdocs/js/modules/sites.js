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
// tails.  You should have received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

import * as ajax from "ajax";
import $ from "jquery";

export function fetch_site_status()
{
    ajax.call_ajax("wato_ajax_fetch_site_status.py", {
        response_handler : function (handler_data, response_json) {
            let response = JSON.parse(response_json);
            let success = response.result_code === 0;
            let site_states = response.result;

            if (!success) {
                show_error("Site status update failed: " + site_states);
                return;
            }

            for (let [site_id, site_status] of Object.entries(site_states)) {
                var livestatus_container = document.getElementById("livestatus_status_" + site_id);
                livestatus_container.innerHTML = site_status.livestatus;

                var replication_container = document.getElementById("replication_status_" + site_id);
                replication_container.innerHTML = site_status.replication;
            }
        },
        error_handler    : function (handler_data, status_code, error_msg) {
            if (status_code != 0) {
                show_error("Site status update failed [" + status_code + "]: " + error_msg);
            }
        },
        method           : "POST",
        add_ajax_id      : false
    });
}

function show_error(msg)
{
    var o = document.getElementById("message_container");
    o.innerHTML = "<div class=error>" + msg + "</div>";

    // Remove all loading icons
    $(".reloading").remove();
}
