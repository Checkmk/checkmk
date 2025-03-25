/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import {call_ajax} from "./ajax";
import {add_class, remove_class, time} from "./utils";

//#.
//#   .-AsyncProg.---------------------------------------------------------.
//#   |           _                         ____                           |
//#   |          / \   ___ _   _ _ __   ___|  _ \ _ __ ___   __ _          |
//#   |         / _ \ / __| | | | '_ \ / __| |_) | '__/ _ \ / _` |         |
//#   |        / ___ \\__ \ |_| | | | | (__|  __/| | | (_) | (_| |_        |
//#   |       /_/   \_\___/\__, |_| |_|\___|_|   |_|  \___/ \__, (_)       |
//#   |                    |___/                            |___/          |
//#   +--------------------------------------------------------------------+
//#   | Generic asynchronous process handling used by activate changes and |
//#   | the service discovery dialogs                                      |
//#   '--------------------------------------------------------------------'

// How long to wait before showing an error message when the site is restarting.
const siteRestartWaitTime = 30;

interface AsyncProgressHandlerData {
    update_url: string;
    error_function: (arg0: any) => void;
    update_function: (arg0: any, arg1: any) => void;
    is_finished_function: (arg0: any) => any;
    finish_function: (arg0: any) => void;
    post_data: string;
    start_time?: number;
    host_name?: string;
    folder_path?: string;
    transid?: string;
}

// Is called after the activation has been started (got the activation_id) and
// then in interval of 500 ms for updating the dialog state
export function monitor(handler_data: AsyncProgressHandlerData) {
    call_ajax(handler_data.update_url, {
        response_handler: handle_update,
        error_handler: handle_error,
        handler_data: handler_data,
        method: "POST",
        post_data: handler_data.post_data,
        add_ajax_id: false,
    });
}

function handle_update(
    handler_data: AsyncProgressHandlerData,
    response_json: string,
) {
    const response = JSON.parse(response_json);
    if (response.result_code == 1) {
        handler_data.error_function(response.result);
        return; // Abort on error!
    } else {
        handler_data.update_function(handler_data, response.result);

        if (!handler_data.is_finished_function(response.result)) {
            setTimeout(function () {
                return monitor(handler_data);
            }, 500);
        } else {
            handler_data.finish_function(response.result);
        }
    }
}

function handle_error(
    handler_data: AsyncProgressHandlerData,
    status_code: string | number,
    error_msg: string,
) {
    if (
        time() - handler_data.start_time! <= siteRestartWaitTime &&
        status_code == 503
    ) {
        show_info(
            "Fetching site state... This may take up to 30 seconds when a site restart is required.",
        );
    } else if (status_code == 0) {
        return; // not really an error. Reached when navigating away from the page
    } else {
        show_error(
            "Failed to fetch state [" +
                status_code +
                "]: " +
                error_msg +
                ". " +
                "Retrying in 1 second." +
                "<br><br>" +
                "In case this error persists for more than some seconds, please verify that all " +
                "processes of the site are running.",
        );
    }

    setTimeout(function () {
        return monitor(handler_data);
    }, 1000);
}

export function show_error(text: string) {
    const container = document.getElementById("async_progress_msg")!;
    container.style.display = "block";
    const msg = container.childNodes[0] as HTMLElement;

    add_class(msg, "error");
    remove_class(msg, "success");

    /* eslint-disable-next-line no-unsanitized/property -- Highlight existing violations CMK-17846 */
    msg.innerHTML = text;
}

export function show_info(text: string) {
    const container = document.getElementById("async_progress_msg")!;
    container.style.display = "block";

    let msg = container.childNodes[0] as HTMLElement;
    if (!msg) {
        msg = document.createElement("div");
        container.appendChild(msg);
    }

    add_class(msg, "success");
    remove_class(msg, "error");

    /* eslint-disable-next-line no-unsanitized/property -- Highlight existing violations CMK-17846 */
    msg.innerHTML = text;
}

export function hide_msg() {
    const msg = document.getElementById("async_progress_msg");
    if (msg) msg.style.display = "none";
}
