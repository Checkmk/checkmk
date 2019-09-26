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

import * as ajax from "ajax";
import * as selection from "selection";

export const browser = {
    agent: navigator.userAgent.toLowerCase(),
    is_opera: function() { return this.agent.indexOf("opera") != -1; },
    is_firefox: function() { return this.agent.indexOf("firefox") != -1 || this.agent.indexOf("namoroka") != -1; },
    is_ie_below_9: function() { return document.all && !document.addEventListener; }
};

// simple implementation of function default arguments when
// using objects as function parameters. Example:
// function xxx(args) {
//     args = merge_args({
//         'arg2': 'default_val',
//     });
// }
// xxx({
//   'arg1': 'val1',
//   'arg3': 'val3',
// })
export function merge_args(defaults, args = {})
{
    for (var name in args)
        defaults[name] = args[name];

    return defaults;
}

export function prevent_default_events(event) {
    event.preventDefault();
    event.stopPropagation();
    return false;
}


// Updates the contents of a snapin or dashboard container after get_url
export function update_contents(id, code)
{
    var obj = document.getElementById(id);
    if (obj) {
        obj.innerHTML = code;
        execute_javascript_by_object(obj);
    }
}

export var current_script = null;

export function execute_javascript_by_object(obj)
{
    var aScripts = obj.getElementsByTagName("script");
    for(var i = 0; i < aScripts.length; i++) {
        if (aScripts[i].src && aScripts[i].src !== "") {
            var oScr = document.createElement("script");
            oScr.src = aScripts[i].src;
            document.getElementsByTagName("HEAD")[0].appendChild(oScr);
        }
        else {
            try {
                current_script = aScripts[i];
                eval(aScripts[i].text);
                current_script = null;
            } catch(e) {
                //console.log(e);
                alert(aScripts[i].text + "\nError:" + e.message);
            }
        }
    }
}

// Whether or not the current browser window/tab is visible to the user
export function is_window_active()
{
    return !has_class(document.body, "hidden");
}

export function has_class(o, cn) {
    if (typeof(o.className) === "undefined")
        return false;
    var parts = o.className.split(" ");
    for (var x=0; x<parts.length; x++) {
        if (parts[x] == cn)
            return true;
    }
    return false;
}

export function remove_class(o, cn) {
    var parts = o.className.split(" ");
    var new_parts = Array();
    for (var x=0; x<parts.length; x++) {
        if (parts[x] != cn)
            new_parts.push(parts[x]);
    }
    o.className = new_parts.join(" ");
}

export function add_class(o, cn) {
    if (!has_class(o, cn))
        o.className += " " + cn;
}

export function change_class(o, a, b) {
    remove_class(o, a);
    add_class(o, b);
}

// Adds document/window global event handlers
// TODO: Move the window fallback to the call sites (when necessary) and nuke this function
export function add_event_handler(type, func, obj) {
    obj = (typeof(obj) === "undefined") ? window : obj;
    obj.addEventListener(type, func, false);
}


export function get_target(event) {
    return event.target ? event.target : event.srcElement;
}

export function get_button(event) {
    if (event.which == null)
        /* IE case */
        return (event.button < 2) ? "LEFT" : ((event.button == 4) ? "MIDDLE" : "RIGHT");
    else
        /* All others */
        return (event.which < 2) ? "LEFT" : ((event.which == 2) ? "MIDDLE" : "RIGHT");
}

export function page_height() {
    if (window.innerHeight !== null && typeof window.innerHeight !== "undefined" && window.innerHeight !== 0)
        return window.innerHeight;
    else if (document.documentElement && document.documentElement.clientHeight)
        return document.documentElement.clientHeight;
    else if (document.body !== null)
        return document.body.clientHeight;
    return null;
}

export function page_width() {
    if (window.innerWidth !== null && typeof window.innerWidth !== "undefined" && window.innerWidth !== 0)
        return window.innerWidth;
    else if (document.documentElement && document.documentElement.clientWidth)
        return document.documentElement.clientWidth;
    else if (document.body !== null)
        return document.body.clientWidth;
    return null;
}


export function update_header_timer() {
    var container = document.getElementById("headertime");
    if (!container)
        return;

    var t = new Date();

    var hours = t.getHours();
    if (hours < 10)
        hours = "0" + hours;

    var min = t.getMinutes();
    if (min < 10)
        min = "0" + min;

    container.innerHTML = hours + ":" + min;

    var date = document.getElementById("headerdate");
    if (!date)
        return;

    var day   = ("0" + t.getDate()).slice(-2);
    var month = ("0" + (t.getMonth() + 1)).slice(-2);
    var year  = t.getFullYear();
    var date_format = date.getAttribute("format");
    date.innerHTML = date_format.replace(/yyyy/, year).replace(/mm/, month).replace(/dd/, day);
}

export function update_header_info(text)
{
    var oDiv = document.getElementById("headinfo");
    if (oDiv) {
        oDiv.innerHTML = text;
    }
}

// Function gets the value of the given url parameter
export function get_url_param(name, url) {
    name = name.replace("[", "\\[").replace("]", "\\]");
    url = (typeof url === "undefined") ? window.location : url;

    var regex = new RegExp("[\\?&]" + name + "=([^&#]*)");
    var results = regex.exec(url);
    if(results === null)
        return "";
    return results[1];
}

/**
 * Function creates a new cleaned up URL
 * - Can add/overwrite parameters
 * - Removes _* parameters
 */
export function makeuri(addvars, url) {
    url = (typeof(url) === "undefined") ? window.location.href : url;

    var tmp = url.split("?");
    var base = tmp[0];
    if(tmp.length > 1) {
        // Remove maybe existing anchors
        tmp = tmp[1].split("#");
        // Split to array of param-strings (key=val)
        tmp = tmp[0].split("&");
    } else {
        // Uri has no parameters
        tmp = [];
    }

    var params = [];
    var pair = null;

    // Skip unwanted parmas
    for(var i = 0; i < tmp.length; i++) {
        pair = tmp[i].split("=");
        if(pair[0][0] == "_" && pair[0] != "_username" && pair[0] != "_secret") // Skip _<vars>
            continue;
        if(addvars.hasOwnProperty(pair[0])) // Skip vars present in addvars
            continue;
        params.push(tmp[i]);
    }

    // Add new params
    for (var key in addvars) {
        params.push(encodeURIComponent(key) + "=" + encodeURIComponent(addvars[key]));
    }

    return base + "?" + params.join("&");
}

// Returns timestamp in seconds incl. subseconds as decimal
export function time() {
    return (new Date()).getTime() / 1000;
}

var g_sidebar_reload_timer = null;

// reload sidebar, but preserve quicksearch field value and focus
export function reload_sidebar()
{
    if (!parent || !parent.frames[0]) {
        return;
    }

    var val = "";
    var focused = false;
    var field = parent.frames[0].document.getElementById("mk_side_search_field");
    if (field) {
        val = field.value;
        focused = parent.frames[0].document.activeElement == field;
    }

    parent.frames[0].document.reloading = 1;
    parent.frames[0].document.location.reload();

    if (!field) {
        return;
    }

    g_sidebar_reload_timer = setInterval(function (value, has_focus) {
        return function() {
            if (!parent.frames[0].document.reloading
                && parent.frames[0].document.readyState === "complete") {
                var field = parent.frames[0].document.getElementById("mk_side_search_field");
                if (field) {
                    field.value = value;
                    if (has_focus) {
                        field.focus();

                        // Move caret to end
                        if (field.setSelectionRange !== undefined)
                            field.setSelectionRange(value.length, value.length);
                    }
                }

                clearInterval(g_sidebar_reload_timer);
                g_sidebar_reload_timer = null;
            }
        };
    }(val, focused), 50);

    field = null;
}

//#.
//#   .-Page Reload--------------------------------------------------------.
//#   |        ____                    ____      _                 _       |
//#   |       |  _ \ __ _  __ _  ___  |  _ \ ___| | ___   __ _  __| |      |
//#   |       | |_) / _` |/ _` |/ _ \ | |_) / _ \ |/ _ \ / _` |/ _` |      |
//#   |       |  __/ (_| | (_| |  __/ |  _ <  __/ | (_) | (_| | (_| |      |
//#   |       |_|   \__,_|\__, |\___| |_| \_\___|_|\___/ \__,_|\__,_|      |
//#   |                   |___/                                            |
//#   +--------------------------------------------------------------------+
//#   |                                                                    |
//#   '--------------------------------------------------------------------'

// Stores the reload timer object (of views and also dashboards)
var g_reload_timer = null;
// This stores the refresh time of the page (But never 0)
var g_reload_interval = 0; // seconds
// This flag tells the handle_content_reload_error() function to add an
// error message about outdated data to the content container or not.
// The error message is only being added on the first error.
var g_reload_error = false;

// When called with one or more parameters parameters it reschedules the
// timer to the given interval. If the parameter is 0 the reload is stopped.
// When called with two parmeters the 2nd one is used as new url.
export function set_reload(secs, url)
{
    stop_reload_timer();
    set_reload_interval(secs);
    if (secs !== 0) {
        schedule_reload(url);
    }
}


// Issues the timer for the next page reload. If some timer is already
// running, this timer is terminated and replaced by the new one.
export function schedule_reload(url, milisecs)
{
    if (typeof url === "undefined")
        url = ""; // reload current page (or just the content)

    if (typeof milisecs === "undefined")
        milisecs = parseFloat(g_reload_interval) * 1000; // use default reload interval

    stop_reload_timer();

    g_reload_timer = setTimeout(function() {
        do_reload(url);
    }, milisecs);
}


export function stop_reload_timer()
{
    if (g_reload_timer) {
        clearTimeout(g_reload_timer);
        g_reload_timer = null;
    }
}

function do_reload(url)
{
    // Reschedule the reload in case the browser window / tab is not visible
    // for the user. Retry after short time.
    if (!is_window_active()) {
        setTimeout(function(){ do_reload(url); }, 250);
        return;
    }

    // Nicht mehr die ganze Seite neu laden, wenn es ein DIV "data_container" gibt.
    // In dem Fall wird die aktuelle URL aus "window.location.href" geholt, für den Refresh
    // modifiziert, der Inhalt neu geholt und in das DIV geschrieben.
    if (!document.getElementById("data_container") || url !== "") {
        if (url === "")
            window.location.reload(false);
        else
            window.location.href = url;
    }
    else {
        // Enforce specific display_options to get only the content data.
        // All options in "opts" will be forced. Existing upper-case options will be switched.
        var display_options = get_url_param("display_options");
        // Removed "w" to reflect original rendering mechanism during reload
        // For example show the "Your query produced more than 1000 results." message
        // in views even during reload.
        var opts = [ "h", "t", "b", "f", "c", "o", "d", "e", "r", "u" ];
        var i;
        for (i = 0; i < opts.length; i++) {
            if (display_options.indexOf(opts[i].toUpperCase()) > -1)
                display_options = display_options.replace(opts[i].toUpperCase(), opts[i]);
            else
                display_options += opts[i];
        }

        // Add optional display_options if not defined in original display_options
        opts = [ "w" ];
        for (i = 0; i < opts.length; i++) {
            if (display_options.indexOf(opts[i].toUpperCase()) == -1)
                display_options += opts[i];
        }

        var params = {"_display_options": display_options};
        var real_display_options = get_url_param("display_options");
        if (real_display_options !== "")
            params["display_options"] = real_display_options;

        params["_do_actions"] = get_url_param("_do_actions");

        // For dashlet reloads add a parameter to mark this request as reload
        if (window.location.href.indexOf("dashboard_dashlet.py") != -1)
            params["_reload"] = "1";

        if (selection.is_selection_enabled())
            params["selection"] = selection.get_selection_id();

        ajax.call_ajax(makeuri(params), {
            response_handler : handle_content_reload,
            error_handler    : handle_content_reload_error,
            method           : "GET"
        });
    }
}

function handle_content_reload(_unused, code) {
    g_reload_error = false;
    var o = document.getElementById("data_container");
    o.innerHTML = code;
    execute_javascript_by_object(o);

    // Update the header time
    update_header_timer();

    schedule_reload();
}


function handle_content_reload_error(_unused, status_code)
{
    if (!g_reload_error) {
        var o = document.getElementById("data_container");
        o.innerHTML = "<div class=error>Update failed (" + status_code
                      + "). The shown data might be outdated</div>" + o.innerHTML;
        g_reload_error = true;
    }

    // Continue update after the error
    schedule_reload();
}

export function set_reload_interval(secs) {
    update_foot_refresh(secs);
    if (secs !== 0) {
        g_reload_interval = secs;
    }
}

function update_foot_refresh(secs)
{
    var o = document.getElementById("foot_refresh");
    var o2 = document.getElementById("foot_refresh_time");
    if (!o) {
        return;
    }

    if(secs == 0) {
        o.style.display = "none";
    } else {
        o.style.display = "inline-block";
        if(o2) {
            o2.innerHTML = secs;
        }
    }
}

export function toggle_folding(img, to_be_opened) {
    if (to_be_opened) {
        change_class(img, "closed", "open");
    } else {
        change_class(img, "open", "closed");
    }
}

// Relative to viewport
export function mouse_position(event) {
    return {
        x: event.clientX,
        y: event.clientY
    };
}

export function wheel_event_delta(event)
{
    return event.deltaY ? event.deltaY : event.detail ? event.detail * (-120) : event.wheelDelta;
}

export function count_context_button(oA)
{
    // Extract view name from id of parent div element
    var handler = ajax.call_ajax("count_context_button.py?id=" + oA.parentNode.id, {
        sync:true
    });
    return handler.responseText;
}

export function unhide_context_buttons(toggle_button)
{
    var cells = toggle_button.parentNode.parentNode;
    var children = cells.children;
    for (var i = 0; i < children.length; i++) {
        var node = children[i];
        if (node.tagName == "DIV" && !has_class(node, "togglebutton"))
            node.style.display = "";
    }
    toggle_button.parentNode.style.display = "none";
}

var g_tag_groups = {
    "host": {},
    "service": {}
};

export function set_tag_groups(object_type, grouped) {
    g_tag_groups[object_type] = grouped;
}

export function tag_update_value(object_type, prefix, grp) {
    var value_select = document.getElementById(prefix + "_val");

    // Remove all options
    value_select.options.length = 0;

    if(grp === "")
        return; // skip over when empty group selected

    var opt = null;
    for (var i = 0, len = g_tag_groups[object_type][grp].length; i < len; i++) {
        opt = document.createElement("option");
        opt.value = g_tag_groups[object_type][grp][i][0];
        opt.text  = g_tag_groups[object_type][grp][i][1];
        value_select.appendChild(opt);
    }
}
