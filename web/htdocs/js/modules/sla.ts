/**
 * Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import * as utils from "utils";

export function details_period_hover(
    td: HTMLTableCellElement,
    sla_period: string,
    onoff: 0 | 1
) {
    if (utils.has_class(td, "lock_hilite")) {
        return;
    }

    const sla_period_elements = utils.querySelectorAllByClassName(sla_period);
    for (let i = 0; i < sla_period_elements.length; i++) {
        if (onoff) {
            utils.add_class(sla_period_elements[i], "sla_hilite");
        } else {
            utils.remove_class(sla_period_elements[i], "sla_hilite");
        }
    }
}

export function details_period_click(
    td: HTMLTableCellElement,
    sla_period: string
) {
    const sla_period_elements = utils.querySelectorAllByClassName(sla_period);
    const onoff = utils.has_class(td, "lock_hilite");
    for (let i = 0; i < sla_period_elements.length; i++) {
        if (onoff) {
            utils.remove_class(sla_period_elements[i], "sla_hilite");
            utils.remove_class(sla_period_elements[i], "lock_hilite");
        } else {
            utils.add_class(sla_period_elements[i], "sla_hilite");
            utils.add_class(sla_period_elements[i], "lock_hilite");
        }
    }
}

export function details_table_hover(
    tr: HTMLTableRowElement,
    row_id: string,
    onoff: 1 | 0
) {
    const sla_period_elements = tr
        .closest("table")!
        .closest("tbody")!
        .getElementsByClassName(row_id) as HTMLCollectionOf<HTMLElement>;
    for (let i = 0; i < sla_period_elements.length; i++) {
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
