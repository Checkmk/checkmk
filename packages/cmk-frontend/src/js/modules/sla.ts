/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import {
    add_class,
    has_class,
    querySelectorAllByClassName,
    remove_class,
} from "./utils";

export function details_period_hover(
    td: HTMLTableCellElement,
    sla_period: string,
    onoff: 0 | 1,
) {
    if (has_class(td, "lock_hilite")) {
        return;
    }

    const sla_period_elements = querySelectorAllByClassName(sla_period);
    for (let i = 0; i < sla_period_elements.length; i++) {
        if (onoff) {
            add_class(sla_period_elements[i], "sla_hilite");
        } else {
            remove_class(sla_period_elements[i], "sla_hilite");
        }
    }
}

export function details_period_click(
    td: HTMLTableCellElement,
    sla_period: string,
) {
    const sla_period_elements = querySelectorAllByClassName(sla_period);
    const onoff = has_class(td, "lock_hilite");
    for (let i = 0; i < sla_period_elements.length; i++) {
        if (onoff) {
            remove_class(sla_period_elements[i], "sla_hilite");
            remove_class(sla_period_elements[i], "lock_hilite");
        } else {
            add_class(sla_period_elements[i], "sla_hilite");
            add_class(sla_period_elements[i], "lock_hilite");
        }
    }
}

export function details_table_hover(
    tr: HTMLTableRowElement,
    row_id: string,
    onoff: 1 | 0,
) {
    const sla_period_elements = tr
        .closest("table")!
        .closest("tbody")!
        .getElementsByClassName(row_id) as HTMLCollectionOf<HTMLElement>;
    for (let i = 0; i < sla_period_elements.length; i++) {
        if (onoff) {
            add_class(sla_period_elements[i], "sla_hilite");
            add_class(sla_period_elements[i], "sla_error_hilite");
        } else {
            remove_class(sla_period_elements[i], "sla_error_hilite");
            if (!has_class(sla_period_elements[i], "lock_hilite")) {
                remove_class(sla_period_elements[i], "sla_hilite");
            }
        }
    }
}
