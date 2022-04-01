// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

import * as utils from "utils";

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
interface element_dragging{
    dragging: any,
    moved: boolean,
    drop_handler: any,
}
var g_element_dragging :null|element_dragging= null;

export function start(event, dragger, dragging_tag, drop_handler) {
    if (!event) event = window.event;

    var button = utils.get_button(event);

    // Skip calls when already dragging or other button than left mouse
    if (g_element_dragging !== null || button != "LEFT") return true;

    // Find the first parent of the given tag type
    var dragging = dragger;
    while (dragging && dragging.tagName != dragging_tag) dragging = dragging.parentNode;

    if (dragging.tagName != dragging_tag)
        throw "Failed to find the parent node of " + dragger + " having the tag " + dragging_tag;

    utils.add_class(dragging, "dragging");

    g_element_dragging = {
        dragging: dragging,
        moved: false,
        drop_handler: drop_handler,
    };

    return utils.prevent_default_events(event);
}

function element_dragging(event) {
    if (!event) event = window.event;

    if (g_element_dragging === null) return true;

    position_dragging_object(event);
}

function position_dragging_object(event) {
    var dragging = g_element_dragging?.dragging,
        container = g_element_dragging?.dragging.parentNode;

    var get_previous = function (node) {
        var previous = node.previousElementSibling;

        // In case this is a header TR, don't move it above this!
        // TODO: Does not work with all tables! See comment in finalize_dragging()
        if (previous && previous.children && previous.children[0].tagName == "TH") return null;
        // Do not move above the action rows of tables rendered with "table.py"
        if (previous && utils.has_class(previous, "actions")) return null;

        return previous;
    };

    var get_next = function (node) {
        return node.nextElementSibling;
    };

    // Move it up?
    var previous = get_previous(dragging);
    while (previous && mouse_offset_to_middle(previous, event).y < 0) {
        g_element_dragging!.moved = true;
        container.insertBefore(dragging, previous);
        previous = get_previous(dragging);
    }

    // Move it down?
    var next = get_next(dragging);
    while (next && mouse_offset_to_middle(next, event).y > 0) {
        g_element_dragging!.moved = true;
        container.insertBefore(dragging, next.nextElementSibling);
        next = get_next(dragging);
    }
}

// mouse offset to the middle coordinates of an object
function mouse_offset_to_middle(obj, event) {
    var obj_pos = obj.getBoundingClientRect();
    var mouse_pos = utils.mouse_position(event);
    return {
        x: mouse_pos.x - (obj_pos.left + obj_pos.width / 2),
        y: mouse_pos.y - (obj_pos.top + obj_pos.height / 2),
    };
}

function element_drag_stop(event) {
    if (!event) event = window.event;

    if (g_element_dragging === null) return true;

    finalize_dragging();
    g_element_dragging = null;

    return utils.prevent_default_events(event);
}

function finalize_dragging() {
    var dragging = g_element_dragging?.dragging;
    utils.remove_class(dragging, "dragging");

    if (!g_element_dragging?.moved) return; // Nothing changed. Fine.

    var elements = dragging.parentNode.children;

    var index = Array.prototype.slice.call(elements).indexOf(dragging);

    // This currently makes the draggig work with tables having:
    // - no header
    // - one header line
    var has_header = elements[0].children[0].tagName == "TH";
    if (has_header) index -= 1;

    // - possible existing "table.py" second header (actions in tables)
    var has_action_row = elements.length > 1 && utils.has_class(elements[1], "actions");
    if (has_action_row) index -= 1;

    g_element_dragging.drop_handler(index);
}

export function url_drop_handler(base_url, index) {
    var url = base_url + "&_index=" + encodeURIComponent(index);
    location.href = url;
}

export function register_event_handlers() {
    utils.add_event_handler("mousemove", function (event) {
        return element_dragging(event);
    });

    utils.add_event_handler("mouseup", function (event) {
        return element_drag_stop(event);
    });
}
