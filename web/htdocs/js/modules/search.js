// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

import {call_ajax} from "ajax";
import {add_class, remove_class} from "utils";

var g_call_ajax_obj = null;

class Search {
    constructor(id) {
        this.id = id;
        this.content_id = "content_inner_" + id;
        this.search_id = "content_inner_" + id + "_search";
        this.input_id = "mk_side_search_field_" + id + "_search";
    }

    execute_search() {
        if (this.has_search_query()) {
            Search.kill_previous_search();
            this.show_results_div();
            const obj = document.getElementById(this.search_id);
            g_call_ajax_obj = call_ajax(
                "ajax_search_" + this.id + ".py?q=" + encodeURIComponent(this.get_current_input()),
                {
                    response_handler: Search.handle_search_response,
                    handler_data: {obj: obj},
                }
            );
        } else {
            this.hide_results_div();
        }
    }

    get_current_input() {
        return document.getElementById(this.input_id).value;
    }

    has_search_query() {
        return this.get_current_input().length > 0 ? true : false;
    }

    hide_results_div() {
        remove_class(document.getElementById(this.content_id), "hidden");
    }

    show_results_div() {
        add_class(document.getElementById(this.content_id), "hidden");
    }

    static handle_search_response(handler_data, ajax_response) {
        const response = JSON.parse(ajax_response);
        if (response.result_code !== 0) {
            // TODO: Decide what to display in case of non-zero result code
            handler_data.obj.innerHTML = "Ajax Call returned non-zero result code.";
        } else {
            handler_data.obj.innerHTML = response.result;
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

export function on_input_search(id) {
    let current_search = null;
    switch (id) {
        case "monitoring":
            current_search = monitoring_search;
            break;
        case "setup":
            current_search = setup_search;
            break;
        default:
            console.log("on_input_search called for non-implemented search!");
            break;
    }
    if (current_search) {
        current_search.execute_search();
    }
}
