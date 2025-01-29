/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import $ from "jquery";

import {call_ajax} from "./ajax";

interface AjaxJsonResponse<Result = any> {
    result_code: number;
    result: Result;
    serverity: "success" | "error";
}

interface SiteState {
    livestatus: string;
    replication: string;
    message_broker: string;
}

export function fetch_site_status() {
    call_ajax("wato_ajax_fetch_site_status.py", {
        response_handler: function (_handler_data: any, response_json: string) {
            const response: AjaxJsonResponse<Record<string, SiteState>> =
                JSON.parse(response_json);
            const success = response.result_code === 0;
            const site_states = response.result;

            if (!success) {
                show_error("Site status update failed: " + site_states);
                return;
            }

            for (const [site_id, site_status] of Object.entries(site_states)) {
                const livestatus_container = document.getElementById(
                    "livestatus_status_" + site_id,
                )!;
                /* eslint-disable-next-line no-unsanitized/property -- Highlight existing violations CMK-17846 */
                livestatus_container.innerHTML = site_status.livestatus;

                const replication_container = document.getElementById(
                    "replication_status_" + site_id,
                )!;
                /* eslint-disable-next-line no-unsanitized/property -- Highlight existing violations CMK-17846 */
                replication_container.innerHTML = site_status.replication;

                const message_broker_container = document.getElementById(
                    "message_broker_status_" + site_id,
                )!;
                /* eslint-disable-next-line no-unsanitized/property -- Highlight existing violations CMK-17846 */
                message_broker_container.innerHTML = site_status.message_broker;
            }
        },
        error_handler: function (
            _handler_data: any,
            status_code: number,
            error_msg: string,
        ) {
            if (status_code != 0) {
                show_error(
                    "Site status update failed [" +
                        status_code +
                        "]: " +
                        error_msg,
                );
            }
        },
        method: "POST",
        add_ajax_id: false,
    });
}

function show_error(msg: string) {
    const o = document.getElementById("message_container");
    /* eslint-disable-next-line no-unsanitized/property -- Highlight existing violations CMK-17846 */
    o!.innerHTML = "<div class=error>" + msg + "</div>";

    // Remove all loading icons
    $(".reloading").remove();
}
