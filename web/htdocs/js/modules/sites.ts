// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

import * as ajax from "ajax";
import $ from "jquery";

interface SiteState {
    livestatus: string;
    replication: string;
}
export function fetch_site_status() {
    ajax.call_ajax("wato_ajax_fetch_site_status.py", {
        response_handler: function (handler_data, response_json) {
            let response = JSON.parse(response_json);
            let success = response.result_code === 0;
            let site_states: Record<string, SiteState> = response.result;

            if (!success) {
                show_error("Site status update failed: " + site_states);
                return;
            }

            for (let [site_id, site_status] of Object.entries(site_states)) {
                var livestatus_container = document.getElementById(
                    "livestatus_status_" + site_id
                )!;
                livestatus_container.innerHTML = site_status.livestatus;

                var replication_container = document.getElementById(
                    "replication_status_" + site_id
                )!;
                replication_container.innerHTML = site_status.replication;
            }
        },
        error_handler: function (handler_data, status_code, error_msg) {
            if (status_code != 0) {
                show_error(
                    "Site status update failed [" +
                        status_code +
                        "]: " +
                        error_msg
                );
            }
        },
        method: "POST",
        add_ajax_id: false,
    });
}

function show_error(msg) {
    var o = document.getElementById("message_container");
    o!.innerHTML = "<div class=error>" + msg + "</div>";

    // Remove all loading icons
    $(".reloading").remove();
}
