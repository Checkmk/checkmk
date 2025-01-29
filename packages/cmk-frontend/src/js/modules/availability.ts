/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import {add_class, remove_class} from "./utils";

export function timeline_hover(
    timeline_nr: number,
    row_nr: number,
    onoff: number,
) {
    const row = document.getElementById(
        "timetable_" + timeline_nr + "_entry_" + row_nr,
    );
    if (!row) return;

    if (onoff) {
        add_class(row, "hilite");
    } else {
        remove_class(row, "hilite");
    }
}

export function timetable_hover(
    timeline_nr: number,
    row_nr: number,
    onoff: number,
) {
    const slice = document.getElementById(
        "timeline_" + timeline_nr + "_entry_" + row_nr,
    );
    if (!slice) return;

    if (onoff) {
        add_class(slice, "hilite");
    } else {
        remove_class(slice, "hilite");
    }
}
