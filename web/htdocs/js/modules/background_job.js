// Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

import * as async_progress from "async_progress";
import * as utils from "utils";

export function start(update_url, job_id) {
    async_progress.monitor({
        update_url: update_url,
        is_finished_function: response => response.is_finished,
        update_function: update,
        finish_function: finish,
        error_function: error,
        post_data: "request=" + encodeURIComponent(JSON.stringify({job_id: job_id})),
    });
}

function update(handler_data, response) {
    async_progress.hide_msg();

    const old_log = document.getElementById("progress_log");
    const scroll_pos = old_log ? old_log.scrollTop : 0;
    // Start with tail mode (when there is no progress_log before)
    const is_scrolled_down = !old_log || scroll_pos >= old_log.scrollHeight - old_log.clientHeight;

    const container = document.getElementById("status_container");
    container.style.display = "block";
    container.innerHTML = response.status_container_content;
    utils.execute_javascript_by_object(container);

    // Restore the previous scrolling state
    const new_log = document.getElementById("progress_log");
    if (new_log && is_scrolled_down) {
        new_log.scrollTop = new_log.scrollHeight - new_log.clientHeight;
    } else if (old_log) {
        new_log.scrollTop = scroll_pos;
    }
}

function error(response) {
    async_progress.show_error(response);
}

function finish(response) {
    if (response.job_state == "exception" || response.job_state == "stopped") {
        async_progress.show_error(response.message);
    }
}
