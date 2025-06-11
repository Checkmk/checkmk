/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import {KeyShortcutService} from "./keyShortcuts";

export function handle_main_menu(id: string): void {
    const menu_id = "popup_trigger_main_menu_".concat(id);
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

export function register_shortcuts(keyShortcuts: KeyShortcutService): void {
    keyShortcuts.on(
        {
            key: ["m"],
            alt: true,
        },
        () => {
            handle_main_menu("monitoring");
        },
    );

    keyShortcuts.on(
        {
            key: ["c"],
            alt: true,
        },
        () => {
            handle_main_menu("customize");
        },
    );

    keyShortcuts.on(
        {
            key: ["s"],
            alt: true,
        },
        () => {
            handle_main_menu("setup");
        },
    );
}
