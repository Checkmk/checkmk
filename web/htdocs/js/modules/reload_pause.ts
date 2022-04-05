// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

import * as utils from "utils";

// Stores the reload pause timer object once the regular reload has
// been paused e.g. by modifying a graphs timerange or vertical axis.
var g_reload_pause_timer: number | null = null;

// Sets the reload timer in pause mode for X seconds. This is shown to
// the user with a pause overlay icon. The icon also shows the time when
// the pause ends. Once the user clicks on the pause icon or the time
// is reached, the whole page is reloaded.
export function pause(seconds) {
    utils.stop_reload_timer();
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

    var counter = document.getElementById("reload_pause_counter");
    if (counter) counter.style.display = "none";
}

function set_timer(seconds) {
    g_reload_pause_timer = window.setTimeout(function () {
        update_timer(seconds);
    }, 1000);
}

function update_timer(seconds_left) {
    seconds_left -= 1;

    if (seconds_left <= 0) {
        window.location.reload();
    } else {
        // update the pause counter
        var counter = document.getElementById("reload_pause_counter");
        if (counter) {
            counter.innerHTML = seconds_left;
        }

        g_reload_pause_timer = window.setTimeout(function () {
            update_timer(seconds_left);
        }, 1000);
    }
}

function draw_overlay(seconds) {
    var container = <HTMLAnchorElement>document.getElementById("reload_pause");
    var counter;
    if (container) {
        // only render once. Just update the counter.
        counter = document.getElementById("reload_pause_counter");
        counter.innerHTML = seconds;
        return;
    }

    container = <HTMLAnchorElement>document.createElement("a");
    container.setAttribute("id", "reload_pause");
    container.href = "javascript:window.location.reload(false)";
    // FIXME: Localize
    container.title = "Page update paused. Click for reload.";

    var p1 = document.createElement("div");
    p1.className = "pause_bar p1";
    container.appendChild(p1);

    var p2 = document.createElement("div");
    p2.className = "pause_bar p2";
    container.appendChild(p2);

    container.appendChild(document.createElement("br"));

    counter = document.createElement("a");
    counter.setAttribute("id", "reload_pause_counter");
    // FIXME: Localize
    counter.title = "Click to stop the countdown.";
    counter.href = "javascript:cmk.reload_pause.stop()";
    container.appendChild(counter);

    document.body.appendChild(container);
}
