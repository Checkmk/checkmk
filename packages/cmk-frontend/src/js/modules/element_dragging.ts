/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import {
    add_class,
    add_event_handler,
    get_button,
    has_class,
    mouse_position,
    prevent_default_events,
    remove_class,
} from "./utils";

//#   .-ElementDrag--------------------------------------------------------.
//#   |     _____ _                           _   ____                     |
//#   |    | ____| | ___ _ __ ___   ___ _ __ | |_|  _ \ _ __ __ _  __ _    |
//#   |    |  _| | |/ _ \ '_ ` _ \ / _ \ '_ \| __| | | | '__/ _` |/ _` |   |
//#   |    | |___| |  __/ | | | | |  __/ | | | |_| |_| | | | (_| | (_| |   |
//#   |    |_____|_|\___|_| |_| |_|\___|_| |_|\__|____/|_|  \__,_|\__, |   |
//#   |                                                           |___/    |
//#   +--------------------------------------------------------------------+
//#   | Generic GUI element dragger. The user can grab an elment, drag it  |
//#   | and moves a parent element of the picked element to another place. |
//#   | On dropping, the page is being reloaded for persisting the move.   |
//#   '--------------------------------------------------------------------
interface element_dragging {
    dragging: any;
    moved: boolean;
    drop_handler: (index: number) => void;
}

let g_element_dragging: null | element_dragging = null;

export function start(
    event: Event,
    dragger: HTMLAnchorElement,
    dragging_tag: string,
    drop_handler: (index: number) => void,
) {
    const button = get_button(event as MouseEvent);

    // Skip calls when already dragging or other button than left mouse
    if (g_element_dragging !== null || button != "LEFT") return true;

    // Find the first parent of the given tag type
    let dragging: HTMLAnchorElement | null | ParentNode = dragger;

    while (dragging instanceof HTMLElement && dragging.tagName != dragging_tag)
        dragging = dragging.parentNode;

    if ((dragging as HTMLElement).tagName != dragging_tag)
        throw (
            "Failed to find the parent node of " +
            dragger +
            " having the tag " +
            dragging_tag
        );

    add_class(dragging as HTMLElement, "dragging");

    g_element_dragging = {
        dragging: dragging,
        moved: false,
        drop_handler: drop_handler,
    };

    return prevent_default_events(event);
}

function element_dragging(event: MouseEvent): true | void {
    if (g_element_dragging === null) return true;

    position_dragging_object(event);
}

function position_dragging_object(event: MouseEvent) {
    const dragging = g_element_dragging?.dragging;
    const container = g_element_dragging?.dragging.parentNode;

    const get_previous = function (node: Element) {
        const previous = node.previousElementSibling;

        // In case this is a header TR, don't move it above this!
        // TODO: Does not work with all tables! See comment in finalize_dragging()
        if (
            previous &&
            previous.children &&
            previous.children[0].tagName == "TH"
        )
            return null;
        // Do not move above the action rows of tables rendered with "table.py"
        if (previous && has_class(previous as HTMLElement, "actions"))
            return null;

        return previous;
    };

    const get_next = function (node: Element) {
        return node.nextElementSibling;
    };

    // Move it up?
    let previous = get_previous(dragging);
    while (previous && mouse_offset_to_middle(previous, event).y < 0) {
        g_element_dragging!.moved = true;
        container.insertBefore(dragging, previous);
        previous = get_previous(dragging);
    }

    // Move it down?
    let next = get_next(dragging);
    while (next && mouse_offset_to_middle(next, event).y > 0) {
        g_element_dragging!.moved = true;
        container.insertBefore(dragging, next.nextElementSibling);
        next = get_next(dragging);
    }
}

// mouse offset to the middle coordinates of an object
function mouse_offset_to_middle(obj: Element, event: MouseEvent) {
    const obj_pos = obj.getBoundingClientRect();
    const mouse_pos = mouse_position(event);
    return {
        x: mouse_pos.x - (obj_pos.left + obj_pos.width / 2),
        y: mouse_pos.y - (obj_pos.top + obj_pos.height / 2),
    };
}

function element_drag_stop(event: Event) {
    if (g_element_dragging === null) return true;

    finalize_dragging();
    g_element_dragging = null;

    return prevent_default_events(event);
}

function finalize_dragging() {
    const dragging = g_element_dragging?.dragging;
    remove_class(dragging, "dragging");

    if (!g_element_dragging?.moved) return; // Nothing changed. Fine.

    const elements = dragging.parentNode.children;

    let index = Array.prototype.slice.call(elements).indexOf(dragging);

    // This currently makes the draggig work with tables having:
    // - no header
    // - one header line
    const has_header = elements[0].children[0].tagName == "TH";
    if (has_header) index -= 1;

    // - possible existing "table.py" second header (actions in tables)
    const has_action_row =
        elements.length > 1 && has_class(elements[1], "actions");
    if (has_action_row) index -= 1;

    g_element_dragging.drop_handler(index);
}

export function url_drop_handler(base_url: string, index: number) {
    const url = base_url + "&_index=" + encodeURIComponent(index);
    location.href = url;
}

export function register_event_handlers() {
    add_event_handler("mousemove", function (event: Event) {
        return element_dragging(event as MouseEvent);
    });

    add_event_handler("mouseup", function (event: Event) {
        return element_drag_stop(event);
    });
}
