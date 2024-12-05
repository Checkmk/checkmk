/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import {call_ajax} from "./ajax";

let iCurrent: number | null = null;
let oCurrent: HTMLAnchorElement | null = null;
let oldValue = "";

// Register an input field to be a search field and add eventhandlers
export function register_search_field(field: string) {
    const oField = document.getElementById(field) as HTMLInputElement | null;
    if (oField) {
        oField.onkeydown = function (e) {
            return mkSearchKeyDown(e, oField);
        };
        oField.onkeyup = function (e) {
            return mkSearchKeyUp(e, oField);
        };
        oField.onclick = function () {
            close_popup();
            return true;
        };

        // On doubleclick toggle the list
        oField.ondblclick = function () {
            toggle_popup(oField);
        };
    }
}

// On key release event handler
function mkSearchKeyUp(e: KeyboardEvent, oField: HTMLInputElement) {
    const keyCode = e.which || e.keyCode;

    switch (keyCode) {
        // 18: Return/Enter
        // 27: Escape
        case 13:
        case 27:
            close_popup();
            e.returnValue = false;
            e.cancelBubble = true;
            break;

        // Other keys
        default:
            if (oField.value == "") {
                e.returnValue = false;
                e.cancelBubble = true;
                close_popup();
            } else {
                mkSearch(oField);
            }
            break;
    }
}

// On key press down event handler
export function on_search_click() {
    const oField = document.getElementById(
        "mk_side_search_field",
    ) as HTMLInputElement;
    const ev = {which: 0, keyCode: 13} as KeyboardEvent;
    return mkSearchKeyDown(ev, oField);
}

function search_dropdown_value() {
    if (oCurrent) return oCurrent.id.replace("result_", "");
    else return null;
}

function mkSearchKeyDown(
    e: KeyboardEvent,
    oField: HTMLInputElement,
): false | void {
    const keyCode = e.which || e.keyCode;
    switch (keyCode) {
        // Return/Enter
        case 13:
            if (oCurrent != null) {
                mkSearchNavigate();
                oField.value = search_dropdown_value() ?? "";
                close_popup();
            } else {
                if (oField.value == "")
                    return; /* search field empty, rather not show all services! */
                // When nothing selected, navigate with the current contents of the field
                //@ts-ignore
                top!.frames["main"].location.href =
                    "search_open.py?q=" + encodeURIComponent(oField.value);
                close_popup();
            }

            e.returnValue = false;
            e.cancelBubble = true;
            break;

        // Escape
        case 27:
            close_popup();
            e.returnValue = false;
            e.cancelBubble = true;
            break;

        // Tab
        case 9:
            if (mkSearchResultShown()) {
                close_popup();
            }
            return;

        // Up/Down arrow (Must not be handled in onkeyup since this does not fire repeated events)
        case 38:
        case 40:
            if (!mkSearchResultShown()) {
                mkSearch(oField);
            }

            mkSearchMoveElement(keyCode == 38 ? -1 : 1);

            e.preventDefault();
            return false;
    }
    oldValue = oField.value;
}

// Navigate to the target of the selected event
function mkSearchNavigate() {
    //@ts-ignore
    top!.frames["main"].location.href = oCurrent!.href;
}

// Move one step of given size in the result list
function mkSearchMoveElement(step: number) {
    if (iCurrent == null) {
        iCurrent = -1;
    }

    iCurrent += step;

    let oResults: HTMLElement | null | HTMLElement[] =
        document.getElementById("mk_search_results");

    if (!oResults) return;

    if (iCurrent < 0) iCurrent = oResults.children.length - 1;

    if (iCurrent > oResults.children.length - 1) iCurrent = 0;

    oResults = Array.from(oResults.childNodes) as HTMLElement[];

    let a = 0;
    for (let i = 0; i < oResults.length; i++) {
        if (oResults[i].tagName == "A") {
            if (a == iCurrent) {
                oCurrent = oResults[i] as HTMLAnchorElement;
                oResults[i].setAttribute("class", "active");
            } else {
                oResults[i].setAttribute("class", "inactive");
            }
            a++;
        }
    }
}

// Is the result list shown at the moment?
function mkSearchResultShown() {
    return !!document.getElementById("mk_search_results");
}

// Toggle the result list
function toggle_popup(oField: HTMLInputElement) {
    if (mkSearchResultShown()) {
        close_popup();
    } else {
        mkSearch(oField);
    }
}

// Close the result list
export function close_popup() {
    const oContainer = document.getElementById("mk_search_results");
    if (oContainer) {
        oContainer.parentNode?.removeChild(oContainer);
    }

    iCurrent = null;
    oCurrent = null;
}

function handle_search_response(oField: HTMLInputElement, code: string) {
    if (code != "") {
        let oContainer = document.getElementById("mk_search_results");
        if (!oContainer) {
            oContainer = document.createElement("div");
            oContainer.setAttribute("id", "mk_search_results");
            oField.parentNode!.appendChild(oContainer);
        }

        /* eslint-disable-next-line no-unsanitized/property -- Highlight existing violations CMK-17846 */
        oContainer.innerHTML = code;
    } else {
        close_popup();
    }
}

let g_call_ajax_search_obj: null | XMLHttpRequest = null;

// Build a new result list and show it up
function mkSearch(oField: HTMLInputElement | null) {
    if (oField == null) return;

    kill_previous_quicksearch();

    const val = oField.value;
    if (mkSearchResultShown() && val == oldValue) return; // nothing changed, no new search
    oldValue = val;

    g_call_ajax_search_obj = call_ajax(
        "ajax_search.py?q=" + encodeURIComponent(val),
        {
            response_handler: handle_search_response,
            handler_data: oField,
        },
    );
}

function kill_previous_quicksearch() {
    // Terminate already running request
    if (g_call_ajax_search_obj) {
        g_call_ajax_search_obj.abort();
        g_call_ajax_search_obj = null;
    }
}
