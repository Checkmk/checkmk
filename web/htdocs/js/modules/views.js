// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

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

    var post_data = "request=" + encodeURIComponent(JSON.stringify({
        "site": site,
        "host": host,
        "service": service,
        "wait_svc": wait_svc,
    }));

    ajax.call_ajax("ajax_reschedule.py", {
        method: "POST",
        post_data: post_data,
        response_handler: reschedule_check_response_handler,
        handler_data: {
            img: img,
        },
    });
}

function reschedule_check_response_handler(handler_data, ajax_response) {
    var img = handler_data.img;
    utils.remove_class(img, "reloading");

    var response = JSON.parse(ajax_response);
    if (response.result_code != 0) {
        utils.add_class(img, "reload_failed");
        img.title = "Error [" + response.result_code + "]: " + response.result; // eslint-disable-line
        return;
    }

    if (response.result.state === "OK") {
        window.location.reload();
    } else if(response.result.state === "TIMEOUT") {
        utils.add_class(img, "reload_failed");
        img.title = "Timeout while performing action: " + response.result.message;
    } else {
        utils.add_class(img, "reload_failed");
        img.title = response.result.message;
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

