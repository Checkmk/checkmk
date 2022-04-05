// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

import * as utils from "utils";
import * as ajax from "ajax";

//#   .-Help Toggle--------------------------------------------------------.
//#   |          _   _      _         _____                 _              |
//#   |         | | | | ___| |_ __   |_   _|__   __ _  __ _| | ___         |
//#   |         | |_| |/ _ \ | '_ \    | |/ _ \ / _` |/ _` | |/ _ \        |
//#   |         |  _  |  __/ | |_) |   | | (_) | (_| | (_| | |  __/        |
//#   |         |_| |_|\___|_| .__/    |_|\___/ \__, |\__, |_|\___|        |
//#   |                      |_|                |___/ |___/                |
//#   '--------------------------------------------------------------------'

function is_help_active() {
    const helpdivs = document.getElementsByClassName(
        "help"
    ) as HTMLCollectionOf<HTMLElement>;
    return helpdivs.length !== 0 && helpdivs[0].style.display === "block";
}

export function toggle(title_show, title_hide) {
    if (is_help_active()) {
        switch_help(false);
        switch_help_text(title_show);
    } else {
        switch_help(true);
        switch_help_text(title_hide);
    }
}

function switch_help(how) {
    // recursive scan for all div class=help elements
    var helpdivs = document.getElementsByClassName(
        "help"
    ) as HTMLCollectionOf<HTMLElement>;
    var i;
    for (i = 0; i < helpdivs.length; i++) {
        helpdivs[i].style.display = how ? "block" : "none";
    }

    // small hack for wato ruleset lists, toggle the "float" and "nofloat"
    // classes on those objects to make the layout possible
    var rulesetdivs = document.getElementsByClassName("ruleset");
    for (i = 0; i < rulesetdivs.length; i++) {
        if (how) {
            if (utils.has_class(rulesetdivs[i], "float")) {
                utils.remove_class(rulesetdivs[i], "float");
                utils.add_class(rulesetdivs[i], "nofloat");
            }
        } else {
            if (utils.has_class(rulesetdivs[i], "nofloat")) {
                utils.remove_class(rulesetdivs[i], "nofloat");
                utils.add_class(rulesetdivs[i], "float");
            }
        }
    }

    ajax.get_url("ajax_switch_help.py?enabled=" + (how ? "yes" : ""));
}

function switch_help_text(title) {
    var helpspan = document.getElementById("menu_entry_inline_help")!
        .childNodes[0].childNodes[1];
    helpspan.textContent = title;
}
