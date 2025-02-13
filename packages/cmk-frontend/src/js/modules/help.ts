/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import {call_ajax} from "./ajax";
import {add_class, has_class, remove_class} from "./utils";

//#   .-Help Toggle--------------------------------------------------------.
//#   |          _   _      _         _____                 _              |
//#   |         | | | | ___| |_ __   |_   _|__   __ _  __ _| | ___         |
//#   |         | |_| |/ _ \ | '_ \    | |/ _ \ / _` |/ _` | |/ _ \        |
//#   |         |  _  |  __/ | |_) |   | | (_) | (_| | (_| | |  __/        |
//#   |         |_| |_|\___|_| .__/    |_|\___/ \__, |\__, |_|\___|        |
//#   |                      |_|                |___/ |___/                |
//#   '--------------------------------------------------------------------'

const SHOW_HELP_CLASS = "inline_help_as_text";

function is_help_active() {
    return has_class(document.body, SHOW_HELP_CLASS);
}

export function toggle() {
    if (is_help_active()) {
        switch_help(false);
    } else {
        switch_help(true);
    }
    toggle_help_page_menu_icon();
}

function switch_help(how: boolean) {
    if (how) add_class(document.body, SHOW_HELP_CLASS);
    else remove_class(document.body, SHOW_HELP_CLASS);

    call_ajax("ajax_switch_help.py?enabled=" + (how ? "yes" : ""));
}

function toggle_help_page_menu_icon() {
    const icon = document
        .getElementById("menu_entry_inline_help")!
        .getElementsByTagName("img")[0];
    icon.src = icon.src.includes("toggle_on")
        ? icon.src.replace("toggle_on", "toggle_off")
        : icon.src.replace("toggle_off", "toggle_on");
}
