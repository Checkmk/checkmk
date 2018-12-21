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
// ails.  You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

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
    if (event.preventDefault)
        event.preventDefault();
    if (event.stopPropagation)
        event.stopPropagation();
    event.returnValue = false;
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

// There may be some javascript code in the html code rendered by
// sidebar.py. Execute it here. This is needed in some browsers.
// TODO: Clean this special case up
export function execute_javascript_by_id(id)
{
    execute_javascript_by_object(document.getElementById(id));
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
                console.log(e);
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
export function add_event_handler(type, func, obj) {
    obj = (typeof(obj) === "undefined") ? window : obj;

    if (obj.addEventListener) {
        // W3 standard browsers
        obj.addEventListener(type, func, false);
    }
    else if (obj.attachEvent) {
        // IE<9
        obj.attachEvent("on" + type, func);
    }
    else {
        obj["on" + type] = func;
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

