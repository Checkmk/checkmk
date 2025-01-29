/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import {add_event_handler} from "./utils";

function handle_main_menu_shortcuts(event: Event): void {
    if (!(event instanceof KeyboardEvent)) return;

    let menu_id = "";
    if (event.altKey && event.key.toLowerCase() === "m") {
        menu_id = "popup_trigger_mega_menu_monitoring";
    } else if (event.altKey && event.key.toLowerCase() === "s") {
        // Make sure this does not collide with browser shortcuts (Firefox)
        event.preventDefault();
        menu_id = "popup_trigger_mega_menu_setup";
    } else if (event.altKey && event.key.toLowerCase() === "c") {
        menu_id = "popup_trigger_mega_menu_customize";
    }

    // Get the top level document, when already executed from that context and
    // also when executed from the content frame document
    let menu_document = document;
    if (!document || !menu_document.getElementById("main_menu"))
        menu_document = window.parent.document;
    // If the context is within another iframe (for example view in dashboard)
    // the menu document is two layers above the current frame document
    if (!document || !menu_document.getElementById("main_menu"))
        menu_document = window.parent.parent.document;

    if (!menu_document || !menu_document.getElementById("main_menu")) return;

    const menu_item = menu_document.getElementById(menu_id);
    if (!menu_item) return;

    menu_item.getElementsByTagName("a")[0].click();
}

export function register_shortcuts(): void {
    add_event_handler("keydown", handle_main_menu_shortcuts, document);
}
