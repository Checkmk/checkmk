/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import {call_ajax} from "./ajax";
import {resize_main_menu_popup, toggle_popup} from "./popup_menu";
import {add_class, remove_class} from "./utils";

let g_call_ajax_obj: null | XMLHttpRequest = null;

class Search {
    id: string;
    content_id: string;
    search_id: string;
    input_id: string;
    clear_id: string;
    more_id: string;
    previous_timeout_id: number | null;
    current_search_position: number | null;

    constructor(id: string) {
        this.id = id;
        this.content_id = "content_inner_" + id;
        this.search_id = "content_inner_" + id + "_search";
        this.input_id = "mk_side_search_field_" + id + "_search";
        this.clear_id = "mk_side_search_field_clear_" + id + "_search";
        this.more_id = "more_main_menu_" + id;
        this.previous_timeout_id = null;
        this.current_search_position = null;
    }

    execute_search() {
        if (this.has_search_query()) {
            Search.kill_previous_search();
            add_class(document.getElementById(this.clear_id), "clearable");
            this.display_search_results();
            const obj = document.getElementById(this.search_id)!;
            add_class(obj, "search");
            g_call_ajax_obj = call_ajax(
                "ajax_search_" +
                    this.id +
                    ".py?q=" +
                    encodeURIComponent(this.get_current_input()),
                {
                    response_handler: Search.handle_search_response,
                    handler_data: {
                        obj: obj,
                        menu_popup: document.getElementById(
                            "popup_menu_" + this.id,
                        )!,
                    },
                },
            );
        } else {
            remove_class(document.getElementById(this.clear_id), "clearable");
            remove_class(document.getElementById(this.search_id), "search");
            this.display_menu_items();
        }
    }

    get_current_input() {
        return (document.getElementById(this.input_id) as HTMLInputElement)
            .value;
    }

    has_search_query() {
        // Search only for 2 or more characters
        return this.get_current_input().length > 1 ? true : false;
    }

    display_menu_items() {
        // Clear also the result list, as the popup resize mechanism is relying on finding only
        // ul's which corresponds to the main menu items
        document.getElementById(this.search_id)!.innerHTML = "";

        const more_button = document.getElementById(this.more_id);
        if (more_button) {
            remove_class(
                more_button.parentNode as HTMLElement | null,
                "hidden",
            );
        }
        remove_class(document.getElementById(this.content_id), "hidden");
    }

    display_search_results() {
        this.current_search_position = null;

        // The more button has currently no function in the search results, so hide it during
        // search in case it is available.
        const more_button = document.getElementById(this.more_id);
        if (more_button) {
            add_class(more_button.parentNode as HTMLElement | null, "hidden");
        }
        add_class(document.getElementById(this.content_id), "hidden");
    }

    static handle_search_response(
        handler_data: {obj: HTMLElement; menu_popup: HTMLElement},
        ajax_response: string,
    ) {
        const response: {
            result_code: number;
            result: string;
            severity: string;
        } = JSON.parse(ajax_response);
        if (response.result_code !== 0) {
            // TODO: Decide what to display in case of non-zero result code
            /* eslint-disable-next-line no-unsanitized/property -- Highlight existing violations CMK-17846 */
            handler_data.obj.innerHTML =
                "Ajax Call returned non-zero result code.";
        } else {
            /* eslint-disable-next-line no-unsanitized/property -- Highlight existing violations CMK-17846 */
            handler_data.obj.innerHTML = response.result;
            resize_main_menu_popup(handler_data.menu_popup);
        }
        return;
    }

    static kill_previous_search() {
        // Terminate eventually already running request
        if (g_call_ajax_obj) {
            g_call_ajax_obj.abort();
            g_call_ajax_obj = null;
        }
    }
}

// Let all current implemented searches be singletons
const monitoring_search = new Search("monitoring");
const setup_search = new Search("setup");

export function on_input_search(id: string) {
    const current_search: Search = get_current_search(id)!;
    if (current_search) {
        if (current_search.previous_timeout_id !== null) {
            clearTimeout(current_search.previous_timeout_id);
        }
        current_search.previous_timeout_id = window.setTimeout(function () {
            current_search.execute_search();
            resize_main_menu_popup(document.getElementById("popup_menu_" + id));
        }, 300);
        remove_class(
            document.getElementById("content_inner_" + id + "_search"),
            "extended_topic",
        );
    }
}

export function on_click_collapse_topic(topic: string) {
    const current_topic = document.getElementById(topic)!;
    const topic_results = current_topic.getElementsByTagName("li");
    remove_class(current_topic, "extended");
    add_class(current_topic, "extendable");
    remove_class(
        current_topic.closest(".content, .inner, .search"),
        "extended_topic",
    );
    Array.from(topic_results).forEach(li => {
        if (li.dataset.extended == "true") {
            li.dataset.extended = "false";
            add_class(li, "hidden");
        }
    });
    resize_main_menu_popup(current_topic.closest(".popup_menu_handler"));
}

export function on_click_show_all_results(
    topic: string,
    popup_menu_id: string,
) {
    const current_topic = document.getElementById(topic)!;
    const topic_results = current_topic.getElementsByTagName("li");
    remove_class(current_topic, "extendable");
    add_class(current_topic, "extended");
    add_class(
        current_topic.closest(".content, .inner, .search"),
        "extended_topic",
    );
    Array.from(topic_results).forEach(li => {
        if (li.dataset.extended == "false") {
            li.dataset.extended = "true";
            remove_class(li, "hidden");
        }
    });
    resize_main_menu_popup(document.getElementById(popup_menu_id));
}

function get_current_search(id: string) {
    let current_search: null | Search = null;

    switch (id) {
        case "monitoring":
            current_search = monitoring_search;
            break;
        case "setup":
            current_search = setup_search;
            break;
        default:
            console.log("The requested search is not implemented: " + id);
            break;
    }

    return current_search;
}

export function on_click_reset(id: string) {
    const current_search = get_current_search(id)!;
    if (current_search.has_search_query()) {
        (
            document.getElementById(current_search.input_id) as HTMLInputElement
        ).value = "";
        current_search.display_menu_items();
        remove_class(
            document.getElementById(current_search.clear_id),
            "clearable",
        );
    }
    remove_class(
        document.getElementById("content_inner_" + id + "_search"),
        "extended_topic",
    );
    resize_main_menu_popup(document.getElementById("popup_menu_" + id));
}

export function on_key_down(id: string) {
    const current_search = get_current_search(id);
    const current_key = (window.event as KeyboardEvent).key;

    if (!(current_key || current_search)) {
        return;
    }
    switch (current_key) {
        case "ArrowDown":
        case "ArrowUp":
            move_current_search_position(
                current_key == "ArrowDown" ? 1 : -1,
                current_search!,
            );
            event!.preventDefault();
            break;
        case "Enter":
            follow_current_search_query(current_search!);
            break;
        case "Escape":
            if (!current_search) return;
            if (current_search.has_search_query()) on_click_reset(id);
            else
                toggle_popup(
                    event,
                    this,
                    "main_menu_" + id,
                    {type: "inline"},
                    null,
                    null,
                    null,
                    false,
                );

            break;
    }
}

function follow_current_search_query(current_search: Search) {
    // Case 1: no specific result selected
    if (current_search.current_search_position === null) {
        // Regex endpoint for monitoring
        switch (current_search.id) {
            case "monitoring":
                //@ts-ignore
                top!.frames["main"].location.href =
                    "search_open.py?q=" +
                    encodeURIComponent(current_search.get_current_input());
                toggle_popup(
                    event,
                    this,
                    "main_menu_" + current_search.id,
                    {type: "inline"},
                    null,
                    null,
                    null,
                    false,
                );
                on_click_reset(current_search.id);
                break;
            default:
                // TODO: Implement ajax call for setup
                break;
        }
        return;
    }
    // Case 2: Click on the currently selected search result
    (
        document
            .getElementById(current_search.search_id)!
            .getElementsByTagName("li")
            [
                current_search.current_search_position
            ].getElementsByClassName("active")[0] as HTMLLIElement
    ).click();
    on_click_reset(current_search.id);
}

function move_current_search_position(step: number, current_search: Search) {
    if (current_search.current_search_position === null) {
        current_search.current_search_position = -1;
    }

    current_search.current_search_position += step;

    const result_list = document
        .getElementById(current_search.search_id)!
        .getElementsByTagName("li");
    if (!result_list) return;

    if (current_search.current_search_position < 0)
        current_search.current_search_position = result_list.length - 1;
    if (current_search.current_search_position > result_list.length - 1)
        current_search.current_search_position = 0;

    Array.from(result_list).forEach((value, idx) => {
        idx == current_search.current_search_position
            ? add_class(value.childNodes[0] as HTMLElement, "active")
            : remove_class(value.childNodes[0] as HTMLElement, "active");
    });
}
