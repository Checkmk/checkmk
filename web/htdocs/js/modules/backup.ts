// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

import * as utils from "utils";
import * as ajax from "ajax";

type BackupHandlerData = {url: string; ident: string; is_site: boolean};

export function refresh_job_details(
    url: string,
    ident: string,
    is_site: boolean
) {
    setTimeout(function () {
        do_job_detail_refresh(url, ident, is_site);
    }, 1000);
}

function do_job_detail_refresh(url: string, ident: string, is_site: boolean) {
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

function handle_job_detail_response(
    handler_data: BackupHandlerData,
    response_body: string
) {
    // when a message was shown and now not anymore, assume the job has finished
    const had_message = document.getElementById("job_detail_msg")
        ? true
        : false;

    const container = document.getElementById("job_details");
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

function handle_job_detail_error(
    handler_data: BackupHandlerData,
    status_code: number,
    error_msg: string
) {
    hide_job_detail_msg();

    if (status_code == 0) return; // ajax request aborted. Stop refresh.

    const container = document.getElementById("job_details");

    const msg = document.createElement("div");
    container?.insertBefore(msg, container.children[0]);
    msg.setAttribute("id", "job_detail_msg");
    msg.className = "message";

    let txt = "";
    if (handler_data.is_site)
        txt +=
            "The restore is still in progress. Please keep this page open until it's finished." +
            "<br><br>The site will automatically stop and restart during the restore process.";
    else
        txt +=
            "Could not update the job details. Maybe the device is currently being rebooted.";

    txt +=
        "<br>You may see error messages on this page while it is stopping and restarting." +
        "<br>These should disappear with the refresh at the end of the process.";

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
    const msg = document.getElementById("job_detail_msg");
    if (msg) msg.parentNode?.removeChild(msg);
}
