/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

//#   +--------------------------------------------------------------------+
//#   | Floating popup menus with content fetched via AJAX calls           |
//#   '--------------------------------------------------------------------'

import {call_ajax} from "./ajax";
import type {Nullable} from "./utils";
import {
    add_class,
    add_event_handler,
    change_class,
    del_event_handler,
    get_computed_style,
    has_class,
    is_visible,
    querySelectorAllByClassName,
    reload_whole_page,
    remove_class,
} from "./utils";
import {add_color_picker} from "./valuespecs";

interface PopUpSpec {
    id: string;
    trigger_obj: HTMLElement;
    data: any;
    onclose: string | null;
    onopen: string | null;
    remove_on_close: boolean;
}

class PopUp {
    id: string | null;
    container: null | HTMLElement;
    popup: null | HTMLElement | ChildNode;
    data: any;
    onclose: string | null;
    onopen: string | null;
    remove_on_close: boolean;

    constructor() {
        this.id = null;
        this.container = null;
        this.popup = null;
        this.data = null;
        this.onclose = null;
        this.onopen = null;
        this.remove_on_close = false;
    }

    register(spec: PopUpSpec) {
        spec = spec || {};
        this.id = spec.id || null;
        this.data = spec.data || null;
        this.onclose = spec.onclose || null;
        this.onopen = spec.onopen || null;
        this.remove_on_close = spec.remove_on_close || false;

        if (this.id) {
            add_event_handler("click", handle_popup_close);
        }

        if (spec.trigger_obj) {
            this.container = spec.trigger_obj
                ? (spec.trigger_obj.parentNode as HTMLElement)
                : null;
            this.popup = this.container ? this.container.lastChild : null;
        }

        if (this.container) {
            add_class(this.container, "active");
        }
    }

    open() {
        if (this.onopen) {
            /* eslint-disable-next-line no-eval -- Highlight existing violations CMK-17846 */
            eval(this.onopen);
        }
    }

    close() {
        if (this.container) {
            remove_class(this.container, "active");
            if (this.remove_on_close && this.popup) {
                this.container.removeChild(this.popup);
            }
        }

        if (this.id) {
            del_event_handler("click", handle_popup_close);
        }

        if (this.onclose) {
            /* eslint-disable-next-line no-eval -- Highlight existing violations CMK-17846 */
            eval(this.onclose);
        }

        this.id = null;
        this.container = null;
        this.popup = null;
        this.data = null;
        this.onclose = null;
        this.remove_on_close = false;
    }
}

const active_popup = new PopUp();

export function close_popup() {
    active_popup.close();
}

export function open_popup() {
    active_popup.open();
}

export function is_open(ident: string): boolean {
    return Boolean(active_popup.id && active_popup.id === ident);
}

// Registerd as click handler on the page while the popup menu is opened
// This is used to close the menu when the user clicks elsewhere
function handle_popup_close(event: Event | undefined): true | void {
    const container = active_popup.container;
    const target = event!.target as HTMLElement;

    if (container && container.contains(target as Node)) {
        return true; // clicked menu or statusicon
    }

    close_popup();
}

interface PopupMethod {
    type: string;
}

interface MethodAjax extends PopupMethod {
    type: "ajax";
    endpoint: string | null;
    url_vars: string | null;
}

interface MethodInline extends PopupMethod {
    type: "inline";
}

interface MethodColorpicker extends PopupMethod {
    type: "colorpicker";
    varprefix: string | null;
    value: string | null;
}

type JSPopupMethod = MethodColorpicker | MethodInline | MethodAjax;

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
export function toggle_popup(
    event: Event | undefined,
    trigger_obj: HTMLElement,
    ident: string,
    method: JSPopupMethod,
    data: any,
    onclose: string | null,
    onopen: string | null,
    resizable: boolean,
) {
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
        const rgb = (trigger_obj.firstChild as HTMLElement).style
            .backgroundColor;
        if (rgb !== "") {
            method.value = rgb2hex(rgb);
        }
        const content = generate_menu(
            trigger_obj.parentNode as HTMLElement,
            resizable,
        );
        generate_colorpicker_body(content, method.varprefix!, method.value!);
    } else if (method.type === "ajax") {
        const content = generate_menu(
            trigger_obj.parentNode as HTMLElement,
            resizable,
        );
        content.innerHTML =
            '<img src="themes/facelift/images/icon_reload.svg" class="icon reloading">';
        const url_vars = !method.url_vars ? "" : "?" + method.url_vars;
        call_ajax("ajax_popup_" + method.endpoint + ".py" + url_vars, {
            response_handler: handle_render_popup_contents,
            handler_data: {
                ident: ident,
                content: content,
                event: event!,
            },
        });
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

let switch_popup_timeout: null | number = null;

// When one of the popups of a group is open, open other popups once hovering over another popups
// trigger. This currently only works on PopupMethodInline based popups.
export function switch_popup_menu_group(
    trigger: HTMLElement,
    group_cls: string,
    delay: number | null,
) {
    const popup = trigger.nextSibling;

    remove_class(popup!.parentNode as HTMLElement, "delayed");

    // When the new focucssed dropdown is already open, leave it open
    if (has_class(popup!.parentNode as HTMLElement, "active")) {
        return;
    }

    // Do not open the menu when no other dropdown is open at the moment
    const popups = Array.prototype.slice.call(
        document.getElementsByClassName(group_cls),
    );
    if (!popups.some(elem => has_class(elem.parentNode, "active"))) {
        return;
    }

    if (!delay) {
        trigger.click();
        return;
    }

    stop_popup_menu_group_switch(trigger);

    add_class(popup!.parentNode as HTMLElement, "delayed");
    switch_popup_timeout = window.setTimeout(
        () => switch_popup_menu_group(trigger, group_cls, null),
        delay,
    );
}

export function stop_popup_menu_group_switch(trigger: HTMLElement) {
    if (switch_popup_timeout !== null) {
        const popup = trigger.nextSibling;
        remove_class(popup!.parentNode as HTMLElement, "delayed");

        clearTimeout(switch_popup_timeout);
    }
}

function generate_menu(container: HTMLElement, resizable: boolean) {
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
        add_class(menu, "resizable");
    }

    container.appendChild(menu);
    fix_popup_menu_position(event, menu);

    return content;
}

function generate_colorpicker_body(
    content: HTMLElement,
    varprefix: string,
    value: string,
) {
    const picker = document.createElement("div");
    picker.className = "cp-small";
    picker.setAttribute("id", varprefix + "_picker");
    content.appendChild(picker);

    const cp_input = document.createElement("div");
    cp_input.className = "cp-input";
    cp_input.innerHTML = "Hex color:";
    content.appendChild(cp_input);

    const input_field = document.createElement("input");
    input_field.setAttribute("id", varprefix + "_input");
    input_field.setAttribute("type", "text");
    cp_input.appendChild(input_field);

    add_color_picker(varprefix, value);
}

function rgb2hex(rgb: string) {
    if (/^#[0-9A-F]{6}$/i.test(rgb)) return rgb;

    const matches = rgb.match(/^rgb\((\d+),\s*(\d+),\s*(\d+)\)$/)!;

    let hex_string = "#";
    for (let i = 1; i < matches.length; i++) {
        hex_string += ("0" + parseInt(matches[i], 10).toString(16)).slice(-2);
    }
    return hex_string;
}

function handle_render_popup_contents(
    data: {
        ident: string;
        content: HTMLElement;
        event: Event;
    },
    response_text: string,
) {
    if (data.content) {
        /* eslint-disable-next-line no-unsanitized/property -- Highlight existing violations CMK-17846 */
        data.content.innerHTML = response_text;
        const menu = data.content.closest("div#popup_menu") as HTMLElement;
        fix_popup_menu_position(data.event, menu);
    }
}

function fix_popup_menu_position(_event: Event | undefined, menu: HTMLElement) {
    const rect = menu.getBoundingClientRect();

    // Check whether or not the menu is out of the bottom border
    // -> if so, move the menu up
    if (
        rect.bottom >
        (window.innerHeight || document.documentElement.clientHeight)
    ) {
        const height = rect.bottom - rect.top;
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
    if (
        rect.right > (window.innerWidth || document.documentElement.clientWidth)
    ) {
        const width = rect.right - rect.left;
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
export function add_to_visual(visual_type: string, visual_name: string) {
    const element_type = active_popup.data![0];
    const create_info = {
        context: active_popup.data![1],
        params: active_popup.data![2],
    };
    const create_info_json = JSON.stringify(create_info);

    close_popup();

    const url =
        "ajax_add_visual.py" +
        "?visual_type=" +
        visual_type +
        "&visual_name=" +
        visual_name +
        "&type=" +
        element_type;

    call_ajax(url, {
        method: "POST",
        post_data: "create_info=" + encodeURIComponent(create_info_json),
        plain_error: true,
        response_handler: function (_handler_data: any, response_body: string) {
            // After adding a dashlet, go to the choosen dashboard
            if (response_body.substr(0, 2) == "OK") {
                window.location.href = response_body.substr(3);
            } else {
                console.error("Failed to add element: " + response_body);
            }
        },
    });
}

// FIXME: Adapt error handling which has been addded to add_to_visual() in the meantime
export function pagetype_add_to_container(
    page_type: string,
    page_name: string,
) {
    const element_type = active_popup.data![0]; // e.g. "pnpgraph"
    // complex JSON struct describing the thing
    const create_info = {
        context: active_popup.data![1],
        parameters: active_popup.data![2],
    };
    const create_info_json = JSON.stringify(create_info);

    close_popup();

    const url =
        "ajax_pagetype_add_element.py" +
        "?page_type=" +
        page_type +
        "&page_name=" +
        page_name +
        "&element_type=" +
        element_type;

    call_ajax(url, {
        method: "POST",
        post_data: "create_info=" + encodeURIComponent(create_info_json),
        response_handler: function (_handler_data: any, response_body: string) {
            // We get to lines of response. The first is an URL we should be
            // redirected to. The second is "true" if we should reload the
            // sidebar.
            if (response_body) {
                const parts = response_body.split("\n");
                if (parts[1] == "true") {
                    if (parts[0]) reload_whole_page(parts[0]);
                    else reload_whole_page();
                }
                if (parts[0]) window.location.href = parts[0];
            }
        },
    });
}

export function graph_export(page: string) {
    const request = {
        specification: active_popup.data![2]["definition"]["specification"],
        data_range: active_popup.data![2]["data_range"],
    };
    location.href =
        page + ".py?request=" + encodeURIComponent(JSON.stringify(request));
}

/****************************************
 * Main menu
 ****************************************/

export function initialize_main_menus() {
    ["resize", "load"].forEach(event => {
        window.addEventListener(event, () => {
            resize_all_main_menu_popups();
        });
    });
}

function resize_all_main_menu_popups() {
    for (const popup of querySelectorAllByClassName("popup_menu_handler")) {
        resize_main_menu_popup(popup);
    }
}

export function resize_main_menu_popup(menu_popup: Nullable<HTMLElement>) {
    /* Resize a main menu to the size of its content. Three cases are considered here:
     *   1) The overview of all topics is opened.
     *   2) The extended menu that shows all items of a topic is opened.
     *   3) The menu's search results are opened.
     */
    if (!menu_popup) throw new Error("menu_popup shouldn't be null!");
    const topics = menu_popup.getElementsByClassName(
        "topic",
    ) as HTMLCollectionOf<HTMLElement>;
    if (topics.length === 0) {
        return;
    }

    const ncol = main_menu_last_topic_grow(topics);
    const search_results = menu_popup.getElementsByClassName("hidden").length;
    const extended_topic = Array.prototype.slice
        .call(topics)
        .find(e => has_class(e, "extended"));

    if (!extended_topic || search_results) {
        const visible_topics = Array.prototype.slice
            .call(topics)
            .filter(e => is_visible(e));
        if (visible_topics.length === 0) {
            return;
        }

        const topic = visible_topics[visible_topics.length - 1];

        // If we have only a single column, we need a bigger menu width, as the search field and
        // the more button needs to have enough space
        if (ncol === 1) {
            Array.from(topics).forEach(topic =>
                add_class(topic, "single_column"),
            );
            add_class(menu_popup, "single_column");
        } else if (has_class(menu_popup, "single_column")) {
            Array.from(topics).forEach(topic =>
                remove_class(topic, "single_column"),
            );
            remove_class(menu_popup, "single_column");
            resize_main_menu_popup(menu_popup);
            return;
        }
        menu_popup.style.width =
            Math.min(maximum_popup_width(), topic.offsetWidth * ncol) + "px";
    } else {
        const items = extended_topic.getElementsByTagName("ul")[0];
        const visible_items = Array.prototype.slice
            .call(items.children)
            .filter(e => is_visible(e));
        if (visible_items.length === 0) {
            return;
        }
        const last_item = visible_items[visible_items.length - 1];
        /* account for the padding of 20px on both sides  */
        const items_width = Math.min(
            maximum_popup_width(),
            last_item.offsetLeft + last_item.offsetWidth - 20,
        );
        items.style.width = items_width + "px";
        menu_popup.style.width = items_width + 40 + "px";
    }
}

function main_menu_last_topic_grow(topics: HTMLCollectionOf<HTMLElement>) {
    // For each column, let the last topic grow by setting/removing the css class "grow"
    // Return the number of columns
    if (topics.length === 0) {
        return 0;
    }

    let ncol = 1;
    let previous_node: null | HTMLElement = null;
    Array.from(topics).forEach(function (node) {
        if (get_computed_style(node, "display") == "none") {
            remove_class(node, "grow");
            return;
        }

        if (previous_node) {
            if (previous_node.offsetTop > node.offsetTop) {
                add_class(previous_node, "grow");
                ncol += 1;
            } else {
                remove_class(previous_node, "grow");
            }
        }
        previous_node = node;
    });
    if (previous_node) add_class(previous_node, "grow"); // last node needs to grow, too

    return ncol;
}

function maximum_popup_width() {
    return (
        window.innerWidth -
        document.getElementById("check_mk_navigation")!.offsetWidth
    );
}

export function main_menu_show_all_items(current_topic_id: string) {
    const current_topic = document.getElementById(current_topic_id);
    const main_menu: HTMLElement = current_topic!.closest(".main_menu")!;

    // Check whether we're already coming from an extended topic. In that case we set a class
    // "previously_extended" to be able to reopen that topic again.
    // We assume here that only one level of previously extended topics is possible
    // (i.e. "Show all" > multilevel topic segment)
    // Multiple multilevel topic segments cannot be handled by this show/collapse code.
    const previously_extended_topic = main_menu.getElementsByClassName(
        "topic extended",
    )[0] as HTMLElement;
    if (previously_extended_topic) {
        change_class(
            previously_extended_topic,
            "extended",
            "previously_extended",
        );
    }

    // Preserve the popup menu's height so there's no vertical jump
    // This only concerns our small menus "help" and "user"
    const popup_menu: HTMLElement = main_menu.closest(".popup_menu_handler")!;
    popup_menu.style.minHeight = `${popup_menu.clientHeight}px`;

    remove_class(current_topic, "extendable");
    add_class(current_topic, "extended");
    add_class(main_menu, "extended_topic");
    resize_main_menu_popup(popup_menu);
}

export function main_menu_collapse_topic(current_topic_id: string) {
    const current_topic = document.getElementById(current_topic_id);
    const main_menu: HTMLElement = current_topic!.closest(".main_menu")!;

    remove_class(current_topic, "extended");
    current_topic?.getElementsByTagName("ul")[0].removeAttribute("style");

    // See comment in main_menu_show_all_items
    const previously_extended_topic = main_menu.getElementsByClassName(
        "topic previously_extended",
    )[0] as HTMLElement;
    if (previously_extended_topic) {
        change_class(
            previously_extended_topic,
            "previously_extended",
            "extended",
        );
        return;
    }

    const popup_menu: HTMLElement = main_menu.closest(".popup_menu_handler")!;
    popup_menu.style.minHeight = "";

    remove_class(main_menu, "extended_topic");
    main_menu_hide_entries(main_menu.id);
    resize_main_menu_popup(popup_menu);
}

export function main_menu_reset_default_expansion(main_menu_name: string) {
    const main_menu: HTMLElement | null = document.getElementById(
        "main_menu_" + main_menu_name,
    );
    if (main_menu === null) {
        return;
    }

    const extended_topics = main_menu.querySelectorAll(
        ".topic.extended, .topic.previously_extended",
    ) as NodeListOf<HTMLElement>;
    if (extended_topics.length === 0) {
        return;
    }

    for (const topic of extended_topics) {
        remove_class(topic, "extended");
        topic.getElementsByTagName("ul")[0].removeAttribute("style");
    }

    remove_class(main_menu, "extended_topic");
    main_menu_hide_entries(main_menu.id);
    resize_main_menu_popup(main_menu.closest(".popup_menu_handler")!);
}

export function main_menu_hide_entries(menu_id: string) {
    const menu = document.getElementById(menu_id);
    const more_is_active = menu?.classList.contains("more");
    const topics = menu?.getElementsByClassName(
        "topic",
    ) as HTMLCollectionOf<HTMLElement>;
    Array.from(topics!).forEach(topic => {
        if (topic.classList.contains("extended")) return;
        const max_entry_number = Number(topic.getAttribute("data-max-entries"));
        if (!max_entry_number) {
            return;
        }
        const entries = topic.getElementsByTagName("li");
        const show_all_items_entry = entries[entries.length - 1];
        if (entries.length > max_entry_number + 1) {
            // + 1 is needed for the show_all_items entry
            let counter = 0;
            Array.from(entries).forEach(entry => {
                if (
                    (!more_is_active &&
                        entry.classList.contains("show_more_mode")) ||
                    entry == show_all_items_entry
                )
                    return;
                if (counter >= max_entry_number) add_class(entry, "extended");
                else remove_class(entry, "extended");
                counter++;
            });
            if (counter > max_entry_number) add_class(topic, "extendable");
            else remove_class(topic, "extendable");
        }
    });
    resize_main_menu_popup(menu!.parentElement!);
}

export function focus_search_field(input_id: string) {
    document.getElementById(input_id)?.focus();
}
