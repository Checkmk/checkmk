// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

import * as utils from "utils";
import * as ajax from "ajax";

export function refresh_job_details(url, ident, is_site) {
    setTimeout(function () {
        do_job_detail_refresh(url, ident, is_site);
    }, 1000);
}

function do_job_detail_refresh(url, ident, is_site) {
    ajax.call_ajax(url, {
        method: "GET",
        post_data: "job=" + encodeURIComponent(ident),
        response_handler: handle_job_detail_response,
        error_handler: handle_job_detail_error,
        handler_data: {
            url: url,
            ident: ident,
            is_site: is_site,
        },
    });
}

function handle_job_detail_response(handler_data, response_body) {
    // when a message was shown and now not anymore, assume the job has finished
    var had_message = document.getElementById("job_detail_msg") ? true : false;

    var container = document.getElementById("job_details");
    container!.innerHTML = response_body;

    if (!had_message) {
        refresh_job_details(
            handler_data["url"],
            handler_data["ident"],
            handler_data["is_site"]
        );
    } else {
        utils.reload_whole_page();
    }
}

function handle_job_detail_error(handler_data, status_code, error_msg) {
    hide_job_detail_msg();

    if (status_code == 0) return; // ajax request aborted. Stop refresh.

    var container = document.getElementById("job_details");

    var msg = document.createElement("div");
    container?.insertBefore(msg, container.children[0]);
    msg.setAttribute("id", "job_detail_msg");
    msg.className = "message";

    var txt = "Could not update the job details.";
    if (handler_data.is_site)
        txt += " The site will be started again after the restore.";
    else txt += " Maybe the device is currently being rebooted.";

    txt += "<br>Will continue trying to refresh the job details.";

    txt += "<br><br>HTTP status code: " + status_code;
    if (error_msg) txt += ", Error: " + error_msg;

    msg.innerHTML = txt;

    refresh_job_details(
        handler_data["url"],
        handler_data["ident"],
        handler_data["is_site"]
    );
}

function hide_job_detail_msg() {
    var msg = document.getElementById("job_detail_msg");
    if (msg) msg.parentNode?.removeChild(msg);
}
