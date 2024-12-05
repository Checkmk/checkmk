/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import {add_class, remove_class} from "./utils";

//#   .--Visibility----------------------------------------------------------.
//#   |               __     ___     _ _     _ _ _ _                         |
//#   |               \ \   / (_)___(_) |__ (_) (_) |_ _   _                 |
//#   |                \ \ / /| / __| | '_ \| | | | __| | | |                |
//#   |                 \ V / | \__ \ | |_) | | | | |_| |_| |                |
//#   |                  \_/  |_|___/_|_.__/|_|_|_|\__|\__, |                |
//#   |                                                |___/                 |
//#   +----------------------------------------------------------------------+
//#   | Code for detecting the visibility of the current browser window/tab  |
//#   '----------------------------------------------------------------------'

let g_visibility_detection_enabled = true;

export function initialize() {
    let hidden_attr_name = "hidden";

    // Standards:
    if (hidden_attr_name in document)
        document.addEventListener("visibilitychange", on_visibility_change);
    else if ((hidden_attr_name = "mozHidden") in document)
        document.addEventListener("mozvisibilitychange", on_visibility_change);
    else if ((hidden_attr_name = "webkitHidden") in document)
        document.addEventListener(
            "webkitvisibilitychange",
            on_visibility_change,
        );
    else if ((hidden_attr_name = "msHidden") in document)
        document.addEventListener("msvisibilitychange", on_visibility_change);

    // This feature will not support IE 9 and lower or other incompatible
    // browsers. By enabling the code below we could add the support, but
    // we need to be sure that these assignments don't conflict with other
    // already registered event handlers.
    //else if ("onfocusin" in document) {
    //    // IE 9 and lower:
    //    document.onfocusin = document.onfocusout = onchange;
    //}
    //else {
    //    // All others:
    //    window.onpageshow = window.onpagehide
    //        = window.onfocus = window.onblur = onchange;
    //}

    window.addEventListener("beforeunload", disable_visibility_detection);

    function disable_visibility_detection() {
        g_visibility_detection_enabled = false;
    }

    function on_visibility_change(evt: {type: string}) {
        const v = "visible",
            h = "hidden",
            evtMap: Record<string, "visible" | "hidden"> = {
                focus: v,
                focusin: v,
                pageshow: v,
                blur: h,
                focusout: h,
                pagehide: h,
            };

        if (!g_visibility_detection_enabled) return;

        remove_class(document.body, "visible");
        remove_class(document.body, "hidden");

        let new_class: "visible" | "hidden";
        if (evt.type in evtMap) {
            new_class = evtMap[evt.type];
        } else {
            new_class = this[hidden_attr_name] ? "hidden" : "visible";
        }

        //console.log([evt.type, new_class, document.hidden, location.href]);
        add_class(document.body, new_class);
    }

    // set the initial state (but only if browser supports the Page Visibility API)
    //@ts-ignore
    if (document[hidden_attr_name] !== undefined)
        on_visibility_change({
            //@ts-ignore
            type: document[hidden_attr_name] ? "blur" : "focus",
        });
}
