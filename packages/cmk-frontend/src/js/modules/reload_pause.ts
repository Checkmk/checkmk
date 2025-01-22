/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import {stop_reload_timer} from "./utils";

// Stores the reload pause timer object once the regular reload has
// been paused e.g. by modifying a graphs timerange or vertical axis.
let g_reload_pause_timer: number | null = null;

// Sets the reload timer in pause mode for X seconds. This is shown to
// the user with a pause overlay icon. The icon also shows the time when
// the pause ends. Once the user clicks on the pause icon or the time
// is reached, the whole page is reloaded.
export function pause(seconds: number) {
    stop_reload_timer();
    draw_overlay(seconds);
    // Reset the timer if pause was used. Otherwise the page will reload even
    // in pause mode.
    if (g_reload_pause_timer) {
        clearTimeout(g_reload_pause_timer);
        return;
    }
    set_timer(seconds);
}

export function stop() {
    if (!g_reload_pause_timer) return;

    clearTimeout(g_reload_pause_timer);
    g_reload_pause_timer = null;

    const counter = document.getElementById("reload_pause_counter");
    if (counter) counter.style.display = "none";
}

function set_timer(seconds: number) {
    g_reload_pause_timer = window.setTimeout(function () {
        update_timer(seconds);
    }, 1000);
}

function update_timer(seconds_left: number) {
    seconds_left -= 1;

    if (seconds_left <= 0) {
        window.location.reload();
    } else {
        // update the pause counter
        const counter = document.getElementById("reload_pause_counter");
        if (counter) {
            /* eslint-disable-next-line no-unsanitized/property -- Highlight existing violations CMK-17846 */
            counter.innerHTML = seconds_left.toString();
        }

        g_reload_pause_timer = window.setTimeout(function () {
            update_timer(seconds_left);
        }, 1000);
    }
}

function draw_overlay(seconds: number) {
    let container = <HTMLAnchorElement>document.getElementById("reload_pause");
    if (container) {
        // only render once. Just update the counter.
        const existingCounter = document.getElementById(
            "reload_pause_counter",
        )!;
        /* eslint-disable-next-line no-unsanitized/property -- Highlight existing violations CMK-17846 */
        existingCounter.innerHTML = seconds.toString();
        return;
    }

    container = <HTMLAnchorElement>document.createElement("a");
    container.setAttribute("id", "reload_pause");
    container.href = "javascript:window.location.reload(false)";
    // FIXME: Localize
    container.title = "Page update paused. Click for reload.";

    const p1 = document.createElement("div");
    p1.className = "pause_bar p1";
    container.appendChild(p1);

    const p2 = document.createElement("div");
    p2.className = "pause_bar p2";
    container.appendChild(p2);

    container.appendChild(document.createElement("br"));

    const counter = document.createElement("a");
    counter.setAttribute("id", "reload_pause_counter");
    // FIXME: Localize
    counter.title = "Click to stop the countdown.";
    counter.href = "javascript:cmk.reload_pause.stop()";
    container.appendChild(counter);

    document.body.appendChild(container);
}
