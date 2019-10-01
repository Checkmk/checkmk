// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
// +------------------------------------------------------------------+
//
// This file is part of Check_MK.
// The official homepage is at http://mathias-kettner.de/check_mk.
//
// check_mk is free software;  you can redistribute it and/or modify it
// under the  terms of the  GNU General Public License  as published by
// the Free Software Foundation in version 2.  check_mk is  distributed
// in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
// out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
// PARTICULAR PURPOSE. See the  GNU General Public License for more de-
// tails.  You should have received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

import * as utils from "utils";
import * as ajax from "ajax";
import * as foldable_container from "foldable_container";

var g_dial_direction = 1;
var g_last_optiondial = null;

export function init_optiondial(id)
{
    var container = document.getElementById(id);
    make_unselectable(container);
    utils.add_event_handler(utils.wheel_event_name(), optiondial_wheel, container);
}

function make_unselectable(elem)
{
    elem.onselectstart = function() { return false; };
    elem.style.MozUserSelect = "none";
    elem.style.KhtmlUserSelect = "none";
    elem.unselectable = "on";
}

function optiondial_wheel(event) {
    event = event || window.event;
    var delta = utils.wheel_event_delta(event);

    // allow updates every 100ms
    if (g_last_optiondial > utils.time() - 0.1) {
        return utils.prevent_default_events(event);
    }
    g_last_optiondial = utils.time();

    var container = utils.get_target(event);
    if (event.nodeType == 3) // defeat Safari bug
        container = container.parentNode;
    while (!container.className)
        container = container.parentNode;

    if (delta > 0)
        g_dial_direction = -1;
    container.onclick(event);
    g_dial_direction = 1;

    return utils.prevent_default_events(event);
}

// used for refresh und num_columns
export function dial_option(oDiv, viewname, option, choices) {
    // prevent double click from select text
    var new_choice = choices[0]; // in case not contained in choices
    for (var c = 0, choice = null, val = null; c < choices.length; c++) {
        choice = choices[c];
        val = choice[0];
        if (utils.has_class(oDiv, "val_" + val)) {
            new_choice = choices[(c + choices.length + g_dial_direction) % choices.length];
            utils.change_class(oDiv, "val_" + val, "val_" + new_choice[0]);
            break;
        }
    }

    // Start animation
    var step = 0;
    var speed = 10;
    var way;

    for (way = 0; way <= 10; way +=1) {
        step += speed;
        setTimeout(function(option, text, way, direction) {
            return function() {
                turn_dial(option, text, way, direction);
            };
        }(option, "", way, g_dial_direction), step);
    }

    for (way = -10; way <= 0; way +=1) {
        step += speed;
        setTimeout(function(option, text, way, direction) {
            return function() {
                turn_dial(option, text, way, direction);
            };
        }(option, new_choice[1], way, g_dial_direction), step);
    }

    var url = "ajax_set_viewoption.py?view_name=" + viewname +
              "&option=" + option + "&value=" + new_choice[0];
    ajax.call_ajax(url, {
        method           : "GET",
        response_handler : function(handler_data) {
            if (handler_data.option == "refresh")
                utils.set_reload(handler_data.new_value);
            else
                utils.schedule_reload("", 400.0);
        },
        handler_data     : {
            new_value : new_choice[0],
            option    : option
        }
    });
}

// way ranges from -10 to 10 means centered (normal place)
function turn_dial(option, text, way, direction)
{
    var oDiv = document.getElementById("optiondial_" + option).getElementsByTagName("DIV")[0];
    if (text && oDiv.innerHTML != text)
        oDiv.innerHTML = text;
    oDiv.style.top = (way * 1.3 * direction) + "px";
}

export function toggle_grouped_rows(tree, id, cell, num_rows)
{
    var group_title_row = cell.parentNode;

    var display, toggle_img_open, state;
    if (utils.has_class(group_title_row, "closed")) {
        utils.remove_class(group_title_row, "closed");
        display = "";
        toggle_img_open = true;
        state = "on";
    }
    else {
        utils.add_class(group_title_row, "closed");
        display = "none";
        toggle_img_open = false;
        state = "off";
    }

    utils.toggle_folding(cell.getElementsByTagName("IMG")[0], toggle_img_open);
    foldable_container.persist_tree_state(tree, id, state);

    var row = group_title_row;
    for (var i = 0; i < num_rows; i++) {
        row = row.nextElementSibling;
        row.style.display = display;
    }
}

export function reschedule_check(oLink, site, host, service, wait_svc) {
    var img = oLink.getElementsByTagName("IMG")[0];
    utils.remove_class(img, "reload_failed");
    utils.add_class(img, "reloading");

    ajax.get_url("ajax_reschedule.py" +
            "?site="     + encodeURIComponent(site) +
            "&host="     + encodeURIComponent(host) +
            "&service="  + service + // Already URL-encoded!
            "&wait_svc=" + wait_svc,
            reschedule_check_response_handler, img); // eslint-disable-line indent
}

// Protocol is:
// For regular response:
// [ 'OK', 'last check', 'exit status plugin', 'output' ]
// For timeout:
// [ 'TIMEOUT', 'output' ]
// For error:
// [ 'ERROR', 'output' ]
// Everything else:
// <undefined> - Unknown format. Simply echo.
function reschedule_check_response_handler(img, code) {
    var validResponse = true;
    var response = null;

    utils.remove_class(img, "reloading");

    try {
        response = eval(code);
    } catch(e) {
        validResponse = false;
    }

    if(validResponse && response[0] === "OK") {
        window.location.reload();
    } else if(validResponse && response[0] === "TIMEOUT") {
        utils.add_class(img, "reload_failed");
        img.title = "Timeout while performing action: " + response[1];
    } else if(validResponse) {
        utils.add_class(img, "reload_failed");
        img.title = "Problem while processing - Response: " + response.join(" ");
    } else {
        utils.add_class(img, "reload_failed");
        img.title = "Invalid response: " + response;
    }
}

export function update_togglebutton(id, enabled)
{
    var on  = document.getElementById(id + "_on");
    var off = document.getElementById(id + "_off");
    if (!on || !off)
        return;

    if (enabled) {
        on.style.display = "block";
        off.style.display = "none";
    } else {
        on.style.display = "none";
        off.style.display = "block";
    }
}

/* Switch filter, commands and painter options */
export function toggle_form(button, form_id) {
    var display = "none";
    var down    = "up";

    var form = document.getElementById(form_id);
    if (form && form.style.display == "none") {
        display = "";
        down    = "down";
    }

    // Close all other view forms
    var alldivs = document.getElementsByClassName("view_form");
    var i;
    for (i=0; i<alldivs.length; i++) {
        if (alldivs[i] != form) {
            alldivs[i].style.display = "none";
        }
    }

    if (form)
        form.style.display = display;

    // Make other buttons inactive
    var allbuttons = document.getElementsByClassName("togglebutton");
    for (i=0; i<allbuttons.length; i++) {
        var b = allbuttons[i];
        if (b != button && !utils.has_class(b, "empth") && !utils.has_class(b, "checkbox")) {
            utils.remove_class(b, "down");
            utils.add_class(b, "up");
        }
    }
    utils.remove_class(button, "down");
    utils.remove_class(button, "up");
    utils.add_class(button, down);
}

