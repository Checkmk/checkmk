// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

import * as utils from "utils";

export function details_period_hover(td, sla_period, onoff) {
    if (utils.has_class(td, "lock_hilite")) {
        return;
    }

    var sla_period_elements = document.getElementsByClassName(sla_period);
    for (var i = 0; i < sla_period_elements.length; i++) {
        if (onoff) {
            utils.add_class(sla_period_elements[i], "sla_hilite");
        } else {
            utils.remove_class(sla_period_elements[i], "sla_hilite");
        }
    }
}

export function details_period_click(td, sla_period) {
    var sla_period_elements = document.getElementsByClassName(sla_period);
    var onoff = utils.has_class(td, "lock_hilite");
    for (var i = 0; i < sla_period_elements.length; i++) {
        if (onoff) {
            utils.remove_class(sla_period_elements[i], "sla_hilite");
            utils.remove_class(sla_period_elements[i], "lock_hilite");
        } else {
            utils.add_class(sla_period_elements[i], "sla_hilite");
            utils.add_class(sla_period_elements[i], "lock_hilite");
        }
    }
}

export function details_table_hover(tr, row_id, onoff) {
    var sla_period_elements = tr
        .closest("table")
        .closest("tbody")
        .getElementsByClassName(row_id);
    for (var i = 0; i < sla_period_elements.length; i++) {
        if (onoff) {
            utils.add_class(sla_period_elements[i], "sla_hilite");
            utils.add_class(sla_period_elements[i], "sla_error_hilite");
        } else {
            utils.remove_class(sla_period_elements[i], "sla_error_hilite");
            if (!utils.has_class(sla_period_elements[i], "lock_hilite")) {
                utils.remove_class(sla_period_elements[i], "sla_hilite");
            }
        }
    }
}
