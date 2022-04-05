// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

import * as ajax from "ajax";
import * as utils from "utils";

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

// Is called after the activation has been started (got the activation_id) and
// then in interval of 500 ms for updating the dialog state
export function monitor(handler_data) {
    ajax.call_ajax(handler_data.update_url, {
        response_handler: handle_update,
        error_handler: handle_error,
        handler_data: handler_data,
        method: "POST",
        post_data: handler_data.post_data,
        add_ajax_id: false,
    });
}

function handle_update(handler_data, response_json) {
    var response = JSON.parse(response_json);
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

function handle_error(handler_data, status_code, error_msg) {
    if (utils.time() - handler_data.start_time <= 10 && status_code == 503) {
        show_info(
            "Failed to fetch state. This may be normal for a period of some seconds."
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
                "processes of the site are running."
        );
    }

    setTimeout(function () {
        return monitor(handler_data);
    }, 1000);
}

export function show_error(text) {
    var container = document.getElementById("async_progress_msg")!;
    container.style.display = "block";
    var msg = container.childNodes[0] as HTMLElement;

    utils.add_class(msg, "error");
    utils.remove_class(msg, "success");

    msg.innerHTML = text;
}

export function show_info(text) {
    const container = document.getElementById("async_progress_msg")!;
    container.style.display = "block";

    let msg = container.childNodes[0] as HTMLElement;
    if (!msg) {
        msg = document.createElement("div");
        container.appendChild(msg);
    }

    utils.add_class(msg, "success");
    utils.remove_class(msg, "error");

    msg.innerHTML = text;
}

export function hide_msg() {
    var msg = document.getElementById("async_progress_msg");
    if (msg) msg.style.display = "none";
}
