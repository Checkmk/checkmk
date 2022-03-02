// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

//#   +--------------------------------------------------------------------+
//#   | Floating popup menus with content fetched via AJAX calls           |
//#   '--------------------------------------------------------------------'

import * as utils from "utils";
import * as ajax from "ajax";
import * as valuespecs from "valuespecs";

var active_popup = popup_context();

function popup_context() {
    const popup = {
        id: null,
        container: null,
        popup: null,
        data: null,
        onclose: null,
        onopen: null,
        remove_on_close: false,
    };

    popup.register = function (spec) {
        spec = spec || {};
        this.id = spec.id || null;
        this.data = spec.data || null;
        this.onclose = spec.onclose || null;
        this.onopen = spec.onopen || null;
        this.remove_on_close = spec.remove_on_close || false;

        if (this.id) {
            utils.add_event_handler("click", handle_popup_close);
        }

        if (spec.trigger_obj) {
            this.container = spec.trigger_obj ? spec.trigger_obj.parentNode : null;
            this.popup = this.container ? this.container.lastChild : null;
        }

        if (this.container) {
            utils.add_class(this.container, "active");
        }
    };

    popup.open = function () {
        if (this.onopen) {
            eval(this.onopen);
        }
    };

    popup.close = function () {
        if (this.container) {
            utils.remove_class(this.container, "active");
            if (this.remove_on_close && this.popup) {
                this.container.removeChild(this.popup);
            }
        }

        if (this.id) {
            utils.del_event_handler("click", handle_popup_close);
        }

        if (this.onclose) {
            eval(this.onclose);
        }

        this.id = null;
        this.container = null;
        this.popup = null;
        this.data = null;
        this.onclose = null;
        this.remove_on_close = false;
    };

    return popup;
}

export function close_popup() {
    active_popup.close();
}

export function open_popup() {
    active_popup.open();
}

// Registerd as click handler on the page while the popup menu is opened
// This is used to close the menu when the user clicks elsewhere
function handle_popup_close(event) {
    const container = active_popup.container;
    const target = utils.get_target(event);

    if (container && container.contains(target)) {
        return true; // clicked menu or statusicon
    }

    close_popup();
}

// event:       The browser event that triggered the action
// trigger_obj: DOM object of the action
// ident:       page global uinique identifier of the popup container
// method:      A JavaScript object that describes the method that is used
//              to add the content of the popup menu. The different methods
//              are distinguished by the attribute "type". Currently the
//              methods ajax, inline and colorpicker are supported.
//
//              ajax: Contains an attribute endpoint that used to construct the
//                    webservice url "ajax_popup_" + method.endpoint + ".py".
//                    The attribute url_vars contains the URL variables that are
//                    added to ajax_popup_*.py calls for rendering the popup menu.
//                    The url_vars may be null.
//
//              inline: The popup is already a hidden element in the DOM. It only
//                      has to be made visible. This can be achieved with CSS that
//                      uses the "active" class that is set on the container when
//                      the popup is registered.
//                      The object contains no further attributes.
//
//              colorpicker: Used to render color pickers. The object contains the
//                           attributes varprefix and value used to determine the
//                           ID of the color picker and its recent color.
//
// data:        JSON data which can be used by actions in popup menus
// onopen:      JavaScript code represented as a string that is evaluated when the
//              popup is opened
// onclose:     JavaScript code represented as a string that is evaluated when the
//              popup is closed
// resizable:   Allow the user to resize the popup by drag/drop (not persisted)
export function toggle_popup(event, trigger_obj, ident, method, data, onclose, onopen, resizable) {
    if (!event) event = window.event;

    if (active_popup.id) {
        if (active_popup.id === ident) {
            close_popup();
            return; // same icon clicked: just close the menu
        } else {
            close_popup();
        }
    }

    // Add the popup to the DOM if required by the method.
    if (method.type === "colorpicker") {
        const rgb = trigger_obj.firstChild.style.backgroundColor;
        if (rgb !== "") {
            method.value = rgb2hex(rgb);
        }
        const content = generate_menu(trigger_obj.parentNode, resizable);
        generate_colorpicker_body(content, method.varprefix, method.value);
    } else if (method.type === "ajax") {
        const content = generate_menu(trigger_obj.parentNode, resizable);
        content.innerHTML =
            '<img src="themes/facelift/images/icon_reload.svg" class="icon reloading">';
        const url_vars = !method.url_vars ? "" : "?" + method.url_vars;
        ajax.get_url(
            "ajax_popup_" + method.endpoint + ".py" + url_vars,
            handle_render_popup_contents,
            {
                ident: ident,
                content: content,
                event: event,
            }
        );
    }

    active_popup.register({
        id: ident,
        trigger_obj: trigger_obj,
        data: data,
        onclose: onclose,
        onopen: onopen,
        remove_on_close: method.type !== "inline",
    });

    open_popup();
}

var switch_popup_timeout = null;

// When one of the popups of a group is open, open other popups once hovering over another popups
// trigger. This currently only works on PopupMethodInline based popups.
export function switch_popup_menu_group(trigger, group_cls, delay) {
    const popup = trigger.nextSibling;

    utils.remove_class(popup.parentNode, "delayed");

    // When the new focucssed dropdown is already open, leave it open
    if (utils.has_class(popup.parentNode, "active")) {
        return;
    }

    // Do not open the menu when no other dropdown is open at the moment
    const popups = Array.prototype.slice.call(document.getElementsByClassName(group_cls));
    if (!popups.some(elem => utils.has_class(elem.parentNode, "active"))) {
        return;
    }

    if (!delay) {
        trigger.click();
        return;
    }

    stop_popup_menu_group_switch(trigger);

    utils.add_class(popup.parentNode, "delayed");
    switch_popup_timeout = setTimeout(
        () => switch_popup_menu_group(trigger, group_cls, null),
        delay
    );
}

export function stop_popup_menu_group_switch(trigger) {
    if (switch_popup_timeout !== null) {
        const popup = trigger.nextSibling;
        utils.remove_class(popup.parentNode, "delayed");

        clearTimeout(switch_popup_timeout);
    }
}

function generate_menu(container, resizable) {
    // Generate the popup menu structure and return the content div
    const menu = document.createElement("div");
    menu.setAttribute("id", "popup_menu");
    menu.className = "popup_menu";

    const wrapper = document.createElement("div");
    wrapper.className = "wrapper";
    menu.appendChild(wrapper);

    const content = document.createElement("div");
    content.className = "content";
    wrapper.appendChild(content);

    if (resizable) {
        utils.add_class(menu, "resizable");
    }

    container.appendChild(menu);
    fix_popup_menu_position(event, menu);

    return content;
}

function generate_colorpicker_body(content, varprefix, value) {
    var picker = document.createElement("div");
    picker.className = "cp-small";
    picker.setAttribute("id", varprefix + "_picker");
    content.appendChild(picker);

    var cp_input = document.createElement("div");
    cp_input.className = "cp-input";
    cp_input.innerHTML = "Hex color:";
    content.appendChild(cp_input);

    var input_field = document.createElement("input");
    input_field.setAttribute("id", varprefix + "_input");
    input_field.setAttribute("type", "text");
    cp_input.appendChild(input_field);

    valuespecs.add_color_picker(varprefix, value);
}

function rgb2hex(rgb) {
    if (/^#[0-9A-F]{6}$/i.test(rgb)) return rgb;

    const matches = rgb.match(/^rgb\((\d+),\s*(\d+),\s*(\d+)\)$/);

    let hex_string = "#";
    for (let i = 1; i < matches.length; i++) {
        hex_string += ("0" + parseInt(matches[i], 10).toString(16)).slice(-2);
    }
    return hex_string;
}

function handle_render_popup_contents(data, response_text) {
    if (data.content) {
        data.content.innerHTML = response_text;
        const menu = data.content.closest("div#popup_menu");
        fix_popup_menu_position(data.event, menu);
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
            menu.style.top = "-" + (rect.top - 15) + "px";
            menu.style.bottom = "auto";
        } else {
            menu.style.top = "auto";
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
            menu.style.left = "-" + (rect.left - 15) + "px";
            menu.style.right = "auto";
        } else {
            menu.style.left = "auto";
            menu.style.right = "15px";
        }
    }
}

// TODO: Remove this function as soon as all visuals have been
// converted to pagetypes.py
export function add_to_visual(visual_type, visual_name) {
    var element_type = active_popup.data[0];
    var create_info = {
        context: active_popup.data[1],
        params: active_popup.data[2],
    };
    var create_info_json = JSON.stringify(create_info);

    close_popup();

    var url =
        "ajax_add_visual.py" +
        "?visual_type=" +
        visual_type +
        "&visual_name=" +
        visual_name +
        "&type=" +
        element_type;

    ajax.call_ajax(url, {
        method: "POST",
        post_data: "create_info=" + encodeURIComponent(create_info_json),
        plain_error: true,
        response_handler: function (handler_data, response_body) {
            // After adding a dashlet, go to the choosen dashboard
            if (response_body.substr(0, 2) == "OK") {
                window.location.href = response_body.substr(3);
            } else {
                alert("Failed to add element: " + response_body);
            }
        },
    });
}

// FIXME: Adapt error handling which has been addded to add_to_visual() in the meantime
export function pagetype_add_to_container(page_type, page_name) {
    var element_type = active_popup.data[0]; // e.g. "pnpgraph"
    // complex JSON struct describing the thing
    var create_info = {
        context: active_popup.data[1],
        parameters: active_popup.data[2],
    };
    var create_info_json = JSON.stringify(create_info);

    close_popup();

    var url =
        "ajax_pagetype_add_element.py" +
        "?page_type=" +
        page_type +
        "&page_name=" +
        page_name +
        "&element_type=" +
        element_type;

    ajax.call_ajax(url, {
        method: "POST",
        post_data: "create_info=" + encodeURIComponent(create_info_json),
        response_handler: function (handler_data, response_body) {
            // We get to lines of response. The first is an URL we should be
            // redirected to. The second is "true" if we should reload the
            // sidebar.
            if (response_body) {
                var parts = response_body.split("\n");
                if (parts[1] == "true") {
                    if (parts[0]) utils.reload_whole_page(parts[0]);
                    else utils.reload_whole_page();
                }
                if (parts[0]) window.location.href = parts[0];
            }
        },
    });
}

export function graph_export(page) {
    var request = {
        specification: active_popup.data[2]["definition"]["specification"],
        data_range: active_popup.data[2]["data_range"],
    };
    location.href = page + ".py?request=" + encodeURIComponent(JSON.stringify(request));
}

/****************************************
 * Mega menu
 ****************************************/

export function initialize_mega_menus() {
    ["resize", "load"].forEach(event => {
        window.addEventListener(event, () => {
            resize_all_mega_menu_popups();
        });
    });
}

function resize_all_mega_menu_popups() {
    for (const popup of document.getElementsByClassName("main_menu_popup")) {
        resize_mega_menu_popup(popup);
    }
}

export function resize_mega_menu_popup(menu_popup) {
    /* Resize a mega menu to the size of its content. Three cases are considered here:
     *   1) The overview of all topics is opened.
     *   2) The extended menu that shows all items of a topic is opened.
     *   3) The menu's search results are opened.
     */
    const topics = menu_popup.getElementsByClassName("topic");
    if (topics.length === 0) {
        return;
    }

    const ncol = mega_menu_last_topic_grow(topics);
    const search_results = menu_popup.getElementsByClassName("hidden").length;
    const extended_topic = Array.prototype.slice
        .call(topics)
        .find(e => utils.has_class(e, "extended"));

    if (!extended_topic || search_results) {
        const visible_topics = Array.prototype.slice.call(topics).filter(e => utils.is_visible(e));
        if (visible_topics.length === 0) {
            return;
        }

        const topic = visible_topics[visible_topics.length - 1];

        // If we have only a single column, we need a bigger menu width, as the search field and
        // the more button needs to have enough space
        if (ncol === 1) {
            Array.from(topics).forEach(topic => utils.add_class(topic, "single_column"));
            utils.add_class(menu_popup, "single_column");
        } else if (utils.has_class(menu_popup, "single_column")) {
            Array.from(topics).forEach(topic => utils.remove_class(topic, "single_column"));
            utils.remove_class(menu_popup, "single_column");
            resize_mega_menu_popup(menu_popup);
            return;
        }
        menu_popup.style.width = Math.min(maximum_popup_width(), topic.offsetWidth * ncol) + "px";
    } else {
        const items = extended_topic.getElementsByTagName("ul")[0];
        const visible_items = Array.prototype.slice
            .call(items.children)
            .filter(e => utils.is_visible(e));
        if (visible_items.length === 0) {
            return;
        }
        const last_item = visible_items[visible_items.length - 1];
        /* account for the padding of 20px on both sides  */
        const items_width = Math.min(
            maximum_popup_width(),
            last_item.offsetLeft + last_item.offsetWidth - 20
        );
        items.style.width = items_width + "px";
        menu_popup.style.width = items_width + 40 + "px";
    }
}

function mega_menu_last_topic_grow(topics) {
    // For each column, let the last topic grow by setting/removing the css class "grow"
    // Return the number of columns
    if (topics.length === 0) {
        return 0;
    }

    let ncol = 1;
    let previous_node = null;
    Array.from(topics).forEach(function (node) {
        if (utils.get_computed_style(node, "display") == "none") {
            utils.remove_class(node, "grow");
            return;
        }

        if (previous_node) {
            if (previous_node.offsetTop > node.offsetTop) {
                utils.add_class(previous_node, "grow");
                ncol += 1;
            } else {
                utils.remove_class(previous_node, "grow");
            }
        }
        previous_node = node;
    });
    if (previous_node) utils.add_class(previous_node, "grow"); // last node needs to grow, too

    return ncol;
}

function maximum_popup_width() {
    return window.innerWidth - document.getElementById("check_mk_navigation").offsetWidth;
}

export function mega_menu_show_all_items(current_topic_id) {
    let current_topic = document.getElementById(current_topic_id);
    utils.remove_class(current_topic, "extendable");
    utils.add_class(current_topic, "extended");
    utils.add_class(current_topic.closest(".main_menu"), "extended_topic");
    resize_mega_menu_popup(current_topic.closest(".main_menu_popup"));
}

export function mega_menu_show_all_topics(current_topic_id) {
    let current_topic = document.getElementById(current_topic_id);
    utils.remove_class(current_topic, "extended");
    utils.remove_class(current_topic.closest(".main_menu"), "extended_topic");
    mega_menu_hide_entries(current_topic.closest(".main_menu").id);
    current_topic.getElementsByTagName("ul")[0].removeAttribute("style");
    resize_mega_menu_popup(current_topic.closest(".main_menu_popup"));
}

export function mega_menu_hide_entries(menu_id) {
    let menu = document.getElementById(menu_id);
    let more_is_active = menu.classList.contains("more");
    let topics = menu.getElementsByClassName("topic");
    Array.from(topics).forEach(topic => {
        if (topic.classList.contains("extended")) return;
        let max_entry_number = Number(topic.getAttribute("data-max-entries"));
        if (!max_entry_number) {
            return;
        }
        let entries = topic.getElementsByTagName("li");
        let show_all_items_entry = entries[entries.length - 1];
        if (entries.length > max_entry_number + 1) {
            // + 1 is needed for the show_all_items entry
            let counter = 0;
            Array.from(entries).forEach(entry => {
                if (
                    (!more_is_active && entry.classList.contains("show_more_mode")) ||
                    entry == show_all_items_entry
                )
                    return;
                if (counter >= max_entry_number) utils.add_class(entry, "extended");
                else utils.remove_class(entry, "extended");
                counter++;
            });
            if (counter > max_entry_number) utils.add_class(topic, "extendable");
            else utils.remove_class(topic, "extendable");
        }
    });
    resize_mega_menu_popup(menu.parentElement);
}

export function focus_search_field(input_id) {
    document.getElementById(input_id).focus();
}
