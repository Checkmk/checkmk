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

//#   +--------------------------------------------------------------------+
//#   | Floating popup menus with content fetched via AJAX calls           |
//#   '--------------------------------------------------------------------'

import * as utils from "utils";
import * as ajax from "ajax";

var popup_data      = null;
var popup_id        = null;

export function close_popup()
{
    del_event_handler("click", handle_popup_close);

    var menu = document.getElementById("popup_menu");
    if (menu) {
        // hide the open menu
        menu.parentNode.removeChild(menu);
    }
    popup_id = null;

    if (on_popup_close)
        eval(on_popup_close);
}

function del_event_handler(type, func, obj) {
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

// Registerd as click handler on the page while the popup menu is opened
// This is used to close the menu when the user clicks elsewhere
function handle_popup_close(event) {
    var target = utils.get_target(event);

    // Check whether or not a parent of the clicked node is the popup menu
    while (target && target.id != "popup_menu" && !utils.has_class(target, "popup_trigger")) { // FIXME
        target = target.parentNode;
    }

    if (target) {
        return true; // clicked menu or statusicon
    }

    close_popup();
}

// trigger_obj: DOM object of trigger object (e.g. icon)
// ident:       page global uinique identifier of the popup
// what:        type of popup (used for constructing webservice url "ajax_popup_"+what+".py")
//              This can be null for fixed content popup windows. In this case
//              "data" and "url_vars" are not used and can be left null.
//              The static content of the menu is given in the "menu_content" parameter.
// data:        json data which can be used by actions in popup menus
// url_vars:    vars are added to ajax_popup_*.py calls for rendering the popup menu
// resizable:   Allow the user to resize the popup by drag/drop (not persisted)
var on_popup_close = null;
export function toggle_popup(event, trigger_obj, ident, what, data, url_vars, menu_content, onclose, resizable)
{
    on_popup_close = onclose;

    if (!event)
        event = window.event;
    var container = trigger_obj.parentNode;

    if (popup_id) {
        if (popup_id === ident) {
            close_popup();
            return; // same icon clicked: just close the menu
        }
        else {
            close_popup();
        }
    }
    popup_id = ident;

    utils.add_event_handler("click", handle_popup_close);

    var menu = document.createElement("div");
    menu.setAttribute("id", "popup_menu");
    menu.className = "popup_menu";

    if (resizable)
        utils.add_class(menu, "resizable");

    container.appendChild(menu);
    fix_popup_menu_position(event, menu);

    var wrapper = document.createElement("div");
    wrapper.className = "wrapper";
    menu.appendChild(wrapper);

    var content = document.createElement("div");
    content.className = "content";
    wrapper.appendChild(content);

    if (resizable) {
        // Add a handle because we can not customize the styling of the default resize handle using css
        var resize = document.createElement("div");
        resize.className = "resizer";
        wrapper.appendChild(resize);
    }

    // update the menus contents using a webservice
    if (what) {
        popup_data = data;

        content.innerHTML = "<img src=\"themes/facelift/images/icon_reload.png\" class=\"icon reloading\">";

        url_vars = !url_vars ? "" : "?"+url_vars;
        ajax.get_url("ajax_popup_"+what+".py"+url_vars, handle_render_popup_contents, {
            ident: ident,
            content: content,
            event: event,
        });
    } else {
        content.innerHTML = menu_content;
        utils.execute_javascript_by_object(content);
    }
}

function handle_render_popup_contents(data, response_text)
{
    if (data.content) {
        data.content.innerHTML = response_text;
        fix_popup_menu_position(data.event, data.content);
    }
}

function fix_popup_menu_position(event, menu) {
    var rect = menu.getBoundingClientRect();

    // Check whether or not the menu is out of the bottom border
    // -> if so, move the menu up
    if (rect.bottom > (window.innerHeight || document.documentElement.clientHeight)) {
        var height = rect.bottom - rect.top;
        if (rect.top - height < 0) {
            // would hit the top border too, then put the menu to the top border
            // and hope that it fits within the screen
            menu.style.top    = "-" + (rect.top - 15) + "px";
            menu.style.bottom = "auto";
        } else {
            menu.style.top    = "auto";
            menu.style.bottom = "15px";
        }
    }

    // Check whether or not the menu is out of right border and
    // a move to the left would fix the issue
    // -> if so, move the menu to the left
    if (rect.right > (window.innerWidth || document.documentElement.clientWidth)) {
        var width = rect.right - rect.left;
        if (rect.left - width < 0) {
            // would hit the left border too, then put the menu to the left border
            // and hope that it fits within the screen
            menu.style.left  = "-" + (rect.left - 15) + "px";
            menu.style.right = "auto";
        } else {
            menu.style.left  = "auto";
            menu.style.right = "15px";
        }
    }
}

// TODO: Remove this function as soon as all visuals have been
// converted to pagetypes.py
export function add_to_visual(visual_type, visual_name)
{
    var element_type = popup_data[0];
    var create_info = {
        "context": popup_data[1],
        "params": popup_data[2],
    };
    var create_info_json = JSON.stringify(create_info);

    close_popup();

    popup_data = null;

    var url = "ajax_add_visual.py"
        + "?visual_type=" + visual_type
        + "&visual_name=" + visual_name
        + "&type=" + element_type;

    ajax.call_ajax(url, {
        method : "POST",
        post_data: "create_info=" + encodeURIComponent(create_info_json),
        plain_error : true,
        response_handler: function(handler_data, response_body) {
            // After adding a dashlet, go to the choosen dashboard
            if (response_body.substr(0, 2) == "OK") {
                window.location.href = response_body.substr(3);
            } else {
                alert("Failed to add element: "+response_body);
            }
        }
    });
}

// FIXME: Adapt error handling which has been addded to add_to_visual() in the meantime
export function pagetype_add_to_container(page_type, page_name)
{
    var element_type = popup_data[0]; // e.g. "pnpgraph"
    // complex JSON struct describing the thing
    var create_info  = {
        "context"    : popup_data[1],
        "parameters" : popup_data[2]
    };
    var create_info_json = JSON.stringify(create_info);

    close_popup();

    popup_data = null;

    var url = "ajax_pagetype_add_element.py"
              + "?page_type=" + page_type
              + "&page_name=" + page_name
              + "&element_type=" + element_type;

    ajax.call_ajax(url, {
        method           : "POST",
        post_data        : "create_info=" + encodeURIComponent(create_info_json),
        response_handler : function(handler_data, response_body) {
            // We get to lines of response. The first is an URL we should be
            // redirected to. The second is "true" if we should reload the
            // sidebar.
            if (response_body) {
                var parts = response_body.split("\n");
                if (parts[1] == "true")
                    utils.reload_sidebar();
                if (parts[0])
                    window.location.href = parts[0];
            }
        }
    });
}

export function graph_export(page)
{
    var request = {
        "specification": popup_data[2]["definition"]["specification"],
        "data_range": popup_data[2]["data_range"],
    };
    location.href = page + ".py?request=" + encodeURIComponent(JSON.stringify(request));
}
