// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

import * as utils from "utils";

export function timeline_hover(timeline_nr, row_nr, onoff) {
    var row = document.getElementById(
        "timetable_" + timeline_nr + "_entry_" + row_nr
    );
    if (!row) return;

    if (onoff) {
        utils.add_class(row, "hilite");
    } else {
        utils.remove_class(row, "hilite");
    }
}

export function timetable_hover(timeline_nr, row_nr, onoff) {
    var slice = document.getElementById(
        "timeline_" + timeline_nr + "_entry_" + row_nr
    );
    if (!slice) return;

    if (onoff) {
        utils.add_class(slice, "hilite");
    } else {
        utils.remove_class(slice, "hilite");
    }
}
