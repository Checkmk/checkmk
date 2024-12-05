/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

//#.
//#   .-Designer--------------------------------------------------------------.
//#   |               ____            _                                       |
//#   |              |  _ \  ___  ___(_) __ _ _ __   ___ _ __                 |
//#   |              | | | |/ _ \/ __| |/ _` | '_ \ / _ \ '__|                |
//#   |              | |_| |  __/\__ \ | (_| | | | |  __/ |                   |
//#   |              |____/ \___||___/_|\__, |_| |_|\___|_|                   |
//#   |                                 |___/                                 |
//#   +-----------------------------------------------------------------------+
//#   |  Code for the interactive graph designed                              |
//#   '-----------------------------------------------------------------------'

function count_graph_designer_checked_checkbox() {
    const all_checkboxes = document.querySelectorAll(
        "#form_graph input[type='checkbox']",
    ) as NodeListOf<HTMLInputElement>;
    return Array.from(all_checkboxes).filter(el => el.checked).length;
}

export function fix_graph_designer_operator_visibiliy() {
    toggle_graph_designer_block_visibility(
        "graph_designer_operators",
        count_graph_designer_checked_checkbox() >= 2,
    );
}

export function fix_graph_designer_transform_visibiliy() {
    toggle_graph_designer_block_visibility(
        "graph_designer_transformations",
        count_graph_designer_checked_checkbox() == 1,
    );
}

export function toggle_graph_designer_block_visibility(
    elementid: string,
    visible: boolean,
) {
    const block = document.getElementById(elementid);
    const block_off = document.getElementById(elementid + "_off");
    if (!(block && block_off))
        throw new Error("block and block_off shouldn't be null!");
    if (visible) {
        block.style.display = "";
        block_off.style.display = "none";
    } else {
        block.style.display = "none";
        block_off.style.display = "";
    }
}
