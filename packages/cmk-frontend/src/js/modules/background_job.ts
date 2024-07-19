/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import {hide_msg, monitor, show_error} from "./async_progress";
import {execute_javascript_by_object, reload_whole_page} from "./utils";

interface BackGroundJobStart {
    status_container_content: string;
    is_finished: boolean;
    job_state?: string;
    message?: string;
}

export function start(update_url: string, job_id: string) {
    monitor({
        update_url: update_url,
        is_finished_function: response => response.is_finished,
        update_function: update,
        finish_function: finish,
        error_function: error,
        post_data:
            "request=" + encodeURIComponent(JSON.stringify({job_id: job_id})),
    });
}

function update(_handler_data: any, response: BackGroundJobStart) {
    hide_msg();

    const old_log = document.getElementById("progress_log");
    const scroll_pos = old_log ? old_log.scrollTop : 0;
    // Start with tail mode (when there is no progress_log before)
    const is_scrolled_down =
        !old_log || scroll_pos >= old_log.scrollHeight - old_log.clientHeight;

    const container = document.getElementById("status_container")!;
    container.style.display = "block";
    /* eslint-disable-next-line no-unsanitized/property -- Highlight existing violations CMK-17846 */
    container.innerHTML = response.status_container_content;
    execute_javascript_by_object(container);

    // Restore the previous scrolling state
    const new_log = document.getElementById("progress_log");
    if (new_log && is_scrolled_down) {
        new_log.scrollTop = new_log.scrollHeight - new_log.clientHeight;
    } else if (old_log) {
        new_log!.scrollTop = scroll_pos;
    }
}

function error(response: BackGroundJobStart) {
    show_error(String(response));
}

function finish(response: BackGroundJobStart) {
    if (response.job_state == "exception" || response.job_state == "stopped") {
        show_error(response.message!);
    } else {
        reload_whole_page();
    }
}
