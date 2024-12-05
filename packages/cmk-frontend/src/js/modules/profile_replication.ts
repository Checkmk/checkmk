/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import {call_ajax} from "./ajax";
import type {CMKAjaxReponse} from "./types";
import {reload_whole_page} from "./utils";

type ReplicationImage =
    | "repl_success"
    | "repl_failed"
    | "repl_75"
    | "repl_50"
    | "repl_25"
    | "repl_pending";

let g_num_replsites = 0;
let g_back_url = "";
const profile_replication_progress: Record<string, number> = {};

export function prepare(num: number, back_url: string) {
    g_num_replsites = num;
    g_back_url = back_url;
}

export function start(siteid: string, est: number, progress_text: string) {
    call_ajax("wato_ajax_profile_repl.py", {
        response_handler: function (
            handler_data: {site_id: string},
            response_json: string,
        ) {
            const response: CMKAjaxReponse<string> = JSON.parse(response_json);

            const success = response.result_code === 0;
            const msg = response.result;

            set_result(handler_data["site_id"], success, msg);
        },
        error_handler: function (
            handler_data: {
                site_id: string;
            },
            status_code: number,
            error_msg: string,
        ) {
            set_result(
                handler_data["site_id"],
                false,
                "Failed to perform profile replication [" +
                    status_code +
                    "]: " +
                    error_msg,
            );
        },
        method: "POST",
        post_data:
            "request=" +
            encodeURIComponent(
                JSON.stringify({
                    site: siteid,
                }),
            ),
        handler_data: {
            site_id: siteid,
        },
        add_ajax_id: false,
    });

    profile_replication_progress[siteid] = 20; // 10 of 10 10ths
    setTimeout(step, est / 20, siteid, est, progress_text);
}

function set_status(siteid: string, image: ReplicationImage, text: string) {
    const icon = document
        .getElementById("site-" + siteid)!
        .getElementsByClassName("repl_status")[0];
    (icon as HTMLElement).title = text;
    icon.className = "icon repl_status " + image;
}

export function step(siteid: string, est: number, progress_text: string) {
    if (profile_replication_progress[siteid] > 0) {
        profile_replication_progress[siteid]--;
        const perc = ((20.0 - profile_replication_progress[siteid]) * 100) / 20;
        let img: ReplicationImage;
        if (perc >= 75) img = "repl_75";
        else if (perc >= 50) img = "repl_50";
        else if (perc >= 25) img = "repl_25";
        else img = "repl_pending";
        set_status(siteid, img, progress_text);
        setTimeout(step, est / 20, siteid, est, progress_text);
    }
}

function set_result(site_id: string, success: boolean, msg: string) {
    profile_replication_progress[site_id] = 0;

    const icon_name = success ? "repl_success" : "repl_failed";

    set_status(site_id, icon_name, msg);

    g_num_replsites--;
    if (g_num_replsites == 0) {
        setTimeout(finish, 1000);
    }
}

function finish() {
    reload_whole_page(g_back_url);
}
