// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

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
    let classname = o.className;
    if (o.className.baseVal !== undefined) // SVG className
        classname = o.className.baseVal;

    var parts = classname.split(" ");
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


export function del_event_handler(type, func, obj) {
    obj = (typeof(obj) === "undefined") ? window : obj;

    if (obj.removeEventListener) {
        // W3 stadnard browsers
        obj.removeEventListener(type, func, false);
    }
    else if (obj.detachEvent) {
        // IE<9
        obj.detachEvent("on"+type, func);
    }
    else {
        obj["on" + type] = null;
    }
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
export function makeuri(addvars, url, filename) {
    url = (typeof(url) === "undefined") ? window.location.href : url;

    var tmp = url.split("?");
    var base = (typeof(filename) === "undefined") ? tmp[0] : filename;
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

export function makeuri_contextless(vars, filename)
{
    var params = [];
    // Add new params
    for (var key in vars) {
        params.push(encodeURIComponent(key) + "=" + encodeURIComponent(vars[key]));
    }

    return filename + "?" + params.join("&");
}

// Returns timestamp in seconds incl. subseconds as decimal
export function time() {
    return (new Date()).getTime() / 1000;
}

// reload sidebar, but preserve quicksearch field value and focus
export function reload_sidebar()
{
    window.top.cmk.sidebar.reset_sidebar_scheduler();
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

// Reschedule the global timer to the given interval.
export function set_reload(secs, url)
{
    stop_reload_timer();
    set_reload_interval(secs);
    schedule_reload(url);
}


// Issues the timer for the next page reload. If some timer is already
// running, this timer is terminated and replaced by the new one.
export function schedule_reload(url, milisecs)
{
    if (typeof url === "undefined")
        url = ""; // reload current page (or just the content)

    if (typeof milisecs === "undefined") {
        if (g_reload_interval === 0) {
            return;  // the reload interval is set to "off"
        }
        milisecs = parseFloat(g_reload_interval) * 1000; // use default reload interval
    }

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

export function wheel_event_name()
{
    if ("onwheel" in window)
        return "wheel";
    else if (browser.is_firefox())
        return "DOMMouseScroll";
    else
        return "mousewheel";
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

export function toggle_more(trigger, toggle_id, dom_levels_up) {
    event.stopPropagation();
    let container = trigger;
    let state;
    for (var i=0; i < dom_levels_up; i++) {
        container = container.parentNode;
        while (container.className.includes("simplebar-"))
            container = container.parentNode;
    }

    if (has_class(container, "more")) {
        change_class(container, "more", "less");
        state = "off";
    } else {
        change_class(container, "less", "more");
        // The class withanimation is used to fade in the formlery
        // hidden items - which must not be done when they are already
        // visible when rendering the page.
        add_class(container, "withanimation");
        state = "on";
    }

    ajax.get_url("tree_openclose.py?tree=more_buttons"
            + "&name=" + encodeURIComponent(toggle_id)
            + "&state=" + encodeURIComponent (state));
}
